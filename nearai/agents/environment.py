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
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List, Literal, Optional, Tuple, Union, cast

import psutil
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
from openai.types.file_object import FileObject
from openai.types.vector_store import VectorStore
from openai.types.vector_stores import VectorStoreFile
from py_near.account import Account
from py_near.constants import DEFAULT_ATTACHED_GAS

import nearai.shared.near.sign as near
from nearai.agents import tool_json_helper
from nearai.agents.agent import Agent
from nearai.agents.tool_registry import ToolRegistry
from nearai.shared.client_config import DEFAULT_PROVIDER_MODEL
from nearai.shared.inference_client import InferenceClient
from nearai.shared.models import (
    AutoFileChunkingStrategyParam,
    ChunkingStrategy,
    ExpiresAfter,
    GitHubSource,
    GitLabSource,
    RunMode,
    StaticFileChunkingStrategyObjectParam,
    ThreadMode,
)
from nearai.shared.near.sign import (
    CompletionSignaturePayload,
    validate_completion_signature,
)
from nearai.shared.secure_openai_clients import SecureAsyncOpenAI, SecureOpenAI

DELIMITER = "\n"
CHAT_FILENAME = "chat.txt"
SYSTEM_LOG_FILENAME = "system_log.txt"
AGENT_LOG_FILENAME = "agent_log.txt"
TERMINAL_FILENAME = "terminal.txt"

LLAMA_TOOL_FORMAT_PATTERN = re.compile(r"(.*?)<function=(\w+)>(.*?)(</function>|$|\Z)(.*?)", re.DOTALL | re.MULTILINE)
LLAMA_TOOL_FORMAT_PATTERN2 = re.compile(r"(.*)<tool_call>\n(.*)\n</tool_call>(.*)", re.DOTALL)


default_approvals: Dict[str, Any] = {"confirm_execution": lambda _: True}


class InferenceParameters:
    def __init__(  # noqa: D107
        self,
        model: str,
        messages: Iterable[ChatCompletionMessageParam],
        stream: bool,
        temperature=None,
        max_tokens=None,
    ):
        self.model = model
        self.messages = messages
        self.stream = stream
        self.temperature = temperature
        self.max_tokens = max_tokens


class CustomLogHandler(logging.Handler):
    def __init__(self, add_reply_func, namespace: str):  # noqa: D107
        super().__init__()
        self.add_reply_func = add_reply_func
        self.namespace = namespace

    def emit(self, record):  # noqa: D102
        log_entry = self.format(record)
        self.add_reply_func(message=log_entry, message_type=f"{self.namespace}:log")


class Environment(object):
    def __init__(  # noqa: D107
        self,
        path: str,
        agents: List[Agent],
        client: InferenceClient,
        hub_client: OpenAI,
        thread_id: str,
        run_id: str,
        create_files: bool = True,
        env_vars: Optional[Dict[str, Any]] = None,
        tool_resources: Optional[Dict[str, Any]] = None,
        print_system_log: bool = False,
        agent_runner_user: Optional[str] = None,
        fastnear_api_key: Optional[str] = None,
        approvals=None,
    ) -> None:
        # Warning: never expose `client` or `_hub_client` to agent's environment

        self.base_url = client._config.base_url

        # user_auth is used to authenticate the user in the ts_runner. It will be removed after that in
        # `nearai/agents/agent.py`
        auth = client._auth
        self.user_auth = auth

        # Initialize secure openai clients
        openai_client_params = {
            "api_key": auth,
            "base_url": client._config.base_url,
            "default_headers": {"Authorization": f"Bearer {auth}"},
        }
        self.openai = SecureOpenAI(**openai_client_params)
        self.async_openai = SecureAsyncOpenAI(**openai_client_params)

        # Placeholder for solver
        self.client: Optional[InferenceClient] = None

        self._path = path
        self._agents = agents
        self._done = False
        self._pending_ext_agent = False
        self.env_vars: Dict[str, Any] = env_vars if env_vars else {}
        self._last_used_model = ""
        self.tool_resources: Dict[str, Any] = tool_resources if tool_resources else {}
        self.print_system_log = print_system_log
        self.agent_runner_user = agent_runner_user
        self._approvals = approvals if approvals else default_approvals
        self._thread_id = thread_id
        self._run_id = run_id
        self._debug_mode: bool = any(
            str(value).lower() in ("true", "1", "yes", "on")
            for key, value in self.env_vars.items()
            if key.lower() == "debug"
        )
        # Expose the NEAR account_id of a user that signs this request to run an agent.
        self.signer_account_id: str = client._config.auth.account_id if client._config.auth else ""

        if fastnear_api_key:
            default_mainnet_rpc = f"https://{fastnear_api_key}@rpc.mainnet.fastnear.com"
        else:
            default_mainnet_rpc = "https://rpc.mainnet.near.org"

        class NearAccount(Account):
            user_rpc_addr: Union[str, None]

            async def view(
                self,
                contract_id: str,
                method_name: str,
                args: dict,
                block_id: Optional[int] = None,
                threshold: Optional[int] = None,
                max_retries: int = 3,
            ):
                """Wrapper for the view method of the Account class, adding multiple retry attempts.

                Parameters
                ----------
                contract_id : str
                    The ID of the contract to call.
                method_name : str
                    The name of the method to invoke on the contract.
                args : dict
                    The arguments to pass to the contract method.
                block_id : Optional[int]
                    The block ID to query at.
                threshold : Optional[int]
                    The threshold for the view function.
                max_retries : int
                    The maximum number of retry attempts.

                Returns
                -------
                The result of the contract method call.

                Raises
                ------
                Exception
                    If all retry attempts fail, the exception is propagated.

                """
                acc = Account(self.account_id, self.private_key, self.user_rpc_addr or default_mainnet_rpc)
                await acc.startup()
                max_retries = min(max_retries, 10)

                for attempt in range(1, max_retries + 1):
                    try:
                        # Attempt to read the contract view method
                        return await acc.view_function(contract_id, method_name, args, block_id, threshold)
                    except Exception as e:
                        # Log the error message for the current attempt
                        print(
                            f"Attempt {attempt}/{max_retries} to view method '{method_name}' on contract "
                            f"'{contract_id}' failed with error: {e}"
                        )

                        # If it's the last attempt, re-raise the exception
                        if attempt == max_retries:
                            raise

            async def call(
                self,
                contract_id: str,
                method_name: str,
                args: dict,
                gas: int = DEFAULT_ATTACHED_GAS,
                amount: int = 0,
                nowait: bool = False,
                included: bool = False,
                max_retries: int = 1,
            ):
                """Wrapper for the call method of the Account class, adding multiple retry attempts.

                Parameters
                ----------
                contract_id : str
                    The ID of the contract to call.
                method_name : str
                    The name of the method to invoke on the contract.
                args : dict
                    The arguments to pass to the contract method.
                gas : int
                    The amount of gas to attach to the call.
                amount : int
                    The amount of tokens to attach to the call.
                nowait : bool
                    If nowait is True, return transaction hash, else wait execution.
                included : bool
                    If included is True, return transaction hash, else wait execution
                max_retries : int
                    The maximum number of retry attempts.

                Returns
                -------
                The result of the contract method call.

                Raises
                ------
                Exception
                    If all retry attempts fail, the exception is propagated.

                """
                acc = Account(self.account_id, self.private_key, self.user_rpc_addr or default_mainnet_rpc)
                await acc.startup()
                max_retries = min(max_retries, 10)

                for attempt in range(1, max_retries + 1):
                    try:
                        # Attempt to call the contract method
                        return await acc.function_call(contract_id, method_name, args, gas, amount, nowait, included)
                    except Exception as e:
                        # Log the error message for the current attempt
                        print(
                            f"Attempt {attempt}/{max_retries} to call method '{method_name}' on contract "
                            f"'{contract_id}' failed with error: {e}"
                        )

                        # If it's the last attempt, re-raise the exception
                        if attempt == max_retries:
                            raise

            async def get_balance(self, account_id: Optional[str] = None) -> int:
                """Retrieves the balance of the specified NEAR account.

                Parameters
                ----------
                account_id : Optional[str]
                    The ID of the account to retrieve the balance for. If not provided, the balance of the current
                    account is retrieved.

                Returns
                -------
                int
                    The balance of the specified account in yoctoNEAR.

                Raises
                ------
                Exception
                    If there is an error retrieving the balance.

                """
                acc = Account(self.account_id, self.private_key, self.user_rpc_addr or default_mainnet_rpc)
                await acc.startup()
                return await acc.get_balance(account_id)

            def __init__(
                self,
                account_id: Optional[str] = None,
                private_key: Optional[Union[List[Union[str, bytes]], str, bytes]] = None,
                rpc_addr: Optional[str] = None,
            ):
                self.user_rpc_addr = rpc_addr
                self.account_id = account_id
                self.private_key = private_key
                super().__init__(account_id, private_key, rpc_addr)

        self.set_near = NearAccount

        self._tools = ToolRegistry()

        if create_files:
            os.makedirs(self._path, exist_ok=True)
            open(os.path.join(self._path, CHAT_FILENAME), "a").close()
        os.chdir(self._path)

        # Protected client methods
        def query_vector_store(vector_store_id: str, query: str, full_files: bool = False):
            """Queries a vector store.

            vector_store_id: The id of the vector store to query.
            query: The query to search for.
            """
            return client.query_vector_store(vector_store_id, query, full_files)

        self.query_vector_store = query_vector_store

        def upload_file(
            file_content: str,
            purpose: Literal["assistants", "batch", "fine-tune", "vision"] = "assistants",
            encoding: Optional[str] = "utf-8",
            file_name: Optional[str] = "file.txt",
            file_type: Optional[str] = "text/plain",
        ):
            """Uploads a file to the registry."""
            return client.upload_file(
                file_content, purpose, encoding=encoding, file_name=file_name, file_type=file_type
            )

        self.upload_file = upload_file

        def remove_file(file_id: str):
            """Removes a file from the registry."""
            return client.remove_file(file_id)

        self.remove_file = remove_file

        def create_vector_store_from_source(
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
            return client.create_vector_store_from_source(
                name=name,
                source=source,
                source_auth=source_auth,
                chunking_strategy=chunking_strategy,
                expires_after=expires_after,
                metadata=metadata,
            )

        self.create_vector_store_from_source = create_vector_store_from_source

        def add_file_to_vector_store(vector_store_id: str, file_id: str):
            """Adds a file to the vector store."""
            return client.add_file_to_vector_store(vector_store_id, file_id)

        self.add_file_to_vector_store = add_file_to_vector_store

        # positional arguments are not allowed because arguments list will be updated
        def find_agents(
            *,
            owner_id: Optional[str] = None,
            with_capabilities: Optional[bool] = False,
            latest_versions_only: Optional[bool] = True,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
        ):
            """Find agents based on various parameters."""
            return client.find_agents(owner_id, with_capabilities, latest_versions_only, limit, offset)

        self.find_agents = find_agents

        def create_vector_store(
            name: str,
            file_ids: list,
            expires_after: Union[ExpiresAfter, NotGiven] = NOT_GIVEN,
            chunking_strategy: Union[
                AutoFileChunkingStrategyParam, StaticFileChunkingStrategyObjectParam, NotGiven
            ] = NOT_GIVEN,
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
            return client.create_vector_store(
                name=name,
                file_ids=file_ids,
                chunking_strategy=chunking_strategy,
                expires_after=expires_after,
                metadata=metadata,
            )

        self.create_vector_store = create_vector_store

        def get_vector_store(vector_store_id: str) -> VectorStore:
            """Gets a vector store by id."""
            return client.get_vector_store(vector_store_id)

        self.get_vector_store = get_vector_store

        def get_vector_store_files(vector_store_id: str) -> Optional[List[VectorStoreFile]]:
            """Gets a list of vector store files."""
            return client.get_vector_store_files(vector_store_id)

        self.get_vector_store_files = get_vector_store_files

        # Save cache of requested models for inference to avoid extra server calls
        self.cached_models_for_inference: Dict[str, str] = {}

        def get_model_for_inference(model: str = "") -> str:
            """Returns 'provider::model_full_path'."""
            if self.cached_models_for_inference.get(model, None) is None:
                provider = self.get_primary_agent().model_provider if self._agents else ""
                if model == "":
                    model = self.get_primary_agent().model if self._agents else ""
                if model == "":
                    return DEFAULT_PROVIDER_MODEL

                _, model_for_inference = client.provider_models.match_provider_model(model, provider)

                self.cached_models_for_inference[model] = model_for_inference

            return self.cached_models_for_inference[model]

        self.get_model_for_inference = get_model_for_inference

        def _run_inference_completions(
            messages: Union[Iterable[ChatCompletionMessageParam], str],
            model: Union[Iterable[ChatCompletionMessageParam], str],
            stream: bool,
            **kwargs: Any,
        ) -> Union[ModelResponse, CustomStreamWrapper]:
            """Run inference completions for given parameters."""
            params, kwargs = self.get_inference_parameters(messages, model, stream, **kwargs)

            completions = client.completions(
                params.model, params.messages, params.stream, params.temperature, params.max_tokens, **kwargs
            )

            return completions

        self._run_inference_completions = _run_inference_completions

        def get_agent_public_key():
            """Returns public key of the agent."""
            agent_name = self.get_primary_agent().get_full_name()

            return client.get_agent_public_key(agent_name)

        self.get_agent_public_key = get_agent_public_key

        def run_agent(
            agent_id: str,
            query: Optional[str] = None,
            thread_mode: ThreadMode = ThreadMode.FORK,
            run_mode: RunMode = RunMode.SIMPLE,
        ):
            """Runs a child agent on the thread."""
            child_thread_id = self._thread_id

            if thread_mode == ThreadMode.SAME:
                pass
            elif thread_mode == ThreadMode.FORK:
                child_thread_id = client.threads_fork(self._thread_id).id
                self.add_system_log(f"Forked thread {child_thread_id}", logging.INFO)
            elif thread_mode == ThreadMode.CHILD:
                child_thread_id = client.create_subthread(self._thread_id).id
                self.add_system_log(f"Created subthread {child_thread_id}", logging.INFO)

            if query:
                client.threads_messages_create(thread_id=child_thread_id, content=query, role="user")

            self.add_system_log(f"Running agent {agent_id}", logging.INFO)
            client.run_agent(
                parent_run_id=self._run_id,
                run_on_thread_id=child_thread_id,
                assistant_id=agent_id,
                run_mode=run_mode,
            )
            self._pending_ext_agent = True

            return child_thread_id

        self.run_agent = run_agent

        def schedule_run(
            agent: str,
            input_message: str,
            run_at: datetime,
            run_params: Optional[Dict[str, str]] = None,
            thread_id: Optional[str] = None,
        ):
            """Schedules a run."""
            return client.schedule_run(agent, input_message, thread_id, run_params, run_at)

        self.schedule_run = schedule_run

        # TODO(https://github.com/nearai/nearai/issues/549): Allow only a subset of agents to access/update user memory.
        def add_user_memory(memory: str):
            """Add user memory."""
            return client.add_user_memory(memory)

        self.add_user_memory = add_user_memory

        def query_user_memory(query: str):
            """Query user memory."""
            return client.query_user_memory(query)

        self.query_user_memory = query_user_memory

        def generate_image(prompt: str):
            """Generate an image."""
            return client.generate_image(prompt)

        self.generate_image = generate_image

        def save_agent_data(key, data: Dict[str, Any]):
            """Save agent data."""
            try:
                return client.save_agent_data(key, data)
            except Exception as ex:
                self.add_system_log(f"Error saving agent data by key {key}: {ex}", logging.ERROR)
                return None

        self.save_agent_data = save_agent_data

        def get_agent_data():
            """Get agent data."""
            return client.get_agent_data()

        self.get_agent_data = get_agent_data

        def get_agent_data_by_key(key, default=None):
            """Get agent data by key."""
            namespace = self.get_primary_agent().namespace
            name = self.get_primary_agent().name
            try:
                result = client.get_agent_data_by_key(key)
            except Exception as ex:
                self.add_system_log(f"Error getting agent data by key {key}: {ex}", logging.ERROR)
                result = None
            return (
                result
                if result
                else {
                    "value": default,
                    "namespace": namespace,
                    "key": key,
                    "name": name,
                    "updated_at": "",
                    "created_at": "",
                }
            )

        self.get_agent_data_by_key = get_agent_data_by_key

        # HubClient methods
        def add_reply(
            message: str,
            attachments: Optional[Iterable[Attachment]] = None,
            message_type: Optional[str] = None,
            thread_id: str = self._thread_id,
        ):
            """Assistant adds a message to the environment."""
            # NOTE: message from `user` are not stored in the memory

            return hub_client.beta.threads.messages.create(
                thread_id=thread_id,
                role="assistant",
                content=message,
                extra_body={
                    "assistant_id": self.get_primary_agent().identifier,
                    "run_id": self._run_id,
                },
                attachments=attachments,
                metadata={"message_type": message_type} if message_type else None,
            )

        self.add_reply = add_reply

        def get_thread(thread_id=self._thread_id):
            """Returns the current Thread object or the requested Thread."""
            return client.get_thread(thread_id)

        self.get_thread = get_thread

        def _add_message(
            role: str,
            message: str,
            attachments: Optional[Iterable[Attachment]] = None,
            **kwargs: Any,
        ):
            return hub_client.beta.threads.messages.create(
                thread_id=self._thread_id,
                role=role,  # type: ignore
                content=message,
                extra_body={
                    "assistant_id": self.get_primary_agent().identifier,
                    "run_id": self._run_id,
                },
                metadata=kwargs,
                attachments=attachments,
            )

        self._add_message = _add_message

        def _list_messages(
            limit: Union[int, NotGiven] = NOT_GIVEN,
            order: Literal["asc", "desc"] = "asc",
            thread_id: Optional[str] = None,
        ) -> List[Message]:
            """Returns messages from the environment."""
            messages = hub_client.beta.threads.messages.list(
                thread_id=thread_id or self._thread_id, limit=limit, order=order
            )
            self.add_system_log(f"Retrieved {len(messages.data)} messages from NEAR AI Hub")
            return messages.data

        self._list_messages = _list_messages

        def list_files_from_thread(
            order: Literal["asc", "desc"] = "asc", thread_id: Optional[str] = None
        ) -> List[FileObject]:
            """Lists files in the thread."""
            messages = self._list_messages(order=order)
            # Extract attachments from messages
            attachments = [a for m in messages if m.attachments for a in m.attachments]
            # Extract files from attachments
            file_ids = [a.file_id for a in attachments]
            files = [hub_client.files.retrieve(f) for f in file_ids if f]
            return files

        self.list_files_from_thread = list_files_from_thread

        def read_file_by_id(file_id: str, decode: Union[str, None] = "utf-8"):
            """Read a file from the thread."""
            content = hub_client.files.content(file_id).content

            if decode:
                return content.decode(decode)

            return content

        self.read_file_by_id = read_file_by_id

        def write_file(
            filename: str,
            content: Union[str, bytes],
            encoding: Union[str, None] = "utf-8",
            filetype: str = "text/plain",
            write_to_disk: bool = True,
        ) -> FileObject:
            """Writes a file to the environment.

            filename: The name of the file to write to
            content: The content to write to the file
            encoding: The encoding to use when writing the file (default is utf-8)
            filetype: The MIME type of the file (default is text/plain)
            write_to_disk: If True, write locally to disk (default is True)
            """
            if write_to_disk:
                # Write locally
                path = Path(self.get_primary_agent_temp_dir()) / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                if isinstance(content, bytes):
                    with open(path, "wb") as f:
                        f.write(content)
                else:
                    with open(path, "w", encoding=encoding) as f:
                        f.write(content)

            if isinstance(content, bytes):
                file_data = content
            else:
                file_data = io.BytesIO(content.encode(encoding))  # type:ignore

            # Upload to Hub
            file = hub_client.files.create(file=(filename, file_data, filetype), purpose="assistants")
            res = self.add_reply(
                message=f"Successfully wrote {len(content) if content else 0} characters to {filename}",
                attachments=[{"file_id": file.id, "tools": [{"type": "file_search"}]}],
                message_type="system:file_write",
            )
            self.add_system_log(
                f"Uploaded file {filename} with {len(content)} characters, id: {file.id}. Added in thread as: {res.id}"
            )
            return file

        self.write_file = write_file

        def mark_done() -> Run:  # noqa: D102
            self._done = True
            res = hub_client.beta.threads.runs.update(
                thread_id=self._thread_id,
                run_id=self._run_id,
                extra_body={
                    "status": "completed",
                    "completed_at": datetime.now().isoformat(),
                },
            )
            return res

        self.mark_done = mark_done

        def mark_failed() -> Run:
            """Marks the environment run as failed."""
            self._done = True
            self.add_system_log("Environment run failed", logging.ERROR)
            res = hub_client.beta.threads.runs.update(
                thread_id=self._thread_id,
                run_id=self._run_id,
                extra_body={"status": "failed", "failed_at": datetime.now().isoformat()},
            )
            return res

        self.mark_failed = mark_failed

        def request_user_input() -> Run:
            """Must be called to request input from the user."""
            self._done = True
            return hub_client.beta.threads.runs.update(
                thread_id=self._thread_id,
                run_id=self._run_id,
                extra_body={"status": "requires_action", "required_action": {"type": "user_input"}},
            )

        self.request_user_input = request_user_input

        def request_agent_input() -> Run:
            """Mark the run as ready for input from another agent."""
            self._done = True
            return hub_client.beta.threads.runs.update(
                thread_id=self._thread_id,
                run_id=self._run_id,
                extra_body={"status": "requires_action", "required_action": {"type": "agent_input"}},
            )

        self.request_agent_input = request_agent_input

        # Must be placed after method definitions
        self.register_standard_tools()

    # end of protected client methods

    def get_tool_registry(self, new: bool = False) -> ToolRegistry:
        """Returns the tool registry, a dictionary of tools that can be called by the agent."""
        if new:
            self._tools = ToolRegistry()
        return self._tools

    def register_standard_tools(self) -> None:  # noqa: D102
        reg = self.get_tool_registry()
        reg.register_tool(self.exec_command)
        reg.register_tool(self.read_file)
        reg.register_tool(self.write_file)
        reg.register_tool(self.request_user_input)
        reg.register_tool(self.list_files)
        reg.register_tool(self.query_vector_store)

    def get_last_message(self, role: str = "user"):
        """Reads last message from the given role and returns it."""
        for message in reversed(self.list_messages()):
            if message.get("role") == role:
                return message

        return None

    def add_message(
        self,
        role: str,
        message: str,
        attachments: Optional[Iterable[Attachment]] = None,
        **kwargs: Any,
    ):
        """Deprecated. Please use `add_reply` instead. Assistant adds a message to the environment."""
        # Prevent agent to save messages on behalf of `user` to avoid adding false memory
        role = "assistant"

        return self._add_message(role, message, attachments, **kwargs)

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

            # Add Thread log handler
            if self._debug_mode:
                custom_handler = CustomLogHandler(self.add_reply, "system")
                custom_handler.setFormatter(formatter)
                logger.addHandler(custom_handler)

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

            # Add Thread log handler
            if self._debug_mode:
                custom_handler = CustomLogHandler(self.add_reply, "agent")
                custom_handler.setFormatter(formatter)
                logger.addHandler(custom_handler)

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

    def list_messages(
        self,
        thread_id: Optional[str] = None,
        limit: Union[int, NotGiven] = 200,  # api defaults to 20
        order: Literal["asc", "desc"] = "asc",
    ):
        """Backwards compatibility for chat_completions messages."""
        messages = self._list_messages(thread_id=thread_id, limit=limit, order=order)

        # Filter out system and agent log messages when running in debug mode. Agent behavior shouldn't change based on logs.  # noqa: E501
        messages = [
            m
            for m in messages
            if not (
                m.metadata
                and any(m.metadata.get("message_type", "").startswith(prefix) for prefix in ["system:", "agent:"])
            )
        ]

        legacy_messages = [
            {
                "id": m.id,
                "content": "\n".join([c.text.value for c in m.content]),  # type: ignore
                "role": m.role,
                "attachments": m.attachments,
            }
            for m in messages
        ]
        return legacy_messages

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
            self.get_primary_agent().name,
            callback_url,
        )

    def list_files(self, path: str, order: Literal["asc", "desc"] = "asc") -> List[str]:
        """Lists files in the environment."""
        return os.listdir(os.path.join(self.get_primary_agent_temp_dir(), path))

    def get_system_path(self) -> Path:
        """Returns the system path where chat.txt & system_log are stored."""
        return Path(self._path)

    def get_agent_temp_path(self) -> Path:
        """Returns temp dir for primary agent where execution happens."""
        return self.get_primary_agent_temp_dir()

    def read_file(self, filename: str, decode: Union[str, None] = "utf-8") -> Optional[Union[bytes, str]]:
        """Reads a file from the environment or thread."""
        file_content: Optional[Union[bytes, str]] = None
        # First try to read from local filesystem
        local_path = os.path.join(self.get_primary_agent_temp_dir(), filename)
        print(f"Reading file {filename} from local path: {local_path}")
        if os.path.exists(local_path):
            try:
                with open(local_path, "rb") as local_path_file:
                    local_file_content = local_path_file.read()
                    file_content = local_file_content
                    if decode:
                        file_content = file_content.decode(decode)
            except Exception as e:
                print(f"Error with read_file: {e}")

        if not file_content:
            # Next check files written out by the agent.
            # Agent output files take precedence over files packaged with the agent
            thread_files = self.list_files_from_thread(order="desc")

            # Then try to read from thread, starting from the most recent
            for f in thread_files:
                if f.filename == filename:
                    file_content = self.read_file_by_id(f.id, decode)
                    break

            if not file_content:
                # Next check agent file cache
                # Agent output files & thread files take precedence over cached files
                file_cache = self.get_primary_agent().file_cache
                if file_cache:
                    file_content = file_cache.get(filename, None)

            # Write the file content from the thread or cache to the local filesystem
            # This allows exec_command to operate on the file
            if file_content:
                if not os.path.exists(os.path.dirname(local_path)):
                    os.makedirs(os.path.dirname(local_path))

                with open(local_path, "wb") as local_file:
                    if isinstance(file_content, bytes):
                        local_file.write(file_content)
                    else:
                        local_file.write(file_content.encode("utf-8"))

        if not file_content:
            self.add_system_log(f"Warn: File {filename} not found during read_file operation")

        return file_content

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

    def get_inference_parameters(
        self,
        messages: Union[Iterable[ChatCompletionMessageParam], str],
        model: Union[Iterable[ChatCompletionMessageParam], str],
        stream: bool,
        **kwargs: Any,
    ) -> Tuple[InferenceParameters, Any]:
        """Run inference parameters to run completions."""
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

        temperature = kwargs.pop("temperature", self.get_primary_agent().model_temperature if self._agents else None)
        max_tokens = kwargs.pop("max_tokens", self.get_primary_agent().model_max_tokens if self._agents else None)

        params = InferenceParameters(
            model=model,
            messages=messages,
            stream=stream,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return params, kwargs

    # TODO(286): `messages` may be model and `model` may be messages temporarily to support deprecated API.
    def completions(
        self,
        messages: Union[Iterable[ChatCompletionMessageParam], str],
        model: Union[Iterable[ChatCompletionMessageParam], str] = "",
        stream: bool = False,
        thread_id: Optional[str] = None,
        attachments: Optional[Iterable[Attachment]] = None,
        message_type: Optional[str] = None,
        **kwargs: Any,
    ) -> Union[ModelResponse, CustomStreamWrapper]:
        """Returns all completions for given messages using the given model.

        Always returns a ModelResponse object. When stream=True, aggregates the streamed
        content into a ModelResponse. When stream=False, returns the ModelResponse directly.
        """
        params, kwargs = self.get_inference_parameters(messages, model, stream, **kwargs)
        if stream:
            message_id = None
            kwargs.setdefault("extra_headers", {}).update(
                {
                    k: v
                    for k, v in {
                        "run_id": self._run_id,
                        "thread_id": thread_id if thread_id else self._thread_id,
                        "message_id": message_id,
                    }.items()
                    if v is not None
                }
            )

            # Pass thread_id, attachments, and message_type to the server
            stream_results = self._run_inference_completions(
                messages, model, True, thread_id=thread_id, attachments=attachments, message_type=message_type, **kwargs
            )
            full_content = ""
            for chunk in stream_results:
                if not isinstance(chunk, (tuple, str)) and hasattr(chunk, "choices"):
                    if chunk.choices and hasattr(chunk.choices[0], "delta"):
                        delta = chunk.choices[0].delta
                        if hasattr(delta, "content") and delta.content:
                            full_content += delta.content

            response = ModelResponse(
                id="streamed_completion",
                object="chat.completion",
                created=int(time.time()),
                model=params.model,
                choices=[
                    Choices(index=0, message={"role": "assistant", "content": full_content}, finish_reason="stop")
                ],
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            )
            return response
        else:
            return self._run_inference_completions(messages, model, False, **kwargs)

    def verify_signed_message(
        self,
        completion: str,
        messages: Union[Iterable[ChatCompletionMessageParam], str],
        public_key: Union[str, None] = None,
        signature: Union[str, None] = None,
        model: Union[Iterable[ChatCompletionMessageParam], str] = "",
        **kwargs: Any,
    ) -> bool:
        """Verifies a signed message."""
        if public_key is None or signature is None:
            return False

        params, _ = self.get_inference_parameters(messages, model, False, **kwargs)

        messages_without_ids = [{k: v for k, v in item.items() if k != "id"} for item in params.messages]
        ordered_messages_without_ids = [
            {"role": str(item["role"]), "content": str(item["content"])} for item in messages_without_ids
        ]

        return validate_completion_signature(
            public_key,
            signature,
            CompletionSignaturePayload(
                agent_name=self.get_primary_agent().get_full_name(),
                completion=completion,
                model=params.model,
                messages=ordered_messages_without_ids,
                temperature=params.temperature,
                max_tokens=params.max_tokens,
            ),
        )

    def completions_and_run_tools(
        self,
        messages: List[ChatCompletionMessageParam],
        model: str = "",
        tools: Optional[List] = None,
        add_responses_to_messages: bool = True,
        agent_role_name="assistant",
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
                        try:
                            function_response_json = json.dumps(function_response) if function_response else ""
                            if add_responses_to_messages:
                                self.add_message(
                                    tool_role_name,
                                    function_response_json,
                                    tool_call_id=tool_call.id,
                                    name=function_name,
                                )
                        except Exception as e:
                            # some tool responses may not be serializable
                            error_message = f"Unable to add tool output as a message {function_name}: {e}"
                            self.add_system_log(error_message, level=logging.INFO)
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
        content = response_message.content
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

        llama_matches = LLAMA_TOOL_FORMAT_PATTERN2.findall(content)
        if llama_matches:
            text = ""
            tool_calls = []
            for llama_match in llama_matches:
                before_call_text, function_name_and_args, after_call_text = llama_match
                try:
                    parsed_function_name_and_args = json.loads(function_name_and_args)
                    function_name = parsed_function_name_and_args.get("name")
                    args = parsed_function_name_and_args.get("arguments")
                    function = Function(name=function_name, arguments=args)
                    tool_call = ChatCompletionMessageToolCall(id=str(uuid.uuid4()), function=function)
                    text += before_call_text + after_call_text
                    tool_calls.append(tool_call)
                except json.JSONDecodeError:
                    print(f"Error parsing tool_call function name and args: {function_name_and_args}")
                    continue
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
        messages: Union[Iterable[ChatCompletionMessageParam], str],
        model: Union[Iterable[ChatCompletionMessageParam], str] = "",
        **kwargs: Any,
    ) -> str:
        """Returns a completion for the given messages using the given model."""
        raw_response = self.completions(messages, model, **kwargs)
        assert isinstance(raw_response, ModelResponse), "Expected ModelResponse"
        response: ModelResponse = raw_response
        assert all(map(lambda choice: isinstance(choice, Choices), response.choices)), "Expected Choices"
        choices: List[Choices] = response.choices  # type: ignore
        response_message = choices[0].message.content
        assert response_message, "No completions returned"
        return response_message

    def signed_completion(
        self,
        messages: Union[Iterable[ChatCompletionMessageParam], str],
        model: Union[Iterable[ChatCompletionMessageParam], str] = "",
        **kwargs: Any,
    ) -> Dict[str, str]:
        """Returns a completion for the given messages using the given model with the agent signature."""
        # TODO Return signed completions for non-latest versions only?
        agent_name = self.get_primary_agent().get_full_name()
        raw_response = self.completions(messages, model, agent_name=agent_name, **kwargs)
        assert isinstance(raw_response, ModelResponse), "Expected ModelResponse"
        response: ModelResponse = raw_response

        signature_data = json.loads(response.system_fingerprint) if response.system_fingerprint else {}

        assert all(map(lambda choice: isinstance(choice, Choices), response.choices)), "Expected Choices"
        choices: List[Choices] = response.choices  # type: ignore
        response_message = choices[0].message.content
        assert response_message, "No completions returned"

        return {
            "response": response_message,
            "signature": signature_data.get("signature", None),
            "public_key": signature_data.get("public_key", None),
        }

    def completion_and_get_tools_calls(
        self,
        messages: List[ChatCompletionMessageParam],
        model: str = "",
        **kwargs: Any,
    ) -> SimpleNamespace:
        """Returns completion message and/or tool calls from OpenAI or Llama tool formats."""
        raw_response = self._run_inference_completions(messages, model, stream=False, **kwargs)

        assert isinstance(raw_response, ModelResponse), "Expected ModelResponse"
        response: ModelResponse = raw_response
        assert all(map(lambda choice: isinstance(choice, Choices), response.choices)), "Expected Choices"
        choices: List[Choices] = response.choices  # type: ignore

        (message_without_tool_call, tool_calls) = self._parse_tool_call(choices[0].message)

        if message_without_tool_call is None:
            response_message = choices[0].message.content
            message_without_tool_call = response_message

        return SimpleNamespace(message=message_without_tool_call, tool_calls=tool_calls)

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

    def get_primary_agent_temp_dir(self) -> Path:
        """Returns temp dir for primary agent."""
        return self.get_primary_agent().temp_dir

    def is_done(self) -> bool:  # noqa: D102
        return self._done

    def create_snapshot(self) -> bytes:
        """Create an in memory snapshot."""
        with tempfile.NamedTemporaryFile(suffix=".tar.gz") as f:
            with tarfile.open(fileobj=f, mode="w:gz") as tar:
                tar.add(self._path, arcname=".")
            f.flush()
            f.seek(0)
            snapshot = f.read()
        return snapshot

    def environment_run_info(self, base_id, run_type) -> dict:
        """Returns the environment run information."""
        if not self._agents or not self.get_primary_agent():
            raise ValueError("Agent not found")
        primary_agent = self.get_primary_agent()

        full_agent_name = "/".join([primary_agent.namespace, primary_agent.name, primary_agent.version])
        safe_agent_name = full_agent_name.replace("/", "_")
        uid = uuid.uuid4().hex
        generated_name = f"environment_run_{safe_agent_name}_{uid}"
        name = generated_name

        timestamp = datetime.now(timezone.utc).isoformat()
        return {
            "name": name,
            "version": "0",
            "description": f"Agent {run_type} {full_agent_name} {uid} {timestamp}",
            "category": "environment",
            "tags": ["environment"],
            "details": {
                "base_id": base_id,
                "timestamp": timestamp,
                "agents": [agent.name for agent in self._agents],
                "primary_agent_namespace": primary_agent.namespace,
                "primary_agent_name": primary_agent.name,
                "primary_agent_version": primary_agent.version,
                "run_id": self._run_id,
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

    def clear_temp_agent_files(self, verbose=True) -> None:
        """Remove temp agent files created to be used in `runpy`."""
        for agent in self._agents:
            if os.path.exists(agent.temp_dir):
                if verbose:
                    print("removed agent.temp_files", agent.temp_dir)
                shutil.rmtree(agent.temp_dir)

    def set_next_actor(self, who: str) -> None:
        """Set the next actor / action in the dialogue."""
        next_action_fn = os.path.join(self._path, ".next_action")
        if who == "agent":
            self._done = False

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
    ) -> None:
        """Runs agent(s) against a new or previously created environment."""
        if new_message:
            self._add_message("user", new_message)

        iteration = 0
        self.set_next_actor("agent")

        while iteration < max_iterations and not self.is_done() and self.get_next_actor() != "user":
            iteration += 1
            if max_iterations > 1:
                self.add_system_log(
                    f"Running agent, iteration {iteration}/{max_iterations}",
                    logging.INFO,
                )
            try:
                error_message, traceback_message = self.get_primary_agent().run(self, task=new_message)
                if self._debug_mode and (error_message or traceback_message):
                    if self._debug_mode and (error_message or traceback_message):
                        message_parts = []

                        if error_message:
                            message_parts.append(f"Error: \n ```\n{error_message}\n```")

                        if traceback_message:
                            message_parts.append(f"Error Traceback: \n ```\n{traceback_message}\n```")

                        self.add_reply("\n\n".join(message_parts), message_type="system:debug")

            except Exception as e:
                self.add_system_log(f"Environment run failed: {e}", logging.ERROR)
                self.mark_failed()
                raise e

        if not self._pending_ext_agent and not self.is_done():
            # If no external agent was called, mark the whole run as done.
            # Else this environment will stop for now but this run will be continued later.
            self.mark_done()

    def generate_folder_hash_id(self, path: str) -> str:
        """Returns hash based on files and their contents in path, including subfolders."""  # noqa: E501
        hash_obj = hashlib.md5()

        for root, _dirs, files in os.walk(path):
            for file in sorted(files):
                file_path = os.path.join(root, file)
                with open(file_path, "rb") as f:
                    while chunk := f.read(8192):
                        hash_obj.update(chunk)

        return hash_obj.hexdigest()
