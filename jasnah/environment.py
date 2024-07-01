import json
import os
import shutil
import subprocess
import shlex
import tarfile
import tempfile
import threading
from pathlib import Path
import uuid
import datetime
from typing import List, Optional, Dict

import psutil

from jasnah.completion import InferenceRouter

DELIMITER = '\n'
CHAT_FILENAME = 'chat.txt'
TERMINAL_FILENAME = 'terminal.txt'


class Environment(object):

    def __init__(self, path: str, agents: List['Agent'], config, registry=None, user_name=None):
        self._path = path
        self._agents = agents
        self._done = False
        self._config = config
        self._inference = InferenceRouter(config)
        self._registry = registry
        self._user_name = user_name
        os.makedirs(self._path, exist_ok=True)
        os.chdir(self._path)
        open(os.path.join(self._path, CHAT_FILENAME), 'a').close()

    @staticmethod
    def _generate_run_id():
        return uuid.uuid4().hex

    def add_message(self, role: str, message: str, filename: str=CHAT_FILENAME):
        with open(os.path.join(self._path, filename), 'a') as f:
            f.write(json.dumps({'role': role, 'content': message}) + DELIMITER)

    def list_messages(self, filename: str=CHAT_FILENAME):
        path = os.path.join(self._path, filename)

        if not os.path.exists(path):
            return []

        with open(path, 'r') as f:
            return [json.loads(message) for message in f.read().split(DELIMITER) if message]

    def list_files(self, path) -> List[str]:
        return os.listdir(path)

    def get_path(self) -> str:
        return self._path

    def read_file(self, filename: str) -> str:
        if not os.path.exists(os.path.join(self._path, filename)):
            return ''
        try:
            with open(os.path.join(self._path, filename), 'r') as f:
                return f.read()
        except Exception as e:
            return f'failed to read file: {e}'

    def write_file(self, filename: str, content: str):
        path = Path(self._path) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            f.write(content)

    def exec_command(self, command: str) -> Dict[str, str]:
        """Executes a command in the environment and logs the output."""
        if self._config.get('confirm_commands', True):
            yes_no = input('> Do you want to run the following command? (Y/n): ' + command)
            if yes_no != '' and yes_no.lower() != 'y':
                return {'command': command, 'returncode': 999, 'stdout': '', 'stderr': 'declined by user'}

        try:
            process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0, universal_newlines=True)

            msg = ""

            def kill_process_tree(p):
                nonlocal msg
                msg = "Killing process due to timeout"

                process = psutil.Process(p.pid)
                for proc in process.children(recursive=True):
                    proc.kill()
                process.kill()

            timer = threading.Timer(2, kill_process_tree, (process, ))
            timer.start()
            process.wait()
            timer.cancel()

            result = {'command': command, 'stdout': process.stdout.read(), 'stderr': process.stderr.read(), 'returncode': process.returncode, 'msg': msg}
        except Exception as e:
            result = {'command': command, 'returncode': 999, 'stdout': '', 'stderr': f'failed to execute command: {e}'}
        with open(os.path.join(self._path, TERMINAL_FILENAME), 'a') as f:
            f.write(json.dumps(result) + DELIMITER)
        return result

    def completions(self, model, messages, stream=False):
        """Returns all completions for given messages using the given model."""
        return self._inference.completions(model, messages, stream=stream)

    def completion(self, model: str, messages) -> str:
        """Returns a completion for the given messages using the given model."""
        return self.completions(model, messages).choices[0].message.content

    def call_agent(self, agent_path: str, task: str):
        """Calls agent with given task."""
        self._agents[agent_path].run(self, task=task)

    def get_agents(self) -> List['Agent']:
        """Returns list of agents available in environment."""
        return self._agents

    def is_done(self):
        return self._done

    def mark_done(self):
        self._done = True

    def create_snapshot(self):
        """Create an in memory snapshot"""
        with tempfile.NamedTemporaryFile( suffix='.tar.gz') as f:
            with tarfile.open(fileobj=f, mode='w:gz') as tar:
                tar.add(self._path, arcname='.')
            f.flush()
            f.seek(0)
            snapshot = f.read()
        return snapshot

    def save_to_registry(self, run_type: str, run_id: str, base_id: Optional[str|int] = None):
        """Save Environment to Registry."""
        agent_name = self._agents[0].name

        with tempfile.NamedTemporaryFile( suffix='.tar.gz') as f:
            with tarfile.open(fileobj=f, mode='w:gz') as tar:
                tar.add(self._path, arcname='.')
            f.flush()
            f.seek(0)
            snapshot = f.read()
            tar_filename = f.name

            author = self._user_name
            s3_path = f"environments/{run_id}"
            timestamp = datetime.datetime.now(datetime.UTC).isoformat()
            name = f"environment_run_{agent_name}_{run_id}"
            description = f"Agent {run_type} run {agent_name} {run_id} {timestamp}"
            details={
                "base_id": base_id,
                "timestamp": timestamp,
                "agents": [agent.name for agent in self._agents],
                "run_id": run_id,
                "run_type": run_type,
                "filename": tar_filename,
            },
            tags_l = ['environment']
            registry_id = self._registry.upload(
                path=Path(tar_filename),
                s3_path=s3_path,
                author=author,
                description=description,
                name=name,
                details=details,
                show_entry=True,
                tags=tags_l,
            )
            print(f'Saved environment {registry_id} to registry. To load use flag `--load-env={registry_id}`. ')
            return snapshot

    def load_snapshot(self, snapshot: bytes):
        """Load Environment from Snapshot."""
        shutil.rmtree(self._path, ignore_errors=True)

        with tempfile.NamedTemporaryFile(suffix='.tar.gz') as f:
            f.write(snapshot)
            f.flush()
            f.seek(0)

            with tarfile.open(fileobj=f, mode='r:gz') as tar:
                tar.extractall(self._path)

    def load_from_registry(self, load_env):
        print(f"Loading environment from {load_env} {type(load_env)} to {self._path}")
        directory = self._registry.download(load_env)
        files = os.listdir(directory)
        tarfile_file = next(f for f in files if f.endswith(".tar.gz"))

        with tarfile.open(directory / tarfile_file, 'r') as tar:
            tar.extractall(self._path)
        return directory.name

    def __str__(self):
        return f'Environment({self._path})'

    def run_agent(self, task):
        self._agents[0].run(self, task=task)

    def set_next_actor(self, who):
        next_action_fn = os.path.join(self._path, '.next_action')

        with open(next_action_fn, 'w') as f:
            f.write(who)

    def run_interactive(self, record_run: str, load_env: str):
        """Run an interactive session within the given environment."""
        run_id = self._generate_run_id()
        if load_env:
            base_id = self.load_from_registry(load_env)
        else:
            base_id = None
        last_message_idx = 0

        def print_messages(last_message_idx):
            messages = self.list_messages()
            for item in messages[last_message_idx:]:
                print(f"[{item['role']}]: {item['content']}", flush=True)
            return len(messages)

        last_message_idx = print_messages(last_message_idx)

        while True:
            next_action_fn = os.path.join(self._path, '.next_action')
            if os.path.exists(next_action_fn):
                with open(next_action_fn) as f:
                    next_action = f.read().strip(' \n')
            else:
                # By default the user starts the conversation.
                next_action = 'user'

            next_is_user = next_action == 'user'

            if not next_is_user:
                messages = self.list_messages()
                new_message = None if not messages else messages[-1]['content']

                self.run_agent(new_message)

                last_message_idx = print_messages(last_message_idx)
                if self.is_done(): break

            else:
                new_message = input('> ')
                if new_message == 'exit': break
                self.add_message('user', new_message)

                self.set_next_actor('agent')

        if record_run:
            self.save_to_registry('interactive', run_id, base_id)

    def run_task(self, task: str, record_run: str = None, load_env: str = None, max_iterations: int = 10,):
        """Runs a task within the given environment."""
        run_id = self._generate_run_id()
        if load_env:
            base_id = self.load_from_registry(load_env)
        else:
            base_id = None
        iteration = 0

        if task:
            self.add_message('user', task)

        while iteration < max_iterations and not self.is_done():
            iteration += 1
            self._agents[0].run(self, task=task)

        if record_run:
            self.save_to_registry('task', run_id, base_id)
