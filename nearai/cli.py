import json
import os
import runpy
import sys
import textwrap
from dataclasses import asdict
from pathlib import Path
from subprocess import check_output, run
from typing import Any, List, Optional, Tuple, Union

import fire
import pkg_resources
from fabric import ThreadingGroup as Group
from tabulate import tabulate

import nearai
from nearai.agent import load_agent
from nearai.benchmark import BenchmarkExecutor, DatasetInfo
from nearai.config import CONFIG, DATA_FOLDER, update_config
from nearai.dataset import load_dataset
from nearai.db import db
from nearai.environment import Environment
from nearai.finetune import FinetuneCli
from nearai.registry import Registry, agent, dataset, model, registry
from nearai.server import ServerClient, run_server
from nearai.solvers import SolverStrategy, SolverStrategyRegistry
from nearai.supervisor import SupervisorClient, run_supervisor
from nearai.tensorboard_feed import TensorboardCli


class Host:
    # SSH destination
    host: str
    # URL of the supervisor API
    endpoint: str
    # Name of the cluster for this endpoint
    cluster: str

    def __init__(self, host: str, cluster: str):  # noqa: D107
        self.host = host
        url = host.split("@")[1]
        self.endpoint = f"http://{url}:8000"
        self.cluster = cluster


def parse_hosts(hosts_path: Path) -> List[Host]:
    hostnames = set()
    hosts = []
    with open(hosts_path) as f:
        for line in f:
            p = line.find("#")
            if p != -1:
                line = line[:p]
            line = line.strip(" \n")
            if not line:
                continue
            host, cluster = line.split()
            hostnames.add(host)
            hosts.append(Host(host, cluster))

    assert len(hostnames) == len(hosts), "Duplicate hosts"
    return hosts


def install(hosts_description: List[Host], skip_install: str) -> None:
    """Install supervisor on every host.

    Skip nearai installation on the dev machine (skip_install).
    """
    hosts_str = [h.host for h in hosts_description]
    all_hosts = Group(*hosts_str)
    install_hosts = Group(*[h.host for h in hosts_description if h.host != skip_install])

    # Check we have connection to every host
    result = all_hosts.run("hostname", hide=True, warn=False)
    for host, res in sorted(result.items()):
        stdout = res.stdout.strip(" \n")
        print(f"Host: {host}, hostname: {stdout}")

    def run_bash_script(name: str) -> None:
        # Install setup_host.sh script
        script = nearai.etc(name)
        assert script.exists(), script
        install_hosts.put(script, f"/tmp/{name}")
        install_hosts.run(f"bash /tmp/{name}", warn=False)

    run_bash_script("install_cli.sh")

    nearai_path = "/home/setup/.local/bin/nearai"

    for conn in all_hosts:
        conn.run(f"{nearai_path} config set supervisor_id {conn.host}")

    all_hosts.run(f"{nearai_path} config set db_user {CONFIG.db_user}")
    all_hosts.run(f"{nearai_path} config set db_password {CONFIG.db_password}")

    result = all_hosts.run(f"{nearai_path} config get supervisor_id")
    for host, res in sorted(result.items()):
        stdout = res.stdout.strip(" \n")
        print(f"Host: {host}, supervisor_id: {stdout}")

    run_bash_script("setup_supervisor.sh")


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
    def __init__(self, registry: Registry):  # noqa: D107
        self._registry = registry

    def add(self, s3_path: str, description: str, name: Optional[str] = None, tags: str = "", **details: Any) -> None:
        """Add an item to the registry that was previously uploaded to S3."""
        tags_l = parse_tags(tags)
        assert self._registry.exists_in_s3(s3_path), f"Item {s3_path} does not exist in S3"
        self._registry.add(
            s3_path=s3_path,
            author=CONFIG.get_user_name(),
            description=description,
            name=name,
            show_entry=True,
            tags=tags_l,
            details=details,
        )

    def add_tags(self, identifier: int, tags: str) -> None:
        """Add tags to an item in the registry."""
        tags_l = parse_tags(tags)
        self._registry.add_tags(identifier=identifier, tags=tags_l)

    def remove_tag(self, identifier: int, tag: str) -> None:  # noqa: D102
        self._registry.remove_tag(identifier=identifier, tag=tag)

    def list(self, total: int = 16, show_all: bool = False, verbose: bool = False, tags: str = "") -> None:
        """List available items."""
        tags_l = parse_tags(tags)

        header = ["id", "name", "description", "tags"]

        if verbose:
            header += ["author", "date", "path"]

        table: list[list[Any]] = [header]

        for entry in self._registry.list(tags=tags_l, total=total, show_all=show_all):
            tags = ", ".join(entry.tags)

            row = [
                entry.id,
                (entry.name or entry.path) if not verbose else entry.name,
                textwrap.fill(entry.description or "", width=50),
                textwrap.fill(tags, width=20),
            ]

            if verbose:
                row += [entry.author, entry.time.strftime("%Y-%m-%d"), entry.path]

            table.append(row)

        print(tabulate(table, headers="firstrow", tablefmt="simple_grid"))

    def update(
        self,
        identifier: int,
        *,
        author: Optional[str] = None,
        description: Optional[str] = None,
        name: Optional[str] = None,
        details: Optional[dict] = None,
        show_entry: Optional[bool] = None,
    ) -> None:
        """Update item in the registry."""
        self._registry.update(
            identifier=identifier,
            author=author,
            description=description,
            name=name,
            details=details,
            show_entry=show_entry,
        )

    def info(self) -> None:
        """Show information about an item."""
        raise NotImplementedError()

    def upload(
        self,
        path: str,
        s3_path: str,
        description: str,
        name: Optional[str] = None,
        show_entry: bool = True,
        tags: str = "",
        **details: Any,
    ) -> None:
        """Upload item to the registry."""
        tags_l = parse_tags(tags)

        author = CONFIG.get_user_name()
        self._registry.upload(
            path=Path(path),
            s3_path=s3_path,
            author=author,
            description=description,
            name=name,
            details=details,
            show_entry=show_entry,
            tags=tags_l,
        )

    def download(self, name: str) -> None:
        """Download item."""
        self._registry.download(name)


class SupervisorCli:
    def install(self) -> None:
        """Install supervisor service in current machine."""
        file = nearai.etc("supervisor.service")
        target = Path("/etc/systemd/system/nearai_supervisor.service")
        run(["sudo", "cp", str(file), str(target)])
        run(["sudo", "systemctl", "daemon-reload"])

    def start(self) -> None:
        """Start installed supervisor service in current machine."""
        run(["sudo", "systemctl", "restart", "nearai_supervisor"])

    def run(self) -> None:
        """Run supervisor app in debug mode."""
        run_supervisor()


class ServerCli:
    def install_supervisors(self, hosts: str, skip: str = "") -> None:
        """Install and start supervisor in every host machine."""
        hosts_l = parse_hosts(Path(hosts))
        install(hosts_l, skip)

    def start(self, hosts: str) -> None:  # noqa: D102
        parsed_hosts = parse_hosts(Path(hosts))
        update_config("supervisors", [h.endpoint for h in parsed_hosts])

        db.set_all_supervisors_unavailable()

        for host in parsed_hosts:
            client = SupervisorClient(host.endpoint)
            client.init(host.cluster, host.endpoint)

        file = nearai.etc("server.service")
        target = Path("/etc/systemd/system/nearai_server.service")

        run(["sudo", "cp", str(file), str(target)])
        run(["sudo", "systemctl", "daemon-reload"])
        run(["sudo", "systemctl", "restart", "nearai_server"])

    def run(self) -> None:
        """Run server app in debug mode."""
        run_server()


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
    def __init__(self, datasets: RegistryCli, models: RegistryCli):  # noqa: D107
        self.datasets = datasets
        self.models = models

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
        benchmark_id = db.get_benchmark_id(dataset, solver_strategy, force, subset=subset, **solver_kwargs)

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
        env = Environment(path, [], CONFIG, create_files=False)
        env.inspect()

    def save_folder(self, path: str, name: Optional[str] = None) -> None:
        """Saves all subfolders with agent task runs (must contain non-empty chat.txt)."""
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
        env = Environment("/", [], CONFIG, create_files=False)
        # Read from stdin (piped input)
        lines = sys.stdin.readlines()
        env.save_from_history(lines, name)

    def interactive(self, agents: str, path: str, record_run: str = "true", load_env: str = "") -> None:
        """Runs agent interactively with environment from given path."""
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
        _agents = [load_agent(agent) for agent in agents.split(",")]
        env = Environment(path, _agents, CONFIG)
        env.run_task(task, record_run, load_env, max_iterations)

    def run(self, agents: str, task: str, path: str) -> None:
        """Runs agent in the current environment."""
        _agents = [load_agent(agent) for agent in agents.split(",")]
        env = Environment(path, [], CONFIG)
        env.exec_command("sleep 10")
        # TODO: Setup server that will allow to interact with agents and environment


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


class CLI:
    def __init__(self) -> None:  # noqa: D107
        self.registry = RegistryCli(registry)
        self.datasets = RegistryCli(dataset)
        self.models = RegistryCli(model)
        self.agents = RegistryCli(agent)

        self.supervisor = SupervisorCli()
        self.server = ServerCli()
        self.config = ConfigCli()
        self.benchmark = BenchmarkCli(self.datasets, self.models)
        self.environment = EnvironmentCli()
        self.finetune = FinetuneCli()
        self.tensorboard = TensorboardCli()
        self.vllm = VllmCli()

    def submit(self, command: str, name: str, nodes: int = 1, cluster: str = "truthwatcher") -> None:
        """Submit task."""
        author = CONFIG.get_user_name()

        client = ServerClient(CONFIG.server_url)

        # Check we can connect to the server
        client.status()

        # Detect in-progress git action
        # https://adamj.eu/tech/2023/05/29/git-detect-in-progress-operation/
        operation = ["CHERRY_PICK_HEAD", "MERGE_HEAD", "REBASE_HEAD", "REVERT_HEAD"]
        for op in operation:
            result = run(["git", "rev-parse", "--verify", op], capture_output=True)
            if result.returncode == 0:
                print(f"Detected in-progress git operation: {op}")
                return

        repository_url = check_output(["git", "remote", "-v"]).decode().split("\n")[0].split("\t")[1].split()[0]
        commit = check_output(["git", "rev-parse", "HEAD"]).decode().strip()
        diff = check_output(["git", "diff", "HEAD"]).decode()

        submission_result = client.submit(name, repository_url, commit, command, author, diff, nodes, cluster)

        print("experiment id:", submission_result["experiment"]["id"])

    def inference(self) -> None:
        """Submit inference task."""
        raise NotImplementedError()

    def location(self) -> None:  # noqa: D102
        print(nearai.cli_path())

    def version(self) -> None:  # noqa: D102
        # TODO: Show current commit or tag
        print(pkg_resources.get_distribution("nearai").version)

    def update(self) -> None:
        """Update nearai version."""
        path = DATA_FOLDER / "nearai"

        if path.absolute() != nearai.cli_path().absolute():
            print()
            print(f"Updating nearai version installed in {path}")
            print(f"The invoked nearai is in {nearai.cli_path()}")
            print()

        if path.exists():
            run(["git", "pull"], cwd=path)

    def status(self) -> None:
        """Show status of the cluster."""
        client = ServerClient(CONFIG.server_url)
        status = client.status()

        for experiment in status.get("last_experiments", []):
            experiment["diff_len"] = len(experiment.pop("diff", ""))

        print(json.dumps(status))


def main() -> None:
    fire.Fire(CLI)
