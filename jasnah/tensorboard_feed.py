import json
import time
from pathlib import Path
from typing import Dict

import tensorboardX

from jasnah.db import db


class TensorboardCli:
    def start(self, logdir: str, limit: int = 100, timeout: int = 1):
        experiments: Dict[str, tensorboardX.SummaryWriter] = {}

        logdir_path = Path(logdir)
        logdir_path.mkdir(parents=True, exist_ok=True)
        next_id_path = logdir_path / ".next_id"

        if not next_id_path.exists():
            next_id_path.write_text("0")

        while True:
            next_id = int(next_id_path.read_text())
            result = db.get_logs("tensorboard", next_id, limit)

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

                print(content)

                if experiment_id not in experiments:
                    experiments[experiment_id] = tensorboardX.SummaryWriter(logdir_path / experiment_id)

                writer = experiments[experiment_id]

                for key, value in content.items():
                    writer.add_scalar(key, value, step, walltime=when)
