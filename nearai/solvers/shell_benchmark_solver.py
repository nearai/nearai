# NearAI custom shell benchmark.
# Data columns:
# - `input`: input task given to an agent.
# - `question`: the question in input; it's used by a solver to determine whether the question was answered,
#               and only if `response` is present.
# - `input_file`: a solver will add this file before running agent.
# - `input_file_content`: content of `input_file`.
# - `steps`: number of steps an agent is expected to take to solve this task.
# - `response`: expected response, if any.
# - `output_file`: expected output file, if any.
# - `output_file_content`: expected content of `output_file`.

import os
from datetime import date, datetime
from typing import List, Union

import pytz
from datasets import Dataset, DatasetDict  # type: ignore[attr-defined]
from pydantic import BaseModel

from nearai.solvers import SolverInferenceSession, SolverStrategy


class ShellTaskDatum(BaseModel):
    input: str
    question: str
    input_file: str
    input_file_content: str
    response: str
    output_file: str
    output_file_content: str
    steps: str


class ShellBenchmarkSolverStrategy(SolverStrategy):
    """Solver strategy for the nearai shell dataset."""

    def __init__(self, dataset_ref: Union[Dataset, DatasetDict], model: str = "", agent: str = "") -> None:  # noqa: D107
        super().__init__(model, agent)
        self.dataset_ref = dataset_ref

    def evaluation_name(self) -> str:  # noqa: D102
        return "nearai_shell"

    def compatible_datasets(self) -> List[str]:  # noqa: D102
        return ["shell_benchmark"]

    def _run_task(  # noqa: D102
        self,
        session: SolverInferenceSession,
        task: str,
        max_steps: int,
        correct_answer: str,
        question: str,
        max_iterations: int = 10,
    ) -> str:
        response = session.run_task(task)
        if not session.env:
            return response

        num_iterations = 1
        num_steps = 0
        num_messages_parsed = len(session.env.list_messages())
        print(response)
        while not session.env.is_done() and num_iterations < max_iterations:
            messages = session.env.list_messages()
            num_messages = len(messages)
            last_message = messages[num_messages - 1]
            if last_message["role"] == "assistant":
                num_steps = num_steps + 1
                if num_steps == max_steps:
                    return response

            if correct_answer != "" and self._is_response(question, response):
                return response

            session.env.run(max_iterations=1)
            num_iterations = num_iterations + 1

            messages = session.env.list_messages()
            num_messages = len(messages)
            output = []
            for i in range(num_messages_parsed, num_messages):
                if messages[i]["role"] == "assistant":
                    output.append(messages[i]["content"])
            response = "\n".join(output)
            print(response)
            num_messages_parsed = num_messages

        return response

    def _is_response(self, question: str, response: str) -> bool:
        session = self.start_inference_session("")
        question = f"Is '{response}' an answer (and not a command to get an answer) to a question '{question}' (it does not matter if it is a correct answer or not)? Respond with either 'yes' or 'no' and nothing else."  # noqa: E501
        answer = session.run_task(question)
        print(f"[question] {question} [answer] {answer}")
        return answer == "yes"

    def _is_good_response(self, response: str, correct_answer: str) -> bool:
        response = response.strip()
        correct_answer = correct_answer.strip()

        if correct_answer == "<date>":
            current_date = date.today()
            session = self.start_inference_session("")
            return (
                session.run_task(
                    f"Are '{response}' and '{current_date}' represent the same date? Respond with either 'yes' or 'no' and nothing else."  # noqa: E501
                )
                == "yes"
            )

        if correct_answer == "<day_of_week>":
            current_date = date.today()
            day_of_week = current_date.strftime("%A")
            session = self.start_inference_session("")
            return (
                session.run_task(
                    f"Are '{response}' and '{day_of_week}' represent the same day of week? Respond with either 'yes' or 'no' and nothing else."  # noqa: E501
                )
                == "yes"
            )

        if correct_answer == "<utc_time>":
            utc_time = datetime.now(pytz.UTC).strftime("%H:%M")
            session = self.start_inference_session("")
            return (
                session.run_task(
                    f"Are times '{response}' and '{utc_time}' within few minutes? Respond with either 'yes' or 'no' and nothing else."  # noqa: E501
                )
                == "yes"
            )

        if correct_answer == "<local_time>":
            local_time = datetime.now().strftime("%H:%M")
            session = self.start_inference_session("")
            return (
                session.run_task(
                    f"Are times '{response}' and '{local_time}' within few minutes? Respond with either 'yes' or 'no' and nothing else."  # noqa: E501
                )
                == "yes"
            )

        return response == correct_answer

    def solve(self, datum: dict) -> bool:  # noqa: D102
        task = ShellTaskDatum(**datum)
        print("-----------------------------------------------------------------------------------------------------")
        print(f"[input] {task.input}")

        session = self.start_inference_session("")
        print(f"[path] {session.path}")

        steps = 1
        if task.steps:
            steps = int(task.steps)
        question = task.input
        if task.question:
            question = task.question
        if task.input_file:
            file_path = os.path.join(session.path, task.input_file)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(os.path.join(session.path, task.input_file), "w") as f:
                f.write(task.input_file_content)

        try:
            response = self._run_task(session, task.input, steps, task.response, question)
        except Exception as e:
            print(f"{e}")
            return False

        if task.response:
            if not self._is_good_response(response, task.response):
                return False

        if task.output_file:
            if not os.path.exists(os.path.join(session.path, task.output_file)):
                return False
            if task.output_file_content:
                with open(os.path.join(session.path, task.output_file), "r") as f:
                    if f.read().strip() != task.output_file_content:
                        return False

        print("Correct")
        return True
