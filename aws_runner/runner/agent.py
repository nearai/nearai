import io
import os
import runpy
import shutil
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional

AGENT_FILENAME = "agent.py"


class Agent(object):
    def __init__(self, identifier: str, path: str, agent_files: List, user_env_vars: Dict, metadata: Dict):  # noqa: D107
        name_parts = identifier.split("/")
        self.namespace = name_parts[0]
        self.name = name_parts[1]
        self.version = name_parts[2]

        self.env_vars: Dict[str, Any] = {}

        self.model = ""
        self.model_provider = ""
        self.model_temperature: Optional[float] = None
        self.model_max_tokens: Optional[int] = None
        self.welcome_title: Optional[str] = None
        self.welcome_description: Optional[str] = None

        self.path = path
        self.set_agent_metadata(metadata)
        self.env_vars.update(user_env_vars)

        temp_dir = os.path.join(tempfile.gettempdir(), str(int(time.time())))
        os.makedirs(temp_dir, exist_ok=True)

        for file_obj in agent_files:
            file_path = os.path.join(temp_dir, file_obj["filename"])

            content = file_obj["content"]
            if isinstance(content, dict):
                content = str(content)

            if isinstance(content, str):
                content = content.encode("utf-8")

            with open(file_path, "wb") as f:
                with io.BytesIO(content) as byte_stream:
                    shutil.copyfileobj(byte_stream, f)

        self.temp_dir = temp_dir

    def set_agent_metadata(self, metadata) -> None:
        """Set agent details from metadata."""
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
        if not os.path.exists(os.path.join(self.temp_dir, AGENT_FILENAME)):
            raise ValueError("Agent run error: {AGENT_FILENAME} does not exist")

        # combine agent's env_vars and user's env_vars
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
