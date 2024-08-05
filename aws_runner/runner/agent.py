from typing import Any, Optional

AGENT_FILENAME = "agent.py"


class Agent(object):
    def __init__(self, name: str, path: str, code: str):  # noqa: D107
        self.name = name
        self.path = path
        self.code = code

    def run(self, env: Any, task: Optional[str] = None) -> None:  # noqa: D102
        d = {"env": env, "agent": self, "task": task}
        exec(self.code, d, d)
