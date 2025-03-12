import json
import time
from typing import Any

from pydantic import BaseModel

from nearai.config import CONFIG, DATA_FOLDER
from nearai.openapi_client.api.logs_api import LogsApi


class LogMetadata(BaseModel):
    last_id: int


class LogStore:
    def __init__(self, account_id: str, target: str):
        """Interface for log local storage."""
        self.folder = DATA_FOLDER / "logs" / account_id
        self.folder.mkdir(parents=True, exist_ok=True)
        self.file = self.folder / f"{target}.jsonl"
        self.meta = self.folder / f"{target}-meta.json"

        if not self.meta.exists():
            with open(self.meta, "w") as f:
                f.write(LogMetadata(last_id=0).model_dump_json())

        if not self.file.exists():
            self.file.touch()

    def last_id(self) -> int:
        """Get the id of the latest downloaded logs."""
        with open(self.meta) as f:
            metadata = LogMetadata.model_validate_json(f.read())
        return metadata.last_id

    def update_last_id(self, id: int):
        """Update the id of the latest downloaded logs."""
        with open(self.meta, "w") as f:
            f.write(LogMetadata(last_id=id).model_dump_json())

    def add(self, info: Any):
        """Add a log to the local store."""
        with open(self.file, "a") as f:
            info_json = json.dumps(info)
            f.write(info_json + "\n")


class LogCLI:
    def __init__(self):
        """Log CLI."""
        self.api = LogsApi()

    def push(self, target: str, **kwargs):
        """Push a log to the hub."""
        self.api.add_log_v1_logs_add_log_post(target=target, body=kwargs)

    def track(self, target: str, follow: bool = False, max_wait_time: int = 60):
        """Start tracking logs."""
        if CONFIG.auth is None:
            print("You need to login first.")
            return
        account_id = CONFIG.auth.account_id
        store = LogStore(account_id=account_id, target=target)
        limit = 32

        wait_time = 1

        while True:
            last_id = store.last_id()
            logs = self.api.get_logs_v1_logs_get_logs_get(target=target, after_id=last_id, limit=limit)

            for log in logs:
                last_id = max(last_id, log.id)

                if log.info is not None:
                    store.add(log.info)
                    print("Log: ", log.id)
                    print(log.info)

            if len(logs) == 0:
                print("No new logs found.")

            if last_id > store.last_id():
                store.update_last_id(last_id)

            if not follow:
                break

            if len(logs) == 0:
                wait_time = min(wait_time * 2, max_wait_time)
            else:
                wait_time = 1

            print(f"Waiting for {wait_time} seconds...")
            time.sleep(wait_time)
