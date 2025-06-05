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
from nearai.aws_runner.service import EnvironmentRun, start_with_environment
from nearai.cli_help import handle_help_request
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
from nearai.shared.file_encryption import FileEncryption
from nearai.shared.naming import NamespacedName, create_registry_name
from nearai.shared.provider_models import ProviderModels, fetch_models_from_provider, get_provider_namespaced_model
from nearai.tensorboard_feed import TensorboardCli


class RegistryCli:
    """Manage items in the NEAR AI Registry including agents, models, datasets, and evaluations.

    These commands allow you to upload, download, update, and list available items in the NEAR AI Registry.

    Commands:
      nearai registry upload : Upload an item to the registry
        (<path>*)
      nearai registry download : Download an item from the registry
        (<entry-location>*, --force)
      nearai registry info : Show information about a registry item
        (<entry-location>*)
      nearai registry list : List available items in the registry
        (--namespace, --category, --tags, --total, --offset, --show-all, --show-latest-version, --star)
      nearai registry metadata-template : Create a metadata template
        (--local-path, --category, --description)
      nearai registry update : Update metadata of a registry item
        (<path>*)

    Options:
      <path>* (str) :
        Path to the directory containing the agent to upload
      <entry-location>* (str) :
        Entry location of the item to download (format: namespace/name/version)
      --force (bool) :
        Force download even if the item exists locally
      --namespace (str) :
        Filter items by namespace
      --category (str) :
        Filter items by category (e.g., 'agent', 'model')
      --tags (str) :
        Filter items by tags (comma-separated)
      --total (int) :
        Maximum number of items to show
      --offset (int) :
        Offset for pagination
      --show-all (bool) :
        Show all versions of items
      --show-latest-version (bool) :
        Show only the latest version of each item
      --star (str) :
        Show items starred by a specific user

    Examples:
      # Upload an agent to the registry
      nearai registry upload ./path/to/agent

      # Download an agent from the registry
      nearai registry download example.near/agent-name/0.0.3

      # Show information about a registry item
      nearai registry info example.near/agent-name/0.0.3

      # List items by category
      nearai registry list --category evaluation

      # List items with specific tags
      nearai registry list --tags "vector-store"

    Documentation:
        https://docs.near.ai/agents/registry

    """

    def info(self, entry: str) -> None:
        """Display detailed information about a registry item.

        Includes metadata and available provider matches for models.

        Args:
          entry (str) :
            Entry location of the item to display information for (format: namespace/name/version)

        Examples:
          # Show information about a specific registry item
          nearai registry info example.near/agent-name/0.0.3

          # Show information about a model
          nearai registry info example.near/model-name/1.0.0

        Documentation:
          https://docs.near.ai/agents/registry

        """
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
        """Create a metadata template file for a registry item.

        This generates a properly formatted metadata.json file with default values
        that can be customized for your agent or model.

        Args:
          local_path : str
            Path to the directory where the metadata template will be created
          category : str
            Category of the item (e.g., 'agent', 'model', 'dataset', 'evaluation')
          description : str
            Description of the item

        Examples:
          # Create a metadata template in the current directory
          nearai registry metadata-template

          # Create a metadata template for an agent with description
          nearai registry metadata-template --category agent --description "My helpful assistant"

          # Create a metadata template in a specific directory
          nearai registry metadata-template path/to/directory --category model

        """
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
        """List available items in the NEAR AI registry.

        You can filter the results by namespace, category, tags, and other criteria to find specific items.

        Args:
          namespace (str) :
            Filter items by namespace/user account (example.near)
          category (str) :
            Filter items by category ('agent', 'model', 'evaluation')
          tags (str) :
            Filter items by tags (comma-separated)
          total (int) :
            Maximum number of items to show
          offset (int) :
            Offset for pagination
          show_all (bool) :
            Show all versions of items
          show_latest_version (bool) :
            Show only the latest version of each item
          star (str) :
            Show items starred by a specific user

        Examples:
          # List all items in the registry
          nearai registry list

          # List agents in the registry
          nearai registry list --category agent

          # List items with specific tags
          nearai registry list --tags "summarization,text"

          # List items from a specific namespace
          nearai registry list --namespace example.near

          # Show all versions of items
          nearai registry list --show-all

        """
        # Check if we're listing models specifically and provide alternative options
        if category.lower() == "model":
            print("\n⚠️  The category=model entries in the registry are deprecated.")
            print("We recommend using Fireworks, OpenAI, Anthropic, Crynux, or other provider models instead.")
            print("\nEnter one of the following options:")
            print("- registry        : See the registry models anyway")
            print("- nearai          : List models from NEAR AI endpoint (Fireworks models, free inference)")
            print("- openai          : List available OpenAI models. Requires OPENAI_API_KEY.")
            print("- anthropic       : List available Anthropic models. Requires ANTHROPIC_API_KEY.")
            print(
                "- crynux          : List available Crynux models (framework support, public API key, low rate limit)"
            )
            print("(May require api keys or correct moon phase)")
            print("")

            choice = input("\nYour choice: ").strip().lower()

            if choice != "registry":
                models = fetch_models_from_provider(choice)
                for model in models:
                    print(f"{model}")
                return

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
        """Update the remote metadata of an item in the NEAR AI Registry.

        Looks for a metadata.json file in the given directory and updates the remote metadata with the new values.

        Args:
          local_path (str) :
            Path to the directory containing the item to update

        Examples:
          # Update metadata for the item in the current directory
          nearai registry update

          # Update metadata for a specific item
          nearai registry update path/to/item

        """
        path = resolve_local_path(Path(local_path))

        if CONFIG.auth is None:
            print("Please login with `nearai login`")
            exit(1)

        metadata_path = path / "metadata.json"
        check_metadata_present(metadata_path)

        with open(metadata_path) as f:
            metadata: Dict[str, Any] = json.load(f)

        namespace = get_namespace(path)

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
        """Create new registry items for unregistered common provider models.

        This command helps keep the registry up-to-date with the latest models from various providers.

        Args:
          dry_run (bool) :
            Perform a dry run without actually uploading

        Examples:
          # Perform a dry run to see what would be uploaded
          nearai registry upload-unregistered-common-provider-models

          # Actually upload the unregistered models
          nearai registry upload-unregistered-common-provider-models --dry-run=False

        """
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
        self,
        local_path: str,
        bump: bool = False,
        minor_bump: bool = False,
        major_bump: bool = False,
        encrypt: bool = False,
    ) -> Optional[EntryLocation]:
        """Upload an item to the NEAR AI registry for public use.

        Args:
          local_path (str) :
            Path to the agent directory
          bump (bool) :
            Automatically increment patch version if it already exists
          minor_bump (bool) :
            Bump with minor version increment (0.1.0 → 0.2.0)
          major_bump (bool) :
            Bump with major version increment (1.5.2 → 2.0.0)
          encrypt (bool) :
            Encrypt all uploaded files using a generated encryption key

        Examples:
          # Upload an item in the current directory
          nearai registry upload .

          # Upload a specific agent directory
          nearai registry upload ./path/to/item

          # Upload with automatic version bumping
          nearai registry upload ./path/to/item --bump

          # Upload with minor version bump
          nearai registry upload ./path/to/item --minor-bump

          # Upload with encryption enabled (private entries)
          nearai registry upload ./path/to/item --encrypt

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

        # Handle encryption key generation if --encrypt flag is used
        if encrypt:
            # Initialize details if not present
            if "details" not in metadata:
                metadata["details"] = {}

            # Generate encryption key if not present
            if "encryption_key" not in metadata["details"]:
                encryption_key = FileEncryption.generate_encryption_key()
                metadata["details"]["encryption_key"] = encryption_key

                # Update metadata.json file with the new encryption key
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, indent=2)

                console.print(
                    Panel(
                        Text.assemble(
                            ("🔐 Encryption enabled\n\n", "bold green"),
                            (f"Encryption key {encryption_key} generated and stored in metadata.json\n", "dim"),
                        ),
                        title="Encryption",
                        border_style="green",
                        padding=(1, 2),
                    )
                )

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
                    ("  --major-bump    # Major update (0.1.0 → 1.0.0)\n", "green"),
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
            result = registry.upload(path, show_progress=True, encrypt=encrypt)

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

    def download(self, entry_location: str, force: bool = False, encryption_key: Optional[str] = None) -> None:
        """Download an item from the NEAR AI registry to your local machine.

        This allows you to use or inspect agents, models, datasets, etc. that have been published by others.

        Args:
          entry_location (str) :
            Entry location of the item to download (format: namespace/name/version)
          force (bool) :
            Force download even if the item already exists locally
          encryption_key (str) :
            Decrypt files with this encryption key

        Examples:
          # Download a specific registry item
          nearai registry download example.near/agent-name/0.0.3

          # Force download an item that already exists locally
          nearai registry download example.near/model-name/1.0.0 --force

        """
        registry.download(entry_location, force=force, show_progress=True, encryption_key=encryption_key)

    def __call__(self):
        """Show help when 'nearai registry' is called without subcommands."""
        custom_args = ["nearai", "registry", "--help"]
        handle_help_request(custom_args)


class ConfigCli:
    """Configuration commands help you manage your NEAR AI CLI settings.

    You can view, set, and modify various configuration values that control how the CLI behaves.

    Commands:
      nearai config set : Add or update a configuration value
        (key*, value*, --local)
      nearai config get : Retrieve a configuration value
        (key*)
      nearai config show : Display all configuration values

    Options:
      key* (str) :
        The configuration key to set or get
      value* (str) :
        The value to assign to the configuration key
      --local (bool) :
        Store the configuration value in the local config file

    Examples:
      # View all configuration values
      nearai config show

      # Get a specific configuration value
      nearai config get api_url

      # Set a configuration value (globally)
      nearai config set model claude-3-opus-20240229

      # Set a configuration value (locally for current project)
      nearai config set model claude-3-opus-20240229 --local

      # Change the API URL
      nearai config set api_url https://custom-api.example.com

    """

    def set(self, key: str, value: str, local: bool = False) -> None:
        """Add key-value pair to the config file."""
        update_config(key, value, local)

    def get(self, key: str) -> None:
        """Get value of a key in the config file."""
        print(CONFIG.get(key))

    def show(self) -> None:  # noqa: D102
        for key, value in asdict(CONFIG).items():
            print(f"{key}: {value}")

    def __call__(self) -> None:
        """Show help when 'nearai config' is called without subcommands."""
        custom_args = ["nearai", "config", "--help"]
        handle_help_request(custom_args)


class BenchmarkCli:
    """Commands for running and listing benchmarks on datasets with solver strategies.

    Commands:
      nearai benchmark run : Run benchmark on a dataset with a solver strategy
        (dataset*, solver_strategy*, --max-concurrent, --force, --subset,
        --check-compatibility, --record, --num-inference-retries)
      nearai benchmark list : List all executed benchmarks
        (--namespace, --benchmark, --solver, --args, --total, --offset)

    Options:
      dataset* (str) :
        Dataset to benchmark on
      solver_strategy* (str) :
        Solver strategy to use
      --max-concurrent (int) :
        Number of concurrent tasks to run
      --force (bool) :
        Force re-run even if cached results exist
      --subset (str) :
        Subset of the dataset to run on
      --check-compatibility (bool) :
        Check if solver is compatible with dataset
      --record (bool) :
        Record the benchmark results
      --num-inference-retries (int) :
        Number of retries for inference
      --namespace (str) :
        Filter benchmarks by namespace
      --benchmark (str) :
        Filter benchmarks by benchmark name
      --solver (str) :
        Filter benchmarks by solver name
      --args (str) :
        Filter benchmarks by solver arguments
      --total (int) :
        Total number of results to show
      --offset (int) :
        Offset for pagination

    Examples:
      # Run a benchmark on a dataset with a solver strategy
      nearai benchmark run my-dataset my-solver-strategy --max-concurrent 4 --force

      # List benchmark results filtered by namespace
      nearai benchmark list --namespace my-namespace --benchmark my-benchmark --total 50

    """

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

        This command executes a benchmark on a specified dataset using a given solver strategy.
        Results are cached in the database for subsequent runs unless --force is used.

        Args:
          dataset (str) :
            Name of the dataset to benchmark against
          solver_strategy (str) :
            Name of the solver strategy to use
          max_concurrent (int) :
            Maximum number of concurrent runs (-1 for CPU count)
          force (bool) :
            Force re-running the benchmark and update cache
          subset (str) :
            Optional subset of the dataset to use
          check_compatibility (bool) :
            Whether to check solver-dataset compatibility
          record (bool) :
            Whether to record detailed benchmark results
          num_inference_retries (int) :
            Number of retries for inference operations
          **solver_args : (dict)
            Additional arguments passed to the solver strategy

        Examples:
            # Run a benchmark with default settings
            nearai benchmark run my-dataset my-solver-strategy

            # Run with custom concurrency and force update
            nearai benchmark run my-dataset my-solver-strategy --max-concurrent 4 --force

            # Run on a subset with custom solver arguments
            nearai benchmark run my-dataset my-solver-strategy --subset train --arg1 value1 --arg2 value2

        Documentation:
            https://docs.near.ai/models/benchmarks_and_evaluations/

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
    ) -> None:
        """List all executed benchmarks.

        This command displays a table of all executed benchmarks, with options to filter
        by namespace, benchmark name, solver name, and solver arguments. Results are
        paginated using limit and offset parameters.

        Args:
          namespace (str) :
            Filter results by namespace
          benchmark (str) :
            Filter results by benchmark name
          solver (str) :
            Filter results by solver name
          args (str) :
            Filter results by solver arguments (JSON string)
          total (int) :
            Maximum number of results to display
          offset (int) :
            Number of results to skip

        Examples:
            # List all benchmarks with default pagination
            nearai benchmark list

            # Filter by namespace and benchmark name
            nearai benchmark list --namespace my-namespace --benchmark-name my-benchmark

            # Filter by solver with custom pagination
            nearai benchmark list --solver-name my-solver --limit 20 --offset 40

            # Filter by solver arguments
            nearai benchmark list --solver-args '{"arg1": "value1"}'

        Documentation:
            https://docs.near.ai/models/benchmarks_and_evaluations/

        """
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

    def __call__(self) -> None:
        """Show help when 'nearai benchmark' is called without subcommands."""
        custom_args = ["nearai", "benchmark", "--help"]
        handle_help_request(custom_args)


class EvaluationCli:
    """Commands for evaluating and analyzing model performance on benchmark datasets.

    Commands:
      nearai evaluation table : Print table of evaluations
        (--all-key-columns, --all-metrics, --num-columns, --metric-name-max-length)
      nearai evaluation read_solutions : Read solutions.json from evaluation entry
        (entry*, --status, --verbose)

    Options:
      entry* (str) :
        Evaluation entry to read solutions from (format: namespace/name/version)
      --all-key-columns (bool) :
        Show all key columns in the table
      --all-metrics (bool) :
        Show all metrics in the table
      --num-columns (int) :
        Maximum number of columns to display
      --metric-name-max-length (int) :
        Maximum length for metric names in display
      --status (bool) :
        Filter solutions by status (true/false)
      --verbose (bool) :
        Show verbose information including detailed logs

    Examples:
      # Display evaluation table with default settings
      nearai evaluation table

      # Display evaluation table with all metrics and columns
      nearai evaluation table --all-key-columns --all-metrics --num-columns 10

      # Read solutions from an evaluation entry
      nearai evaluation read_solutions example.near/benchmark-result/0.1.0

      # Read only successful solutions with verbose output
      nearai evaluation read_solutions example.near/benchmark-result/0.1.0 --status true --verbose

      Documentation:
        https://docs.near.ai/models/benchmarks_and_evaluations/

    """

    def table(
        self,
        all_key_columns: bool = False,
        all_metrics: bool = False,
        num_columns: int = 6,
        metric_name_max_length: int = 30,
    ) -> None:
        """Displays a table of all evaluation results, with options to customize the display of columns and metrics.

        The table can be configured to show all key columns and metrics, or a limited subset for better readability.

        Args:
        ----
          all_key_columns (bool) :
            Show all key columns in the table instead of just the important ones. Default is False.
          all_metrics (bool) :
            Show all available metrics instead of just the default subset. Default is False.
          num_columns (int) :
            Maximum number of columns to display in the table.
          metric_name_max_length (int) :
            Maximum length for metric names in the display.

        Examples:
        --------
            # Display evaluation table with default settings
            nearai evaluation table

            # Show all available columns and metrics
            nearai evaluation table --all-key-columns --all-metrics

            # Customize table display
            nearai evaluation table --num-columns 8 --metric-name-max-length 40

        Documentation:
            https://docs.near.ai/models/benchmarks_and_evaluations/

        """
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
        """Reads and displays the solutions.json file from a specified evaluation entry.

          It can filter solutions by status and show either concise or verbose output for each solution.

        Args:
        ----
          entry (str) :
            Evaluation entry to read solutions from (format: namespace/name/version)
          status (Optional[bool]) :
            Filter solutions by status (true/false)
          verbose (bool) :
            Show verbose information including detailed logs

        Examples:
        --------
            # Read all solutions from an evaluation entry
            nearai evaluation read_solutions example.near/benchmark-result/0.1.0

            # Read only successful solutions
            nearai evaluation read_solutions example.near/benchmark-result/0.1.0 --status true

            # Read solutions with verbose output
            nearai evaluation read_solutions example.near/benchmark-result/0.1.0 --verbose

        Documentation:
            https://docs.near.ai/models/benchmarks_and_evaluations/

        """
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

    def __call__(self) -> None:
        """Show help when 'nearai evaluation' is called without subcommands."""
        custom_args = ["nearai", "evaluation", "--help"]
        handle_help_request(custom_args)


class AgentCli:
    """For creating and interacting with agents.

    Agent commands allow you to create and interact with agents by running them locally or via NEAR AI Cloud.

    Commands:
      nearai agent create : Create a new agent
        (--name, --description)
      nearai agent interactive : Run an agent interactively
        (--agent, --thread-id, --tool-resources, --local, --verbose, --env-vars)
      nearai agent task : Run a single task with an agent
        (--agent*, --task*, --thread-id, --tool-resources, --file-ids, --local, --verbose, --env-vars)
      nearai agent upload : Upload an agent to the registry
        (--local-path, --bump, --minor-bump, --major-bump)
      nearai agent dev : Run local UI for development of agents
      nearai agent inspect : Inspect environment from given path
        (<path>*)

    Options:
      <path>* (str) :
        Path to the agent directory or agent ID
      --name (str) :
        Name for the new agent
      --description (str) :
        Description of the new agent
      --agent (str) :
        Path to the agent directory or agent ID
      --thread-id (str) :
        Thread ID to continue an existing conversation
      --tool-resources (dict) :
        Tool resources to pass to the agent
      --file-ids (list) :
        File IDs to attach to the message
      --local (bool) :
        Run the agent locally instead of in the cloud
      --verbose (bool) :
        Show detailed debug information during execution
      --env-vars (dict) :
        Environment variables to pass to the agent
      --task (str) :
        Task to run with the agent
      --bump (bool) :
        Automatically increment patch version if it already exists
      --minor-bump (bool) :
        Bump with minor version increment (0.1.0 → 0.2.0)
      --major-bump (bool) :
        Bump with major version increment (1.5.0 → 2.0.0)
      --stream (bool) :
        Stream the agent's output, only works with agents that stream completions

    Examples:
      # Create a new agent interactively (Step-by-step prompts)
      nearai agent create

      # Create a new agent with specific name and description
      nearai agent create --name my-agent --description "My helpful assistant"

      # Run an agent interactively (Choose an agent from the list)
      nearai agent interactive

      # Run a specific agent interactively in local mode
      nearai agent interactive --agent path/to/agent --local

      # Run a single task with an agent
      nearai agent task --agent example.near/agent-name/0.0.3 --task "Summarize this article: https://example.com/article"

      # Upload an agent to the registry
      nearai agent upload ./path/to/agent

      # Upload an agent with automatic version bumping
      nearai agent upload ./path/to/agent --bump

    Documentation:
      https://docs.near.ai/agents/quickstart

    """

    def dev(self) -> int:
        """Run a local development UI for agents that have their own UI.

        This launches a local server for testing and developing agent functionality in a browser-based environment.

        Examples:
          # Start the local development server
          nearai agent dev

        """
        if not os.path.exists("hub/demo/.env"):
            shutil.copy("hub/demo/.env.example", "hub/demo/.env")

        ret_val = os.system("npm install --prefix hub/demo")
        if ret_val != 0:
            print("Node.js is required to run the development server.")
            print("Please install Node.js from https://nodejs.org/")
        ret_val = os.system("npm run dev --prefix hub/demo")
        return ret_val

    def inspect(self, path: str) -> None:
        """Inspect the environment and contents of an agent at the specified path.

        This launches a Streamlit interface showing the agent's structure, code, and metadata.

        Args:
          path : str
            Path to the agent directory to inspect (required)

        Examples:
          # Inspect a local agent
          nearai agent inspect ./path/to/agent

          # Inspect a downloaded registry agent
          nearai agent inspect .near-registry/your-namespace/agent-name/0.1.0

        """
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
        """Run an agent interactively in a conversational interface.

        If no agent is specified, you'll be presented with a list of available agents to choose from.
        Specifying an agent will run the agent from NEAR AI Cloud. If you want to run a specific local agent,
        pass the path to the agent followed by the --local flag. (See examples below.)

        Args:
          agent (str) :
            Path to the agent directory or agent ID (optional)
          thread_id (str) :
            Thread ID to continue an existing conversation
          tool_resources (dict) :
            Tool resources to pass to the agent (JSON format)
          local (bool) :
            Run the agent locally instead of in the cloud
          verbose (bool) :
            Show detailed debug information during execution
          env_vars (dict) :
            Environment variables to pass to the agent (JSON format)
          stream (bool) :
            Whether to stream the agent's output, only works with agents that stream completions


        Examples:
          # Select from a list of agents to run that you created or downloaded
          nearai agent interactive

          # Run an agent hosted on NEAR AI Cloud
          nearai agent interactive example.near/agent-name/latest

          # Run a specific agent locally
          nearai agent interactive ./path/to/local/agent --local

          # Run an agent locally with verbose output
          nearai agent interactive ./path/to/local/agent --local --verbose

          # Continue an existing conversation
          nearai agent interactive example.near/agent-name/0.0.3 --thread-id abc123

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

        if local:
            if stream:
                print("NOTE: streaming in interactive --local is not implemented.")
            env_run = self._start_local_session(
                agent=agent_id,
                thread_id=thread_id,
                tool_resources=tool_resources,
                local_path=agent_path,
                verbose=verbose,
                env_vars=env_vars,
            )

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

            if local:
                last_message_id = self._run_local_session(
                    task=new_message, env_run=env_run, last_message_id=last_message_id
                )
            else:
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
        """Run a single non-interactive task with an agent.

        The agent will process the task and return its response.
        This is useful for automation or when you don't need an ongoing conversation.

        Args:
          agent (str) :
            Path to the agent directory or agent ID (required)
          task (str) :
            The task or question to send to the agent (required)
          thread_id (str) :
            Thread ID to continue an existing conversation
          tool_resources (dict) :
            Tool resources to pass to the agent (JSON format)
          file_ids (list) :
            File IDs to attach to the message
          local (bool) :
            Run the agent locally instead of in the cloud
          verbose (bool) :
            Show detailed debug information during execution
          env_vars (dict) :
            Environment variables to pass to the agent (JSON format)
          stream (bool) :
            Stream the agent's output, only works with agents that stream completions

        Examples:
          # Send a simple task to an agent
          nearai agent task --agent example.near/agent-name/0.0.3 --task "Summarize this article: https://example.com/article"

          # Run a local agent with environment variables
          nearai agent task --agent path/to/agent --task "Generate a report" --local --env-vars '{"API_KEY": "secret"}'

          # Continue a conversation in an existing thread
          nearai agent task --agent example.near/agent-name/0.0.3 --task "Continue the analysis" --thread-id abc123

        """
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

    def _start_local_session(
        self,
        agent: str,
        thread_id: Optional[str] = None,
        tool_resources: Optional[Dict[str, Any]] = None,
        local_path: Optional[Path] = None,
        verbose: bool = False,
        env_vars: Optional[Dict[str, Any]] = None,
    ) -> EnvironmentRun:
        """Starts local session, no messages yet from user."""
        assert_user_auth()

        hub_client = get_hub_client()
        if thread_id:
            thread = hub_client.beta.threads.retrieve(thread_id)
        else:
            thread = hub_client.beta.threads.create(
                tool_resources=tool_resources,
            )
        thread_id = thread.id
        print(f"thread_id = {thread_id}")

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
        return start_with_environment(str(local_path), auth, thread_id, run.id, str(local_path), params)

    def _run_local_session(
        self,
        task: str,
        env_run: EnvironmentRun,
        last_message_id: Optional[str] = None,
    ) -> Optional[str]:
        env_run.run(task)

        # List new messages
        hub_client = get_hub_client()
        messages = hub_client.beta.threads.messages.list(
            thread_id=env_run.thread_id, after=last_message_id, order="asc"
        )
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
        self.last_thread_id = env_run.thread_id

        return last_message_id

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

    def create(self, name: Optional[str] = None, description: Optional[str] = None) -> None:
        """Create a new AI agent from scratch.

        Args:
          name (str) :
            Name for the new agent (optional).
          description (str) :
            Description of the new agent (optional).

        Examples:
          # Create a new agent step-by-step with prompts
          nearai agent create

          # Create with specific name and description
          nearai agent create --name my_agent --description "My new agent"

        Documentation:
          https://docs.near.ai/agents/quickstart

        """
        # Check if the user is authenticated
        if CONFIG.auth is None or CONFIG.auth.namespace is None:
            print("Please login with `nearai login` before creating an agent.")
            return

        namespace = CONFIG.auth.namespace

        # Import the agent creator functions
        from nearai.agent_creator import create_new_agent

        # Create a new agent from scratch
        create_new_agent(namespace, name, description)

    def upload(
        self,
        local_path: str = ".",
        bump: bool = False,
        minor_bump: bool = False,
        major_bump: bool = False,
        encrypt: bool = False,
    ) -> Optional[EntryLocation]:
        """Alias for 'nearai registry upload'."""
        assert_user_auth()
        # Create an instance of RegistryCli and call its upload method
        registry_cli = RegistryCli()
        return registry_cli.upload(local_path, bump, minor_bump, major_bump, encrypt)

    def __call__(self) -> None:
        """Show help when 'nearai agent' is called without subcommands."""
        custom_args = ["nearai", "agent", "--help"]
        handle_help_request(custom_args)


class VllmCli:
    """Commands for running VLLM server with OpenAI-compatible API for local inference.

    Commands:
      nearai vllm run : Run VLLM server with OpenAI-compatible API
        (--model, --host, --port, --tensor-parallel-size, --gpu-memory-utilization)

    Options:
      --model (str) :
        Path to the model or model name from Hugging Face
      --host (str) :
        Host to bind the server to
      --port (int) :
        Port to bind the server to
      --tensor-parallel-size (int) :
        Number of GPUs to use for tensor parallelism
      --gpu-memory-utilization (float) :
        Fraction of GPU memory to use

    Examples:
      # Run VLLM server with default settings
      nearai vllm run --model mistralai/Mistral-7B-Instruct-v0.1

      # Run VLLM server with custom host and port
      nearai vllm run --model meta-llama/Llama-2-7b-chat-hf --host 0.0.0.0 --port 8080

      # Run with multiple GPUs and specific memory utilization
      nearai vllm run --model meta-llama/Llama-2-13b-chat-hf --tensor-parallel-size 2 --gpu-memory-utilization 0.8

    """

    def run(self, *args: Any, **kwargs: Any) -> None:  # noqa: D102 D417
        """Run a VLLM server with an OpenAI-compatible API for local inference.

        This command starts a VLLM server that provides an OpenAI-compatible API for running
        language models locally. The server supports various configuration options for
        optimizing performance and resource utilization.

        Args:
          **kwargs : (dict)
            Keyword arguments that can include:
            model (str):
              Path to the model or model name from Hugging Face
            host (str):
              Host to bind the server to
            port (int):
              Port to bind the server to
            tensor_parallel_size (int):
              Number of GPUs to use for tensor parallelism
            gpu_memory_utilization (float):
              Fraction of GPU memory to use

        Examples:
            # Run VLLM server with default settings
            nearai vllm run --model mistralai/Mistral-7B-Instruct-v0.1

            # Run VLLM server with custom host and port
            nearai vllm run --model meta-llama/Llama-2-7b-chat-hf --host 0.0.0.0 --port 8080

            # Run with multiple GPUs and specific memory utilization
            nearai vllm run --model meta-llama/Llama-2-13b-chat-hf --tensor-parallel-size 2 --gpu-memory-utilization 0.8

            # Run with additional VLLM configuration
            nearai vllm run --model mistralai/Mistral-7B-Instruct-v0.1 --max-model-len 4096 --dtype float16

        """
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

    def __call__(self) -> None:
        """Show help when 'nearai vllm' is called without subcommands."""
        custom_args = ["nearai", "vllm", "--help"]
        handle_help_request(custom_args)


class HubCLI:
    """Interact with models hosted on the NEAR AI hub.

    Commands:
      nearai hub chat : Chat with model from NEAR AI hub
        (--query, --model, --provider, --endpoint, --info)

    Options:
      --query (str) :
        User's query to send to the model
      --model (str) :
        Name of the model to use
      --provider (str) :
        Name of the provider (e.g., "fireworks", "hyperbolic")
      --endpoint (str) :
        NEAR AI Hub's URL to connect to
      --info (bool) :
        Display system information about the request

    Examples:
      # Chat with the default model
      nearai hub chat --query "Explain quantum computing in simple terms"

      # Chat with a specific model from a provider
      nearai hub chat --query "Write a limerick about AI" --model claude-3-opus-20240229 --provider fireworks

      # Display system information about the request
      nearai hub chat --query "Tell me a joke" --info

    """

    def chat(self, **kwargs):
        """Chat with a model from the NEAR AI hub.

        This command allows you to interact with language models hosted on the NEAR AI hub.
        You can specify which model to use, which provider to use, and customize the chat
        experience with various parameters.

        Args:
            **kwargs : (dict)
                Keyword arguments that can include:
                query (str):
                  User's query to send to the model
                model (str):
                  Name of the model to use
                provider (str):
                  Name of the provider (e.g., "fireworks", "hyperbolic")
                endpoint (str):
                  NEAR AI Hub's URL to connect to
                info (bool):
                  Display system information about the request
                Additional parameters passed to the model

        Examples:
            # Chat with the default model
            nearai hub chat --query "Explain quantum computing in simple terms"

            # Chat with a specific model from a provider
            nearai hub chat --query "Write a limerick about AI" --model claude-3-opus-20240229 --provider hyperbolic

            # Display system information about the request
            nearai hub chat --query "Tell me a joke" --info

            # Chat with a model using a custom endpoint
            nearai hub chat --query "Summarize this text" --endpoint https://custom-hub.example.com

        """
        from nearai.hub import Hub

        hub = Hub(CONFIG)
        hub.chat(kwargs)

    def __call__(self) -> None:
        """Show help when 'nearai hub' is called without subcommands."""
        custom_args = ["nearai", "hub", "--help"]
        handle_help_request(custom_args)


class LogoutCLI:
    """Clear your NEAR account authentication data from the local configuration.

    Commands:
      nearai logout : Logout and remove authentication data

    Examples:
      # Remove authentication data
      nearai logout

    """

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
    """Commands for authenticating with your NEAR account for accessing NEAR AI services.

    Commands:
      nearai login : Login with NEAR Mainnet account
        (--remote, --auth_url, --accountId, --privateKey)
      nearai login status : Display login status and auth details
      nearai login save : Save NEAR account auth data
        (--accountId, --signature, --publicKey, --callbackUrl, --nonce)

    Options:
      --remote (bool) :
        Enable remote login to sign message with NEAR account on another machine
      --auth_url (str) :
        URL to the authentication portal
      --accountId (str) :
        NEAR account ID in .near-credentials folder to sign message
      --privateKey (str) :
        Private key to sign a message directly
      --signature (str) :
        Signature for manual authentication
      --publicKey (str) :
        Public key used to sign the message
      --callbackUrl (str) :
        Callback URL for the authentication flow
      --nonce (str) :
        Nonce value for authentication security

    Examples:
      # Login using web-based flow
      nearai login

      # Login using credentials from .near-credentials
      nearai login --accountId your-account.near

      # Login with direct key (less secure, use with caution)
      nearai login --accountId your-account.near --privateKey ed25519:YOUR_PRIVATE_KEY

      # Check current login status
      nearai login status

    """

    def __call__(self, **kwargs):
        """Login with NEAR Mainnet account."""
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
            kwargs (dict) :
                Keyword arguments that can include:
                accountId (str) :
                    Near Account ID
                signature (str) :
                    Signature
                publicKey (str) :
                    Public Key used to sign the message
                callbackUrl (str) :
                    Callback Url
                nonce (str) :
                    Nonce

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
    """Commands for managing permissions and access control for NEAR AI resources.

    Commands:
      nearai permission grant : Grant permission to an account
        (account_id*, permission*)
      nearai permission revoke : Revoke permission from an account
        (account_id*, --permission)

    Options:
      account_id (str) :
        The NEAR account ID to grant or revoke permissions for
      permission (str) :
        The permission to grant or revoke (leave empty on revoke to remove all permissions)

    Examples:
      # Grant model access permission to an account
      nearai permission grant alice.near model_access

      # Grant multiple permissions (run multiple commands)
      nearai permission grant bob.near agent_creation
      nearai permission grant bob.near model_access

      # Revoke a specific permission
      nearai permission revoke charlie.near model_access

      # Revoke all permissions from an account
      nearai permission revoke dave.near

    """

    def __init__(self) -> None:  # noqa: D107
        self.client = PermissionsApi()

    def grant(self, account_id: str, permission: str):
        """Grant a specific permission to a NEAR account.

        This command allows you to grant a specific permission to a NEAR account, enabling
        them to access certain NEAR AI resources or perform specific actions.

        Args:
        ----
           account_id : (str)
               The NEAR account ID to grant the permission to
           permission : (str)
               The permission to grant (e.g., 'model_access', 'agent_creation')

        Examples:
        --------
            # Grant model access permission to an account
            nearai permission grant alice.near model_access

            # Grant agent creation permission
            nearai permission grant bob.near agent_creation

            # Grant evaluation access permission
            nearai permission grant charlie.near evaluation_access

        """
        self.client.grant_permission_v1_permissions_grant_permission_post(account_id, permission)

    def revoke(self, account_id: str, permission: str = ""):
        """Revoke permissions from a NEAR account.

        If no permission is specified, all permissions will be revoked from the account.

        Args:
        ----
            account_id : (str)
                The NEAR account ID to revoke the permission from
            permission : (str)
                The permission to revoke (optional, if empty all permissions are revoked)

        Examples:
        --------
            # Revoke a specific permission
            nearai permission revoke alice.near model_access

            # Revoke all permissions from an account
            nearai permission revoke bob.near

            # Revoke agent creation permission
            nearai permission revoke charlie.near agent_creation

        """
        self.client.revoke_permission_v1_permissions_revoke_permission_post(account_id, permission)

    def __call__(self) -> None:
        """Show help when 'nearai permission' is called without subcommands."""
        custom_args = ["nearai", "permission", "--help"]
        handle_help_request(custom_args)


class CLI:
    # TODO: Dynamically generate help menu based on available commands
    """List of commands for NEAR AI CLI to be used in the help menu.

    Getting Started:
      nearai              CLI MAIN MENU HELP
      nearai login        Authenticate with your NEAR account
      nearai logout       Clear your NEAR account authentication data
      nearai version      Display the current version of the CLI
      nearai location     Show the installation location of the CLI

    Agent Development:
      nearai agent              AGENT HELP MENU
      nearai agent create       Create a new agent
      nearai agent upload       Upload an agent to the NEAR AI agent registry
      nearai agent interactive  Run an agent interactively
      nearai agent task         Run a single task with an agent
      nearai agent dev          Run local UI for development of agents
      nearai agent inspect      Inspect environment from given path

    Registry Management:
      nearai registry                    REGISTRY HELP MENU
      nearai registry upload             Upload an item to the registry
      nearai registry download           Download an item from the registry
      nearai registry info               Show information about a registry item
      nearai registry list               List available items in the registry
      nearai registry update             Update the remote version in an agent's metadata.json file
      nearai registry metadata-template  Create a metadata template
      nearai permission                  PERMISSION HELP MENU (manage access control)

    Model Operations:
      nearai benchmark run      Run benchmark on a dataset with a solver strategy
      nearai benchmark list     List all executed benchmarks
      nearai evaluation table   Print table of evaluations
      nearai finetune           Commands for fine-tuning modelsnear
      nearai tensorboard        Commands for TensorBoard integration
      nearai vllm run           Run VLLM server with OpenAI-compatible API
      nearai hub chat           Chat with model from NEAR AI hub

    Configuration:
      nearai config             CONFIG HELP MENU
      nearai config set         Set a configuration value
      nearai config get         Get a configuration value
      nearai config show        Show all configuration values

    """  # noqa: D400 D415 D210

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

    def help(self) -> None:
        """Display help information about the NEAR AI CLI."""
        custom_args = ["nearai", "--help"]
        handle_help_request(custom_args)


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
    """Main entry point for the NEAR AI CLI."""
    check_update()

    # Check if help is requested
    if "--help" in sys.argv or len(sys.argv) == 1:
        if handle_help_request():
            return

    # Otherwise, proceed with normal command processing
    fire.Fire(CLI)
