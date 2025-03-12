import ast
import re
from itertools import islice
from multiprocessing import Process, Queue
from typing import List, Union

from datasets import Dataset, DatasetDict  # type: ignore[attr-defined]
from jinja2 import Template
from pydantic import BaseModel

from nearai.config import PROMPTS_FOLDER
from nearai.solvers import SolverStrategy


def get_function_name(code_str: str) -> str:
    parsed = ast.parse(code_str)
    function_name = None
    for node in ast.walk(parsed):
        if isinstance(node, ast.FunctionDef):
            function_name = node.name
            break
    assert function_name is not None, "No function definition found in code string."
    return function_name


def parse_python_code_block(answer_text: str) -> List[str]:
    pattern = r"```python\n(.*?)\n```"
    code_blocks = re.findall(pattern, answer_text, re.DOTALL)
    return code_blocks


def parse_code_block(answer_text: str) -> List[str]:
    pattern = r"```\n(.*?)\n```"
    code_blocks = re.findall(pattern, answer_text, re.DOTALL)
    return code_blocks


def run_code(code, queue):
    try:
        exec(code)
        queue.put(True)
    except Exception:
        queue.put(False)


def run_with_timeout(code, timeout=10):
    queue = Queue()
    process = Process(target=run_code, args=(code, queue))
    process.daemon = True
    process.start()

    try:
        return queue.get(timeout=timeout)
    except Exception:
        print("process.terminate()")
        process.terminate()
        return False


class MBPPDatum(BaseModel):
    task_id: int
    text: str
    code: str
    test_list: List[str]
    challenge_test_list: List[str]


class MBPPSolverStrategy(SolverStrategy):
    """Solver strategy for the MBPP dataset."""

    def __init__(  # noqa: D107
        self, dataset_ref: Union[Dataset, DatasetDict], model: str = "", agent: str = "", shots: int = 3
    ) -> None:
        super().__init__(model, agent)
        self.dataset_ref = dataset_ref
        self.shots = shots

    def evaluation_name(self) -> str:  # noqa: D102
        prefix = self.dataset_evaluation_name if self.dataset_evaluation_name else "mbpp"
        return f"{prefix}_{self.shots}shots"

    def compatible_datasets(self) -> List[str]:  # noqa: D102
        return ["mbpp"]

    def solve(self, datum: dict) -> bool:  # noqa: D102
        datum = MBPPDatum(**datum).model_dump()

        ## Allow LLM to think "out loud" for it's answer
        function_name = get_function_name(datum["code"])
        example_problems = list(islice(self.dataset_ref["prompt"], self.shots))
        base_prompt = Template(open(PROMPTS_FOLDER / "mbpp_verbose_answer.j2").read(), trim_blocks=True).render(
            function_name=function_name,
            example_problems=example_problems,
            challenge_problem=datum,
        )
        response = self.start_inference_session(str(datum["task_id"])).run_task(base_prompt)

        ## Extract the answer from the response
        extract_answer_prompt = Template(
            open(PROMPTS_FOLDER / "mbpp_extract_answer.j2").read(), trim_blocks=True
        ).render(
            function_name=function_name,
            answer_text=response,
        )
        response = self.start_inference_session(str(datum["task_id"])).run_task(extract_answer_prompt)

        ## Parse the python code
        python_code_blocks = parse_python_code_block(response) + parse_code_block(response)
        code = ""
        if len(python_code_blocks) == 0:
            code = response
        else:
            code = python_code_blocks[0]

        ## Evaluate the code
        try:
            for test in datum["test_list"] + datum["challenge_test_list"]:
                test_code = code + "\n" + test
                if not run_with_timeout(test_code):
                    return False
            return True
        except Exception:
            return False
