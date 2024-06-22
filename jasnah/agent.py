import os
import json

from jasnah.environment import Environment
from jasnah.registry import agent

AGENT_FILENAME = 'agent.py'


class Agent(object):

    def __init__(self, name: str, version: str, code: str):
        self.name = name
        self.version = version
        self.code = code

    def from_disk(path: str) -> 'Agent':
        """Path must contain alias and version.
        
        .../agents/<alias>/<version>/agent.py
        """
        parts = path.split('/')
        with open(os.path.join(path, AGENT_FILENAME)) as f:
            return Agent(parts[-2], parts[-1], f.read())

    def run(self, env: Environment):
        exec(self.code, globals(), {'env': env, 'agent': self})

    def run_interactive(self, env: Environment):
        """Run an interactive session with the given environment and agent."""
        last_message_idx = 0
        def print_messages(last_message_idx):
            messages = env.list_messages()
            for item in messages[last_message_idx:]:
                print(f'[{item['role']}]: {item['content']}')
            return len(messages)
        last_message_idx = print_messages(last_message_idx)
        while True:
            new_message = input('> ')
            if new_message == 'exit': break
            env.add_message('user', new_message)
            self.run(env)
            last_message_idx = print_messages(last_message_idx + 1)
            if env.is_done(): break

    def run_task(self, env: Environment, task: str, max_iterations: int = 10):
        """Runs a task with the given environment and agent."""
        iteration = 0
        env.add_message('user', task)
        while iteration < max_iterations and not env.is_done():
            iteration += 1
            self.run(env)



def load_agent(alias_or_name: str) -> Agent:
    path = agent.download(alias_or_name)
    return Agent.from_disk(path.as_posix())
