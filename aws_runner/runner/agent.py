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
    def __init__(self, name: str, path: str, agent_files: List, env_vars: Dict):  # noqa: D107
        self.name = name
        self.path = path
        # self.code = code

        self.env_vars: Dict[str, Any] = env_vars

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
