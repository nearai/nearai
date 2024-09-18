from textwrap import dedent
from typing import Any, Dict, List, Optional, Union, cast

from datasets import Dataset, DatasetDict  # type: ignore[attr-defined]
from litellm import Choices, ModelResponse
from pydantic import BaseModel
from shared.client_config import DEFAULT_PROVIDER, ClientConfig
from shared.inference_client import InferenceClient
from shared.near.primitives import get_provider_model

from nearai.config import CONFIG
from nearai.solvers import SolverStrategy


class GSM8KDatum(BaseModel):
    question: str
    answer: str


class GSM8KSolverStrategy(SolverStrategy):
    """Solver strategy for the GSM8K dataset."""

    SHOTS = 8

    def __init__(self, dataset_ref: Union[Dataset, DatasetDict], model: str) -> None:  # noqa: D107
        super().__init__()
        self.dataset_ref = dataset_ref
        client_config = ClientConfig(base_url=CONFIG.nearai_hub.base_url, auth=CONFIG.auth)
        self.completion_fn = InferenceClient(client_config).completions
        self.model = model

    def evaluation_name(self) -> str:  # noqa: D102
        return "gsm8k"

    def compatible_datasets(self) -> List[str]:  # noqa: D102
        return ["gsm8k"]

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
        parsed_datum: GSM8KDatum = GSM8KDatum(**datum)

        problem_shots_indices = list(range(0, self.SHOTS))
        problem_shots = list(
            map(
                lambda i: GSM8KDatum(**self.dataset_ref["train"][i]).model_dump(),
                problem_shots_indices,
            )
        )
        res: ModelResponse = cast(
            ModelResponse,
            self.completion_fn(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": dedent(
                            """
                    You are a helpful assistant. You're goal is to answer word based math questions.
                    """
                            + "\n\n"
                            + "Here are some examples of math questions and their answers:"
                            + "\n\n".join(
                                [f"Question: {shot['question']}\nAnswer: {shot['answer']}" for shot in problem_shots]
                            )
                            + "\n\n"
                            + "Now, answer the next question provided in the user prompt. "
                            + "Think step by step about how to solve the problem. "
                            + "Then, provide the answer."
                        ),
                    },
                    {"role": "user", "content": parsed_datum.question},
                ],
            ),
        )
        res_output = str(cast(List[Choices], res.choices)[0].message.content).strip()
        res_refined: ModelResponse = cast(
            ModelResponse,
            self.completion_fn(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": dedent(
                            f"""
                    You are a helpful assistant. You're goal is to answer math questions.

                    You have just answered a math question with the following response:

                    --- BEGIN RESPONSE ---
                    {res_output}
                    --- END RESPONSE ---

                    Please refine your answer.

                    Only output the final number *without units* as your answer. Nothing else.
                    """
                        ),
                    },
                ],
            ),
        )

        ## cleanup the output
        res_refined_output = str(cast(List[Choices], res_refined.choices)[0].message.content).strip()
        res_refined_output = res_refined_output.replace("$", "").replace(",", "")
        if " " in res_refined_output:
            res_refined_output = res_refined_output.split(" ")[0]
        try:
            res_refined_output = str(int(res_refined_output))
        except Exception:
            pass
        try:
            res_refined_output = str(int(float(res_refined_output)))
        except Exception:
            pass

        refined_answer = parsed_datum.answer.replace("$", "").replace(",", "")
        print(res_refined_output, refined_answer)
        return res_refined_output == refined_answer
