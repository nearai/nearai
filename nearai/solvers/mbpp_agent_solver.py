import os
import random
import time
from typing import Any, Dict, List, Optional, Union

from datasets import Dataset, DatasetDict  # type: ignore[attr-defined]
from shared.client_config import DEFAULT_PROVIDER, ClientConfig
from shared.inference_client import InferenceClient

from nearai.agents.environment import Environment
from nearai.agents.local_runner import LocalRunner
from nearai.config import CONFIG
from nearai.solvers import SolverStrategy
from nearai.solvers.mbpp_solver import MBPPDatum, get_function_name


class MBPPSolverAgent(SolverStrategy):
    """Solver strategy for the MBPP dataset."""

    def __init__(  # noqa: D107
        self, dataset_ref: Union[Dataset, DatasetDict], agent: str, num_iterations: int = 16, verbose: bool = False
    ) -> None:
        super().__init__()
        self.dataset_ref = dataset_ref
        self.agent = LocalRunner.load_agent(agent)
        self.verbose = verbose
        self.num_iterations = num_iterations

    def evaluation_name(self) -> str:  # noqa: D102
        return "mbpp"

    def compatible_datasets(self) -> List[str]:  # noqa: D102
        return ["mbpp"]

    def model_metadata(self) -> Optional[Dict[str, Any]]:  # noqa: D102
        # TODO: we may want to return the model used by an agent here.
        return None

    def agent_metadata(self) -> Optional[Dict[str, Any]]:  # noqa: D102
        return self.agent.metadata

    def evaluated_entry_namespace(self) -> str:  # noqa: D102
        return self.agent.namespace

    def model_provider(self) -> str:  # noqa: D102
        # TODO: we may want to return the provider used by an agent here.
        return DEFAULT_PROVIDER

    def solve(self, datum: dict) -> bool:  # noqa: D102
        datum = MBPPDatum(**datum).model_dump()
        function_name = get_function_name(datum["code"])

        client_config = ClientConfig(
            base_url=CONFIG.nearai_hub.base_url,
            auth=CONFIG.auth,
        )
        client = InferenceClient(client_config)

        path = os.path.join(
            "/tmp",
            "mbpp",
            str(datum["task_id"]),
            str(int(time.time() * 1000)),
            str(random.randint(0, 1000)),
        )
        env = Environment(
            path,
            [self.agent],
            client,
            approvals={"confirm_execution": lambda _: False},
        )
        new_line = "\n"
        task = f"""{datum["text"]}
Write a single file with python function named `{function_name}` that solves the above problem and satisfied the following tests:
```python\n{new_line.join(datum["test_list"])}\n```"""  # noqa: E501
        if self.verbose:
            print(task)
            print(path)
        env.run(task, max_iterations=self.num_iterations)

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
