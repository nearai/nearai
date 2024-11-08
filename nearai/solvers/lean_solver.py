import json
from dataclasses import dataclass
from typing import List, Union

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


def check_solution(task: LeanDatum, solution: List[str]) -> bool:
    for tactic in solution:
        if "sorry" in tactic:
            print("sorry in tactic is not allowed.")
            return False

    repo = LeanGitRepo(task.url, task.commit)
    theorem = Theorem(repo, task.filename, task.theorem)

    with Dojo(theorem) as (dojo, state):
        for tactic in solution:
            result = dojo.run_tac(state, tactic)

            if isinstance(result, TacticState):
                state = result
            elif isinstance(result, ProofFinished):
                return True
            else:
                return False

    return False


class LeanSolverStrategy(SolverStrategy):
    """Solver strategy to evaluate against Lean problems."""

    def __init__(  # noqa: D107
        self, dataset_ref: Union[Dataset, DatasetDict], model: str = "", agent: str = ""
    ) -> None:
        super().__init__(model, agent)

    def evaluation_name(self) -> str:  # noqa: D102
        return "nearai_lean"

    def compatible_datasets(self) -> List[str]:  # noqa: D102
        return ["lean"]

    def solve(self, datum: dict) -> bool:  # noqa: D102
        lean_datum = LeanDatum.model_validate(datum)
        lean_datum.url = load_repository(lean_datum.url)

        lean_task = LeanTaskInfo(
            lean_datum.url,
            lean_datum.commit,
            lean_datum.filename,
            lean_datum.theorem,
            load_theorem(lean_datum),
        )

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

        response = extract_between_markers(response)
        if not response:
            return False

        tactics = parse_tactics(response)
        if not tactics:
            return False

        return check_solution(lean_datum, tactics)
