import os
import random
import time
from typing import List, Union

from datasets import Dataset, DatasetDict  # type: ignore[attr-defined]

from nearai.agent import load_agent
from nearai.config import CONFIG
from nearai.environment import Environment
from nearai.solvers import SolverStrategy
from nearai.solvers.mbpp_solver import MBPPDatum, get_function_name


class MBPPSolverAgent(SolverStrategy):
    """Solver strategy for the MBPP dataset."""

    def __init__(  # noqa: D107
        self, dataset_ref: Union[Dataset, DatasetDict], agent: str, num_iterations: int = 16, verbose: bool = False
    ) -> None:
        super().__init__()
        self.dataset_ref = dataset_ref
        self.agent = load_agent(agent)
        self.verbose = verbose
        self.num_iterations = num_iterations

    def compatible_datasets(self) -> List[str]:  # noqa: D102
        return ["mbpp"]

    def solve(self, datum: dict) -> bool:  # noqa: D102
        datum = MBPPDatum(**datum).model_dump()
        function_name = get_function_name(datum["code"])

        path = os.path.join(
            "/tmp",
            "mbpp",
            str(datum["task_id"]),
            str(int(time.time() * 1000)),
            str(random.randint(0, 1000)),
        )
        CONFIG.confirm_commands = False
        env = Environment(path, [self.agent], CONFIG)

        new_line = "\n"
        task = f"""{datum["text"]}
Write a single file with python function named `{function_name}` that solves the above problem and satisfied the following tests:
```python\n{new_line.join(datum["test_list"])}\n```"""  # noqa: E501
        if self.verbose:
            print(task)
            print(path)
        env.run_task(task, max_iterations=self.num_iterations)

        code = ""
        for filename in env.list_files("."):
            if filename.endswith(".py"):
                code += env.read_file(filename) + "\n"

        try:
            for test in datum["test_list"] + datum["challenge_test_list"]:
                test_code = code + "\n" + test
                exec(test_code, {}, {})
            return True
        except Exception as e:
            if self.verbose:
                print(e)
            return False
