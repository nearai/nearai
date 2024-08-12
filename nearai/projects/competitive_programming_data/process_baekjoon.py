import json
from typing import Any, Dict, Iterable, List

from datasets import Dataset
from nearai.dataset import get_dataset
from nearai.registry import registry
from openai.types.chat import ChatCompletionMessageParam
from torchtune.data import Message
from torchtune.models.llama3 import llama3_tokenizer
from tqdm import tqdm
from nearai.lib import parse_location


def prepare_system_prompt(item: Dict[str, Any]) -> str:
    statement = item["statement"]
    tests = []

    for i, test in enumerate(item["tests"]):
        t_in = test["input"]
        t_out = test["output"]
        tests.append(f"Sample input {i + 1}:\n{t_in}\nSample output {i + 1}:\n{t_out}")

    tests_str = "\n\n".join(tests)

    return f"{statement}\n\n{tests_str}"


def process_trajectory(item: Dict[str, Any]) -> Iterable[ChatCompletionMessageParam]:
    system_prompt = prepare_system_prompt(item)

    messages: List[ChatCompletionMessageParam] = []
    messages.append({"role": "system", "content": system_prompt})

    for step in item["steps"]:
        if step["kind"] == "text":
            messages.append({"role": "assistant", "content": step["text"]})

        elif step["kind"] == "code":
            messages.append({"role": "assistant", "content": f"!CODE\n{step['code']}\n!END"})

        elif step["kind"] == "execution":
            messages.append({"role": "assistant", "content": f"!TEST\n{step['input']}1END"})
            messages.append({"role": "system", "content": f"Result:\n{step['output']}"})

        elif step["kind"] == "compprog_submit":
            messages.append({"role": "assistant", "content": "!SUBMIT"})
            messages.append({"role": "system", "content": f"Result:\n{step['verdict']}"})
        else:
            raise ValueError(f"Unknown step kind: {step['kind']}")

    return messages


if __name__ == "__main__":
    path = get_dataset("baekjoon-trajectories-raw")
    file_path = path / "baekjoon_20240703.txt"

    ds_dict: Dict[str, List] = {
        "problem_id": [],
        "statement_url": [],
        "statement": [],
        "tests": [],
        "steps": [],
        "messages": [],
        "ntokens_llama3": [],
    }

    # TODO: Upload llama-3 tokenizer to the registry
    tokenizer_path = registry.download("TODO/tokenizers/llama-3") / "tokenizer.model"
    tokenizer = llama3_tokenizer(tokenizer_path)

    max_len = 0
    num_large = 0

    for i, line in (pbar := tqdm(enumerate(file_path.read_bytes().split(b"\n")))):
        if line == b"data" or not line:
            continue

        line_decoded = line.decode("unicode_escape", errors="ignore")
        data = json.loads(line_decoded)

        try:
            messages = process_trajectory(data)
        except Exception:
            print(f"ERROR BUILDING TRAJECTORY FOR SAMPLE: {i}")
            continue

        messages_for_tokenizer = [Message.from_dict(m) for m in messages]
        tokens, _ = tokenizer.tokenize_messages(messages_for_tokenizer)
        num_tokens = len(tokens)

        ds_dict["problem_id"].append(data["problem_id"])
        ds_dict["statement_url"].append(data["statement_url"])
        ds_dict["statement"].append(data["statement"])
        ds_dict["tests"].append(data["tests"])
        ds_dict["steps"].append(data["steps"])
        ds_dict["messages"].append(messages)
        ds_dict["ntokens_llama3"].append(num_tokens)
        max_len = max(max_len, num_tokens)
        if num_tokens > 8192:
            num_large += 1

        pbar.set_description(f"max_len: {max_len}, num_large: {num_large} i={i}")

    ds = Dataset.from_dict(ds_dict)
    ds.save_to_disk("baekjoon-trajectories-processed")
