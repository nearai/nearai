from typing import Any, Dict, List, Optional, Union, cast

from datasets import Dataset, DatasetDict  # type: ignore[attr-defined]
from jinja2 import Template
from litellm import Choices, ModelResponse
from pydantic import BaseModel
from shared.client_config import DEFAULT_PROVIDER, ClientConfig
from shared.inference_client import InferenceClient
from shared.near.primitives import get_provider_model

from nearai.config import CONFIG, PROMPTS_FOLDER
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

    SHOTS = 8

    def __init__(self, dataset_ref: Union[Dataset, DatasetDict], model: str) -> None:  # noqa: D107
        super().__init__()
        self.dataset_ref = dataset_ref
        client_config = ClientConfig(base_url=CONFIG.nearai_hub.base_url, auth=CONFIG.auth)
        self.completion_fn = InferenceClient(client_config).completions
        self.model = model

    def evaluation_name(self) -> str:  # noqa: D102
        return "hellaswag"

    def compatible_datasets(self) -> List[str]:  # noqa: D102
        return ["hellaswag"]

    def model_metadata(self) -> Optional[Dict[str, Any]]:  # noqa: D102
        return {"name": self.model}

    def agent_metadata(self) -> Optional[Dict[str, Any]]:  # noqa: D102
        return None

    def evaluated_entry_namespace(self) -> str:  # noqa: D102
        # Only provider models are supported.
        return ""

    def model_provider(self) -> str:  # noqa: D102
        provider, _ = get_provider_model(DEFAULT_PROVIDER, self.model)
        return provider

    def solve(self, datum: dict) -> bool:  # noqa: D102
        datum = HellaswagDatum(**datum).model_dump()

        choices = ["A", "B", "C", "D"]
        example_problems_indices = list(range(0, 5 * self.SHOTS, 5))
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
        completion_response = cast(
            ModelResponse,
            self.completion_fn(
                self.model,
                messages=[
                    {"role": "system", "content": base_prompt},
                ],
                temperature=0.0,
            ),
        )
        response = str(cast(List[Choices], completion_response.choices)[0].message.content)

        ## Extract the answer from the response
        extract_answer_prompt = Template(
            open(PROMPTS_FOLDER / "hellaswag_extract_answer.j2").read(),
            trim_blocks=True,
        ).render(
            challenge_problem=datum,
            answer_text=response,
            choices=choices,
        )
        completion_response = cast(
            ModelResponse,
            self.completion_fn(
                self.model,
                messages=[
                    {"role": "system", "content": extract_answer_prompt},
                ],
                temperature=0.0,
            ),
        )
        response = str(cast(List[Choices], completion_response.choices)[0].message.content)

        try:
            answer = choices.index(response)
            return bool(answer == int(datum["label"]))
        except Exception:
            print("Failed to parse answer")
            return False
