import asyncio
import random
import enum
from copy import deepcopy
from datetime import datetime
from tempfile import TemporaryDirectory
from typing import List, Tuple

import httpx as hx
import tenacity

from jasnah.agent import load_agent
from jasnah.config import CONFIG,DATA_FOLDER
from jasnah.dataset import Dataset
from jasnah.environment import Environment

from . import SolverStrategy

DDOTS_URL = "http://35.172.184.84:8880/"


class Extensions(enum.Enum):
    PYTHON = "py"
    CPP = "cpp"
    JAVA = "java"
    JAVASCRIPT = "js"

@tenacity.retry(
    wait=tenacity.wait_fixed(1.0),
    stop=tenacity.stop_after_delay(600.0),
    retry=tenacity.retry_if_result(lambda result: result is False),
)
async def is_output_ready(submission_id: str) -> bool:
    async with hx.AsyncClient() as hx_client:
        response = await hx_client.post(
            DDOTS_URL + "api/checker/is_output_ready/",
            data={"submission_id": submission_id},
        )
        return response.content == b"True"


async def get_output(submission_id: str) -> str:
    async with hx.AsyncClient() as hx_client:
        response = await hx_client.post(
            DDOTS_URL + "api/checker/get_output/",
            data={"submission_id": submission_id},
        )
        return response.content.decode("utf-8")


async def submission_accepted(submission_id: str) -> bool:
    async with hx.AsyncClient() as hx_client:
        response = await hx_client.post(
            DDOTS_URL + "api/checker/get_status/",
            data={"submission_id": submission_id},
        )
        return response.content.decode("utf-8") == "1"


async def submit_problem(problem_id: str, code: str, extension: Extensions) -> str:
    async with hx.AsyncClient() as hx_client:
        response = await hx_client.post(
            DDOTS_URL + "api/checker/submit/",
            data={
                "problem_id": problem_id,
                "code": code,
                "extension": extension.value,
                "input": "",
            },
        )
        submission_id = response.content.decode("utf-8")
        return submission_id


class DDOTSEnvironment(Environment):
    def __init__(self, agents: List['Agent'],  problem_id: str, description: str, config):
        self.tdir = TemporaryDirectory()
        super().__init__(self.tdir.name, agents, config)

        self.problem_id = problem_id
        self.solved = False

        files = {'.id': problem_id, 'PROBLEM.txt': description, 'solution.py': '', 'test.in': '', 'test.sh': '#!/bin/bash\npython3 solution.py < test.in'}
        for fname, content in files.items():
            with open(self.tdir.name + '/' + fname, 'w') as f:
                f.write(content)

    async def async_submit(self, code):
        submission_id = await submit_problem(self.problem_id, code, Extensions.PYTHON)

        try:
            await is_output_ready(submission_id)
        except:
            print("WARNING: Submission took too long to execute on DDOTS")
            self.mark_done()
            return False, 'Submission took too long to execute on the platform'

        ok = await submission_accepted(submission_id)

        if ok:
            self.solved = True
            self.mark_done()
            return True, ''

        output = await get_output(submission_id)

        return False, output

    def submit_python(self, code) -> Tuple[bool, str]:
        """
        Returns True if the submission was accepted, False otherwise.

        The second element of the tuple is the output of the checker if the submission was rejected.
        """
        return asyncio.run(self.async_submit(code))


class DDOTSV0Solver(SolverStrategy):
    """
    Solver strategy for competitive programming problems live on DDOTS.

    This dataset will run agents in an Agent environment previously prepared.

    workspace/
        .id             -- Id of the problem
        PROBLEM.txt     -- Description of the problem

    The agent should call env.submit_python(code) to submit the code to the DDOTS server.

    """
    def __init__(self, dataset_ref: Dataset, agents: str, max_iterations: int, save_snapshots: bool = False):
        self.agents = [load_agent(agent) for agent in agents.split(",")]
        self.max_iterations = max_iterations

        date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        rnd_id = random.randint(10**8, 10**9-1)
        self._saved_trajectories = DATA_FOLDER / 'data' / 'ddots_v0_trajectories' / f'{date}_{rnd_id}'
        self._saved_trajectories.mkdir(parents=True, exist_ok=True)

        self.save_snapshots = save_snapshots
        print("Saving trajectories to", self._saved_trajectories)

    def compatible_datasets(self) -> List[str]:
        return ["ddots_codeforces_small/v0", "datasets/ddots_codeforces_medium_A_B/v0"]

    def solve(self, datum: dict) -> bool:
        problem_id = datum['problem_id']
        description = datum['description']

        config = deepcopy(CONFIG.llm_config)
        config['confirm_commands'] = False

        env = DDOTSEnvironment(self.agents, problem_id, description, config)
        env.write_file(".solved", str(False))

        try:
            env.run_task(description, max_iterations=self.max_iterations)
            env.write_file(".solved", str(env.solved))

        except Exception as e:
            print(f"Error running task: {e}")

        finally:
            if self.save_snapshots:
                snapshot = env.create_snapshot()
                with open(self._saved_trajectories / f'{problem_id}.tar.gz', 'wb') as f:
                    f.write(snapshot)

        return env.solved