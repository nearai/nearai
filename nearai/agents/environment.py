import hashlib
import io
import json
import logging
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
from typing import Any, Dict, Iterable, List, Literal, Optional, Tuple, Union, cast

import psutil
import shared.near.sign as near
from litellm.types.completion import ChatCompletionMessageParam
from litellm.types.utils import (
    ChatCompletionMessageToolCall,
    Choices,
    Function,
    ModelResponse,
)
from litellm.utils import CustomStreamWrapper
from openai import NOT_GIVEN, NotGiven, OpenAI
from openai.types.beta.threads.message import Message
from openai.types.beta.threads.message_create_params import Attachment
from openai.types.beta.threads.run import Run
from openai.types.beta.vector_store import VectorStore
from openai.types.file_object import FileObject
from shared.client_config import DEFAULT_PROVIDER_MODEL
from shared.inference_client import InferenceClient
from shared.models import (
    AutoFileChunkingStrategyParam,
    ChunkingStrategy,
    ExpiresAfter,
    GitHubSource,
    GitLabSource,
    StaticFileChunkingStrategyParam,
)

from nearai.agents import tool_json_helper
from nearai.agents.agent import Agent
from nearai.agents.tool_registry import ToolRegistry

DELIMITER = "\n"
CHAT_FILENAME = "chat.txt"
SYSTEM_LOG_FILENAME = "system_log.txt"
AGENT_LOG_FILENAME = "agent_log.txt"
TERMINAL_FILENAME = "terminal.txt"

LLAMA_TOOL_FORMAT_PATTERN = re.compile(r"(.*?)<function=(\w+)>(.*?)(</function>|$|\Z)(.*?)", re.DOTALL | re.MULTILINE)

default_approvals: Dict[str, Any] = {"confirm_execution": lambda _: True}


class Environment(object):
    def __init__(  # noqa: D107
        self,
        path: str,
        agents: List[Agent],
        client: InferenceClient,
        hub_client: OpenAI,
        thread_id: str,
        run_id: str,
        model: str,
        create_files: bool = True,
        env_vars: Optional[Dict[str, Any]] = None,
        tool_resources: Optional[Dict[str, Any]] = None,
        print_system_log: bool = False,
        approvals: Optional[Dict[str, Any]] = default_approvals,
    ) -> None:
        self._path = path
        self._agents = agents
        self._done = False
        self._client = client
        self._tools = ToolRegistry()
        self.register_standard_tools()
        self.env_vars: Dict[str, Any] = env_vars if env_vars else {}
        self._last_used_model = ""
        self.tool_resources: Dict[str, Any] = tool_resources if tool_resources else {}
        self.print_system_log = print_system_log
        self._approvals = approvals
        self._hub_client = hub_client
        self._thread_id = thread_id
        self._model = model
        self._run_id = run_id

        if create_files:
            os.makedirs(self._path, exist_ok=True)
            open(os.path.join(self._path, CHAT_FILENAME), "a").close()
        os.chdir(self._path)

    @staticmethod
    def _generate_run_id() -> str:
        return uuid.uuid4().hex

    def get_tool_registry(self) -> ToolRegistry:
        """Returns the tool registry, a dictionary of tools that can be called by the agent."""
        return self._tools

    def register_standard_tools(self) -> None:  # noqa: D102
        reg = self.get_tool_registry()
        reg.register_tool(self.exec_command)
        reg.register_tool(self.read_file)
        reg.register_tool(self.write_file)
        reg.register_tool(self.request_user_input)
        reg.register_tool(self.list_files)
        reg.register_tool(self.query_vector_store)

    def add_message(
        self,
        role: Literal["user", "assistant"],
        message: str,
        filename: str = CHAT_FILENAME,
        attachments: Optional[Iterable[Attachment]] = None,
        **kwargs: Any,
    ):
        """Assistant adds a message to the environment."""
        return self._hub_client.beta.threads.messages.create(
            thread_id=self._thread_id,
            role=role,
            content=message,
            extra_body={"assistant_id": self._agents[0].identifier, "run_id": self._run_id},
            metadata=kwargs,
            attachments=attachments,
        )

    def add_system_log(self, log: str, level: int = logging.INFO) -> None:
        """Add system log with timestamp and log level."""
        logger = logging.getLogger("system_logger")
        if not logger.handlers:
            # Configure the logger if it hasn't been set up yet
            logger.setLevel(logging.DEBUG)
            file_handler = logging.FileHandler(os.path.join(self._path, SYSTEM_LOG_FILENAME))
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

            if self.print_system_log:
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(formatter)
                logger.addHandler(console_handler)

        # Log the message
        logger.log(level, log)
        # Force the handler to write to disk
        for handler in logger.handlers:
            handler.flush()

    def add_agent_log(self, log: str, level: int = logging.INFO) -> None:
        """Add agent log with timestamp and log level."""
        logger = logging.getLogger("agent_logger")
        if not logger.handlers:
            # Configure the logger if it hasn't been set up yet
            logger.setLevel(logging.DEBUG)
            file_handler = logging.FileHandler(os.path.join(self._path, AGENT_LOG_FILENAME))
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        # Log the message
        logger.log(level, log)
        # Force the handler to write to disk
        for handler in logger.handlers:
            handler.flush()

    def add_agent_start_system_log(self, agent_idx: int) -> None:
        """Adds agent start system log."""
        agent = self._agents[agent_idx]
        message = f"Running agent {agent.name}"
        if agent.model != "":
            model = self.get_model_for_inference(agent.model)
            self._last_used_model = model
            message += f" that will connect to {model}"
            if agent.model_temperature:
                message += f", temperature={agent.model_temperature}"
            if agent.model_max_tokens:
                message += f", max_tokens={agent.model_max_tokens}"
        self.add_system_log(message)

    def list_terminal_commands(self, filename: str = TERMINAL_FILENAME) -> List[Any]:
        """Returns the terminal commands from the terminal file."""
        path = os.path.join(self._path, filename)

        if not os.path.exists(path):
            return []

        with open(path, "r") as f:
            return [json.loads(message) for message in f.read().split(DELIMITER) if message]

    def list_messages(self, limit: Union[int, NotGiven] = NOT_GIVEN) -> List[Message]:
        """Returns messages from the environment."""
        messages = self._hub_client.beta.threads.messages.list(self._thread_id, limit=limit)
        self.add_system_log(f"Retrieved {len(messages.data)} messages from NearAI Hub")
        return messages.data

    def verify_message(
        self,
        account_id: str,
        public_key: str,
        signature: str,
        message: str,
        nonce: str,
        callback_url: str,
    ) -> near.SignatureVerificationResult:
        """Verifies that the user message is signed with NEAR Account."""
        return near.verify_signed_message(
            account_id,
            public_key,
            signature,
            message,
            nonce,
            self._agents[0].name,
            callback_url,
        )

    def list_files(self, path: str) -> List[FileObject]:
        """Lists files in the thread."""
        messages = self.list_messages()
        # Extract attachments from messages
        attachments = [a for m in messages if m.attachments for a in m.attachments]
        # Extract files from attachments
        file_ids = [a.file_id for a in attachments]
        files = [self._hub_client.files.retrieve(f) for f in file_ids if f]
        return files

    def get_path(self) -> str:
        """Returns the path of the current directory."""
        return self._path

    def read_file(self, file_id: str):
        """Read a file from the thread."""
        return self._hub_client.files.content(file_id)

    def write_file(
        self, filename: str, content: str, encoding: str = "utf-8", filetype: str = "text/plain"
    ) -> FileObject:
        """Writes a file to the environment.

        filename: The name of the file to write to
        content: The content to write to the file.
        """
        file_data = io.BytesIO(content.encode(encoding))
        file = self._hub_client.files.create(file=(filename, file_data, filetype), purpose="assistants")
        res = self.add_message(
            role="assistant",
            message=f"Uploaded file {filename} with {len(content)} characters",
            attachments=[{"file_id": file.id, "tools": [{"type": "file_search"}]}],
        )
        self.add_system_log(
            f"Uploaded file {filename} with {len(content)} characters, id: {file.id}. Added in thread as: {res.id}"
        )
        return file

    def query_vector_store(self, vector_store_id: str, query: str):
        """Queries a vector store.

        vector_store_id: The id of the vector store to query.
        query: The query to search for.
        """
        return self._client.query_vector_store(vector_store_id, query)

    def upload_file(
        self,
        file_content: str,
        purpose: Literal["assistants", "batch", "fine-tune", "vision"] = "assistants",
    ):
        """Uploads a file to the registry."""
        return self._client.upload_file(file_content, purpose)

    def create_vector_store_from_source(
        self,
        name: str,
        source: Union[GitHubSource, GitLabSource],
        source_auth: Optional[str] = None,
        chunking_strategy: Optional[ChunkingStrategy] = None,
        expires_after: Optional[ExpiresAfter] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> VectorStore:
        """Creates a vector store from the given source.

        Args:
        ----
            name: The name of the vector store.
            source: The source from which to create the vector store.
            source_auth: The source authentication token.
            chunking_strategy: The chunking strategy to use.
            expires_after: The expiration policy.
            metadata: Additional metadata.

        Returns:
        -------
            VectorStore: The created vector store.

        """
        return self._client.create_vector_store_from_source(
            name=name,
            source=source,
            source_auth=source_auth,
            chunking_strategy=chunking_strategy,
            expires_after=expires_after,
            metadata=metadata,
        )

    def add_file_to_vector_store(self, vector_store_id: str, file_id: str):
        """Adds a file to the vector store."""
        return self._client.add_file_to_vector_store(vector_store_id, file_id)

    def create_vector_store(
        self,
        name: str,
        file_ids: list,
        expires_after: ExpiresAfter | NotGiven = NOT_GIVEN,
        chunking_strategy: AutoFileChunkingStrategyParam | StaticFileChunkingStrategyParam | NotGiven = NOT_GIVEN,
        metadata: Optional[Dict[str, str]] = None,
    ) -> VectorStore:
        """Creates a vector store.

        Args:
        ----
            name: The name of the vector store.
            file_ids: List of file ids to create the vector store.
            chunking_strategy: The chunking strategy to use.
            expires_after: The expiration policy.
            metadata: Additional metadata.

        Returns:
        -------
            VectorStore: The created vector store.

        """
        return self._client.create_vector_store(
            name=name,
            file_ids=file_ids,
            chunking_strategy=chunking_strategy,
            expires_after=expires_after,
            metadata=metadata,
        )

    def get_vector_store(self, vector_store_id: str) -> VectorStore:
        """Gets a vector store by id."""
        return self._client.get_vector_store(vector_store_id)

    def exec_command(self, command: str) -> Dict[str, Union[str, int]]:
        """Executes a command in the environment and logs the output.

        The environment does not allow running interactive programs.
        It will run a program for 1 second then will interrupt it if it is still running
        or if it is waiting for user input.
        command: The command to execute, like 'ls -l' or 'python3 tests.py'
        """
        approval_function = self._approvals["confirm_execution"] if self._approvals else None
        if not approval_function:
            return {
                "stderr": "Agent runner misconfiguration. No command execution approval function found.",
            }
        if not approval_function(command):
            return {
                "command": command,
                "returncode": 999,
                "stdout": "",
                "stderr": "Command execution was not approved.",
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

    def get_model_for_inference(self, model: str = "") -> str:
        """Returns 'provider::model_full_path'."""
        provider = self._agents[0].model_provider if self._agents else ""
        if model == "":
            model = self._agents[0].model if self._agents else ""
        if model == "":
            return DEFAULT_PROVIDER_MODEL
        _, model = self._client.provider_models.match_provider_model(model, provider)
        return model

    def _run_inference_completions(
        self,
        messages: Iterable[ChatCompletionMessageParam] | str,
        model: Iterable[ChatCompletionMessageParam] | str,
        stream: bool,
        **kwargs: Any,
    ) -> Union[ModelResponse, CustomStreamWrapper]:
        """Run inference completions for given parameters."""
        if isinstance(messages, str):
            self.add_system_log(
                "Deprecated completions call. Pass `messages` as a first parameter.",
                logging.WARNING,
            )
            messages_or_model = messages
            model_or_messages = model
            model = cast(str, messages_or_model)
            messages = cast(Iterable[ChatCompletionMessageParam], model_or_messages)
        else:
            model = cast(str, model)
            messages = cast(Iterable[ChatCompletionMessageParam], messages)
        model = self.get_model_for_inference(model)
        if model != self._last_used_model:
            self._last_used_model = model
            self.add_system_log(f"Connecting to {model}")
        return self._client.completions(
            model,
            messages,
            stream=stream,
            temperature=self._agents[0].model_temperature if self._agents else None,
            max_tokens=self._agents[0].model_max_tokens if self._agents else None,
            **kwargs,
        )

    # TODO(286): `messages` may be model and `model` may be messages temporarily to support deprecated API.
    def completions(
        self,
        messages: Iterable[ChatCompletionMessageParam] | str,
        model: Iterable[ChatCompletionMessageParam] | str = "",
        stream: bool = False,
        **kwargs: Any,
    ) -> Union[ModelResponse, CustomStreamWrapper]:
        """Returns all completions for given messages using the given model."""
        return self._run_inference_completions(messages, model, stream, **kwargs)

    def completions_and_run_tools(
        self,
        messages: List[ChatCompletionMessageParam],
        model: str = "",
        tools: Optional[List] = None,
        add_responses_to_messages: bool = True,
        agent_role_name="agent",
        tool_role_name="tool",
        **kwargs: Any,
    ) -> ModelResponse:
        """Returns all completions for given messages using the given model and runs tools."""
        if self._use_llama_tool_syntax(model, tools):
            tool_prompt = self._llama_tool_prompt(tools)
            messages.append({"role": "system", "content": tool_prompt})
        raw_response = self._run_inference_completions(messages, model, stream=False, tools=tools, **kwargs)
        assert isinstance(raw_response, ModelResponse), "Expected ModelResponse"
        response: ModelResponse = raw_response
        assert all(map(lambda choice: isinstance(choice, Choices), response.choices)), "Expected Choices"
        choices: List[Choices] = response.choices  # type: ignore
        response_message = choices[0].message

        self._handle_tool_calls(response_message, add_responses_to_messages, agent_role_name, tool_role_name)

        return response

    def _handle_tool_calls(
        self,
        response_message,
        add_responses_to_messages,
        agent_role_name,
        tool_role_name,
    ):
        (message_without_tool_call, tool_calls) = self._parse_tool_call(response_message)
        if add_responses_to_messages and response_message.content:
            self.add_message(agent_role_name, message_without_tool_call)
        if tool_calls:
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                try:
                    assert function_name, "Tool call must have a function name"
                    function_signature = self.get_tool_registry().get_tool_definition(function_name)
                    assert function_signature, f"Tool {function_name} not found"
                    args = tool_call.function.arguments
                    function_args = tool_json_helper.parse_json_args(function_signature, args)
                    self.add_system_log(f"Calling tool {function_name} with args {function_args}")
                    function_response = self._tools.call_tool(function_name, **function_args if function_args else {})

                    if function_response:
                        function_response_json = json.dumps(function_response) if function_response else ""
                        if add_responses_to_messages:
                            self.add_message(
                                tool_role_name,
                                function_response_json,
                                tool_call_id=tool_call.id,
                                name=function_name,
                            )
                except Exception as e:
                    error_message = f"Error calling tool {function_name}: {e}"
                    self.add_system_log(error_message, level=logging.ERROR)
                    if add_responses_to_messages:
                        self.add_message(
                            tool_role_name,
                            error_message,
                            tool_call_id=tool_call.id,
                            name=function_name,
                        )

    @staticmethod
    def _parse_tool_call(
        response_message,
    ) -> Tuple[Optional[str], Optional[List[ChatCompletionMessageToolCall]]]:
        if hasattr(response_message, "tool_calls") and response_message.tool_calls:
            return response_message.content, response_message.tool_calls
        content = response_message.content
        if content is None:
            return None, None
        llama_matches = LLAMA_TOOL_FORMAT_PATTERN.findall(content)
        if llama_matches:
            text = ""
            tool_calls = []
            for llama_match in llama_matches:
                before_call_text, function_name, args, end_tag, after_call_text = llama_match
                function = Function(name=function_name, arguments=args)
                tool_call = ChatCompletionMessageToolCall(id=str(uuid.uuid4()), function=function)
                text += before_call_text + after_call_text
                tool_calls.append(tool_call)
            return text, tool_calls
        return content, None

    @staticmethod
    def _use_llama_tool_syntax(model: str, tools: Optional[List]) -> bool:
        return tools is not None and "llama" in model

    @staticmethod
    def _llama_tool_prompt(tools: Optional[List]) -> str:
        return (
            """Answer the user's question by making use of the following functions if needed.
            If none of the function can be used, please say so.
            Here is a list of functions in JSON format:"""
            + json.dumps(tools)
            + """Think very carefully before calling functions.
            If you choose to call a function ONLY reply in the following format with no prefix or suffix:

            <function=example_function_name>{"example_name": "example_value"}</function>

            Reminder:
            - Function calls MUST follow the specified format, start with <function= and end with </function>
            - Function arguments MUST be in JSON format using double quotes
            - Required parameters MUST be specified
            - Multiple functions can be called in one message as long as they are on separate lines.
            - Put the entire function call reply on one line
        """
        )

    # TODO(286): `messages` may be model and `model` may be messages temporarily to support deprecated API.
    def completion(
        self,
        messages: Iterable[ChatCompletionMessageParam] | str,
        model: Iterable[ChatCompletionMessageParam] | str = "",
    ) -> str:
        """Returns a completion for the given messages using the given model."""
        raw_response = self.completions(messages, model)
        assert isinstance(raw_response, ModelResponse), "Expected ModelResponse"
        response: ModelResponse = raw_response
        assert all(map(lambda choice: isinstance(choice, Choices), response.choices)), "Expected Choices"
        choices: List[Choices] = response.choices  # type: ignore
        response_message = choices[0].message.content
        assert response_message, "No completions returned"
        return response_message

    def completion_and_run_tools(
        self,
        messages: List[ChatCompletionMessageParam],
        model: str = "",
        tools: Optional[List] = None,
        **kwargs: Any,
    ) -> Optional[str]:
        """Returns a completion for the given messages using the given model and runs tools."""
        completion_tools_response = self.completions_and_run_tools(messages, model, tools, **kwargs)
        assert all(
            map(
                lambda choice: isinstance(choice, Choices),
                completion_tools_response.choices,
            )
        ), "Expected Choices"
        choices: List[Choices] = completion_tools_response.choices  # type: ignore
        response_content = choices[0].message.content
        return response_content

    def call_agent(self, agent_index: int, task: str) -> None:
        """Calls agent with given task."""
        self._agents[agent_index].run(self, task=task)

    def get_agents(self) -> List[Agent]:
        """Returns list of agents available in environment."""
        return self._agents

    def get_primary_agent(self) -> Agent:
        """Returns the agent that is invoked first."""
        return self._agents[0]

    def is_done(self) -> bool:  # noqa: D102
        return self._done

    def mark_done(self) -> Run:  # noqa: D102
        self._done = True
        self.add_system_log("Marking environment run as completed", logging.INFO)
        res = self._hub_client.beta.threads.runs.update(
            thread_id=self._thread_id,
            run_id=self._run_id,
            extra_body={"status": "completed", "completed_at": datetime.now().isoformat()},
        )
        self.add_system_log("Environment run completed", logging.INFO)
        return res

    def create_snapshot(self) -> bytes:
        """Create an in memory snapshot."""
        with tempfile.NamedTemporaryFile(suffix=".tar.gz") as f:
            with tarfile.open(fileobj=f, mode="w:gz") as tar:
                tar.add(self._path, arcname=".")
            f.flush()
            f.seek(0)
            snapshot = f.read()
        return snapshot

    def environment_run_info(self, run_id, base_id, run_type) -> dict:
        """Returns the environment run information."""
        if not self._agents or not self._agents[0]:
            raise ValueError("Agent not found")
        primary_agent = self._agents[0]

        full_agent_name = "/".join([primary_agent.namespace, primary_agent.name, primary_agent.version])
        safe_agent_name = full_agent_name.replace("/", "_")
        generated_name = f"environment_run_{safe_agent_name}_{run_id}"
        name = generated_name

        timestamp = datetime.now(timezone.utc).isoformat()
        return {
            "name": name,
            "version": "0",
            "description": f"Agent {run_type} {full_agent_name} {run_id} {timestamp}",
            "category": "environment",
            "tags": ["environment"],
            "details": {
                "base_id": base_id,
                "timestamp": timestamp,
                "agents": [agent.name for agent in self._agents],
                "primary_agent_namespace": primary_agent.namespace,
                "primary_agent_name": primary_agent.name,
                "primary_agent_version": primary_agent.version,
                "run_id": run_id,
                "run_type": run_type,
            },
            "show_entry": True,
        }

    def load_snapshot(self, snapshot: bytes) -> None:
        """Load Environment from Snapshot."""
        shutil.rmtree(self._path, ignore_errors=True)

        with tempfile.NamedTemporaryFile(suffix=".tar.gz") as f:
            f.write(snapshot)
            f.flush()
            f.seek(0)

            with tarfile.open(fileobj=f, mode="r:gz") as tar:
                tar.extractall(self._path)

    def __str__(self) -> str:  # noqa: D105
        return f"Environment({self._path})"

    def run_agent(self, task: Optional[str]) -> None:  # noqa: D102
        self._agents[0].run(self, task=task)

    def request_user_input(self) -> Run:
        """Must be called to request input from the user."""
        return self._hub_client.beta.threads.runs.update(
            thread_id=self._thread_id,
            run_id=self._run_id,
            extra_body={"status": "requires_action"},
        )

    def clear_temp_agent_files(self) -> None:
        """Remove temp agent files created to be used in `runpy`."""
        for agent in self._agents:
            if agent.temp_dir and os.path.exists(agent.temp_dir):
                shutil.rmtree(agent.temp_dir)

    def set_next_actor(self, who: str) -> None:
        """Set the next actor / action in the dialogue."""
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

    def run(
        self,
        new_message: Optional[str] = None,
        max_iterations: int = 10,
    ) -> str:
        """Runs agent(s) against a new or previously created environment."""
        run_id = self._generate_run_id()
        iteration = 0
        self.set_next_actor("agent")

        if new_message:
            self.add_message("user", new_message)

        while iteration < max_iterations and not self.is_done() and self.get_next_actor() != "user":
            iteration += 1
            print([x.identifier for x in self._agents])
            self._agents[0].run(self, task=new_message)

        return run_id

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
