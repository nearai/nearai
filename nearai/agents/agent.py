import io
import json
import multiprocessing
import os
import pwd
import shutil
import subprocess
import sys
import tempfile
import traceback
import uuid
from pathlib import Path
from types import CodeType
from typing import Any, Dict, List, Optional, Tuple, Union

from dotenv import load_dotenv

from nearai.shared.client_config import ClientConfig

AGENT_FILENAME_PY = "agent.py"
AGENT_FILENAME_TS = "agent.ts"

load_dotenv()


def clear_module_cache(module_names, namespace):
    """Clears specified modules from the cache before executing the main code.

    When executing agent code that imports utility modules from different locations,
    Python's module caching can sometimes use cached versions from the wrong location
    instead of importing from the agent's directory.

    This function removes modules from sys.modules to ensure they're freshly
    imported when used in subsequent code executions, preventing issues with
    cached imports.

    Args:
    ----
        module_names: List of module names to clear from cache
        namespace: Dictionary namespace for code execution

    """
    cleanup_code = "import sys\n"
    for module_name in module_names:
        cleanup_code += f"if '{module_name}' in sys.modules:\n"
        cleanup_code += f"    del sys.modules['{module_name}']\n"

    exec(cleanup_code, namespace)


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
        self.ts_runner_dir = ""
        self.change_to_temp_dir = change_to_temp_dir
        self.agent_filename = ""
        self.agent_language = ""

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

    def run_python_code(
        self, agent_namespace, agent_runner_user, agent_py_modules_import
    ) -> Tuple[Optional[str], Optional[str]]:
        """Launch python agent."""
        try:
            # switch to user env.agent_runner_user
            if agent_runner_user:
                user_info = pwd.getpwnam(agent_runner_user)
                os.setgid(user_info.pw_gid)
                os.setuid(user_info.pw_uid)

            # Run the code
            # NOTE: runpy.run_path does not work in a multithreaded environment when running benchmark.
            #       The performance of runpy.run_path may also change depending on a system, e.g. it may
            #       work on Linux but not work on Mac.
            #       `compile` and `exec` have been tested to work properly in a multithreaded environment.
            if self.code:
                clear_module_cache(agent_py_modules_import, agent_namespace)
                exec(self.code, agent_namespace)

            # If no errors occur, return None
            return None, None

        except Exception as e:
            # Return error message and full traceback as strings
            return str(e), traceback.format_exc()

    def run_ts_agent(self, agent_filename, env_vars, json_params):
        """Launch typescript agent."""
        print(f"Running typescript agent {agent_filename} from {self.ts_runner_dir}")

        # Configure npm to use tmp directories
        env = os.environ.copy()
        env.update(
            {
                "NPM_CONFIG_CACHE": "/tmp/npm_cache",
                "NPM_CONFIG_PREFIX": "/tmp/npm_prefix",
                "HOME": "/tmp",  # Redirect npm home
                "NPM_CONFIG_LOGLEVEL": "error",  # Suppress warnings, show only errors
            }
        )

        # Ensure directory structure exists
        os.makedirs("/tmp/npm_cache", exist_ok=True)
        os.makedirs("/tmp/npm_prefix", exist_ok=True)

        # read file /tmp/build-info.txt if exists
        if os.path.exists("/var/task/build-info.txt"):
            with open("/var/task/build-info.txt", "r") as file:
                print("BUILD ID: ", file.read())

        if env_vars.get("DEBUG"):
            print("Directory structure:", os.listdir("/tmp/ts_runner"))
            print("Check package.json:", os.path.exists(os.path.join(self.ts_runner_dir, "package.json")))
            print("Symlink exists:", os.path.exists("/tmp/ts_runner/node_modules/.bin/tsc"))
            print("Build files exist:", os.path.exists("/tmp/ts_runner/build/sdk/main.js"))

        # Launching a subprocess to run an npm script with specific configurations
        ts_process = subprocess.Popen(
            [
                "npm",  # Command to run Node Package Manager
                "--loglevel=error",  # Suppress npm warnings and info logs, only show errors
                "--prefix",
                self.ts_runner_dir,  # Specifies the directory where npm should look for package.json
                "run",
                "start",  # Runs the "start" script defined in package.json, this launches the agent
                "agents/agent.ts",
                json_params,  # Arguments passed to the "start" script to configure the agent
            ],
            stdout=subprocess.PIPE,  # Captures standard output from the process
            stderr=subprocess.PIPE,  # Captures standard error
            cwd=self.ts_runner_dir,  # Sets the current working directory for the process
            env=env_vars,  # Provides custom environment variables to the subprocess
        )

        stdout, stderr = ts_process.communicate()

        stdout = stdout.decode().strip()
        if stdout and env_vars.get("DEBUG"):
            print(f"TS AGENT STDOUT: {stdout}")

        stderr = stderr.decode().strip()
        if stderr:
            print(f"TS AGENT STDERR: {stderr}")

    def run(self, env: Any, task: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """Run the agent code. Returns error message and traceback message."""
        # combine agent.env_vars and env.env_vars
        total_env_vars = {**self.env_vars, **env.env_vars}

        # save os env vars
        os.environ.update(total_env_vars)
        # save env.env_vars
        env.env_vars = total_env_vars

        agent_ts_files_to_transpile = []
        agent_py_modules_import = []

        if not self.agent_filename or True:
            # if agent has "agent.py" file, we use python runner
            if os.path.exists(os.path.join(self.temp_dir, AGENT_FILENAME_PY)):
                self.agent_filename = os.path.join(self.temp_dir, AGENT_FILENAME_PY)
                self.agent_language = "py"
                with open(self.agent_filename, "r") as agent_file:
                    self.code = compile(agent_file.read(), self.agent_filename, "exec")
            # else, if agent has "agent.ts" file, we use typescript runner
            elif os.path.exists(os.path.join(self.temp_dir, AGENT_FILENAME_TS)):
                self.agent_filename = os.path.join(self.temp_dir, AGENT_FILENAME_TS)
                self.agent_language = "ts"

                # copy files from nearai/ts_runner_sdk to self.temp_dir
                ts_runner_sdk_dir = "/tmp/ts_runner"
                ts_runner_agent_dir = os.path.join(ts_runner_sdk_dir, "agents")

                ts_runner_actual_path = "/var/task/ts_runner"

                shutil.copytree(ts_runner_actual_path, ts_runner_sdk_dir, symlinks=True, dirs_exist_ok=True)

                # make ts agents dir if not exists
                if not os.path.exists(ts_runner_agent_dir):
                    os.makedirs(ts_runner_agent_dir, exist_ok=True)

                # copy agents files
                shutil.copy(os.path.join(self.temp_dir, AGENT_FILENAME_TS), ts_runner_agent_dir)

                self.ts_runner_dir = ts_runner_sdk_dir
            else:
                raise ValueError(f"Agent run error: {AGENT_FILENAME_PY} or {AGENT_FILENAME_TS} does not exist")

            # cache all agent files in file_cache
            for root, dirs, files in os.walk(self.temp_dir):
                is_main_dir = root == self.temp_dir

                if is_main_dir:
                    # add all folders in the root directory as potential modules to import
                    agent_py_modules_import.extend(dirs)

                for file in files:
                    file_path = os.path.join(root, file)

                    # get file extension for agent_filename
                    if file_path.endswith(".ts"):
                        agent_ts_files_to_transpile.append(file_path)

                    if is_main_dir and file != AGENT_FILENAME_PY and file_path.endswith(".py"):
                        # save py file without extension as potential module to import
                        agent_py_modules_import.append(os.path.splitext(os.path.basename(file_path))[0])

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

        user_auth = env.user_auth

        # clear user_auth we saved before
        env.user_auth = None

        error_message, traceback_message = None, None

        try:
            if self.change_to_temp_dir:
                if not os.path.exists(self.temp_dir):
                    os.makedirs(self.temp_dir, exist_ok=True)
                os.chdir(self.temp_dir)
            sys.path.insert(0, self.temp_dir)

            if self.agent_language == "ts":
                agent_json_params = json.dumps(
                    {
                        "thread_id": env._thread_id,
                        "user_auth": user_auth,
                        "base_url": env.base_url,
                        "env_vars": env.env_vars,
                        "agent_ts_files_to_transpile": agent_ts_files_to_transpile,
                    }
                )

                process = multiprocessing.Process(
                    target=self.run_ts_agent, args=[self.agent_filename, env.env_vars, agent_json_params]
                )
                process.start()
                process.join()
            else:
                if env.agent_runner_user:
                    process = multiprocessing.Process(
                        target=self.run_python_code, args=[namespace, env.agent_runner_user]
                    )
                    process.start()
                    process.join()
                else:
                    error_message, traceback_message = self.run_python_code(
                        namespace, env.agent_runner_user, agent_py_modules_import
                    )

                    if error_message:
                        print(f"[ERROR PYTHON]: {error_message}")
                    if traceback_message:
                        print(f"[ERROR PYTHON TRACEBACK]: {traceback_message}")
        finally:
            if os.path.exists(self.temp_dir):
                sys.path.remove(self.temp_dir)
            if self.change_to_temp_dir:
                os.chdir(self.original_cwd)

        return error_message, traceback_message

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
