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
        
        .../agents/<alias>/<version>/agent.json
        """
        parts = path.split('/')
        with open(os.path.join(path, AGENT_FILENAME)) as f:
            return Agent(parts[-2], parts[-1], f.read())


    def run(self, env: Environment):
        exec(self.code, globals(), {'env': env, 'agent': self})


def load_agent(alias_or_name: str) -> Agent:
    path = agent.download(alias_or_name)
    return Agent.from_disk(path.as_posix())


def run_interactive(env: Environment, agent: Agent):
    """Run an interactive session with the given environment and agent."""
    last_message_idx = 0
    def print_messages(last_message_idx):
        messages = env.list_messages()
        for role, message in messages[last_message_idx:]:
            print(f'[{role}]: {message}')
        return len(messages)
    last_message_idx = print_messages(last_message_idx)
    while True:
        new_message = input('> ')
        if new_message == 'exit': break
        env.add_message('user', new_message)
        agent.run(env)
        last_message_idx = print_messages(last_message_idx + 1)
        if env.is_done(): break
