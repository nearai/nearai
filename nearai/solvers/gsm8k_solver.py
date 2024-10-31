from textwrap import dedent
from typing import List, Union

from datasets import Dataset, DatasetDict  # type: ignore[attr-defined]
from pydantic import BaseModel

from nearai.solvers import SolverStrategy


class GSM8KDatum(BaseModel):
    question: str
    answer: str


class GSM8KSolverStrategy(SolverStrategy):
    """Solver strategy for the GSM8K dataset."""

    SHOTS = 8

    def __init__(self, dataset_ref: Union[Dataset, DatasetDict], model: str = "", agent: str = "") -> None:  # noqa: D107
        super().__init__(model, agent)
        self.dataset_ref = dataset_ref

    def evaluation_name(self) -> str:  # noqa: D102
        return "gsm8k"

    def compatible_datasets(self) -> List[str]:  # noqa: D102
        return ["gsm8k"]

    def solve(self, datum: dict) -> bool:  # noqa: D102
        parsed_datum: GSM8KDatum = GSM8KDatum(**datum)

        problem_shots_indices = list(range(0, self.SHOTS))
        problem_shots = list(
            map(
                lambda i: GSM8KDatum(**self.dataset_ref["train"][i]).model_dump(),
                problem_shots_indices,
            )
        )

        session = self.start_inference_session("")
        session.add_system_message(
            dedent(
                """
                    You are a helpful assistant. You're goal is to answer word based math questions.
                    """
                + "\n\n"
                + "Here are some examples of math questions and their answers:"
                + "\n\n".join([f"Question: {shot['question']}\nAnswer: {shot['answer']}" for shot in problem_shots])
                + "\n\n"
                + "Now, answer the next question provided in the user prompt. "
                + "Think step by step about how to solve the problem. "
                + "Then, provide the answer."
            )
        )
        res_output = session.run_task(parsed_datum.question).strip()

        ## cleanup the output
        session = self.start_inference_session("")
        res_refined_output = session.run_task(
            dedent(
                f"""
                    You are a helpful assistant. You're goal is to answer math questions.

                    You have just answered a math question with the following response:

                    --- BEGIN RESPONSE ---
                    {res_output}
                    --- END RESPONSE ---

                    Please refine your answer.

                    Only output the final number *without units* as your answer. Nothing else.
                    """
            )
        ).strip()
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
