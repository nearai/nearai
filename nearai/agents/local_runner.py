from nearai.aws_runner.service import run_with_environment
from nearai.shared.auth_data import AuthData


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
        run_with_environment(agents, auth, thread_id, run_id, additional_path=path, params=params)
