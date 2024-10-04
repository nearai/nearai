import json
import tempfile
from pathlib import Path

import nearai
import openai
import pytest
from nearai.cli import RegistryCli
from nearai.registry import Registry


@pytest.mark.integration
def test_registry():
    """When a directory is uploaded to the registry, it can be listed."""
    registry = Registry()
    assert registry.list_all_visible() == []

    tmp_dir = tempfile.TemporaryDirectory()

    registry_cli = RegistryCli()
    registry_cli.metadata_template(local_path=Path(tmp_dir.name))

    registry.upload(Path(tmp_dir.name))
    assert Path(tmp_dir.name).name in map(lambda x: x.name, registry.list_all_visible())


@pytest.mark.integration
def test_hub_completion():
    # Login to NEAR AI Hub using nearai CLI.
    # Read the auth object from ~/.nearai/config.json
    auth = nearai.config.load_config_file()["auth"]
    signature = json.dumps(auth)

    client = openai.OpenAI(base_url=nearai.config.CONFIG.nearai_hub.base_url, api_key=signature)

    # list models available from NEAR AI Hub
    models = client.models.list()
    assert any(model.id == "local::facebook/opt-125m" for model in models)

    # create a chat completion
    completion = client.completions.create(
        model="local::facebook/opt-125m",
        prompt="Hello, world!",
        max_tokens=16,
    )
    print(completion)
