"""
Convert raw school math dataset, into Dataset format.
"""

import json
import tarfile

from datasets import Dataset

from nearai.dataset import get_dataset
from nearai.registry import dataset

COLUMNS = [
    "nc_work_spec",
    "is_leaf",
    "is_chapter",
    "problem",
    "solution",
    "answer",
    "chapter",
    "children",
    "answer_kind",
    "task_invalid_reason",
    "nc_worker_comment",
    "et_problem",
    "source_file",
]


def main():
    # Download the raw dataset. This will download the file ac.tar.gz
    dataset_path = get_dataset("school_math_ru_tar_gz")

    uncompressed = dataset_path / "uncompressed"
    processed_dataset = dataset_path / "final_dataset"

    if not uncompressed.exists():
        with tarfile.open(dataset_path / "ac.tar.gz") as f:
            f.extractall(uncompressed)

    if not processed_dataset.exists():

        ds = {col: [] for col in COLUMNS}
        sources = []

        for file in uncompressed.glob("*.txt"):
            sources.append(file.name)

            with open(file) as f:
                for line in f:
                    line = line.strip(" \n").replace("\\\\", "\\")

                    doc = json.loads(line)
                    doc["source_file"] = file.name

                    for k, v in ds.items():
                        v.append(doc.get(k, None))

        ds = Dataset.from_dict(ds)
        ds.save_to_disk(str(processed_dataset))

    dataset.upload(
        path=processed_dataset,
        s3_path="school_math_ru/transformed/v0",
        author="prepare_data.py",
        description="School math exercises in Russian. Transformed into a Dataset format.",
        name="school_math_ru",
        details=None,
        show_entry=True,
        tags=[],
    )


if __name__ == "__main__":
    main()
