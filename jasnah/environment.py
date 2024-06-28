import json
import os
import subprocess
import sys

from typing import List, Optional

import openai

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
            self._endpoints[provider_name] = openai.OpenAI(base_url=provider_config['base_url'], api_key=provider_config['api_key'] if provider_config['api_key'] else 'not-needed')
        return self._endpoints[provider_name].chat.completions.create(model=model_path, messages=messages, stream=stream)


class Environment(object):

    def __init__(self, path: str, agents: List['Agent'], config):
        self._path = path
        self._agents = agents
        self._done = False
        self._config = config
        self._inference = InferenceRouter(config)
        os.makedirs(self._path, exist_ok=True)
        os.chdir(self._path)
        open(os.path.join(self._path, CHAT_FILENAME), 'a').close()

    def add_message(self, role: str, message: str):
        with open(os.path.join(self._path, CHAT_FILENAME), 'a') as f:
            f.write(json.dumps({'role': role, 'content': message}) + DELIMITER)

    def list_messages(self):
        with open(os.path.join(self._path, CHAT_FILENAME), 'r') as f:
            return [json.loads(message) for message in f.read().split(DELIMITER) if message]

    def list_files(self, path) -> List[str]:
        os.path.listdir(os.path.join(self._path, path))

    def read_file(self, filename: str) -> str:
        if not os.path.exists(os.path.join(self._path, filename)):
            return ''
        with open(os.path.join(self._path, filename), 'r') as f:
            return f.read()
        
    def write_file(self, filename: str, content: str):
        with open(os.path.join(self._path, filename), 'w') as f:
            f.write(content)

    def exec_command(self, command: str) -> str:
        """Executes a command in the environment and logs the output."""
        if self._config.get('confirm_commands', True):
            yes_no = input('> Do you want to run the following command? (Y/n): ' + command)
            if yes_no != '' and yes_no.lower() != 'y':
                return {'command': command, 'returncode': 999, 'stdout': '', 'stderr': 'declined by user'}

        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        stdout = ''
        for c in iter(lambda: process.stdout.read(1), b""):
            sys.stdout.buffer.write(c)
            stdout += c.decode("utf-8")
        # stdout = ''
        # stderr = ''    
        # with subprocess.Popen(command, stdout=subprocess.PIPE, universal_newlines=True) as process:
        #     for line in process.stdout:
        #         print(line)
        # output = subprocess.run(command, shell=True, stdout = subprocess.PIPE, stderr = subprocess.PIPE, text=True)
        result = {'command': command, 'stdout': stdout, 'stderr': process.stderr, 'returncode': process.returncode}
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

    def save(self, registry):
        """Save Environment to Registry."""
        # TODO
        pass

    def load(self, registry):
        """Load Environment from Registry."""
        # TODO
        pass

    def __str__(self):
        return f'Environment({self._path})'

    def run_interactive(self):
        """Run an interactive session within the given environment."""
        last_message_idx = 0
        def print_messages(last_message_idx):
            messages = self.list_messages()
            for item in messages[last_message_idx:]:
                print(f"[{item['role']}]: {item['content']}")
            return len(messages)
        last_message_idx = print_messages(last_message_idx)
        while True:
            new_message = input('> ')
            if new_message == 'exit': break
            self.add_message('user', new_message)
            self._agents[0].run(self, task=new_message)
            last_message_idx = print_messages(last_message_idx + 1)
            if self.is_done(): break

    def run_task(self, task: str, max_iterations: int = 10):
        """Runs a task within the given environment."""
        iteration = 0
        self.add_message('user', task)
        while iteration < max_iterations and not self.is_done():
            iteration += 1
            self._agents[0].run(self, task=task)
