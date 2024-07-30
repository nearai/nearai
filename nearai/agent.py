import os
from typing import Any, Optional

from nearai.registry import agent

AGENT_FILENAME = "agent.py"


class Agent(object):
    def __init__(self, name: str, path: str, code: str):  # noqa: D107
        self.name = name
        self.path = path
        self.code = code

    @staticmethod
    def from_disk(path: str) -> "Agent":
        """Path must contain alias and version.

        .../agents/<alias>/<version>/agent.py
        """
        parts = path.split("/")
        with open(os.path.join(path, AGENT_FILENAME)) as f:
            return Agent(parts[-2], parts[-1], f.read())

    def run(self, env: Any, task: Optional[str] = None) -> None:  # noqa: D102
        d = {"env": env, "agent": self, "task": task}
        exec(self.code, d, d)


def load_agent(alias_or_name: str) -> Agent:
    # TODO: Figure out how to integrate StreamerAgent as a Agent
    # if alias_or_name == "streamer":
    #     return StreamerAgent()
    path = agent.download(alias_or_name)
    return Agent.from_disk(path.as_posix())
