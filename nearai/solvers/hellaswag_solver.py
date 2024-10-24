from typing import List, Union

from datasets import Dataset, DatasetDict  # type: ignore[attr-defined]
from jinja2 import Template
from pydantic import BaseModel

from nearai.config import PROMPTS_FOLDER
from nearai.solvers import SolverStrategy


class HellaswagDatum(BaseModel):
    activity_label: str
    ctx: str
    ctx_a: str
    ctx_b: str
    endings: List[str]
    ind: int
    label: str
    source_id: str
    split: str
    split_type: str


class HellaswagSolverStrategy(SolverStrategy):
    """Solver strategy for the MMLU dataset."""

    def __init__(  # noqa: D107
        self, dataset_ref: Union[Dataset, DatasetDict], model: str = "", agent: str = "", shots: int = 8
    ) -> None:
        super().__init__(model, agent)
        self.dataset_ref = dataset_ref
        self.shots = shots

    def evaluation_name(self) -> str:  # noqa: D102
        return f"hellaswag_{self.shots}shots"

    def compatible_datasets(self) -> List[str]:  # noqa: D102
        return ["hellaswag"]

    def solve(self, datum: dict) -> bool:  # noqa: D102
        datum = HellaswagDatum(**datum).model_dump()

        choices = ["A", "B", "C", "D"]
        example_problems_indices = list(range(0, 5 * self.shots, 5))
        example_problems = list(
            map(
                lambda d: HellaswagDatum(**d).model_dump(),
                [self.dataset_ref["validation"][i] for i in example_problems_indices],
            )
        )
        base_prompt = Template(
            open(PROMPTS_FOLDER / "hellaswag_verbose_answer.j2").read(),
            trim_blocks=True,
        ).render(
            example_problems=example_problems,
            challenge_problem=datum,
            choices=choices,
        )
        response = self.start_inference_session("").run_task(base_prompt)

        ## Extract the answer from the response
        extract_answer_prompt = Template(
            open(PROMPTS_FOLDER / "hellaswag_extract_answer.j2").read(),
            trim_blocks=True,
        ).render(
            challenge_problem=datum,
            answer_text=response,
            choices=choices,
        )
        response = self.start_inference_session("").run_task(extract_answer_prompt)

        try:
            answer = choices.index(response)
            return bool(answer == int(datum["label"]))
        except Exception:
            print("Failed to parse answer")
            return False
