from typing import Optional

from nearai.agent import Agent
from nearai.environment import Environment
from nearai.registry import get_registry_folder, registry
import os
import tarfile
import tempfile
from pathlib import Path
from shutil import rmtree

from hub.api.v1.entry_location import EntryLocation
from openapi_client import EntryMetadata
from nearai import plain_location


class LocalRunner:
    def __init__(  # noqa: D107
            self,
            env: Environment,
    ) -> None:
        self._path = env._path
        self._agents = env._agents
        self._env = env
        env.set_approvals({"confirm_execution": self.confirm_execution})


    @staticmethod
    def load_agent(name: str, local: bool = False) -> Agent:
        if local:
            path = get_registry_folder() / name
        else:
            path = registry.download(name)

        assert path is not None, f"Agent {name} not found."
        return Agent(path.as_posix())

    def run_interactive(self, record_run: bool = True, load_env: str = "") -> None:
        """Runs an interactive session within the given env."""
        if load_env:
            base_id = self.load_from_registry(load_env)
        else:
            base_id = None

        env = self._env
        self._print_welcome(env._agents[0])

        last_message_idx = 0
        last_message_idx = self._print_messages(env.list_messages(), last_message_idx)
        run_id = "No run id"

        while True:
            if env.get_next_actor() != "user":
                messages = env.list_messages()
                new_message = None if not messages else messages[-1]["content"]

                # Run the agent's turn
                run_id = env.run(new_message, 1)

                # print the agent's response
                last_message_idx = self._print_messages(env.list_messages(), last_message_idx)
                if env.is_done():
                    break

            else:
                new_message = input("> ")
                if new_message.lower() == "exit":
                    break
                env.add_message("user", new_message)

                env.set_next_actor("agent")

        if record_run:
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
        if env._config.auth is None:
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
        if self._env._config.get("confirm_commands", True):
            yes_no = input("> Do you want to run the following command? (Y/n): " + command)
            if yes_no != "" and yes_no.lower() == "y":
                return True
        return False