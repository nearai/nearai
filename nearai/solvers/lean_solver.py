import json
from dataclasses import dataclass
from typing import List, Tuple, Union

from datasets import Dataset, DatasetDict
from jinja2 import Template  # type: ignore[attr-defined]
from lean_dojo import Dojo, LeanGitRepo, ProofFinished, TacticState, Theorem  # type: ignore
from pydantic import BaseModel

from nearai.config import PROMPTS_FOLDER
from nearai.dataset import get_dataset
from nearai.solvers import SolverStrategy

BEGIN_MARKER = "BEGIN"
END_MARKER = "END"


class LeanDatum(BaseModel):
    url: str
    commit: str
    filename: str
    theorem: str


@dataclass
class LeanTaskInfo:
    url: str
    commit: str
    filename: str
    theorem: str
    theorem_raw: str


def extract_between_markers(text: str) -> str:
    try:
        start_pos = text.index(BEGIN_MARKER) + len(BEGIN_MARKER)
        end_pos = text.index(END_MARKER, start_pos)
        return text[start_pos:end_pos].strip()
    except ValueError:
        print(f"Could not extract solution from {text}")
        return ""


def parse_tactics(json_str: str) -> List[str]:
    try:
        # Parse JSON string
        data = json.loads(json_str)

        # Check if tactics key exists
        if "tactics" not in data:
            print(f"JSON must contain 'tactics' key. json: {json_str}")
            return []

        tactics_array = data["tactics"]

        # Validate tactics array
        if not isinstance(tactics_array, list):
            print(f"'tactics' must be an array. json: {json_str}")
            return []

        # Extract tactic strings
        result = []
        for item in tactics_array:
            if isinstance(item, str):
                result.append(item)
                continue
            if not isinstance(item, dict) or "tactic" not in item:
                print(f"Each tactic item must be an object with 'tactic' key. json: {json_str}")
                return []
            result.append(item["tactic"])

        return result

    except json.JSONDecodeError as e:
        print(f"Invalid JSON string: {str(e)}. json: {json_str}")
        return []


def load_theorem(task: LeanDatum) -> str:
    """Use local copy of the repository."""
    repo = LeanGitRepo(task.url, task.commit)
    theorem = Theorem(repo, task.filename, task.theorem)
    with Dojo(theorem) as (_, state):
        return state.pp


def load_repository(url: str) -> str:
    if url == "https://github.com/yangky11/miniF2F-lean4":
        return str(get_dataset("au.near/github_com_yangky11_miniF2F-lean4/0.0.1", verbose=False))

    print(
        "Repository not found on the registry. You need to setup Github credentials to download repository. See https://leandojo.readthedocs.io/en/latest/getting-started.html#"
    )
    return url


def check_solution(task: LeanDatum, solution: List[str]) -> Tuple[bool, str]:
    for tactic in solution:
        if "sorry" in tactic:
            m = "sorry in tactic is not allowed."
            print(m)
            return False, m

    repo = LeanGitRepo(task.url, task.commit)
    theorem = Theorem(repo, task.filename, task.theorem)

    m = "No tactics run."
    with Dojo(theorem) as (dojo, state):
        for tactic in solution:
            result = dojo.run_tac(state, tactic)
            m = str(result)

            if isinstance(result, TacticState):
                state = result
            elif isinstance(result, ProofFinished):
                return True, m
            else:
                return False, m

    return False, m


class LeanSolverStrategy(SolverStrategy):
    """Solver strategy to evaluate against Lean problems."""

    def __init__(  # noqa: D107
        self, dataset_ref: Union[Dataset, DatasetDict], model: str = "", agent: str = ""
    ) -> None:
        super().__init__(model, agent)

    def evaluation_name(self) -> str:  # noqa: D102
        assert self.dataset_evaluation_name
        return self.dataset_evaluation_name

    def compatible_datasets(self) -> List[str]:  # noqa: D102
        return ["lean"]

    def solve(self, datum: dict) -> Tuple[bool, dict]:  # noqa: D102
        lean_datum = LeanDatum.model_validate(datum)
        lean_datum.url = load_repository(lean_datum.url)

        info: dict = {}
        info["verbose"] = {}

        lean_task = LeanTaskInfo(
            lean_datum.url,
            lean_datum.commit,
            lean_datum.filename,
            lean_datum.theorem,
            load_theorem(lean_datum),
        )
        info["verbose"]["theorem_raw"] = lean_task.theorem_raw

        base_prompt = Template(open(PROMPTS_FOLDER / "lean_answer.j2").read(), trim_blocks=True).render(
            url=lean_task.url,
            commit=lean_task.commit,
            filepath=lean_task.filename,
            theorem_name=lean_task.theorem,
            theorem_raw=lean_task.theorem_raw,
            begin_marker=BEGIN_MARKER,
            end_marker=END_MARKER,
        )
        response = self.start_inference_session("").run_task(base_prompt)

        json_response = extract_between_markers(response)
        if not json_response:
            info["error"] = "Failed to extract between markers."
            info["verbose"]["response"] = response
            return False, info

        tactics = parse_tactics(json_response)
        if not tactics:
            info["error"] = "Failed to parse tactics."
            info["verbose"]["response"] = json_response
            return False, info

        # Sometimes, there are timeout errors.
        num_attempts = 3
        info["tactics"] = tactics
        for i in range(0, num_attempts):
            if i != 0:
                info["check_solution_attempts"] = f"{i + 1} (max: {num_attempts})"
            try:
                r, m = check_solution(lean_datum, tactics)
                if r:
                    info["verbose"]["check_solution_message"] = m
                else:
                    info["check_solution_message"] = m
                return r, info
            except Exception as e:
                if i == num_attempts - 1:
                    error_message = f"Exception while checking solution: {str(e)}."
                    print(error_message)
                    info["error"] = error_message
        return False, info
