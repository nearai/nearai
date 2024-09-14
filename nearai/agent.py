import json
import os
import runpy
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

from nearai.lib import check_metadata
from nearai.registry import get_namespace

AGENT_FILENAME = "agent.py"


class Agent(object):
    def __init__(self, path: str):  # noqa: D107
        self.name: str = ""
        self.version: str = ""
        self.env_vars: Dict[str, Any] = {}

        self.model = ""
        self.model_provider = ""
        self.model_temperature: Optional[float] = None
        self.model_max_tokens: Optional[int] = None
        self.welcome_title: Optional[str] = None
        self.welcome_description: Optional[str] = None

        self.path = path
        self.load_agent_metadata()
        self.namespace = get_namespace(Path(self.path))

        temp_dir = os.path.join(tempfile.gettempdir(), str(int(time.time())))

        # Copy all agent files including subfolders
        shutil.copytree(path, temp_dir, dirs_exist_ok=True)

        self.temp_dir = temp_dir

    def load_agent_metadata(self) -> None:
        """Load agent details from metadata.json."""
        metadata_path = os.path.join(self.path, "metadata.json")
        check_metadata(Path(metadata_path))
        with open(metadata_path) as f:
            metadata: Dict[str, Any] = json.load(f)
            self.metadata = metadata

            try:
                self.name = metadata["name"]
                self.version = metadata["version"]
            except KeyError as e:
                raise ValueError(f"Missing key in metadata: {e}") from None

            details = metadata.get("details", {})
            agent = details.get("agent", {})
            welcome = agent.get("welcome", {})

            self.env_vars = details.get("env_vars", {})
            self.welcome_title = welcome.get("title")
            self.welcome_description = welcome.get("description")

            if agent_metadata := details.get("agent", None):
                if defaults := agent_metadata.get("defaults", None):
                    self.model = defaults.get("model", self.model)
                    self.model_provider = defaults.get("model_provider", self.model_provider)
                    self.model_temperature = defaults.get("model_temperature", self.model_temperature)
                    self.model_max_tokens = defaults.get("model_max_tokens", self.model_max_tokens)

        if not self.version or not self.name:
            raise ValueError("Both 'version' and 'name' must be non-empty in metadata.")

    def run(self, env: Any, task: Optional[str] = None) -> None:  # noqa: D102
        if not os.path.exists(os.path.join(self.path, AGENT_FILENAME)):
            raise ValueError("Agent run error: {AGENT_FILENAME} does not exist")

        # combine agent.env_vars and env.env_vars
        total_env_vars = {**self.env_vars, **env.env_vars}

        # save os env vars
        os.environ.update(total_env_vars)
        # save env.env_vars
        env.env_vars = total_env_vars

        context = {"env": env, "agent": self, "task": task}

        original_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            sys.path.insert(0, self.temp_dir)
            runpy.run_path(AGENT_FILENAME, init_globals=context, run_name="__main__")
        finally:
            os.chdir(original_cwd)
            sys.path.pop(0)
