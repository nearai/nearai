import logging

from aws_runner.service import run_with_environment
from shared.auth_data import AuthData

DEFAULT_OUTPUT_PATH = "/tmp/nearai/conversations/"

logger = logging.getLogger(__name__)


class LocalRunner:
    def __init__(  # noqa: D107
        self,
        path,
        agents,
        thread_id,
        run_id,
        auth: AuthData,
        params: dict,
    ) -> None:
        print(
            f"Initializing LocalRunner with path: {path}, agents: {agents}, thread_id: {thread_id},"
            f"run_id: {run_id}, auth: {auth}, params: {params}"
        )

        self._agents = agents
        self._confirm_commands = True
        run_with_environment(agents, auth, thread_id, run_id, additional_path=path, params=params)
