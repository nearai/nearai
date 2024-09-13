# Use this script to download latest live_bench questions, then you can upload them to registry.
# To run: `python load_questions.py`

from datetime import datetime
import json
import os
from typing import Optional
from datasets import load_dataset, Dataset

LIVE_BENCH_HF_ORGANIZATION = "livebench"
LIVE_BENCH_DATA_SUPER_PATH = "live_bench"
LIVE_BENCH_CATEGORIES = [
    "coding",
    "data_analysis",
    "instruction_following",
    "math",
    "reasoning",
    "language",
]


def get_hf_dataset(dataset_name: str, split="test"):
    return load_dataset(f"{LIVE_BENCH_HF_ORGANIZATION}/{dataset_name}", split=split)


def get_tasks_from_hf_category(category: Dataset):
    return list(set(category["task"]))


def get_categories_tasks():
    categories = {
        category_name: get_hf_dataset(category_name)
        for category_name in LIVE_BENCH_CATEGORIES
    }

    tasks = {
        category_name: get_tasks_from_hf_category(categories[category_name])
        for category_name in LIVE_BENCH_CATEGORIES
    }

    return categories, tasks


def load_questions(
    category: Dataset,
    task_name: Optional[str],
    begin: Optional[int],
    end: Optional[int],
):
    """Load questions from a file."""
    if task_name is not None:
        questions = [
            example for example in category.filter(lambda row: row["task"] == task_name)
        ]
    else:
        questions = list(category)
    questions = questions[begin:end]
    for q in questions:
        if "livebench_release_date" in q.keys() and isinstance(
            q["livebench_release_date"], datetime
        ):
            print("question livebench_release_date: ", q["livebench_release_date"])
            q["livebench_release_date"] = datetime.strftime(
                q["livebench_release_date"], "%Y-%m-%d"
            )
        if "release_date" in q.keys() and isinstance(q["release_date"], datetime):
            q["release_date"] = datetime.strftime(q["release_date"], "%Y-%m-%d")
        if (
            "original_json" in q.keys()
            and "contest_date" in q["original_json"].keys()
            and isinstance(q["original_json"]["contest_date"], datetime)
        ):
            q["original_json"]["contest_date"] = datetime.strftime(
                q["original_json"]["contest_date"], "%Y-%m-%d %H:%M:%S"
            )
    return questions


if __name__ == "__main__":
    categories, tasks = get_categories_tasks()

    for category_name, task_names in tasks.items():
        for task_name in task_names:
            questions = load_questions(categories[category_name], task_name, None, None)

            task_full_name = f"{LIVE_BENCH_DATA_SUPER_PATH}/{category_name}/{task_name}"

            # Save questions to a JSONL file
            questions_file = os.path.expanduser(f"~/{task_full_name}/question.jsonl")
            os.makedirs(os.path.dirname(questions_file), exist_ok=True)
            with open(questions_file, "w") as f:
                for question in questions:
                    json.dump(question, f)
                    f.write("\n")

            print(f"Questions from {task_full_name}")
            print(f"Questions saved to {questions_file}")
