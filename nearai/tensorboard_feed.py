import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List


@dataclass
class Log:
    id: int
    origin: str
    time: datetime
    target: str
    content: str


def get_logs(*args, **kwargs) -> List[Log]:
    # TODO: Logs should be pushed/fetched from the API.
    raise NotImplementedError()


class TensorboardCli:
    def start(self, logdir: str, limit: int = 100, timeout: int = 1) -> None:  # noqa: D102
        import tensorboardX

        experiments: Dict[str, tensorboardX.SummaryWriter] = {}

        logdir_path = Path(logdir)
        logdir_path.mkdir(parents=True, exist_ok=True)
        next_id_path = logdir_path / ".next_id"

        if not next_id_path.exists():
            next_id_path.write_text("0")

        while True:
            next_id = int(next_id_path.read_text())
            result = get_logs("tensorboard", next_id, limit)

            if not result:
                time.sleep(timeout)
                continue

            for row in result:
                when = row.time.timestamp()
                content = json.loads(row.content)

                experiment_id = content.pop("experiment_id", None)
                step = content.pop("step", None)

                if experiment_id is None or step is None:
                    continue

                if experiment_id not in experiments:
                    experiments[experiment_id] = tensorboardX.SummaryWriter(logdir_path / experiment_id)

                writer = experiments[experiment_id]

                for key, value in content.items():
                    writer.add_scalar(key, value, step, walltime=when)

                next_id = max(next_id, row.id + 1)

            new_num_logs = len(result)
            print(f"Downloaded {new_num_logs} new logs")
            next_id_path.write_text(str(next_id))
