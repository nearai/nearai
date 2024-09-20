import io
import os
import runpy
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

AGENT_FILENAME = "agent.py"


class Agent(object):
    def __init__(self, identifier: str, agent_files: Union[List, Path], metadata: Dict):  # noqa: D107
        self.identifier = identifier
        name_parts = identifier.split("/")
        self.namespace = name_parts[0]
        self.name = name_parts[1]
        self.version = name_parts[2]

        self.metadata = metadata
        self.env_vars: Dict[str, Any] = {}

        self.model = ""
        self.model_provider = ""
        self.model_temperature: Optional[float] = None
        self.model_max_tokens: Optional[int] = None
        self.welcome_title: Optional[str] = None
        self.welcome_description: Optional[str] = None

        self.set_agent_metadata(metadata)

        self.temp_dir = self._write_agent_files_to_temp(agent_files)

    @staticmethod
    def _write_agent_files_to_temp(agent_files):
        temp_dir = os.path.join(tempfile.gettempdir(), str(int(time.time())))

        if isinstance(agent_files, List):
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
        else:
            # if agent files is a PosixPath, it is a path to the agent directory
            # Copy all agent files including subfolders
            shutil.copytree(agent_files, temp_dir, dirs_exist_ok=True)

        return temp_dir

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
            raise ValueError(f"Agent run error: {AGENT_FILENAME} does not exist")

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
