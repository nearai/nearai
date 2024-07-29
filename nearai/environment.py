import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import tarfile
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

import psutil
from litellm import Choices, CustomStreamWrapper, ModelResponse
from openai.types.chat import ChatCompletionMessageParam

from nearai.agent import Agent
from nearai.completion import InferenceRouter
from nearai.config import Config
from nearai.db import db
from nearai.registry import registry
from nearai.tool_registry import ToolRegistry

DELIMITER = "\n"
CHAT_FILENAME = "chat.txt"
TERMINAL_FILENAME = "terminal.txt"


class Environment(object):
    def __init__(  # noqa: D107
        self, path: str, agents: List[Agent], config: Config, create_files: bool = True
    ) -> None:
        self._path = path
        self._agents = agents
        self._done = False
        self._config = config
        assert config.llm_config is not None, "LLMConfig is not defined."
        self._inference = InferenceRouter(config.llm_config)
        self._user_name = config.user_name
        self._tools = ToolRegistry()
        self.register_standard_tools()
        if create_files:
            os.makedirs(self._path, exist_ok=True)
            open(os.path.join(self._path, CHAT_FILENAME), "a").close()
        os.chdir(self._path)

    @staticmethod
    def _generate_run_id() -> str:
        return uuid.uuid4().hex

    def get_tool_registry(self) -> ToolRegistry:  # noqa: D102
        return self._tools

    def register_standard_tools(self) -> None:  # noqa: D102
        reg = self.get_tool_registry()
        reg.register_tool(self.exec_command)
        reg.register_tool(self.read_file)
        reg.register_tool(self.write_file)
        reg.register_tool(self.request_user_input)
        reg.register_tool(self.list_files)

    def add_message(self, role: str, message: str, filename: str = CHAT_FILENAME, **kwargs: Any) -> None:  # noqa: D102
        with open(os.path.join(self._path, filename), "a") as f:
            f.write(json.dumps({"role": role, "content": message, **kwargs}) + DELIMITER)

    def list_terminal_commands(self, filename: str = TERMINAL_FILENAME) -> List[Any]:  # noqa: D102
        return self.list_messages(filename)

    def list_messages(self, filename: str = CHAT_FILENAME) -> List[Any]:  # noqa: D102
        path = os.path.join(self._path, filename)

        if not os.path.exists(path):
            return []

        with open(path, "r") as f:
            return [json.loads(message) for message in f.read().split(DELIMITER) if message]

    def list_files(self, path: str) -> List[str]:
        """Lists files in the environment.

        path: The path to list files from.
        """
        return os.listdir(os.path.join(self._path, path))

    def get_path(self) -> str:  # noqa: D102
        return self._path

    def read_file(self, filename: str) -> str:
        """Read a file from the environment.

        filename: The name of the file to read.
        """
        if not os.path.exists(os.path.join(self._path, filename)):
            return ""
        try:
            with open(os.path.join(self._path, filename), "r") as f:
                return f.read()
        except Exception as e:
            return f"failed to read file: {e}"

    def write_file(self, filename: str, content: str) -> str:
        """Writes a file to the environment.

        filename: The name of the file to write to
        content: The content to write to the file.
        """
        path = Path(self._path) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        return f"Successfully wrote {len(content) if content else 0} characters to {filename}"

    def exec_command(self, command: str) -> Dict[str, Union[str, int]]:
        """Executes a command in the environment and logs the output.

        The environment does not allow running interactive programs. It will run a program for 1 second then will interrupt it if it is still running or if it is waiting for user input.
        command: The command to execute, like 'ls -l' or 'python3 tests.py'
        """  # noqa: E501
        if self._config.get("confirm_commands", True):
            yes_no = input("> Do you want to run the following command? (Y/n): " + command)
            if yes_no != "" and yes_no.lower() != "y":
                return {
                    "command": command,
                    "returncode": 999,
                    "stdout": "",
                    "stderr": "declined by user",
                }

        try:
            process = subprocess.Popen(
                shlex.split(command),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
                universal_newlines=True,
                cwd=self._path,
            )
        except Exception as e:
            return {
                "command": command,
                "returncode": 999,
                "stdout": "",
                "stderr": "Failed to execute: " + str(e),
            }

        msg = ""

        def kill_process_tree(p: Any) -> None:
            nonlocal msg
            msg = "Killing process due to timeout"

            process = psutil.Process(p.pid)
            for proc in process.children(recursive=True):
                proc.kill()
            process.kill()

        timer = threading.Timer(2, kill_process_tree, (process,))
        timer.start()
        process.wait()
        timer.cancel()

        result = {
            "command": command,
            "stdout": process.stdout.read() if process.stdout and hasattr(process.stdout, "read") else "",
            "stderr": process.stderr.read() if process.stderr and hasattr(process.stderr, "read") else "",
            "returncode": process.returncode,
            "msg": msg,
        }
        with open(os.path.join(self._path, TERMINAL_FILENAME), "a") as f:
            f.write(json.dumps(result) + DELIMITER)
        return result

    def completions(
        self, model: str, messages: Iterable[ChatCompletionMessageParam], stream: bool = False, **kwargs: Any
    ) -> Union[ModelResponse, CustomStreamWrapper]:
        """Returns all completions for given messages using the given model."""
        return self._inference.completions(model, messages, stream=stream, **kwargs)

    def completions_and_run_tools(
        self,
        model: str,
        messages: Iterable[ChatCompletionMessageParam],
        tools: Optional[List] = None,
        **kwargs: Any,
    ) -> ModelResponse:
        """Returns all completions for given messages using the given model and runs tools."""
        raw_response = self._inference.completions(model, messages, stream=False, tools=tools, **kwargs)
        assert isinstance(raw_response, ModelResponse), "Expected ModelResponse"
        response: ModelResponse = raw_response
        assert all(map(lambda choice: isinstance(choice, Choices), response.choices)), "Expected Choices"
        choices: List[Choices] = response.choices  # type: ignore
        response_message = choices[0].message
        if hasattr(response_message, "tool_calls") and response_message.tool_calls:
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                assert function_name, "Tool call must have a function name"
                function_args = json.loads(tool_call.function.arguments)
                function_response = self._tools.call_tool(function_name, **function_args)

                if function_response:
                    function_response_json = json.dumps(function_response) if function_response else ""
                    self.add_message("tool", function_response_json, tool_call_id=tool_call.id, name=function_name)
        return response

    def completion(self, model: str, messages: Iterable[ChatCompletionMessageParam]) -> str:
        """Returns a completion for the given messages using the given model."""
        raw_response = self.completions(model, messages)
        assert isinstance(raw_response, ModelResponse), "Expected ModelResponse"
        response: ModelResponse = raw_response
        assert all(map(lambda choice: isinstance(choice, Choices), response.choices)), "Expected Choices"
        choices: List[Choices] = response.choices  # type: ignore
        response_message = choices[0].message.content
        assert response_message, "No completions returned"
        return response_message

    def completion_and_run_tools(
        self,
        model: str,
        messages: Iterable[ChatCompletionMessageParam],
        tools: Optional[List] = None,
        **kwargs: Any,
    ) -> str:
        """Returns a completion for the given messages using the given model and runs tools."""
        completion_tools_response = self.completions_and_run_tools(model, messages, tools, **kwargs)
        assert all(
            map(lambda choice: isinstance(choice, Choices), completion_tools_response.choices)
        ), "Expected Choices"
        choices: List[Choices] = completion_tools_response.choices  # type: ignore
        response_message = choices[0].message.content
        assert response_message, "No completions returned"
        return response_message

    def call_agent(self, agent_path: int, task: str) -> None:
        """Calls agent with given task."""
        self._agents[agent_path].run(self, task=task)

    def get_agents(self) -> List[Agent]:
        """Returns list of agents available in environment."""
        return self._agents

    def is_done(self) -> bool:  # noqa: D102
        return self._done

    def mark_done(self) -> None:  # noqa: D102
        self._done = True

    def create_snapshot(self) -> bytes:
        """Create an in memory snapshot."""
        with tempfile.NamedTemporaryFile(suffix=".tar.gz") as f:
            with tarfile.open(fileobj=f, mode="w:gz") as tar:
                tar.add(self._path, arcname=".")
            f.flush()
            f.seek(0)
            snapshot = f.read()
        return snapshot

    def save_to_registry(
        self,
        path: str,
        run_type: str,
        run_id: str,
        base_id: Optional[Union[str, int]] = None,
        run_name: Optional[str] = None,
    ) -> Optional[bytes]:
        """Save Environment to Registry."""
        author = self._user_name
        if not author:
            print(
                "Warning: No author specified in config. Run not saved to registry."
                " To set an author run `nearai config set user_name <YOUR_NAME>`"
            )
            return None

        agent_name = self._agents[0].name if self._agents else "unknown"
        generated_name = f"environment_run_{agent_name}_{run_id}"
        if run_name:
            if db.get_registry_entry_by_identifier(run_name, fail_if_not_found=False):
                print(
                    f"Warning: Run with name '{run_name}' already exists in registry. "
                    f"Using generated name '{generated_name}' instead."
                )
                name = generated_name
            else:
                name = run_name
        else:
            name = generated_name

        with tempfile.NamedTemporaryFile(suffix=".tar.gz") as f:
            with tarfile.open(fileobj=f, mode="w:gz") as tar:
                tar.add(path, arcname=".")
            f.flush()
            f.seek(0)
            snapshot = f.read()
            tar_filename = f.name

            s3_path = f"environments/{run_id}"
            timestamp = datetime.now(timezone.utc).isoformat()
            description = f"Agent {run_type} run {agent_name} {run_id} {timestamp}"
            details = {
                "base_id": base_id,
                "timestamp": timestamp,
                "agents": [agent.name for agent in self._agents],
                "run_id": run_id,
                "run_type": run_type,
                "filename": tar_filename,
            }
            tags_l = ["environment"]
            registry_id = registry.upload(
                path=Path(tar_filename),
                s3_path=s3_path,
                author=author,
                description=description,
                name=name,
                details=details,
                show_entry=True,
                tags=tags_l,
            )
            print(
                f"Saved environment {registry_id} to registry. To load use flag `--load-env={registry_id}`. "
                f"or `--load-env={name}`"
            )
            return snapshot

    def load_snapshot(self, snapshot: bytes) -> None:
        """Load Environment from Snapshot."""
        shutil.rmtree(self._path, ignore_errors=True)

        with tempfile.NamedTemporaryFile(suffix=".tar.gz") as f:
            f.write(snapshot)
            f.flush()
            f.seek(0)

            with tarfile.open(fileobj=f, mode="r:gz") as tar:
                tar.extractall(self._path)

    def load_from_registry(self, load_env: Union[str, int]) -> str:  # noqa: D102
        print(f"Loading environment from {load_env} {type(load_env)} to {self._path}")
        directory = registry.download(load_env)
        files = os.listdir(directory)
        tarfile_file = next(f for f in files if f.endswith(".tar.gz"))

        with tarfile.open(directory / tarfile_file, "r") as tar:
            tar.extractall(self._path)
        return directory.name

    def __str__(self) -> str:  # noqa: D105
        return f"Environment({self._path})"

    def run_agent(self, task: Optional[str]) -> None:  # noqa: D102
        self._agents[0].run(self, task=task)

    def request_user_input(self) -> None:
        """Must be called to request input from the user."""
        self.set_next_actor("user")

    def set_next_actor(self, who: str) -> None:  # noqa: D102
        next_action_fn = os.path.join(self._path, ".next_action")

        with open(next_action_fn, "w") as f:
            f.write(who)

    def get_next_actor(self) -> str:  # noqa: D102
        next_action_fn = os.path.join(self._path, ".next_action")

        if os.path.exists(next_action_fn):
            with open(next_action_fn) as f:
                return f.read().strip(" \n")
        else:
            # By default the user starts the conversation.
            return "user"

    def run_interactive(self, record_run: str = "", load_env: str = "") -> None:
        """Run an interactive session within the given environment."""
        run_id = self._generate_run_id()
        if load_env:
            base_id = self.load_from_registry(load_env)
        else:
            base_id = None
        last_message_idx = 0

        def print_messages(last_message_idx: int) -> int:
            messages = self.list_messages()
            for item in messages[last_message_idx:]:
                print(f"[{item['role']}]: {item['content']}", flush=True)
            return len(messages)

        last_message_idx = print_messages(last_message_idx)

        iteration_count = 0
        while True:
            if self.get_next_actor() != "user":
                messages = self.list_messages()
                new_message = None if not messages else messages[-1]["content"]

                iteration_count += 1
                self.run_agent(new_message)

                last_message_idx = print_messages(last_message_idx)
                if self.is_done():
                    break

            else:
                new_message = input("> ")
                if new_message == "exit":
                    break
                self.add_message("user", new_message)

                self.set_next_actor("agent")

        if record_run:
            run_name = record_run if record_run and record_run != "true" else None
            self.save_to_registry(self._path, "interactive", run_id, base_id, run_name)

    def run_task(
        self,
        task: str,
        record_run: str = "",
        load_env: str = "",
        max_iterations: int = 10,
    ) -> None:
        """Runs a task within the given environment."""
        run_id = self._generate_run_id()
        if load_env:
            base_id = self.load_from_registry(load_env)
        else:
            base_id = None
        iteration = 0

        if task:
            self.add_message("user", task)

        while iteration < max_iterations and not self.is_done():
            iteration += 1
            self._agents[0].run(self, task=task)

        if record_run:
            run_name = record_run if record_run and record_run != "true" else None
            self.save_to_registry(self._path, "task", run_id, base_id, run_name)

    def inspect(self) -> None:  # noqa: D102
        filename = Path(os.path.abspath(__file__)).parent / "streamlit_inspect.py"
        subprocess.call(["streamlit", "run", filename, "--", self._path])

    def contains_non_empty_chat_txt(self, directory: str) -> bool:  # noqa: D102
        chat_txt_path = os.path.join(directory, "chat.txt")
        return os.path.isfile(chat_txt_path) and os.path.getsize(chat_txt_path) > 0

    def save_folder(self, name: Optional[str] = None) -> None:  # noqa: D102
        path = self._path
        temp_dir = None

        def copy_relevant_folders(src: str, dest: str) -> None:
            for item in os.listdir(src):
                s = os.path.join(src, item)
                d = os.path.join(dest, item)
                if os.path.isdir(s):
                    if self.contains_non_empty_chat_txt(s):
                        shutil.copytree(s, d)
                    else:
                        os.makedirs(d, exist_ok=True)
                        copy_relevant_folders(s, d)
                        if not os.listdir(d):
                            os.rmdir(d)

        if not self.contains_non_empty_chat_txt(path):
            temp_dir = tempfile.mkdtemp()
            copy_relevant_folders(path, temp_dir)
            path = temp_dir

        try:
            if not os.listdir(path):
                raise ValueError(f"No files found in {path}")

            self.save_to_registry(
                path, "folders" if temp_dir else "folder", self.generate_folder_hash_id(path), None, name
            )
        finally:
            if temp_dir:
                shutil.rmtree(temp_dir)

    def save_from_history(self, lines: List[str], name: Optional[str] = None) -> None:  # noqa: D102
        # Parse lines and extract relevant information
        pattern = r"^\s*(?:\d+\s+)?(\S+)\s+environment\s+interactive\s+(\S+)\s+(\S+)(.*?)$"
        relevant_paths = {}
        for line in lines:
            match = re.match(pattern, line)
            if match:
                program_name, agents, path, other_args = match.groups()
                path = path.strip("/")
                if self.contains_non_empty_chat_txt(path):
                    command = f"{program_name} environment interactive {agents} {path} {other_args}"
                    relevant_paths[path] = {"command": command.strip()}

        if not relevant_paths:
            raise ValueError("No relevant paths with non-empty chat.txt files found in history")

        for path, info in relevant_paths.items():
            print(path)
            # Write start_command.log
            with open(os.path.join(path, "start_command.log"), "w") as f:
                f.write(info["command"])

        # Create temporary directory and copy relevant folders
        temp_dir = tempfile.mkdtemp()
        try:
            for path, _info in relevant_paths.items():
                dest = os.path.join(temp_dir, path.replace("/", "_").strip("_"))
                shutil.copytree(path, dest)
            self.save_to_registry(temp_dir, "folders", self.generate_folder_hash_id(temp_dir), None, name)

        finally:
            shutil.rmtree(temp_dir)

    def generate_folder_hash_id(self, path: str) -> str:
        """Returns id similar to _generate_run_id(), but based on files and their contents in path, including subfolders."""  # noqa: E501
        hash_obj = hashlib.md5()

        for root, _dirs, files in os.walk(path):
            for file in sorted(files):
                file_path = os.path.join(root, file)
                with open(file_path, "rb") as f:
                    while chunk := f.read(8192):
                        hash_obj.update(chunk)

        return hash_obj.hexdigest()
