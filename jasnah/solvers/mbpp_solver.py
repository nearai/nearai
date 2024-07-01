import ast
import re
from itertools import islice

from jinja2 import Template
from openai.types.chat import ChatCompletion
from pydantic import BaseModel
from typing import Any, Callable, Dict, List, Type, Union
from datasets import Dataset, DatasetDict

from jasnah.solvers import SolverStrategy
from jasnah.config import CONFIG, PROMPTS_FOLDER
from jasnah.completion import InferenceRouter


class MBPPSolverStrategy(SolverStrategy):
    """
    Solver strategy for the MBPP dataset
    """

    SHOTS = 3

    def __init__(self, dataset_ref: Union[Dataset, DatasetDict], model):
        super().__init__()
        self.dataset_ref = dataset_ref
        self.completion_fn = InferenceRouter(CONFIG.llm_config).completions
        self.model = model

    def compatible_datasets(self) -> List[str]:
        return ["mbpp"]

    def solve(self, datum: dict) -> bool:
        def get_function_name(code_str: str) -> str:
            parsed = ast.parse(code_str)
            function_name = None
            for node in ast.walk(parsed):
                if isinstance(node, ast.FunctionDef):
                    function_name = node.name
                    break
            assert function_name is not None, "No function definition found in code string."
            return function_name

        def parse_python_code_block(answer_text: str) -> list[str]:
            pattern = r"```python\n(.*?)\n```"
            code_blocks = re.findall(pattern, answer_text, re.DOTALL)
            return code_blocks

        def parse_code_block(answer_text: str) -> list[str]:
            pattern = r"```\n(.*?)\n```"
            code_blocks = re.findall(pattern, answer_text, re.DOTALL)
            return code_blocks

        class MBPPDatum(BaseModel):
            task_id: int
            text: str
            code: str
            test_list: List[str]

        datum = MBPPDatum(**datum).model_dump()

        ## Allow LLM to think "out loud" for it's answer
        function_name = get_function_name(datum["code"])
        example_problems = list(islice(self.dataset_ref["prompt"], self.SHOTS))
        base_prompt = Template(open(PROMPTS_FOLDER / "mbpp_verbose_answer.j2").read(), trim_blocks=True).render(
            function_name=function_name,
            example_problems=example_problems,
            challenge_problem=datum,
        )
        completion_response: ChatCompletion = self.completion_fn(  # type: ignore
            self.model,
            messages=[
                {"role": "system", "content": base_prompt},
            ],
            temperature=0.0,
        )
        response = str(completion_response.choices[0].message.content)

        ## Extract the answer from the response
        extract_answer_prompt = Template(
            open(PROMPTS_FOLDER / "mbpp_extract_answer.j2").read(), trim_blocks=True
        ).render(
            function_name=function_name,
            answer_text=response,
        )
        completion_response = self.completion_fn(  # type: ignore
            self.model,
            messages=[
                {"role": "system", "content": extract_answer_prompt},
            ],
            temperature=0.0,
        )
        response = str(completion_response.choices[0].message.content)

        ## Parse the python code
        python_code_blocks = parse_python_code_block(response) + parse_code_block(response)
        code = ""
        if len(python_code_blocks) == 0:
            code = response
        else:
            code = python_code_blocks[0]

        ## Evaluate the code
        try:
            for test in datum["test_list"]:
                test_code = code + "\n" + test
                exec(test_code)
            return True
        except:
            return False
