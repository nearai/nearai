from typing import List, Union

from datasets import Dataset, DatasetDict  # type: ignore[attr-defined]
from jinja2 import Template
from pydantic import BaseModel

from nearai.config import PROMPTS_FOLDER
from nearai.solvers import SolverStrategy


class MMLUDatum(BaseModel):
    question: str
    subject: str
    choices: List[str]
    answer: int


class MMLUSolverStrategy(SolverStrategy):
    """Solver strategy for the MMLU dataset."""

    def __init__(  # noqa: D107
        self, dataset_ref: Union[Dataset, DatasetDict], model: str = "", agent: str = "", shots: int = 8
    ) -> None:
        super().__init__(model, agent)
        self.dataset_ref = dataset_ref
        self.shots = shots

    def evaluation_name(self) -> str:  # noqa: D102
        prefix = self.dataset_evaluation_name if self.dataset_evaluation_name else "mmlu"
        return f"{prefix}_{self.shots}shots"

    def compatible_datasets(self) -> List[str]:  # noqa: D102
        return ["mmlu"]

    def solve(self, datum: dict) -> bool:  # noqa: D102
        datum = MMLUDatum(**datum).model_dump()

        choices = ["A", "B", "C", "D"]
        example_problems_indices = list(range(0, 5 * self.shots, 5))
        example_problems = list(
            map(
                lambda d: MMLUDatum(**d).model_dump(),
                [self.dataset_ref["dev"][i] for i in example_problems_indices],
            )
        )
        base_prompt = Template(open(PROMPTS_FOLDER / "mmlu_verbose_answer.j2").read(), trim_blocks=True).render(
            example_problems=example_problems,
            challenge_problem=datum,
            choices=choices,
        )

        response = self.start_inference_session("").run_task(base_prompt)

        ## Extract the answer from the response
        extract_answer_prompt = Template(
            open(PROMPTS_FOLDER / "mmlu_extract_answer.j2").read(), trim_blocks=True
        ).render(
            challenge_problem=datum,
            answer_text=response,
            choices=choices,
        )
        response = self.start_inference_session("").run_task(extract_answer_prompt)

        try:
            answer = choices.index(response)
            return bool(answer == datum["answer"])
        except Exception:
            print("Failed to parse answer")
            return False
