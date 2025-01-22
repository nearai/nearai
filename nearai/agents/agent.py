import io
import json
import multiprocessing
import os
import pwd
import shutil
import sys
import tempfile
import uuid
from pathlib import Path
from types import CodeType
from typing import Any, Dict, List, Optional, Union

from nearai.shared.client_config import ClientConfig

AGENT_FILENAME = "agent.py"


class Agent(object):
    def __init__(  # noqa: D107
        self, identifier: str, agent_files: Union[List, Path], metadata: Dict, change_to_temp_dir: bool = True
    ):  # noqa: D107
        self.code: Optional[CodeType] = None
        self.file_cache: dict[str, Union[str, bytes]] = {}
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
        self.max_iterations = 1
        self.welcome_title: Optional[str] = None
        self.welcome_description: Optional[str] = None

        self.set_agent_metadata(metadata)
        self.agent_files = agent_files
        self.original_cwd = os.getcwd()

        self.temp_dir = self.write_agent_files_to_temp(agent_files)
        self.change_to_temp_dir = change_to_temp_dir
        self.agent_filename = ""

    def get_full_name(self):
        """Returns full agent name."""
        return f"{self.namespace}/{self.name}/{self.version}"

    @staticmethod
    def write_agent_files_to_temp(agent_files):
        """Write agent files to a temporary directory."""
        unique_id = uuid.uuid4().hex
        temp_dir = os.path.join(tempfile.gettempdir(), f"agent_{unique_id}")

        if isinstance(agent_files, List):
            os.makedirs(temp_dir, exist_ok=True)

            for file_obj in agent_files:
                file_path = os.path.join(temp_dir, file_obj["filename"])

                try:
                    if not os.path.exists(os.path.dirname(file_path)):
                        os.makedirs(os.path.dirname(file_path))

                    content = file_obj["content"]

                    if isinstance(content, dict) or isinstance(content, list):
                        try:
                            content = json.dumps(content)
                        except Exception as e:
                            print(f"Error converting content to json: {e}")
                        content = str(content)

                    if isinstance(content, str):
                        content = content.encode("utf-8")

                    with open(file_path, "wb") as f:
                        with io.BytesIO(content) as byte_stream:
                            shutil.copyfileobj(byte_stream, f)
                except Exception as e:
                    print(f"Error writing file {file_path}: {e}")
                    raise e

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
                self.max_iterations = defaults.get("max_iterations", self.max_iterations)

        if not self.version or not self.name:
            raise ValueError("Both 'version' and 'name' must be non-empty in metadata.")

    def run(self, env: Any, task: Optional[str] = None) -> None:  # noqa: D102
        # combine agent.env_vars and env.env_vars
        total_env_vars = {**self.env_vars, **env.env_vars}

        # save os env vars
        os.environ.update(total_env_vars)
        # save env.env_vars
        env.env_vars = total_env_vars

        if not self.agent_filename:
            self.agent_filename = os.path.join(self.temp_dir, AGENT_FILENAME)
            if not os.path.exists(self.agent_filename):
                raise ValueError(f"Agent run error: {AGENT_FILENAME} does not exist")
            with open(self.agent_filename, "r") as agent_file:
                self.code = compile(agent_file.read(), self.agent_filename, "exec")

            # cache all agent files in file_cache
            for root, _, files in os.walk(self.temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, self.temp_dir)
                    try:
                        with open(file_path, "rb") as f:
                            content = f.read()
                            try:
                                # Try to decode as text
                                self.file_cache[relative_path] = content.decode("utf-8")
                            except UnicodeDecodeError:
                                # If decoding fails, store as binary
                                self.file_cache[relative_path] = content

                    except Exception as e:
                        print(f"Error with cache creation {file_path}: {e}")

        else:
            print("Using cached agent code")

        namespace = {
            "env": env,
            "agent": self,
            "task": task,
            "__name__": "__main__",
            "__file__": self.agent_filename,
        }

        def run_agent_code(agent_namespace):
            # switch to user env.agent_runner_user
            if env.agent_runner_user:
                user_info = pwd.getpwnam(env.agent_runner_user)
                os.setgid(user_info.pw_gid)
                os.setuid(user_info.pw_uid)

            # Run the code
            # NOTE: runpy.run_path does not work in a multithreaded environment when running benchmark.
            #       The performance of runpy.run_path may also change depending on a system, e.g. it may
            #       work on Linux but not work on Mac.
            #       `compile` and `exec` have been tested to work properly in a multithreaded environment.
            exec(self.code, agent_namespace)

        try:
            if self.change_to_temp_dir:
                if not os.path.exists(self.temp_dir):
                    os.makedirs(self.temp_dir, exist_ok=True)
                os.chdir(self.temp_dir)
            sys.path.insert(0, self.temp_dir)

            if env.agent_runner_user:
                process = multiprocessing.Process(target=run_agent_code, args=namespace)
                process.start()
                process.join()
            else:
                run_agent_code(namespace)
        finally:
            if os.path.exists(self.temp_dir):
                sys.path.remove(self.temp_dir)
            if self.change_to_temp_dir:
                os.chdir(self.original_cwd)

    @staticmethod
    def load_agents(agents: str, config: ClientConfig, local: bool = False):
        """Loads agents from the registry."""
        return [Agent.load_agent(agent, config, local) for agent in agents.split(",")]

    @staticmethod
    def load_agent(
        name: str,
        config: ClientConfig,
        local: bool = False,
    ):
        """Loads a single agent from the registry."""
        from nearai.registry import get_registry_folder, registry

        identifier = None
        if local:
            agent_files_path = get_registry_folder() / name
            if config.auth is None:
                namespace = "not-logged-in"
            else:
                namespace = config.auth.account_id
        else:
            agent_files_path = registry.download(name)
            identifier = name
        assert agent_files_path is not None, f"Agent {name} not found."

        metadata_path = os.path.join(agent_files_path, "metadata.json")
        if not os.path.exists(metadata_path):
            raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
        with open(metadata_path) as f:
            metadata: Dict[str, Any] = json.load(f)

        if not identifier:
            identifier = "/".join([namespace, metadata["name"], metadata["version"]])

        return Agent(identifier, agent_files_path, metadata)
