import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import threading
from pathlib import Path
import uuid
import datetime
from typing import List, Optional, Dict

from litellm import completion as litellm_completion

DELIMITER = '\n'
CHAT_FILENAME = 'chat.txt'
TERMINAL_FILENAME = 'terminal.txt'


class InferenceRouter(object):

    def __init__(self, config):
        self._config = config
        self._endpoints = {}

    def completions(self, model, messages, stream=False):
        """Takes a model `provider:model_name` and a list of messages and returns all completions."""
        assert 'models' in self._config and model in self._config['models'], f'Model {model} not found in config.'
        provider_name, model_path = self._config['models'][model].split(':')
        if provider_name not in self._endpoints:
            assert 'providers' in self._config and provider_name in self._config['providers'], f'Provider {provider_name} not found in config.'
            provider_config = self._config['providers'][provider_name]
            self._endpoints[provider_name] = lambda model, messages, stream: litellm_completion(
                model, messages, stream=stream,
                # TODO: move this to config
                custom_llm_provider='antropic' if 'antropic' in provider_config['base_url'] else 'openai',
                input_cost_per_token=0,
                output_cost_per_token=0,
                base_url=provider_config['base_url'],
                api_key=provider_config['api_key'] if provider_config['api_key'] else 'not-needed')
        return self._endpoints[provider_name](model=model_path, messages=messages, stream=stream)


class Environment(object):

    def __init__(self, path: str, agents: List['Agent'], config, registry, user_name):
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

    def read_file(self, filename: str) -> str:
        if not os.path.exists(os.path.join(self._path, filename)):
            return ''
        with open(os.path.join(self._path, filename), 'r') as f:
            return f.read()

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

        process = subprocess.Popen(command.split(' '), stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0, universal_newlines=True)

        def on_timeout(process):
            """Kill process on timeout and note as status_dict['timeout']=True"""
            process.kill()

        timer = threading.Timer(2, on_timeout, (process, ))
        process.wait()
        timer.cancel()

        result = {'command': command, 'stdout': process.stdout.read(), 'stderr': process.stderr.read(), 'returncode': process.returncode}
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

    def _save(self, run_type: str, run_id: str, base_id: Optional[int]):
        """Save Environment to Registry."""
        agent_name = self._agents[0]
        print(f'Saving environment to registry {type} {agent_name} {run_id}')

        with tempfile.NamedTemporaryFile( suffix='.tar.gz') as f:
            with tarfile.open(fileobj=f, mode='w:gz') as tar:
                tar.add(self._path, arcname='.')
            f.flush()
            f.seek(0)
            snapshot = f.read()
            tar_filename = f.name

            author = self._user_name
            s3_path = f"environments/{run_id}.tar.gz"
            timestamp = datetime.datetime.now(datetime.UTC).isoformat()
            name = f"environment_run_{agent_name}_{run_id}_{run_type}"
            description = f"Agent {run_type} run {agent_name} {run_id} {timestamp}"
            details={
                "base_id": base_id,
                "timestamp": timestamp,
                "agents": self._agents,
                "run_id": run_id,
                "run_type": run_type
            },
            tags_l = ['environment']
            self._registry.upload(
                path=Path(tar_filename),
                s3_path=s3_path,
                author=author,
                description=description,
                name=name,
                details=details,
                show_entry=True,
                tags=tags_l,
            )
        return snapshot

    def _load(self, snapshot: bytes):
        """Load Environment from Registry."""
        shutil.rmtree(self._path, ignore_errors=True)

        with tempfile.NamedTemporaryFile(suffix='.tar.gz') as f:
            f.write(snapshot)
            f.flush()
            f.seek(0)

            with tarfile.open(fileobj=f, mode='r:gz') as tar:
                tar.extractall(self._path)

    def __str__(self):
        return f'Environment({self._path})'

    def run_interactive(self):
        """Run an interactive session within the given environment."""
        run_id = self._generate_run_id()
        last_message_idx = 0
        def print_messages(last_message_idx):
            messages = self.list_messages()
            for item in messages[last_message_idx:]:
                print(f"[{item['role']}]: {item['content']}", flush=True)
            return len(messages)

        next_action_fn = os.path.join(self._path, '.next_action')
        if os.path.exists(next_action_fn):
            with open(next_action_fn) as f:
                next_action = f.read().strip(' \n')
        else:
            # By default the agent starts the conversation. To introduce itself.
            next_action = 'agent'

        start_on_user = next_action == 'user'

        last_message_idx = print_messages(last_message_idx)
        messages = self.list_messages()
        new_message = None if not messages else messages[-1]['content']

        # Alternates between user and agent. In case we break the loop early
        # we store in workspace/.next_action which one should start next between user and agent.
        while True:
            if not start_on_user:
                start_on_user = False
                with open(next_action_fn, 'w') as f:
                    f.write('agent')

                # Agent introuce itself
                self._agents[0].run(self, task=new_message)
                last_message_idx = print_messages(last_message_idx)
                if self.is_done(): break

            with open(next_action_fn, 'w') as f:
                f.write('user')

            new_message = input('> ')
            if new_message == 'exit': break
            self.add_message('user', new_message)
        self._save('interactive', run_id)

    def run_task(self, task: str, max_iterations: int = 10):
        """Runs a task within the given environment."""
        run_id = self._generate_run_id()
        iteration = 0
        self.add_message('user', task)
        while iteration < max_iterations and not self.is_done():
            iteration += 1
            self._agents[0].run(self, task=task)
        self._save('task', run_id)
