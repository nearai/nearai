import json
import os
import tarfile
import tempfile
from pathlib import Path
from shutil import rmtree
from typing import Any, Dict, Optional

from openapi_client import EntryLocation, EntryMetadata
from shared.inference_client import InferenceClient

from nearai import CONFIG, check_metadata, plain_location
from nearai.agents.agent import Agent
from nearai.agents.environment import Environment
from nearai.registry import get_registry_folder, registry

DEFAULT_OUTPUT_PATH = "/tmp/nearai/conversations/"


class LocalRunner:
    def __init__(  # noqa: D107
        self,
        path,
        agents,
        client_config,
        env_vars=None,
        tool_resources=None,
        print_system_log=True,
        confirm_commands=True,
    ) -> None:
        if path:
            self._path = path
        else:
            first_agent = agents[0].identifier
            self._path = f"{DEFAULT_OUTPUT_PATH}{first_agent.replace('/', '_')}"
            print(f"Output path not specified. Using default path: {self._path}")
        self._agents = agents
        self._client_config = client_config
        self._confirm_commands = confirm_commands

        client = InferenceClient(client_config)

        self._env = Environment(
            self._path,
            agents,
            client,
            env_vars=env_vars,
            tool_resources=tool_resources,
            print_system_log=print_system_log,
            approvals={"confirm_execution": self.confirm_execution},
        )

    @staticmethod
    def load_agents(agents: str, local: bool = False) -> list[Agent]:
        """Loads agents from the registry."""
        return [LocalRunner.load_agent(agent, local) for agent in agents.split(",")]

    @staticmethod
    def load_agent(name: str, local: bool = False) -> Agent:
        """Loads a single agent from the registry."""
        identifier = None
        if local:
            agent_files_path = get_registry_folder() / name
            if CONFIG.auth is None:
                namespace = "not-logged-in"
            else:
                namespace = CONFIG.auth.account_id
        else:
            agent_files_path = registry.download(name)
            identifier = name
        assert agent_files_path is not None, f"Agent {name} not found."

        metadata_path = os.path.join(agent_files_path, "metadata.json")
        check_metadata(Path(metadata_path))
        with open(metadata_path) as f:
            metadata: Dict[str, Any] = json.load(f)

        if not identifier:
            identifier = "/".join([namespace, metadata["name"], metadata["version"]])

        return Agent(identifier, agent_files_path, metadata)

    def run_interactive(self, record_run: bool = True, load_env: str = "") -> None:
        """Runs an interactive session within the given env."""
        if load_env:
            base_id = self.load_from_registry(load_env)
        else:
            base_id = None

        env = self._env
        self._print_welcome(env.get_primary_agent())

        last_message_idx = 0
        last_message_idx = self._print_messages(env.list_messages(), last_message_idx)
        run_id = None

        new_message = None
        while True:
            next_actor = env.get_next_actor()
            if next_actor == "user":
                new_message = input("> ")
                if new_message.lower() == "exit":
                    break
                env.set_next_actor("agent")
            else:
                # Run the agent's turn
                run_id = env.run(new_message, 1)

                # print the user's input and the agent's response
                last_message_idx = self._print_messages(env.list_messages(), last_message_idx)
                if env.is_done():
                    break

        if record_run and run_id:
            self.save_env(env, run_id, base_id, "interactive")

        env.clear_temp_agent_files()

    @staticmethod
    def _print_welcome(agent):
        if agent.welcome_description:
            if agent.welcome_title:
                print(f"{agent.welcome_title}: {agent.welcome_description}")
            else:
                print(agent.welcome_description)

    @staticmethod
    def _print_messages(messages, last_message_idx: int) -> int:
        for item in messages[last_message_idx:]:
            print(f"[{item['role']}]: {item['content']}", flush=True)
        return len(messages)

    def run_task(
        self,
        task: str,
        record_run: bool = True,
        load_env: str = "",
        max_iterations: int = 10,
    ) -> None:
        """Runs a task within the given env."""
        base_id = self.load_from_registry(load_env) if load_env else None

        env = self._env
        run_id = env.run(task, max_iterations)

        if record_run:
            self.save_env(env, run_id, base_id, "task")

        env.clear_temp_agent_files()

    def load_from_registry(self, load_env: str) -> str:  # noqa: D102
        print(f"Loading environment from {load_env} to {self._path}")

        directory = registry.download(load_env)
        assert directory is not None, "Failed to download environment"

        files = os.listdir(directory)
        tarfile_file = next(f for f in files if f.endswith(".tar.gz"))

        with tarfile.open(directory / tarfile_file, "r") as tar:
            tar.extractall(self._path)
        return directory.name

    def save_env(self, env, run_id, base_id, run_type) -> Optional[EntryLocation]:
        """Saves the current env to the registry."""
        if self._client_config.auth is None:
            print("Warning: Authentication is not set up. Run not saved to registry. To log in, run `nearai login`")
            return None

        snapshot = env.create_snapshot()
        metadata = env.environment_run_info(run_id, base_id, run_type)
        print("metadata", metadata)
        metadata = EntryMetadata.from_dict(metadata)

        tempdir = Path(tempfile.mkdtemp())
        environment_path = tempdir / "environment.tar.gz"
        with open(environment_path, "w+b") as f:
            f.write(snapshot)
        entry_location = registry.upload(tempdir, metadata, show_progress=True)

        location_str = plain_location(entry_location)

        print(f"Saved environment {entry_location} to registry. To load use flag `--load-env={location_str}`.")

        rmtree(tempdir)
        return entry_location

    def confirm_execution(self, command):
        """If specified by config, prompts the user to confirm the execution of a command."""
        if self._confirm_commands:
            yes_no = input("> Do you want to run the following command? (Y/n): " + command)
            if yes_no != "" and yes_no.lower() == "y":
                return True
        return False
