import importlib.metadata
import json
import os
import re
import runpy
import sys
from collections import OrderedDict
from dataclasses import asdict
from pathlib import Path
from textwrap import fill
from typing import Any, Dict, Optional, Union

import boto3
import fire
from openapi_client import EntryLocation, EntryMetadataInput
from openapi_client.api.benchmark_api import BenchmarkApi
from openapi_client.api.default_api import DefaultApi
from openapi_client.api.evaluation_api import EvaluationApi
from shared.client_config import (
    DEFAULT_MODEL,
    DEFAULT_MODEL_MAX_TOKENS,
    DEFAULT_MODEL_TEMPERATURE,
    DEFAULT_NAMESPACE,
    DEFAULT_PROVIDER,
)
from shared.naming import NamespacedName, create_registry_name
from shared.provider_models import ProviderModels, get_provider_namespaced_model
from tabulate import tabulate

from nearai.agents.local_runner import LocalRunner
from nearai.config import (
    CONFIG,
    get_hub_client,
    update_config,
)
from nearai.finetune import FinetuneCli
from nearai.lib import check_metadata, parse_location, parse_tags
from nearai.registry import get_registry_folder, registry
from nearai.tensorboard_feed import TensorboardCli


class RegistryCli:
    def info(self, entry: str) -> None:
        """Show information about an item."""
        entry_location = parse_location(entry)
        metadata = registry.info(entry_location)

        if metadata is None:
            print(f"Entry {entry} not found.")
            return

        print(metadata.model_dump_json(indent=2))
        if metadata.category == "model":
            available_provider_matches = ProviderModels(CONFIG.get_client_config()).available_provider_matches(
                NamespacedName(name=metadata.name, namespace=entry_location.namespace)
            )
            if len(available_provider_matches) > 0:
                header = ["provider", "name"]

                table = []
                for provider, name in available_provider_matches.items():
                    table.append(
                        [
                            fill(provider),
                            fill(name),
                        ]
                    )
                print(tabulate(table, headers=header, tablefmt="simple_grid"))

    def metadata_template(self, local_path: str = ".", category: str = "", description: str = ""):
        """Create a metadata template."""
        path = Path(local_path)

        metadata_path = path / "metadata.json"

        # Get the name of the folder
        folder_name = path.name

        with open(metadata_path, "w") as f:
            metadata: Dict[str, Any] = {
                "name": folder_name,
                "version": "0.0.1",
                "description": description,
                "category": category,
                "tags": [],
                "details": {},
                "show_entry": True,
            }

            if category == "agent":
                metadata["details"]["agent"] = {}
                metadata["details"]["agent"]["defaults"] = {
                    "model": DEFAULT_MODEL,
                    "model_provider": DEFAULT_PROVIDER,
                    "model_temperature": DEFAULT_MODEL_TEMPERATURE,
                    "model_max_tokens": DEFAULT_MODEL_MAX_TOKENS,
                }

            json.dump(metadata, f, indent=2)

    def list(
        self,
        namespace: str = "",
        category: str = "",
        tags: str = "",
        total: int = 32,
        offset: int = 0,
        show_all: bool = False,
        show_latest_version: bool = True,
        star: str = "",
    ) -> None:
        """List available items."""
        # Make sure tags is a comma-separated list of tags
        tags_l = parse_tags(tags)
        tags = ",".join(tags_l)

        entries = registry.list(
            namespace=namespace,
            category=category,
            tags=tags,
            total=total + 1,
            offset=offset,
            show_all=show_all,
            show_latest_version=show_latest_version,
            starred_by=star,
        )

        more_rows = len(entries) > total
        entries = entries[:total]

        header = ["entry", "category", "description", "tags"]

        table = []
        for entry in entries:
            table.append(
                [
                    fill(f"{entry.namespace}/{entry.name}/{entry.version}"),
                    fill(entry.category, 20),
                    fill(entry.description, 50),
                    fill(", ".join(entry.tags), 20),
                ]
            )

        if more_rows:
            table.append(["...", "...", "...", "..."])

        print(tabulate(table, headers=header, tablefmt="simple_grid"))

        if category == "model" and len(entries) < total and namespace == "" and tags == "" and star == "":
            unregistered_common_provider_models = ProviderModels(
                CONFIG.get_client_config()
            ).get_unregistered_common_provider_models(registry.dict_models())
            if len(unregistered_common_provider_models):
                print(
                    f"There are unregistered common provider models: {unregistered_common_provider_models}. Run 'nearai registry upload-unregistered-common-provider-models' to update registry."  # noqa: E501
                )

    def update(self, local_path: str = ".") -> None:
        """Update metadata of a registry item."""
        path = Path(local_path)

        if CONFIG.auth is None:
            print("Please login with `nearai login`")
            exit(1)

        metadata_path = path / "metadata.json"
        check_metadata(metadata_path)

        with open(metadata_path) as f:
            metadata: Dict[str, Any] = json.load(f)

        namespace = CONFIG.auth.account_id

        entry_location = EntryLocation.model_validate(
            dict(
                namespace=namespace,
                name=metadata.pop("name"),
                version=metadata.pop("version"),
            )
        )

        entry_metadata = EntryMetadataInput.model_validate(metadata)
        result = registry.update(entry_location, entry_metadata)
        print(json.dumps(result, indent=2))

    def upload_unregistered_common_provider_models(self, dry_run: bool = True) -> None:
        """Creates new registry items for unregistered common provider models."""
        provider_matches_list = ProviderModels(CONFIG.get_client_config()).get_unregistered_common_provider_models(
            registry.dict_models()
        )
        if len(provider_matches_list) == 0:
            print("No new models to upload.")
            return

        print("Going to create new registry items:")
        header = ["entry", "description"]
        table = []
        paths = []
        for provider_matches in provider_matches_list:
            provider_model = provider_matches.get(DEFAULT_PROVIDER) or next(iter(provider_matches.values()))
            _, model = get_provider_namespaced_model(provider_model)
            assert model.namespace == ""
            model.name = create_registry_name(model.name)
            model.namespace = DEFAULT_NAMESPACE
            version = "1.0.0"
            description = " & ".join(provider_matches.values())
            table.append(
                [
                    fill(f"{model.namespace}/{model.name}/{version}"),
                    fill(description, 50),
                ]
            )

            path = get_registry_folder() / model.namespace / model.name / version
            path.mkdir(parents=True, exist_ok=True)
            paths.append(path)
            metadata_path = path / "metadata.json"
            with open(metadata_path, "w") as f:
                metadata: Dict[str, Any] = {
                    "name": model.name,
                    "version": version,
                    "description": description,
                    "category": "model",
                    "tags": [],
                    "details": {},
                    "show_entry": True,
                }
                json.dump(metadata, f, indent=2)

        print(tabulate(table, headers=header, tablefmt="simple_grid"))
        if dry_run:
            print("Please verify, then repeat the command with --dry_run=False")
        else:
            for path in paths:
                self.upload(str(path))

    def upload(self, local_path: str = ".") -> None:
        """Upload item to the registry."""
        registry.upload(Path(local_path), show_progress=True)

    def download(self, entry_location: str, force: bool = False) -> None:
        """Download item."""
        registry.download(entry_location, force=force, show_progress=True)


class ConfigCli:
    def set(self, key: str, value: str, local: bool = False) -> None:
        """Add key-value pair to the config file."""
        update_config(key, value, local)

    def get(self, key: str) -> None:
        """Get value of a key in the config file."""
        print(CONFIG.get(key))

    def show(self) -> None:  # noqa: D102
        for key, value in asdict(CONFIG).items():
            print(f"{key}: {value}")


class BenchmarkCli:
    def __init__(self):
        """Initialize Benchmark API."""
        self.client = BenchmarkApi()

    def _get_or_create_benchmark(self, benchmark_name: str, solver_name: str, args: Dict[str, Any], force: bool) -> int:
        if CONFIG.auth is None:
            print("Please login with `nearai login`")
            exit(1)
        namespace = CONFIG.auth.account_id

        # Sort the args to have a consistent representation.
        solver_args = json.dumps(OrderedDict(sorted(args.items())))

        benchmark_id = self.client.get_benchmark_v1_benchmark_get_get(
            namespace=namespace,
            benchmark_name=benchmark_name,
            solver_name=solver_name,
            solver_args=solver_args,
        )

        if benchmark_id == -1 or force:
            benchmark_id = self.client.create_benchmark_v1_benchmark_create_get(
                benchmark_name=benchmark_name,
                solver_name=solver_name,
                solver_args=solver_args,
            )

        assert benchmark_id != -1
        return benchmark_id

    def run(
        self,
        dataset: str,
        solver_strategy: str,
        max_concurrent: int = 2,
        force: bool = False,
        subset: Optional[str] = None,
        check_compatibility: bool = True,
        record: bool = False,
        num_inference_retries: int = 10,
        **solver_args: Any,
    ) -> None:
        """Run benchmark on a dataset with a solver strategy.

        It will cache the results in the database and subsequent runs will pull the results from the cache.
        If force is set to True, it will run the benchmark again and update the cache.
        """
        from nearai.benchmark import BenchmarkExecutor, DatasetInfo
        from nearai.dataset import get_dataset, load_dataset
        from nearai.solvers import SolverScoringMethod, SolverStrategy, SolverStrategyRegistry

        CONFIG.num_inference_retries = num_inference_retries

        args = dict(solver_args)
        if subset is not None:
            args["subset"] = subset

        benchmark_id = self._get_or_create_benchmark(
            benchmark_name=dataset,
            solver_name=solver_strategy,
            args=args,
            force=force,
        )

        solver_strategy_class: Union[SolverStrategy, None] = SolverStrategyRegistry.get(solver_strategy, None)
        assert (
            solver_strategy_class
        ), f"Solver strategy {solver_strategy} not found. Available strategies: {list(SolverStrategyRegistry.keys())}"

        name = dataset
        if solver_strategy_class.scoring_method == SolverScoringMethod.Custom:
            dataset = str(get_dataset(dataset))
        else:
            dataset = load_dataset(dataset)

        solver_strategy_obj: SolverStrategy = solver_strategy_class(dataset_ref=dataset, **solver_args)  # type: ignore
        if check_compatibility:
            assert name in solver_strategy_obj.compatible_datasets() or any(
                map(lambda n: n in name, solver_strategy_obj.compatible_datasets())
            ), f"Solver strategy {solver_strategy} is not compatible with dataset {name}"

        be = BenchmarkExecutor(DatasetInfo(name, subset, dataset), solver_strategy_obj, benchmark_id=benchmark_id)

        cpu_count = os.cpu_count()
        max_concurrent = (cpu_count if cpu_count is not None else 1) if max_concurrent < 0 else max_concurrent
        be.run(max_concurrent=max_concurrent, record=record)

    def list(
        self,
        namespace: Optional[str] = None,
        benchmark: Optional[str] = None,
        solver: Optional[str] = None,
        args: Optional[str] = None,
        total: int = 32,
        offset: int = 0,
    ):
        """List all executed benchmarks."""
        result = self.client.list_benchmarks_v1_benchmark_list_get(
            namespace=namespace,
            benchmark_name=benchmark,
            solver_name=solver,
            solver_args=args,
            total=total,
            offset=offset,
        )

        header = ["id", "namespace", "benchmark", "solver", "args", "score", "solved", "total"]
        table = []
        for benchmark_output in result:
            score = 100 * benchmark_output.solved / benchmark_output.total
            table.append(
                [
                    fill(str(benchmark_output.id)),
                    fill(benchmark_output.namespace),
                    fill(benchmark_output.benchmark),
                    fill(benchmark_output.solver),
                    fill(benchmark_output.args),
                    fill(f"{score:.2f}%"),
                    fill(str(benchmark_output.solved)),
                    fill(str(benchmark_output.total)),
                ]
            )

        print(tabulate(table, headers=header, tablefmt="simple_grid"))


class EvaluationCli:
    def table(
        self,
        all_key_columns: bool = False,
        all_metrics: bool = False,
        num_columns: int = 6,
        metric_name_max_length: int = 30,
    ) -> None:
        """Prints table of evaluations."""
        from nearai.evaluation import print_evaluation_table

        api = EvaluationApi()
        table = api.get_evaluation_table_v1_evaluation_table_get()

        print_evaluation_table(
            table.rows,
            table.columns,
            table.important_columns,
            all_key_columns,
            all_metrics,
            num_columns,
            metric_name_max_length,
        )


class AgentCli:
    def inspect(self, path: str) -> None:
        """Inspect environment from given path."""
        import subprocess

        filename = Path(os.path.abspath(__file__)).parent / "streamlit_inspect.py"
        subprocess.call(["streamlit", "run", filename, "--", path])

    def interactive(
        self,
        agents: str,
        thread_id: Optional[str] = None,
        tool_resources: Optional[Dict[str, Any]] = None,
        local: bool = False,
        env_vars: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Runs agent interactively."""
        last_message_id = None
        while True:
            new_message = input("> ")
            if new_message.lower() == "exit":
                break

            last_message_id = self._task(
                agents=agents,
                task=new_message,
                thread_id=thread_id,
                tool_resources=tool_resources,
                record_run=False,
                last_message_id=last_message_id,
                local=local,
                env_vars=env_vars,
            )

            # Update thread_id for the next iteration
            if thread_id is None:
                thread_id = self.last_thread_id

    def task(
        self,
        agents: str,
        task: str,
        thread_id: Optional[str] = None,
        tool_resources: Optional[Dict[str, Any]] = None,
        local: bool = False,
        env_vars: Optional[Dict[str, Any]] = None,
    ) -> None:
        """CLI wrapper for the _task method."""
        last_message_id = self._task(
            agents=agents,
            task=task,
            thread_id=thread_id,
            tool_resources=tool_resources,
            record_run=True,
            local=local,
            env_vars=env_vars,
        )
        if last_message_id:
            print(f"Task completed. Thread ID: {self.last_thread_id}")
            print(f"Last message ID: {last_message_id}")

    def _task(
        self,
        agents: str,
        task: str,
        thread_id: Optional[str] = None,
        tool_resources: Optional[Dict[str, Any]] = None,
        record_run: bool = True,
        last_message_id: Optional[str] = None,
        local: bool = False,
        env_vars: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Runs agent non-interactively with a single task."""
        hub_client = get_hub_client()
        if thread_id:
            thread = hub_client.beta.threads.retrieve(thread_id)
        else:
            thread = hub_client.beta.threads.create(
                tool_resources=tool_resources,
            )

        hub_client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=task,
        )

        if not local:
            hub_client.beta.threads.runs.create_and_poll(
                thread_id=thread.id,
                assistant_id=agents,
                instructions="You are a helpful assistant. Complete the given task.",
                model="fireworks::accounts/fireworks/models/llama-v3p1-405b-instruct",
            )
        else:
            run = hub_client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=agents,
                instructions="You are a helpful assistant. Complete the given task.",
                model="fireworks::accounts/fireworks/models/llama-v3p1-405b-instruct",
                extra_body={"delegate_execution": True},
            )
            params = {
                "max_iterations": 1,
                "record_run": True,
                "api_url": CONFIG.api_url,
                "tool_resources": run.tools,
                "data_source": "local_files",
                "model": run.model,
                "user_env_vars": env_vars,
                "agent_env_vars": {},
            }
            auth = CONFIG.auth
            assert auth is not None
            LocalRunner(agents, agents, thread.id, run.id, auth, params)

        # List new messages
        messages = hub_client.beta.threads.messages.list(thread_id=thread.id, after=last_message_id, order="asc")
        message_list = list(messages)
        if message_list:
            for msg in message_list:
                if msg.role == "assistant":
                    print(f"Assistant: {msg.content[0].text.value}")
            last_message_id = message_list[-1].id
        else:
            print("No new messages")

        # Store the thread_id for potential use in interactive mode
        self.last_thread_id = thread.id

        return last_message_id

    def run_remote(
        self,
        agents: str,
        new_message: str = "",
        environment_id: str = "",
        provider: str = "aws_lambda",
        params: object = None,
        framework: str = "base",
        environment: str = "production",
    ) -> None:
        """Invoke a Container based AWS lambda function to run agents on a given environment."""
        from nearai.clients.lambda_client import LambdaWrapper

        if not CONFIG.auth:
            print("Please login with `nearai login`")
            return
        if provider != "aws_lambda":
            print(f"Provider {provider} is not supported.")
            return
        if not params:
            params = {"max_iterations": 1}

        wrapper = LambdaWrapper(boto3.client("lambda", region_name="us-east-2"))
        try:
            new_environment = wrapper.invoke_function(
                f"{environment}-agent-runner-{framework}",
                {
                    "agents": agents,
                    "environment_id": environment_id,
                    "auth": CONFIG.auth.model_dump(),
                    "new_message": new_message,
                    "params": params,
                },
            )
            print(f"Agent run finished. New environment is {new_environment}")
        except Exception as e:
            print(f"Error running agent remotely: {e}")

    def create(self, name: Optional[str] = None, description: Optional[str] = None, fork: Optional[str] = None) -> None:
        """Create a new agent or fork an existing one.

        Usage:
          nearai agent create
          nearai agent create --name <agent_name> --description <description>
          nearai agent create --fork <namespace/agent_name/version> [--name <new_agent_name>]

        Options:
          --name          Name of the new agent.
          --description   Description of the new agent.
          --fork          Fork an existing agent specified by namespace/agent_name/version.

        Examples
        --------
          nearai agent create
          nearai agent create --name my_agent --description "My new agent"
          nearai agent create --fork agentic.near/summary/0.0.3 --name new_summary_agent

        """
        # Check if the user is authenticated
        if CONFIG.auth is None or CONFIG.auth.account_id is None:
            print("Please login with `nearai login` before creating an agent.")
            return

        namespace = CONFIG.auth.account_id

        if fork:
            # Fork an existing agent
            self._fork_agent(fork, namespace, name)
        else:
            # Create a new agent from scratch
            self._create_new_agent(namespace, name, description)

    def _create_new_agent(self, namespace: str, name: Optional[str], description: Optional[str]) -> None:
        """Create a new agent from scratch."""
        # Prompt for agent name if not provided
        if not name or not isinstance(name, str):
            name = input("Name: ").strip()
            while not name or not isinstance(name, str):
                print("Agent name cannot be empty.")
                name = input("Name: ").strip()

        # Prompt for description if not provided
        while not description or not isinstance(description, str):
            print("A description is needed for agent matching and cannot be empty.")
            description = input("Description: ").strip()

        # Set the agent path
        agent_path = get_registry_folder() / namespace / name / "0.0.1"
        agent_path.mkdir(parents=True, exist_ok=True)

        # Create metadata.json
        metadata = {
            "name": name,
            "version": "0.0.1",
            "description": description,
            "category": "agent",
            "tags": [],
            "details": {
                "agent": {
                    "defaults": {
                        "model": DEFAULT_MODEL,
                        "model_provider": DEFAULT_PROVIDER,
                        "model_temperature": DEFAULT_MODEL_TEMPERATURE,
                        "model_max_tokens": DEFAULT_MODEL_MAX_TOKENS,
                    }
                }
            },
            "show_entry": True,
        }

        metadata_path = agent_path / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        # Create a default agent.py
        agent_py_content = """from nearai.agents.environment import Environment


def run(env: Environment):
    env.add_message("assistant", "Hello, world!")
    # Your agent code here
    # Example:
    # prompt = {"role": "system", "content": "You are a helpful assistant."}
    # result = env.completion([prompt] + env.list_messages())
    # env.add_message("assistant", result)


run(env)

"""
        agent_py_path = agent_path / "agent.py"
        with open(agent_py_path, "w") as f:
            f.write(agent_py_content)

        print(f"\nAgent created at: {agent_path}")
        print("\nUseful commands:")
        print(f"  > nearai agent interactive {name} --local")
        print(f"  > nearai registry upload {agent_path}")

    def _fork_agent(self, fork: str, namespace: str, new_name: Optional[str]) -> None:
        """Fork an existing agent."""
        import shutil

        # Parse the fork parameter
        try:
            entry_location = parse_location(fork)
            fork_namespace = entry_location.namespace
            fork_name = entry_location.name
            fork_version = entry_location.version
        except ValueError:
            print("Invalid fork parameter format. Expected format: <namespace>/<agent-name>/<version>")
            return

        # Download the agent from the registry
        agent_location = f"{fork_namespace}/{fork_name}/{fork_version}"
        print(f"Downloading agent '{agent_location}'...")
        registry.download(agent_location, force=False, show_progress=True)
        source_path = get_registry_folder() / fork_namespace / fork_name / fork_version

        # Prompt for the new agent name if not provided
        if not new_name:
            new_name = input("Enter the new agent name: ").strip()
            if not new_name:
                print("Agent name cannot be empty.")
                return

            # confirm pattern is ok
            identifier_pattern = re.compile(r"^[a-zA-Z0-9_\-.]+$")
            if identifier_pattern.match(new_name) is None:
                print("Invalid Name, please choose something different")
                return

        # Set the destination path
        dest_path = get_registry_folder() / namespace / new_name / "0.0.1"

        # Copy the agent files
        shutil.copytree(source_path, dest_path)

        # Update metadata.json
        metadata_path = dest_path / "metadata.json"
        with open(metadata_path, "r") as file:
            metadata = json.load(file)

        metadata["name"] = new_name
        metadata["version"] = "0.0.1"

        with open(metadata_path, "w") as file:
            json.dump(metadata, file, indent=2)

        print(f"\nForked agent '{agent_location}' to '{dest_path}'")
        print(f"Agent '{new_name}' created at '{dest_path}' with updated metadata.")
        print("\nUseful commands:")
        print(f"  > nearai agent interactive {new_name} --local")
        print(f"  > nearai registry upload {dest_path}")


class VllmCli:
    def run(self, *args: Any, **kwargs: Any) -> None:  # noqa: D102
        original_argv = sys.argv.copy()
        sys.argv = [
            sys.argv[0],
        ]
        for key, value in kwargs.items():
            sys.argv.extend([f"--{key.replace('_', '-')}", str(value)])
        print(sys.argv)

        try:
            runpy.run_module("vllm.entrypoints.openai.api_server", run_name="__main__", alter_sys=True)
        finally:
            sys.argv = original_argv


class HubCLI:
    def chat(self, **kwargs):
        """Chat with model from NearAI hub.

        Args:
        ----
            query (str): User's query to model
            endpoint (str): NearAI HUB's url
            model (str): Name of a model
            provider (str): Name of a provider
            info (bool): Display system info
            kwargs (Dict[str, Any]): All cli keyword arguments

        """
        from nearai.hub import Hub

        hub = Hub(CONFIG)
        hub.chat(kwargs)


class LogoutCLI:
    def __call__(self, **kwargs):
        """Clear NEAR account auth data."""
        from nearai.config import load_config_file, save_config_file

        config = load_config_file()
        if not config.get("auth") or not config["auth"].get("account_id"):
            print("Auth data does not exist.")
        else:
            config.pop("auth", None)
            save_config_file(config)
            print("Auth data removed")


class LoginCLI:
    def __call__(self, **kwargs):
        """Login with NEAR Mainnet account.

        Args:
        ----
            remote (bool): Remote login allows signing message with NEAR Account on a remote machine
            auth_url (str): Url to the auth portal
            accountId (str): AccountId in .near-credentials folder to signMessage
            privateKey (str): Private Key to sign a message
            kwargs (Dict[str, Any]): All cli keyword arguments

        """
        from nearai.login import generate_and_save_signature, login_with_file_credentials, login_with_near_auth

        remote = kwargs.get("remote", False)
        account_id = kwargs.get("accountId", None)
        private_key = kwargs.get("privateKey", None)

        if not remote and account_id and private_key:
            generate_and_save_signature(account_id, private_key)
        elif not remote and account_id:
            login_with_file_credentials(account_id)
        else:
            auth_url = kwargs.get("auth_url", "https://auth.near.ai")
            login_with_near_auth(remote, auth_url)

    def status(self):
        """Load NEAR account authorization data."""
        from nearai.login import print_login_status

        print_login_status()

    def save(self, **kwargs):
        """Save NEAR account authorization data.

        Args:
        ----
            accountId (str): Near Account
            signature (str): Signature
            publicKey (str): Public Key used to sign
            callbackUrl (str): Callback Url
            nonce (str): nonce
            kwargs (Dict[str, Any]): All cli keyword arguments

        """
        from nearai.login import update_auth_config

        account_id = kwargs.get("accountId")
        signature = kwargs.get("signature")
        public_key = kwargs.get("publicKey")
        callback_url = kwargs.get("callbackUrl")
        nonce = kwargs.get("nonce")

        if account_id and signature and public_key and callback_url and nonce:
            update_auth_config(account_id, signature, public_key, callback_url, nonce)
        else:
            print("Missing data")


class CLI:
    def __init__(self) -> None:  # noqa: D107
        self.registry = RegistryCli()
        self.login = LoginCLI()
        self.logout = LogoutCLI()
        self.hub = HubCLI()

        self.config = ConfigCli()
        self.benchmark = BenchmarkCli()
        self.evaluation = EvaluationCli()
        self.agent = AgentCli()
        self.finetune = FinetuneCli()
        self.tensorboard = TensorboardCli()
        self.vllm = VllmCli()

    def location(self) -> None:  # noqa: D102
        """Show location where nearai is installed."""
        from nearai import cli_path

        print(cli_path())

    def version(self):
        """Show nearai version."""
        print(importlib.metadata.version("nearai"))

    def task(self, *args, **kwargs):
        """CLI command for running a single task."""
        self.agent.task_cli(*args, **kwargs)


def check_update():
    """Check if there is a new version of nearai CLI available."""
    try:
        api = DefaultApi()
        latest = api.version_v1_version_get()
        current = importlib.metadata.version("nearai")

        if latest != current:
            print(f"New version of nearai CLI available: {latest}. Current version: {current}")
            print("Run `pip install --upgrade nearai` to update.")

    except Exception as _:
        pass


def main() -> None:
    check_update()
    fire.Fire(CLI)
