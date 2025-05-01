import asyncio
import importlib.metadata
import json
import os
import re
import runpy
import shutil
import sys
import threading
from collections import OrderedDict
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from textwrap import fill
from typing import Any, Dict, List, Optional, Union

import fire
from openai.types.beta.threads.message import Attachment
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.text import Text
from tabulate import tabulate

from nearai.agents.local_runner import LocalRunner
from nearai.cli_helpers import (
    assert_user_auth,
    display_agents_in_columns,
    display_version_check,
    has_pending_input,
    load_and_validate_metadata,
)
from nearai.config import (
    CONFIG,
    get_hub_client,
    update_config,
)
from nearai.finetune import FinetuneCli
from nearai.lib import check_metadata_present, parse_location, parse_tags
from nearai.log import LogCLI
from nearai.openapi_client import EntryLocation, EntryMetadataInput
from nearai.openapi_client.api.benchmark_api import BenchmarkApi
from nearai.openapi_client.api.default_api import DefaultApi
from nearai.openapi_client.api.delegation_api import DelegationApi
from nearai.openapi_client.api.evaluation_api import EvaluationApi
from nearai.openapi_client.api.jobs_api import JobsApi, WorkerKind
from nearai.openapi_client.api.permissions_api import PermissionsApi
from nearai.openapi_client.models.body_add_job_v1_jobs_add_job_post import BodyAddJobV1JobsAddJobPost
from nearai.registry import (
    check_version_exists,
    get_agent_id,
    get_metadata,
    get_namespace,
    get_registry_folder,
    increment_version_by_type,
    registry,
    resolve_local_path,
    validate_version,
)
from nearai.shared.client_config import (
    DEFAULT_MODEL,
    DEFAULT_MODEL_MAX_TOKENS,
    DEFAULT_MODEL_TEMPERATURE,
    DEFAULT_NAMESPACE,
    DEFAULT_PROVIDER,
)
from nearai.shared.client_config import (
    IDENTIFIER_PATTERN as PATTERN,
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
        path = resolve_local_path(Path(local_path))

        metadata_path = path / "metadata.json"

        version = path.name
        # Validate version format
        is_valid, error = validate_version(version)
        if not is_valid:
            print(error)
            return

        name = path.parent.name
        assert not re.match(PATTERN, name), f"Invalid agent name: {name}"
        assert " " not in name

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
                metadata["details"]["agent"]["framework"] = "minimal"

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
        path = resolve_local_path(Path(local_path))

        if CONFIG.auth is None:
            print("Please login with `nearai login`")
            exit(1)

        metadata_path = path / "metadata.json"
        check_metadata_present(metadata_path)

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
        assert " " not in entry_location.name

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

    def upload(
        self, local_path: str = ".", bump: bool = False, minor_bump: bool = False, major_bump: bool = False
    ) -> Optional[EntryLocation]:
        """Upload item to the registry.

        Args:
        ----
            local_path: Path to the directory containing the agent to upload
            bump: If True, automatically increment patch version if it already exists
            minor_bump: If True, bump with minor version increment (0.1.0 → 0.2.0)
            major_bump: If True, bump with major version increment (0.1.0 → 1.0.0)

        Returns:
        -------
            EntryLocation if upload was successful, None otherwise

        """
        console = Console()
        path = resolve_local_path(Path(local_path))
        metadata_path = path / "metadata.json"

        # Load and validate metadata
        metadata, error = load_and_validate_metadata(metadata_path)
        if error:
            console.print(
                Panel(Text(error, style="bold red"), title="Metadata Error", border_style="red", padding=(1, 2))
            )
            return None

        # At this point, metadata is guaranteed to be not None
        assert metadata is not None, "Metadata should not be None if error is None"

        name = metadata["name"]
        version = metadata["version"]

        # Get namespace using the function from registry.py
        try:
            namespace = get_namespace(path)
        except ValueError:
            console.print(
                Panel(
                    Text("Please login with `nearai login` before uploading", style="bold red"),
                    title="Authentication Error",
                    border_style="red",
                    padding=(1, 2),
                )
            )
            return None

        # Check if this version already exists
        exists, error = check_version_exists(namespace, name, version)

        if error:
            console.print(
                Panel(Text(error, style="bold red"), title="Registry Error", border_style="red", padding=(1, 2))
            )
            return None

        # Display the version check result
        display_version_check(namespace, name, version, exists)

        bump_requested = bump or minor_bump or major_bump

        if exists and bump_requested:
            # Handle version bump
            old_version = version

            # Determine increment type based on flags
            if major_bump:
                increment_type = "major"
            elif minor_bump:
                increment_type = "minor"
            else:
                increment_type = "patch"  # Default for bump

            version = increment_version_by_type(version, increment_type)

            # Enhanced version update message
            update_panel = Panel(
                Text.assemble(
                    ("Updating Version...\n\n", "bold"),
                    ("Previous version: ", "dim"),
                    (f"{old_version}\n", "yellow"),
                    ("New version:     ", "dim"),
                    (f"{version}", "green bold"),
                    ("\n\nIncrement type: ", "dim"),
                    (f"{increment_type}", "cyan"),
                ),
                title="Bump",
                border_style="green",
                padding=(1, 2),
            )
            console.print(update_panel)

            # Update metadata.json with new version
            metadata["version"] = version
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            console.print(f"\n✅ Updated [bold]{metadata_path}[/bold] with new version\n")
            console.print(Rule(style="dim"))

        elif exists and not bump_requested:
            # Show error panel for version conflict
            error_panel = Panel(
                Text.assemble(
                    ("To upload a new version:\n", "yellow"),
                    (f"1. Edit {metadata_path}\n", "dim"),
                    ('2. Update the "version" field (e.g., increment from "0.0.1" to "0.0.2")\n', "dim"),
                    ("3. Try uploading again\n\n", "dim"),
                    ("Or use the following flags:\n", "yellow"),
                    ("  --bump          # Patch update (0.0.1 → 0.0.2)\n", "green"),
                    ("  --minor-bump    # Minor update (0.0.1 → 0.1.0)\n", "green"),
                    ("  --major-bump    # Major update (0.0.1 → 1.0.0)\n", "green"),
                ),
                title="Version Conflict",
                border_style="red",
            )
            console.print(error_panel)
            return None

        # Version doesn't exist or has been bumped, proceed with upload
        console.print(
            f"\n📂 [bold]Uploading[/bold] version [green bold]{version}[/green bold] of [blue bold]{name}[/blue bold] to [cyan bold]{namespace}[/cyan bold]...\n"  # noqa: E501
        )

        try:
            result = registry.upload(path, show_progress=True)

            if result:
                success_panel = Panel(
                    Text.assemble(
                        ("Upload completed successfully! 🚀 \n\n", "bold green"),
                        ("Name:      ", "dim"),
                        (f"{result.name}\n", "cyan"),
                        ("Version:   ", "dim"),
                        (f"{result.version}\n", "cyan"),
                        ("Namespace: ", "dim"),
                        (f"{result.namespace}", "cyan"),
                    ),
                    title="Success",
                    border_style="green",
                    padding=(1, 2),
                )
                console.print(success_panel)
                return result
            else:
                console.print(
                    Panel(
                        Text("Upload failed for unknown reasons", style="bold red"),
                        title="Upload Error",
                        border_style="red",
                        padding=(1, 2),
                    )
                )
                return None

        except Exception as e:
            console.print(
                Panel(
                    Text(f"Error during upload: {str(e)}", style="bold red"),
                    title="Upload Error",
                    border_style="red",
                    padding=(1, 2),
                )
            )
            return None

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
        assert solver_strategy_class, (
            f"Solver strategy {solver_strategy} not found. Available strategies: {list(SolverStrategyRegistry.keys())}"
        )

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
            if not verbose and isinstance(info, dict):
                info.pop("verbose", {})
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
        stream: bool = False,
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
            stream: Whether to stream the agent's output, only works with agents that stream completions

        """
        assert_user_auth()

        if agent is None:
            local = True
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
        if local:
            agent_path = resolve_local_path(agent_path)
        else:
            try:
                parse_location(str(agent_path))
            except Exception:
                print(
                    f'Registry entry format is <namespace>/<name>/<version>, but "{agent_path}" was provided. Did you mean to run with a flag --local?'  # noqa: E501
                )
                exit(1)

        agent_id = get_agent_id(agent_path, local)

        last_message_id = None
        print(f"\n=== Starting interactive session with agent: {agent_id} ===")
        print("")
        print("Type 'exit' to end the session")
        print("Type 'multiline' to enter multiline mode")
        print("")

        metadata = get_metadata(agent_path, local)
        title = metadata.get("details", {}).get("agent", {}).get("welcome", {}).get("title")
        if title:
            print(title)
        description = metadata.get("details", {}).get("agent", {}).get("welcome", {}).get("description")
        if description:
            print(description)

        multiline = False

        def print_multiline_prompt():
            print("On Linux/macOS: To submit, press Ctrl+D at the beginning of a new line after your prompt")
            print("On Windows: Press Ctrl+Z followed by Enter")

        while True:
            first_line = input("> ")
            if first_line.lower() == "exit":
                break
            if not multiline and first_line.lower() == "multiline":
                multiline = True
                print_multiline_prompt()
                continue
            lines = [first_line]

            # NOTE: the code below tries to catch copy-paste by calling has_pending_input().
            # This is OS-specific functionality and has been tested on Unix/Linux/Mac:
            # 1. Works well with blocks of text of 3 lines and more.
            # 2. Alas, does not trigger with text of 2 lines or less.
            pending_input_on_this_line = has_pending_input()
            if multiline or pending_input_on_this_line:
                try:
                    pending_input_on_prev_line = pending_input_on_this_line
                    while True:
                        pending_input_on_this_line = has_pending_input()
                        if pending_input_on_prev_line or pending_input_on_this_line:
                            line = input("")
                        else:
                            if not multiline:
                                multiline = True
                                print_multiline_prompt()
                            line = input("> ")
                        lines.append(line)
                        pending_input_on_prev_line = pending_input_on_this_line
                except EOFError:
                    print("")

            new_message = "\n".join(lines)

            last_message_id = self._task(
                agent=agent_id,
                task=new_message,
                thread_id=thread_id,
                tool_resources=tool_resources,
                last_message_id=last_message_id,
                local_path=agent_path if local else None,
                verbose=verbose,
                env_vars=env_vars,
                streaming=stream,
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
        stream: bool = False,
    ) -> None:
        """CLI wrapper for the _task method."""
        last_message_id = self._task(
            agent=agent,
            task=task,
            thread_id=thread_id,
            tool_resources=tool_resources,
            file_ids=file_ids,
            local_path=resolve_local_path(Path(agent)) if local else None,
            verbose=verbose,
            env_vars=env_vars,
            streaming=stream,
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
        local_path: Optional[Path] = None,
        verbose: bool = False,
        env_vars: Optional[Dict[str, Any]] = None,
        streaming: bool = True,
    ) -> Optional[str]:
        """Runs agent non-interactively with a single task."""
        assert_user_auth()

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

        if not local_path:
            hub_client.beta.threads.runs.create_and_poll(
                thread_id=thread.id,
                assistant_id=agent,
            )
        elif streaming:
            run = hub_client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=agent,
                stream=True,
                extra_body={"delegate_execution": True},
            )
            params: dict = {
                "api_url": CONFIG.api_url,
                "tool_resources": [],  # run.tools, TODO this is not returned from the streaming run
                "data_source": "local_files",
                "user_env_vars": env_vars,
                "agent_env_vars": {},
                "verbose": verbose,
            }
            auth = CONFIG.auth
            assert auth is not None
            run_id = None
            for event in run:
                run_id = event.data.id
                break

            def run_async_loop():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self._print_stream_async(run))
                finally:
                    loop.close()

            streaming_thread = threading.Thread(target=run_async_loop)
            streaming_thread.start()

            LocalRunner(str(local_path), agent, thread.id, run_id, auth, params)
            streaming_thread.join()

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
            LocalRunner(str(local_path), agent, thread.id, run.id, auth, params)

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

    async def _print_stream_async(self, run):
        """Asynchronously print the stream of messages from the run.

        :param run: The stream to iterate over
        :return:
        """
        try:
            for event in run:
                if event and hasattr(event, "event") and event.event == "thread.message.delta":
                    if hasattr(event.data, "delta") and hasattr(event.data.delta, "content"):
                        for content in event.data.delta.content:
                            value = content.text.value
                            if value:
                                print(content.text.value, end="")
                else:
                    if event and hasattr(event, "event"):
                        if event.event == "thread.message.completed":
                            pass
                        elif event.event == "thread.message.error":
                            print(f"Error: {event.data.error}")
                        elif event.event in [
                            "thread.run.completed",
                            "thread.run.error",
                            "thread.run.canceled",
                            "thread.run.expired",
                            "thread.run.requires_action",
                        ]:
                            print("")
                            break
                    await asyncio.sleep(0.01)
        except Exception as e:
            print(f"Error in print_stream_async: {e}")

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

        # Import the agent creator functions
        from nearai.agent_creator import create_new_agent, fork_agent

        if fork:
            # Fork an existing agent
            fork_agent(fork, namespace, name)
        else:
            # Create a new agent from scratch
            create_new_agent(namespace, name, description)

    def upload(
        self, local_path: str = ".", bump: bool = False, minor_bump: bool = False, major_bump: bool = False
    ) -> Optional[EntryLocation]:
        """Upload agent to the registry.

        This is an alias for 'nearai registry upload'.

        Args:
        ----
            local_path: Path to the directory containing the agent to upload
            bump: If True, automatically increment patch version if it already exists
            minor_bump: If True, bump with minor version increment (0.1.0 → 0.2.0)
            major_bump: If True, bump with major version increment (0.1.0 → 1.0.0)

        Returns:
        -------
            EntryLocation if upload was successful, None otherwise

        """
        assert_user_auth()
        # Create an instance of RegistryCli and call its upload method
        registry_cli = RegistryCli()
        return registry_cli.upload(local_path, bump, minor_bump, major_bump)


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

        if location is None:
            print("Error: Failed to upload entry")
            return

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
