import json
import os
import runpy
import sys
from dataclasses import asdict
from pathlib import Path
from subprocess import run
from typing import Any, Dict, List, Optional, Tuple, Union

import boto3
import fire
import pkg_resources
from openapi_client import EntryLocation, EntryMetadataInput

from nearai.agent import load_agent
from nearai.clients.lambda_client import LambdaWrapper
from nearai.config import CONFIG, DATA_FOLDER, update_config
from nearai.finetune import FinetuneCli
from nearai.hub import hub
from nearai.lib import _check_metadata, parse_location
from nearai.registry import registry
from nearai.tensorboard_feed import TensorboardCli


def parse_tags(tags: Union[str, Tuple[str, ...]]) -> List[str]:
    if not tags:
        return []

    elif isinstance(tags, tuple):
        return list(tags)

    elif isinstance(tags, str):
        return tags.split(",")

    else:
        raise ValueError(f"Invalid tags argument: {tags}")


class RegistryCli:
    def info(self, entry: str) -> None:
        """Show information about an item."""
        entry_location = parse_location(entry)
        metadata = registry.info(entry_location)

        if metadata is None:
            print(f"Entry {entry} not found.")
            return

        print(metadata.model_dump_json(indent=2))

    def metadata_template(self, local_path: str = "."):
        """Create a metadata template."""
        path = Path(local_path)

        metadata_path = path / "metadata.json"

        with open(metadata_path, "w") as f:
            json.dump(
                {
                    "name": "foobar",
                    "version": "0.0.1",
                    "description": "Template metadata",
                    "category": "model",
                    "tags": ["foo", "bar"],
                    "details": {},
                    "show_entry": True,
                },
                f,
                indent=2,
            )

    def list(
        self,
        category: str = "",
        tags: str = "",
        total: int = 32,
        show_all: bool = False,
    ) -> None:
        """List available items."""
        # Make sure tags is a comma-separated list of tags
        tags_l = parse_tags(tags)
        tags = ",".join(tags_l)

        entries = registry.list(category, tags, total, show_all)

        for entry in entries:
            print(entry)

    def update(self, local_path: str = ".") -> None:
        """Update metadata of a registry item."""
        path = Path(local_path)

        if CONFIG.auth is None:
            print("Please login with `nearai login`")
            exit(1)

        metadata_path = path / "metadata.json"
        _check_metadata(metadata_path)

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

    def upload(self, local_path: str = ".") -> None:
        """Upload item to the registry."""
        registry.upload(Path(local_path).absolute(), show_progress=True)

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
    def run(
        self,
        dataset: str,
        solver_strategy: str,
        max_concurrent: int = -1,
        force: bool = False,
        subset: Optional[str] = None,
        **solver_kwargs: Any,
    ) -> None:
        """Run benchmark on a dataset with a solver strategy.

        It will cache the results in the database and subsequent runs will pull the results from the cache.
        If force is set to True, it will run the benchmark again and update the cache.
        """
        from nearai.benchmark import BenchmarkExecutor, DatasetInfo
        from nearai.dataset import load_dataset
        from nearai.solvers import SolverStrategy, SolverStrategyRegistry

        # TODO(db-api): Expose an interface to cache the result of the benchmarks
        # benchmark_id = db.get_benchmark_id(dataset, solver_strategy, force, subset=subset, **solver_kwargs)
        benchmark_id = -1

        name, subset, dataset = dataset, subset, load_dataset(dataset)

        solver_strategy_: SolverStrategy | None = SolverStrategyRegistry.get(solver_strategy, None)
        assert (
            solver_strategy
        ), f"Solver strategy {solver_strategy} not found. Available strategies: {list(SolverStrategyRegistry.keys())}"
        solver_strategy_obj: SolverStrategy = solver_strategy_(dataset_ref=dataset, **solver_kwargs)  # type: ignore
        assert (
            name in solver_strategy_obj.compatible_datasets()
        ), f"Solver strategy {solver_strategy} is not compatible with dataset {name}"

        be = BenchmarkExecutor(DatasetInfo(name, subset, dataset), solver_strategy_obj, benchmark_id=benchmark_id)

        cpu_count = os.cpu_count()
        max_concurrent = (cpu_count if cpu_count is not None else 1) if max_concurrent < 0 else max_concurrent
        be.run(max_concurrent=max_concurrent)


class EnvironmentCli:
    def setup(self, dataset: str, task_id: int) -> None:
        """Setup environment with given task from the dataset."""
        pass

    def inspect(self, path: str) -> None:
        """Inspect environment from given path."""
        from nearai.environment import Environment

        env = Environment(path, [], CONFIG, create_files=False)
        env.inspect()

    def save_folder(self, path: str, name: Optional[str] = None) -> None:
        """Saves all subfolders with agent task runs (must contain non-empty chat.txt)."""
        from nearai.environment import Environment

        env = Environment(path, [], CONFIG, create_files=False)
        env.save_folder(name)

    def save_from_history(self, name: Optional[str] = None) -> None:
        """Reads piped history, finds agent task runs, writes start_command.log files, and saves to registry. For detailed usage, run: nearai environment save_from_history --help.

        This command:
        1. Finds agent task runs (must contain non-empty chat.txt)
        2. Writes start_command.log files
        3. Saves to registry

        Only 'interactive' is supported.
        Assumes format:
        ' <line_number>  <program_name> environment interactive <comma_separated_agents> <path> <other_args>'
        Run:
        $ history | grep "environment interactive" | sed "s:~:$HOME:g" | nearai environment save_from_history environment_interactive_runs_from_lambda_00
        """  # noqa: E501
        from nearai.environment import Environment

        env = Environment("/", [], CONFIG, create_files=False)
        # Read from stdin (piped input)
        lines = sys.stdin.readlines()
        env.save_from_history(lines, name)

    def interactive(self, agents: str, path: str, record_run: str = "true", load_env: str = "") -> None:
        """Runs agent interactively with environment from given path."""
        from nearai.environment import Environment

        _agents = [load_agent(agent) for agent in agents.split(",")]
        env = Environment(path, _agents, CONFIG)
        env.run_interactive(record_run, load_env)

    def task(
        self,
        agents: str,
        task: str,
        path: str,
        max_iterations: int = 10,
        record_run: str = "true",
        load_env: str = "",
    ) -> None:
        """Runs agent non interactively with environment from given path."""
        from nearai.environment import Environment

        _agents = [load_agent(agent) for agent in agents.split(",")]
        env = Environment(path, _agents, CONFIG)
        env.run_task(task, record_run, load_env, max_iterations)

    def run(self, agents: str, task: str, path: str) -> None:
        """Runs agent in the current environment."""
        from nearai.environment import Environment

        _agents = [load_agent(agent) for agent in agents.split(",")]
        env = Environment(path, [], CONFIG)
        env.exec_command("sleep 10")
        # TODO: Setup server that will allow to interact with agents and environment

    def run_on_aws_lambda(self, agents: str, environment_id: str, auth: str, new_message: str = ""):
        """Invoke a Container based AWS lambda function to run agents on a given environment."""
        wrapper = LambdaWrapper(boto3.client("lambda", region_name="us-east-2"))
        wrapper.invoke_function(
            "agent-runner-docker",
            {"agents": agents, "environment_id": environment_id, "auth": json.dumps(auth), "new_message": new_message},
        )


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
        hub_query = kwargs.get("query")
        hub_endpoint = kwargs.get("endpoint", "http://127.0.0.1:8081/v1/chat/completions")
        hub_model = kwargs.get("model", "accounts/fireworks/models/llama-v3-70b-instruct")
        hub_provider = kwargs.get("provider", "fireworks")
        hub_info = kwargs.get("info", False)

        if not hub_query:
            return print("Error: 'query' is required for the `hub chat` command.")

        hub(hub_query, hub_endpoint, hub_model, hub_provider, hub_info)


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
        self.hub = HubCLI()

        self.config = ConfigCli()
        self.benchmark = BenchmarkCli()
        self.environment = EnvironmentCli()
        self.finetune = FinetuneCli()
        self.tensorboard = TensorboardCli()
        self.vllm = VllmCli()

    def inference(self) -> None:
        """Submit inference task."""
        raise NotImplementedError()

    def location(self) -> None:  # noqa: D102
        from nearai import cli_path

        print(cli_path())

    def version(self) -> None:  # noqa: D102
        # TODO: Show current commit or tag
        print(pkg_resources.get_distribution("nearai").version)

    def update(self) -> None:
        """Update nearai version."""
        from nearai import cli_path

        path = DATA_FOLDER / "nearai"

        if path.absolute() != cli_path().absolute():
            print()
            print(f"Updating nearai version installed in {path}")
            print(f"The invoked nearai is in {cli_path()}")
            print()

        if path.exists():
            run(["git", "pull"], cwd=path)


def main() -> None:
    # TODO: Check for latest version and prompt to update.
    fire.Fire(CLI)
