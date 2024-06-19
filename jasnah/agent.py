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
        pass


def load_agent(alias_or_name: str) -> Agent:
    path = agent.download(alias_or_name)
    return Agent.from_disk(path.as_posix())


def run_interactive(env: Environment, agent: Agent):
    """Run an interactive session with the given environment and agent."""
    while True:
        new_message = input('> ')
        if new_message == 'exit': break
        index = env.user_message(new_message)
        agent.run(env)
        for agent, message in env.list_messages(index + 1):
            print(f'[{agent}]: {message}')
        if env.is_done(): break
