import json
import os
import tempfile
from pathlib import Path

import nearai
import nearai.registry


def main():
    timestamp = nearai.timestamp()
    assigned_supervisors = os.environ.get("ASSIGNED_SUPERVISORS", None)
    me = nearai.CONFIG.supervisor_id

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)

        with open(path / "info.json", "w") as f:
            json.dump({"me": me, "assigned_supervisors": assigned_supervisors}, f)

        with open(path / "data.txt", "w") as f:
            print("Hello, world!", file=f)

        nearai.registry.dataset.upload(
            path=path,
            s3_path=f"test/auto_simple_task/{timestamp}",
            author="simple_task.py",
            description="Example dataset generated automatically.",
            name=None,
            details={"timestamp": timestamp},
            show_entry=False,
            tags=["test"],
        )


if __name__ == "__main__":
    main()
