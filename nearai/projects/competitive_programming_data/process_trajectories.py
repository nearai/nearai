import json
from typing import Any, Dict, Generator, List

from datasets import Dataset # type: ignore
from nearai.dataset import get_dataset


def process_trajectory(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    messages = []
    if item["type"] == "sequence":
        for c in item["children"]:
            text = ""
            if c["type"] == "sequence":
                for cc in c["children"]:
                    text += cc["text"]
            else:
                text += c.get("text", "")
            if text == "Ready to submit!":
                text = "!SUBMIT"
            if text != "":
                if c["prefix"] == "&code$":
                    messages.append({"role": "assistant", "content": "!CODE\n" + text + "\n!END"})
                elif c["prefix"] == "&execution$":
                    messages.append({"role": "system", "content": text})
                else:
                    messages.append({"role": "assistant", "content": text})
    return messages


if __name__ == "__main__":
    path = get_dataset("datasets/competitive_programming_traces/raw/v0")
    content = json.load(open(path))
    item = content[0]

    def gen() -> Generator[Dict[str, Any], None, None]:
        for item in content:
            yield {"messages": process_trajectory(item)}

    d = Dataset.from_generator(gen)
    output_path = "/tmp/competitive_programming_test_data"
    d.save_to_disk()
    print("Saved %s", output_path)
