import os

from typing import Optional

from environment import Environment

AGENT_FILENAME = "agent.py"


class Agent(object):

    def __init__(self, name: str, path: str, code: str):
        self.name = name
        self.path = path
        self.code = code

    def from_disk(path: str) -> "Agent":
        """Path must contain alias and version.

        .../agents/<alias>/<version>/agent.py
        """
        parts = path.split("/")
        with open(os.path.join(path, AGENT_FILENAME)) as f:
            return Agent(parts[-2], parts[-1], f.read())

    def run(self, env: Environment, task: Optional[str] = None):
        d = {"env": env, "agent": self, "task": task}
        exec(self.code, d, d)
