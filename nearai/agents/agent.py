import io
import json
import multiprocessing
import os
import pwd
import shutil
import subprocess
import sys
import tempfile
import uuid
from dotenv import load_dotenv
from os import getenv
from pathlib import Path
from types import CodeType
from typing import Any, Dict, List, Optional, Union

from nearai.shared.client_config import ClientConfig

AGENT_FILENAME_PY = "agent.py"
AGENT_FILENAME_TS = "agent.ts"

load_dotenv()


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

    def run_agent_code(self, agent_namespace, agent_runner_user):
        print("run_agent_code")
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
        exec(self.code, agent_namespace)

    def run_ts_agent(self, thread_id, user_auth):
        print("run_ts_agent", self.ts_runner_dir)
        # real_cwd = os.path.realpath(self.ts_runner_dir)
        print("💡 run_ts_agent CWD:", self.ts_runner_dir)
        print("💡 Check package.json:", os.path.exists(os.path.join(self.ts_runner_dir, "package.json")))

        # build_process = subprocess.Popen(["npm", "--prefix", self.ts_runner_dir, "run", "build"],
        #                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=self.ts_runner_dir)

        # Configure npm to use tmp directories
        env = os.environ.copy()
        env.update({
            "NPM_CONFIG_CACHE": "/tmp/npm_cache",
            "NPM_CONFIG_PREFIX": "/tmp/npm_prefix",
            "HOME": "/tmp"  # Redirect npm home
        })

        # Ensure directory structure exists
        os.makedirs("/tmp/npm_cache", exist_ok=True)
        os.makedirs("/tmp/npm_prefix", exist_ok=True)

        print("!!!BUILD: 1")
        print("!!!BUILD: ", getenv("BUILD_ID"))

        # Add debug logging
        print("Directory structure:", os.listdir("/tmp/ts_runner"))
        print("Symlink exists:", os.path.exists("/tmp/ts_runner/node_modules/.bin/tsc"))
        print("Build files exist:", os.path.exists("/tmp/ts_runner/build/sdk/main.js"))

        # build_process = subprocess.Popen(["npm", "--prefix", self.ts_runner_dir, "run", "build"],
        #                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=self.ts_runner_dir)

        # build_stdout, build_stderr = build_process.communicate()

        # Добавьте проверку версии TypeScript
        # version_process = subprocess.Popen(
        #     ["node", "-e", "console.log(require('typescript').version)"],
        #     stdout=subprocess.PIPE,
        #     cwd=self.ts_runner_dir
        # )
        # print("TS Version:", version_process.communicate()[0].decode())

        #if build_process.returncode == 0:
        if True:
            json_params = json.dumps({
               "thread_id": thread_id,
               "user_auth": user_auth,
            })

            ts_process = subprocess.Popen(["npm", "--prefix", self.ts_runner_dir, "run", "start", "agents/agent.ts", json_params], stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, cwd=self.ts_runner_dir)
            stdout, stderr = ts_process.communicate()

            print("STDOUT:", stdout.decode())
            print("STDERR:", stderr.decode())

        else:
            print("Build failed:")
            print("build_stdout", build_stdout)
            print(build_stderr.decode())

    def run(self, env: Any, task: Optional[str] = None) -> None:  # noqa: D102
        # combine agent.env_vars and env.env_vars
        total_env_vars = {**self.env_vars, **env.env_vars}

        # save os env vars
        os.environ.update(total_env_vars)
        # save env.env_vars
        env.env_vars = total_env_vars

        agent_file_exists = False

        if not self.agent_filename or True:

            print("self.temp_dir", self.temp_dir)

            if os.path.exists(os.path.join(self.temp_dir, AGENT_FILENAME_PY)):
                self.agent_filename = os.path.join(self.temp_dir, AGENT_FILENAME_PY)
                self.agent_language = "py"
                with open(self.agent_filename, "r") as agent_file:
                    self.code = compile(agent_file.read(), self.agent_filename, "exec")
            elif os.path.exists(os.path.join(self.temp_dir, AGENT_FILENAME_TS)):
                self.agent_filename = os.path.join(self.temp_dir, AGENT_FILENAME_TS)
                self.agent_language = "ts"

                # copy files from nearai/ts_runner_sdk to self.temp_dir
                # ts_runner_sdk_dir = "/Users/alice/projects/jasnah-cli/nearai/ts_runner"
                ts_runner_sdk_dir = "/tmp/ts_runner"
                ts_runner_agent_dir = os.path.join(ts_runner_sdk_dir, "agents")

                print("tempfile.gettempdir()", tempfile.gettempdir())

                def find_ts_runner(start_path='/'):
                    for dirpath, dirnames, filenames in os.walk(start_path):
                        if 'ts_runner' in dirnames:
                            return os.path.join(dirpath, 'ts_runner')
                    return None

                ts_runner_actual_path = find_ts_runner()


                if ts_runner_actual_path:
                    print(f"Папка 'ts_runner' найдена по пути: {ts_runner_actual_path}")
                else:
                    print("Папка 'ts_runner' не найдена.")

                shutil.copytree(ts_runner_actual_path, ts_runner_sdk_dir, symlinks=True, dirs_exist_ok=True)
                print(f"Папка '{ts_runner_actual_path}' скопирована в '{ts_runner_sdk_dir}'")



                print("file", os.path.join(self.temp_dir, AGENT_FILENAME_TS))
                # make dir if not exists
                if not os.path.exists(ts_runner_agent_dir):
                    os.makedirs(ts_runner_agent_dir, exist_ok=True)

                shutil.copy(os.path.join(self.temp_dir, AGENT_FILENAME_TS), ts_runner_agent_dir)


                # self.temp_dir = ts_runner_agent_dir
                self.ts_runner_dir = ts_runner_sdk_dir




            else:
                raise ValueError(f"Agent run error: {AGENT_FILENAME_PY} does not exist")

            print("self.temp_dir", self.temp_dir)

            # cache all agent files in file_cache
            for root, _, files in os.walk(self.temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    print("agent file", file_path)
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
        env.user_auth = None

        try:
            if self.change_to_temp_dir:
                if not os.path.exists(self.temp_dir):
                    os.makedirs(self.temp_dir, exist_ok=True)
                os.chdir(self.temp_dir)
            sys.path.insert(0, self.temp_dir)

            if self.agent_language == "ts":
                print("run_ts_agent try")
                process = multiprocessing.Process(target=self.run_ts_agent, args=[env._thread_id, user_auth])
                process.start()
                process.join()
            else:
                if env.agent_runner_user:
                    process = multiprocessing.Process(target=self.run_agent_code, args=[namespace, env.agent_runner_user])
                    process.start()
                    process.join()
                else:
                    self.run_agent_code(namespace, env.agent_runner_user)
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
