import importlib.metadata
import json
import os
import re
import runpy
import shutil
import sys
from collections import OrderedDict
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from textwrap import fill
from typing import Any, Dict, List, Optional, Tuple, Union

import fire
from openai.types.beta.threads.message import Attachment
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.text import Text
from tabulate import tabulate

from nearai.agents.local_runner import LocalRunner
from nearai.banners import NEAR_AI_BANNER
from nearai.cli_helpers import display_agents_in_columns
from nearai.config import (
    CONFIG,
    get_hub_client,
    update_config,
)
from nearai.finetune import FinetuneCli
from nearai.lib import check_metadata, parse_location, parse_tags
from nearai.log import LogCLI
from nearai.openapi_client import EntryLocation, EntryMetadataInput
from nearai.openapi_client.api.benchmark_api import BenchmarkApi
from nearai.openapi_client.api.default_api import DefaultApi
from nearai.openapi_client.api.delegation_api import DelegationApi
from nearai.openapi_client.api.evaluation_api import EvaluationApi
from nearai.openapi_client.api.jobs_api import JobsApi, WorkerKind
from nearai.openapi_client.api.permissions_api import PermissionsApi
from nearai.openapi_client.models.body_add_job_v1_jobs_add_job_post import BodyAddJobV1JobsAddJobPost
from nearai.registry import get_registry_folder, registry
from nearai.shared.client_config import (
    DEFAULT_MODEL,
    DEFAULT_MODEL_MAX_TOKENS,
    DEFAULT_MODEL_TEMPERATURE,
    DEFAULT_NAMESPACE,
    DEFAULT_PROVIDER,
)
from nearai.shared.naming import NamespacedName, create_registry_name
from nearai.shared.provider_models import ProviderModels, get_provider_namespaced_model
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

        version = path.name
        pattern = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"  # noqa: E501
        assert re.match(pattern, version), f"Invalid semantic version format: {version}"
        name = path.parent.name
        assert not re.match(pattern, name), f"Invalid agent name: {name}"

        with open(metadata_path, "w") as f:
            metadata: Dict[str, Any] = {
                "name": name,
                "version": version,
                "description": description,
                "category": category,
                "tags": [],
                "details": {},
                "show_entry": True,
            }

            if category == "agent":
                metadata["details"]["agent"] = {}
                metadata["details"]["agent"]["welcome"] = {
                    "title": name,
                    "description": description,
                }
                metadata["details"]["agent"]["defaults"] = {
                    "model": DEFAULT_MODEL,
                    "model_provider": DEFAULT_PROVIDER,
                    "model_temperature": DEFAULT_MODEL_TEMPERATURE,
                    "model_max_tokens": DEFAULT_MODEL_MAX_TOKENS,
                    "max_iterations": 1,
                }
                metadata["details"]["agent"]["framework"] = "base"

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

        namespace = CONFIG.auth.namespace

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

    def upload(self, local_path: str = ".") -> EntryLocation:
        """Upload item to the registry."""
        return registry.upload(Path(local_path), show_progress=True)

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
        namespace = CONFIG.auth.namespace

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

        dest_path = get_registry_folder() / name
        metadata_path = dest_path / "metadata.json"
        with open(metadata_path, "r") as file:
            metadata = json.load(file)

        be = BenchmarkExecutor(
            DatasetInfo(name, subset, dataset, metadata), solver_strategy_obj, benchmark_id=benchmark_id
        )

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
        table = api.table_v1_evaluation_table_get()

        print_evaluation_table(
            table.rows,
            table.columns,
            table.important_columns,
            all_key_columns,
            all_metrics,
            num_columns,
            metric_name_max_length,
        )

    def read_solutions(self, entry: str, status: Optional[bool] = None, verbose: bool = False) -> None:
        """Reads solutions.json from evaluation entry."""
        entry_path = registry.download(entry)
        solutions_file = entry_path / "solutions.json"

        if not solutions_file.exists():
            print(f"No solutions file found for entry: {entry}")
            return

        try:
            with open(solutions_file) as f:
                solutions = json.load(f)
        except json.JSONDecodeError:
            print(f"Error reading solutions file for entry: {entry}")
            return

        # Filter solutions if status is specified
        if status is not None:
            solutions = [s for s in solutions if s.get("status") == status]
        if not solutions:
            print("No solutions found matching criteria")
            return
        print(f"\nFound {len(solutions)} solutions{' with status=' + str(status) if status is not None else ''}")

        for i, solution in enumerate(solutions, 1):
            print("-" * 80)
            print(f"\nSolution {i}/{len(solutions)}:")
            datum = solution.get("datum")
            print(f"datum: {json.dumps(datum, indent=2, ensure_ascii=False)}")
            status = solution.get("status")
            print(f"status: {status}")
            info: dict = solution.get("info", {})
            if not verbose:
                info.pop("verbose")
            print(f"info: {json.dumps(info, indent=2, ensure_ascii=False)}")
            if i == 1:
                print("Enter to continue, type 'exit' to quit.")
            new_message = input("> ")
            if new_message.lower() == "exit":
                break


class AgentCli:
    def dev(self) -> int:
        """Run local UI for development of agents that have their own UI."""
        if not os.path.exists("hub/demo/.env"):
            shutil.copy("hub/demo/.env.example", "hub/demo/.env")

        ret_val = os.system("npm install --prefix hub/demo")
        if ret_val != 0:
            print("Node.js is required to run the development server.")
            print("Please install Node.js from https://nodejs.org/")
        ret_val = os.system("npm run dev --prefix hub/demo")
        return ret_val

    def inspect(self, path: str) -> None:
        """Inspect environment from given path."""
        import subprocess

        filename = Path(os.path.abspath(__file__)).parent / "streamlit_inspect.py"
        subprocess.call(["streamlit", "run", filename, "--", path])

    def interactive(
        self,
        agent: Optional[str] = None,
        thread_id: Optional[str] = None,
        tool_resources: Optional[Dict[str, Any]] = None,
        local: bool = False,
        verbose: bool = False,
        env_vars: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Runs agent interactively.

        Args:
        ----
            agent: Optional path to the agent directory. If not provided, will show agent selection menu
            thread_id: Optional thread ID to continue an existing conversation
            tool_resources: Optional tool resources to pass to the agent
            local: Whether to run the agent locally (default: False)
            verbose: Whether to show detailed debug information during execution
            env_vars: Optional environment variables to pass to the agent

        """
        if agent is None:
            # List available agents in the registry folder
            registry_path = Path(get_registry_folder())
            if not registry_path.exists():
                print("Error: Registry folder not found. Please create an agent first.")
                return

            agents = []
            # Walk through registry to find agents
            for namespace in registry_path.iterdir():
                if namespace.is_dir():
                    for agent_name in namespace.iterdir():
                        if agent_name.is_dir():
                            for version in agent_name.iterdir():
                                if version.is_dir():
                                    agents.append(version)

            if not agents:
                print("No agents found. Please create an agent first with 'nearai agent create'")
                return

            # Sort agents by namespace then name
            agents = sorted(agents, key=lambda x: (x.parts[-3], x.parts[-2]))
            display_agents_in_columns(agents)

            while True:
                try:
                    choice = int(Prompt.ask("[blue bold]Select an agent (enter number)")) - 1
                    if 0 <= choice < len(agents):
                        agent = str(agents[choice])
                        break
                    print("Invalid selection. Please try again.")
                except ValueError:
                    print("Please enter a valid number.")
                except KeyboardInterrupt:
                    print("\nOperation cancelled.")
                    return

        # Convert agent path to Path object if it's a string
        agent_path = Path(agent)
        if not agent_path.exists():
            print(f"Error: Agent not found at path: {agent_path}")
            return

        try:
            # Get the last 3 parts of the path (namespace/name/version)
            parts = agent_path.parts[-3:]
            agent_id = "/".join(parts)
        except IndexError:
            print("Error: Invalid agent path. Expected format: path/to/namespace/name/version")
            print("Example: ~/.nearai/registry/namespace/agent-name/0.0.1")
            return

        last_message_id = None
        print(f"\n=== Starting interactive session with agent: {agent_id} ===")
        print("Type 'exit' to end the session\n")

        while True:
            new_message = input("> ")
            if new_message.lower() == "exit":
                break

            last_message_id = self._task(
                agent=agent_id,
                task=new_message,
                thread_id=thread_id,
                tool_resources=tool_resources,
                last_message_id=last_message_id,
                local=local,
                verbose=verbose,
                env_vars=env_vars,
            )

            # Update thread_id for the next iteration
            if thread_id is None:
                thread_id = self.last_thread_id

    def task(
        self,
        agent: str,
        task: str,
        thread_id: Optional[str] = None,
        tool_resources: Optional[Dict[str, Any]] = None,
        file_ids: Optional[List[str]] = None,
        local: bool = False,
        verbose: bool = False,
        env_vars: Optional[Dict[str, Any]] = None,
    ) -> None:
        """CLI wrapper for the _task method."""
        last_message_id = self._task(
            agent=agent,
            task=task,
            thread_id=thread_id,
            tool_resources=tool_resources,
            file_ids=file_ids,
            local=local,
            verbose=verbose,
            env_vars=env_vars,
        )
        if last_message_id:
            print(f"Task completed. Thread ID: {self.last_thread_id}")
            print(f"Last message ID: {last_message_id}")

    def _task(
        self,
        agent: str,
        task: str,
        thread_id: Optional[str] = None,
        tool_resources: Optional[Dict[str, Any]] = None,
        file_ids: Optional[List[str]] = None,
        last_message_id: Optional[str] = None,
        local: bool = False,
        verbose: bool = False,
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
            attachments=[Attachment(file_id=file_id) for file_id in file_ids] if file_ids else None,
        )

        if not local:
            hub_client.beta.threads.runs.create_and_poll(
                thread_id=thread.id,
                assistant_id=agent,
            )
        else:
            run = hub_client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=agent,
                extra_body={"delegate_execution": True},
            )
            params = {
                "api_url": CONFIG.api_url,
                "tool_resources": run.tools,
                "data_source": "local_files",
                "user_env_vars": env_vars,
                "agent_env_vars": {},
                "verbose": verbose,
            }
            auth = CONFIG.auth
            assert auth is not None
            LocalRunner(agent, agent, thread.id, run.id, auth, params)

        # List new messages
        messages = hub_client.beta.threads.messages.list(thread_id=thread.id, after=last_message_id, order="asc")
        message_list = list(messages)
        if message_list:
            for msg in message_list:
                if msg.metadata and msg.metadata.get("message_type"):
                    continue
                if msg.role == "assistant":
                    print(f"Assistant: {msg.content[0].text.value}")
            last_message_id = message_list[-1].id
        else:
            print("No new messages")

        # Store the thread_id for potential use in interactive mode
        self.last_thread_id = thread.id

        return last_message_id

    def create(self, name: Optional[str] = None, description: Optional[str] = None, fork: Optional[str] = None) -> None:
        """Create a new agent or fork an existing one.

        Usage:
          nearai agent create  # Enters interactive mode
          nearai agent create --name <agent_name> --description <description>
          nearai agent create --fork <namespace/agent_name/version> [--name <new_agent_name>]

        Options:
          --name          Name of the new agent (optional).
          --description   Description of the new agent (optional).
          --fork          Fork an existing agent specified by namespace/agent_name/version.

        Examples
        --------
          nearai agent create   # Enters interactive mode
          nearai agent create --name my_agent --description "My new agent"
          nearai agent create --fork agentic.near/summary/0.0.3 --name new_summary_agent

        """
        # Check if the user is authenticated
        if CONFIG.auth is None or CONFIG.auth.namespace is None:
            print("Please login with `nearai login` before creating an agent.")
            return

        namespace = CONFIG.auth.namespace

        if fork:
            # Fork an existing agent
            self._fork_agent(fork, namespace, name)
        else:
            # Create a new agent from scratch
            self._create_new_agent(namespace, name, description)

    def _create_new_agent(self, namespace: str, name: Optional[str], description: Optional[str]) -> None:
        """Create a new agent from scratch."""
        # If no name/description provided, use interactive prompts
        init_instructions = ""
        if name is None and description is None:
            _, name, description, init_instructions = self._prompt_agent_details()

        # Set the agent path
        registry_folder = get_registry_folder()
        if registry_folder is None:
            raise ValueError("Registry folder path cannot be None")

        # Narrow the type of namespace & name from Optional[str] to str
        namespace_str: str = namespace if namespace is not None else ""
        if namespace_str == "":
            raise ValueError("Namespace cannot be None or empty")

        name_str: str = name if name is not None else ""
        if name_str == "":
            raise ValueError("Name cannot be None or empty")

        agent_path = registry_folder / namespace_str / name_str / "0.0.1"
        agent_path.mkdir(parents=True, exist_ok=True)

        metadata: Dict[str, Any] = {
            "name": name_str,
            "version": "0.0.1",
            "description": description or "",
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

        # Create a default agent.py with the provided initial
        agent_py_content = f"""from nearai.agents.environment import Environment


def run(env: Environment):
    # Your agent code here
    prompt = {{"role": "system", "content": "{init_instructions}"}}
    result = env.completion([prompt] + env.list_messages())
    env.add_reply(result)
    env.request_user_input()

run(env)

"""
        agent_py_path = agent_path / "agent.py"
        with open(agent_py_path, "w") as f:
            f.write(agent_py_content)

        # Create success message
        console = Console()
        success_title = Text(" 🎉 SUCCESS!", style="bold green")
        path_text = Text.assemble(("\n  • New AI Agent created at: ", "bold green"), (f"{agent_path}", "bold"))

        files_panel = Panel(
            Text.assemble(
                ("Edit agent code here:\n\n", "yellow"),
                (f"📄 - {agent_path}/agent.py\n", "bold blue"),
                (f"📄 - {agent_path}/metadata.json", "bold blue"),
            ),
            title="Agent Files",
            border_style="yellow",
        )

        commands_panel = Panel(
            Text.assemble(
                ("Run this agent locally:\n", "light_green"),
                (f"  nearai agent interactive {agent_path} --local\n\n", "bold"),
                ("Upload this agent to NEAR AI's public registry:\n", "light_green"),
                (f"  nearai registry upload {agent_path}\n\n", "bold"),
                ("Run ANY agent from your local registry:\n", "light_green"),
                ("  nearai agent interactive --local", "bold"),
            ),
            title="Useful Commands",
            border_style="green",
        )

        console.print("\n")
        console.print(success_title)
        console.print(path_text)
        console.print("\n")
        console.print(files_panel)
        console.print("\n")
        console.print(commands_panel)
        console.print("\n")

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

    def _prompt_agent_details(self) -> Tuple[str, str, str, str]:
        console = Console()

        # Get namespace from CONFIG, with null check
        if CONFIG.auth is None:
            raise ValueError("Not logged in. Please run 'nearai login' first.")
        namespace = CONFIG.auth.namespace

        # Welcome message
        console.print(NEAR_AI_BANNER)
        welcome_panel = Panel(
            Text.assemble(
                ("Let's create a new agent! 🦾 \n", "bold green"),
                ("We'll need some basic information to get started.", "dim"),
            ),
            title="Agent Creator",
            border_style="green",
        )
        console.print(welcome_panel)
        console.print("\n")

        # Name prompt with explanation
        name_info = Panel(
            Text.assemble(
                ("Choose a unique name for your agent using only:\n\n", ""),
                ("• letters\n", "dim"),
                ("• numbers\n", "dim"),
                ("• dots (.)\n", "dim"),
                ("• hyphens (-)\n", "dim"),
                ("• underscores (_)\n\n", "dim"),
                ("Examples: 'code-reviewer', 'data.analyzer', 'text_summarizer'", "green"),
            ),
            title="Agent Name Rules",
            border_style="blue",
        )
        console.print(name_info)

        while True:
            name = Prompt.ask("[bold blue]Enter agent name").strip()
            # Validate name format
            if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$", name):
                console.print(
                    "[red]❌ Invalid name format. " "Please use only letters, numbers, dots, hyphens, or underscores."
                )
                continue
            if " " in name:
                console.print("[red]❌ Spaces are not allowed. Use dots, hyphens, or underscores instead.")
                continue
            break

        console.print("\n")

        # Description prompt
        description_info = Panel(
            "Describe what your agent will do in a few words...", title="Description Info", border_style="blue"
        )
        console.print(description_info)
        description = Prompt.ask("[bold blue]Enter description")

        console.print("\n")

        # Initial instructions prompt
        init_instructions_info = Panel(
            Text.assemble(
                ("Provide initial instructions for your AI agent...\n\n", ""),
                ("This will be used as the system message to guide the agent's behavior.\n", "dim"),
                ("You can edit these instructions later in the `agent.py` file.\n\n", "dim"),
                (
                    "Example: You are a helpful humorous assistant. Use puns or jokes to make the user smile.",
                    "green",
                ),
            ),
            title="Instructions",
            border_style="blue",
        )
        console.print(init_instructions_info)
        init_instructions = Prompt.ask("[bold blue]Enter instructions")

        # Confirmation
        console.print("\n")
        summary_panel = Panel(
            Text.assemble(
                ("Summary of your new agent:\n\n", "bold"),
                ("Namespace/Account:    ", "dim"),
                (f"{namespace}\n", "green"),
                ("Agent Name:           ", "dim"),
                (f"{name}\n", "green"),
                ("Description:          ", "dim"),
                (f"{description}\n", "green"),
                ("Instructions:         ", "dim"),
                (f"{init_instructions}", "green"),
            ),
            title="📋 Review",
            border_style="green",
        )
        console.print(summary_panel)
        console.print("\n")

        if not Confirm.ask("[bold]Would you like to proceed?", default=True):
            console.print("[red]❌ Agent creation cancelled")
            sys.exit(0)
        return namespace, name, description, init_instructions


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
        """Chat with model from NEAR AI hub.

        Args:
        ----
            query (str): User's query to model
            endpoint (str): NEAR AI HUB's url
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


class PermissionCli:
    def __init__(self) -> None:  # noqa: D107
        self.client = PermissionsApi()

    def grant(self, account_id: str, permission: str):
        """Grant permission to an account."""
        self.client.grant_permission_v1_permissions_grant_permission_post(account_id, permission)

    def revoke(self, account_id: str, permission: str = ""):
        """Revoke permission from an account. If permission is empty all permissions are revoked."""
        self.client.revoke_permission_v1_permissions_revoke_permission_post(account_id, permission)


class CLI:
    def __init__(self) -> None:  # noqa: D107
        self.registry = RegistryCli()
        self.login = LoginCLI()
        self.logout = LogoutCLI()
        self.hub = HubCLI()
        self.log = LogCLI()

        self.config = ConfigCli()
        self.benchmark = BenchmarkCli()
        self.evaluation = EvaluationCli()
        self.agent = AgentCli()
        self.finetune = FinetuneCli()
        self.tensorboard = TensorboardCli()
        self.vllm = VllmCli()
        self.permission = PermissionCli()

    def submit(self, path: Optional[str] = None, worker_kind: str = WorkerKind.GPU_8_A100.value):
        """Submit a task to be executed by a worker."""
        if path is None:
            path = os.getcwd()

        worker_kind_t = WorkerKind(worker_kind)

        location = self.registry.upload(path)

        delegation_api = DelegationApi()
        delegation_api.delegate_v1_delegation_delegate_post(
            delegate_account_id=CONFIG.scheduler_account_id,
            expires_at=datetime.now() + timedelta(days=1),
        )

        try:
            client = JobsApi()
            client.add_job_v1_jobs_add_job_post(
                worker_kind_t,
                BodyAddJobV1JobsAddJobPost(entry_location=location),
            )
        except Exception as e:
            print("Error: ", e)
            delegation_api.revoke_delegation_v1_delegation_revoke_delegation_post(
                delegate_account_id=CONFIG.scheduler_account_id,
            )

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
