import csv
import glob
import json
import os
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import shortuuid  # type: ignore
from litellm import Choices, ModelResponse
from litellm.types.completion import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from shared.client_config import DEFAULT_PROVIDER, ClientConfig
from shared.inference_client import InferenceClient
from shared.near.primitives import get_provider_model
from tqdm import tqdm

from nearai.config import CONFIG
from nearai.solvers import (
    SolverScoringMethod,
    SolverStrategy,
    SolverStrategyClassProperty,
)

MessageType = Union[
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam,
]


def convert_message(message: Dict[str, Any]) -> MessageType:
    role = message["role"]
    content = message["content"]

    if role == "system":
        return {"role": "system", "content": content}
    elif role == "user":
        return {"role": "user", "content": content}
    elif role == "assistant":
        return {"role": "assistant", "content": content}
    else:
        raise ValueError(f"Unexpected role: {role}")


def load_questions_jsonl(question_file: str):
    questions = []
    with open(question_file, "r") as ques_file:
        for line in ques_file:
            if line:
                questions.append(json.loads(line))
    return questions


class LiveBenchSolverStrategy(SolverStrategy):
    """Solver strategy for the live bench dataset."""

    def __init__(  # noqa: D107
        self, dataset_ref: str, model: str, step: str = "all"
    ) -> None:
        super().__init__()
        self.dataset_ref = dataset_ref
        client_config = ClientConfig(base_url=CONFIG.nearai_hub.base_url, auth=CONFIG.auth)
        self.completion_fn = InferenceClient(client_config).completions
        assert "/" not in model
        self.model = model
        self.step = step

    def evaluation_name(self) -> str:  # noqa: D102
        return "live_bench"

    def compatible_datasets(self) -> List[str]:  # noqa: D102
        return ["near.ai/live_bench/1.0.0"]

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

    def get_custom_tasks(self) -> List[dict]:  # noqa: D102
        return [{"summary": "all"}]

    @SolverStrategyClassProperty
    def scoring_method(self) -> SolverScoringMethod:  # noqa: D102
        return SolverScoringMethod.Custom

    def solve(self, _datum: dict) -> Tuple[bool, dict]:  # noqa: D102
        if self.step == "gen_model_answer":
            self.gen_model_answer()
            return True, {}
        if self.step == "gen_ground_truth_judgement":
            return self.gen_ground_truth_judgement(), {}
        if self.step == "show_livebench_results":
            return self.show_livebench_results()
        if self.step == "all":
            self.gen_model_answer()
            if not self.gen_ground_truth_judgement():
                return False, {}
            return self.show_livebench_results()
        return False, {}

    def gen_model_answer(self) -> None:  # noqa: D102
        print("")
        print("----------- Step gen_model_answer -----------")
        print("")
        list_of_question_files = glob.glob(f"{self.dataset_ref}/**/question.jsonl", recursive=True)
        for question_file in list_of_question_files:
            questions = load_questions_jsonl(question_file)
            bench_name = os.path.dirname(question_file).split(str(self.dataset_ref))[-1]
            answer_file = f"~/.nearai/live_bench_answers/{bench_name}/model_answer/{self.model}.jsonl"
            print(f"Questions from {question_file}")
            print(f"Output to {answer_file}")
            self.run_eval(questions, answer_file)

    def run_eval(self, questions, answer_file) -> None:  # noqa: D102
        answer_file = os.path.expanduser(answer_file)

        # Load existing answers
        existing_answers = set()
        if os.path.exists(answer_file):
            print(
                f"Answer file {answer_file} exists. Will skip already answered questions. Delete this file if that is not intended."  # noqa: E501
            )
            with open(answer_file, "r") as fin:
                for line in fin:
                    answer = json.loads(line)
                    existing_answers.add(answer["question_id"])

        for question in tqdm(questions):
            if question["question_id"] in existing_answers:
                continue
            choices = self.answer_question(question)

            ans_json = {
                "question_id": question["question_id"],
                "answer_id": shortuuid.uuid(),
                "model_id": self.model,
                "choices": choices,
                "tstamp": time.time(),
            }

            os.makedirs(os.path.dirname(answer_file), exist_ok=True)
            with open(answer_file, "a") as fout:
                fout.write(json.dumps(ans_json) + "\n")

    def answer_question(self, question) -> List[dict]:  # noqa: D102
        conv = []
        # Append system prompt here if needed.
        turns = []
        for qs in question["turns"]:
            conv.append({"role": "user", "content": qs})

            completion_response = cast(
                ModelResponse,
                self.completion_fn(
                    self.model,
                    messages=[convert_message(msg) for msg in conv],
                    temperature=0.0,
                ),
            )
            output = str(cast(List[Choices], completion_response.choices)[0].message.content)

            conv.append({"role": "assistant", "content": output})
            turns.append(output)

        return [{"index": 0, "turns": turns}]

    def gen_ground_truth_judgement(self) -> bool:  # noqa: D102
        print("")
        print("----------- Step gen_ground_truth_judgement -----------")
        print("")
        script_path = "nearai/projects/live_bench/gen_ground_truth_judgement.sh"

        try:
            # Run the script without capturing output
            subprocess.run(["/bin/bash", script_path, self.model, self.dataset_ref], check=True)
            return True

        except subprocess.CalledProcessError as e:
            print(f"An error occurred while running the script: {e}")
            return False

    def show_livebench_results(self) -> Tuple[bool, dict]:  # noqa: D102
        print("")
        print("----------- Step show_livebench_results -----------")
        print("")
        script_path = "nearai/projects/live_bench/show_livebench_results.sh"

        try:
            # Run the script without capturing output
            subprocess.run(["/bin/bash", script_path, self.model], check=True)

        except subprocess.CalledProcessError as e:
            print(f"An error occurred while running the script: {e}")
            return False, {}

        return self.create_result_dict()

    def read_csv_to_dict(self, file_path) -> dict:  # noqa: D102
        file_path = os.path.expanduser(file_path)
        with open(file_path, "r") as f:
            reader = csv.DictReader(f)
            matching_rows = [row for row in reader if row["model"] == self.model]
            return matching_rows[-1] if matching_rows else {}  # Get the last matching row

    def create_result_dict(self) -> Tuple[bool, dict]:  # noqa: D102
        tasks_data = self.read_csv_to_dict("~/.nearai/LiveBench/livebench/all_tasks.csv")
        groups_data = self.read_csv_to_dict("~/.nearai/LiveBench/livebench/all_groups.csv")

        if not tasks_data or not groups_data:
            return False, {}  # Return None if the model is not found in either file

        result: dict = {"tasks": {}, "groups": {}}

        for key, value in tasks_data.items():
            if key != "model":
                result["tasks"][key] = float(value)

        for key, value in groups_data.items():
            if key != "model":
                result["groups"][key] = float(value)

        return True, result

    def get_evaluation_metrics(self, tasks_results: List[Tuple[bool, Any]]) -> Dict[str, Any]:  # noqa: D102
        results: Dict[str, Dict[str, Any]] = tasks_results[-1][1]
        metrics: Dict[str, Any] = {"average": results["groups"]["average"]}

        for group, score in results["groups"].items():
            if group == "average":
                continue
            metrics[f"group/{group}"] = score

        for task, score in results["tasks"].items():
            metrics[f"task/{task}"] = score

        return metrics
