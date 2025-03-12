import json
import re
import tempfile
from pathlib import Path

import datasets
import nearai
import openai
import pytest
from nearai.cli import BenchmarkCli, RegistryCli
from nearai.registry import Registry
from nearai.solvers.hellaswag_solver import HellaswagSolverStrategy

MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"


@pytest.mark.integration
def test_registry():
    """When a directory is uploaded to the registry, it can be listed."""
    registry = Registry()

    tmp_dir = tempfile.TemporaryDirectory()
    name = "test_entry"
    version = "0.0.1"

    # Create nested directory structure
    entry_dir = Path(tmp_dir.name) / name / version
    entry_dir.mkdir(parents=True)

    registry_cli = RegistryCli()
    registry_cli.metadata_template(local_path=entry_dir)

    registry.upload(entry_dir)
    assert name in map(lambda x: x.name, registry.list_all_visible()), f"Registry should contain {name}"


@pytest.mark.integration
def test_hub_completion():
    # Login to NEAR AI Hub using nearai CLI.
    # Read the auth object from ~/.nearai/config.json
    auth = nearai.config.load_config_file()["auth"]
    signature = json.dumps(auth)

    client = openai.OpenAI(base_url=nearai.config.CONFIG.nearai_hub.base_url, api_key=signature)

    # list models available from NEAR AI Hub
    models = client.models.list()
    assert any(model.id == f"local::{MODEL_NAME}" for model in models), f"Model {MODEL_NAME} should be available"

    # create a chat completion
    completion = client.completions.create(
        model=f"local::{MODEL_NAME}",
        prompt="Hello, world!",
        max_tokens=4,
    )
    print(completion)


@pytest.mark.integration
def test_hub_chat():
    auth = nearai.config.load_config_file()["auth"]
    signature = json.dumps(auth)

    client = openai.OpenAI(base_url=nearai.config.CONFIG.nearai_hub.base_url, api_key=signature)

    # list models available from NEAR AI Hub
    models = client.models.list()
    assert any(model.id == f"local::{MODEL_NAME}" for model in models), f"Model {MODEL_NAME} should be available"

    # create a chat completion
    chat_completion = client.chat.completions.create(
        model=f"local::{MODEL_NAME}",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say anything."},
        ],
        max_tokens=4,
    )
    print(chat_completion)


@pytest.mark.integration
def test_spotcheck_benchmark():
    metadata = {
        "name": "hellaswag_spotcheck",
        "version": "0.0.1",
        "description": "A test dataset for ci purposes, hellaswag format specific",
        "category": "dataset",
        "tags": ["dataset"],
        "details": {},
        "show_entry": True,
    }

    with tempfile.TemporaryDirectory() as tmp_dir:
        dataset_path = Path(tmp_dir) / "dataset"

        dataset = datasets.Dataset.from_generator(
            lambda: iter(
                [
                    {
                        "ind": 14,
                        "activity_label": "Wakeboarding",
                        "ctx_a": "A man is being pulled on a water ski as he floats in the water casually.",
                        "ctx_b": "he",
                        "ctx": "A man is being pulled on a water ski as he floats in the water casually. he",
                        "endings": [
                            "mounts the water ski and tears through the water at fast speeds.",
                            "goes over several speeds, trying to stay upright.",
                            "struggles a little bit as he talks about it.",
                            "is seated in a boat with three other people.",
                        ],
                        "source_id": "test",
                        "split": "test",
                        "split_type": "indomain",
                        "label": "",
                    }
                ]
            ),
            features=datasets.Features(
                {
                    "ind": datasets.Value("int32"),
                    "activity_label": datasets.Value("string"),
                    "ctx_a": datasets.Value("string"),
                    "ctx_b": datasets.Value("string"),
                    "ctx": datasets.Value("string"),
                    "endings": datasets.Sequence(datasets.Value("string")),
                    "source_id": datasets.Value("string"),
                    "split": datasets.Value("string"),
                    "split_type": datasets.Value("string"),
                    "label": datasets.Value("string"),
                }
            ),
        )
        dataset_dict = datasets.DatasetDict({"dev": dataset})
        dataset_dict.save_to_disk(dataset_path)

        with open(dataset_path / "metadata.json", "w") as f:
            json.dump(metadata, f)

        registry = Registry()
        registry.upload(dataset_path)

        assert metadata["name"] in map(lambda x: x.name, registry.list_all_visible())
        item = list(filter(lambda x: x.name == metadata["name"], registry.list_all_visible()))[0]

        benchmark_cli = BenchmarkCli()
        benchmark_cli.run(
            solver_strategy=re.search(r"\'.*\'", str(HellaswagSolverStrategy)).group(0).replace("'", "").split(".")[-1],
            model=f"local::{MODEL_NAME}",
            dataset=f"{item.namespace}/{item.name}/{item.version}",
            subset="dev",
            shots=0,
        )


# @pytest.mark.integration
# def test_example_agent():
#     metadata = {
#         "name": "example_travel_agent",
#         "version": "1",
#         "description": "Example agent that helps users with travel",
#         "category": "agent",
#         "tags": ["python", "travel"],
#         "details": {
#             "display_name": "Example Travel Agent",
#             "icon": "https://upload.wikimedia.org/wikipedia/commons/6/66/Likes_Travel_icon.png",
#             "agent": {
#                 "framework": "base",
#                 "welcome": {"title": "Your Travel Agent", "description": "Where would you like to go?"},
#                 "defaults": {
#                     "max_iterations": 1,
#                     "model": f"local::{MODEL_NAME}",
#                     "model_provider": "local",
#                     "model_temperature": 0.0,
#                     "model_max_tokens": 32,
#                 },
#             },
#         },
#         "show_entry": True,
#     }
#     python_code = dedent(f"""
#     # In local interactive mode, the first user input is collected before the agent runs.
#     prompt = {{"role": "system", "content": "You are a travel agent that helps users plan trips."}}
#     try:
#         env.add_message("assistant", "File content: " + env.read_file('test.txt'))
#     except Exception as e:
#         print("Error reading file:", e)

#     result = env.completion([prompt] + env.list_messages(), model="local::{MODEL_NAME}")
#     env.add_message("assistant", result)
#     env.mark_done()
#     """)
#     with tempfile.TemporaryDirectory() as tmp_dir:
#         agent_path = Path(tmp_dir) / "agent"
#         agent_path.mkdir()
#         with open(agent_path / "metadata.json", "w") as f:
#             json.dump(metadata, f)
#         with open(agent_path / "agent.py", "w") as f:
#             f.write(python_code)

#         registry = Registry()
#         registry.upload(agent_path)

#         assert metadata["name"] in map(lambda x: x.name, registry.list_all_visible())
#         item = list(filter(lambda x: x.name == metadata["name"], registry.list_all_visible()))[0]

#     agent_cli = AgentCli()
#     agent_cli.task(
#         f"{item.namespace}/{item.name}/{item.version}",
#         "Tell me about yourself.",
#     )

#     hub_client = get_hub_client()
#     thread = hub_client.beta.threads.retrieve(agent_cli.last_thread_id)
#     assert thread, "Thread should be created"

#     messages = list(hub_client.beta.threads.messages.list(thread_id=agent_cli.last_thread_id).data)
#     assert len(messages) == 2, "Thread should have two messages"

#     ## upload a file, attach in a message
#     file_content = "This is a test file"
#     uploaded_file = hub_client.files.create(
#         file=("test.txt", BytesIO(file_content.encode("utf-8"))), purpose="assistants"
#     )
#     agent_cli.task(
#         f"{item.namespace}/{item.name}/{item.version}",
#         task="what do you think of this file?",
#         thread_id=agent_cli.last_thread_id,
#         file_ids=[uploaded_file.id],
#     )

#     messages = list(hub_client.beta.threads.messages.list(thread_id=agent_cli.last_thread_id).data)
#     for message in messages:
#         print(message)
#     assert len(messages) == 5, "Thread should have five messages"
