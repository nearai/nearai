import os
import threading
import time
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from random import randint
from subprocess import run
from typing import Any, Optional, Tuple

import nearai
from nearai import timestamp
from nearai.config import DATA_FOLDER, ETC_FOLDER
from nearai.model import get_model
from nearai.openapi_client import EntryMetadata
from nearai.registry import registry


class FinetuneCli:
    def start(
        self,
        model: str,
        tokenizer: str,
        dataset: str,
        num_procs: int,
        format: str,
        upload_checkpoint: bool = True,
        num_nodes: int = 1,
        job_id: Optional[str] = None,
        checkpoint: Optional[str] = None,
        **dataset_kwargs: Any,
    ) -> None:
        """Start a finetuning job on the current node.

        Args:
        ----
            model: Name of a model in the registry. Base model to finetune.
            tokenizer: Name of a tokenizer in the registry. Using tokenizer.model format.
            dataset: Name of a dataset in the registry.
            num_procs: Number of GPUs to use for training
            format: Name of the configuration file to use. For example llama3-70b, llama3-8b. Valid options are in etc/finetune.
            upload_checkpoint: Whether to upload the checkpoint to the registry. Default is True.
            num_nodes: Number of nodes to use for training. Default is 1.
            job_id: Unique identifier for the job. Default is None.
            checkpoint: Name of the model checkpoint to start from. Default is None.
            dataset_kwargs: Additional keyword arguments to pass to the dataset constructor.

        """  # noqa: E501
        from nearai.dataset import get_dataset

        assert num_nodes >= 1

        # Prepare job id folder
        if job_id is None:
            job_id = "job"
        job_id = f"{job_id}-{timestamp()}-{randint(10**8, 10**9 - 1)}"
        job_folder = DATA_FOLDER / "finetune" / job_id
        job_folder.mkdir(parents=True, exist_ok=True)

        # Either use the provided config file template or load one predefined one
        if Path(format).exists():
            config_template_path = Path(format)
        else:
            configs = ETC_FOLDER / "finetune"
            config_template_path = configs / f"{format}.yml"

        if not config_template_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_template_path}")

        CONFIG_TEMPLATE = config_template_path.read_text()  # noqa: N806

        # Download model
        model_path = get_model(model)

        # Download tokenizer
        tokenizer_path = registry.download(tokenizer) / "tokenizer.model"
        assert tokenizer_path.exists(), f"tokenizer.model not found in {tokenizer_path}"

        # Download checkpoint if any
        checkpoint_path = get_model(checkpoint) if checkpoint else "null"
        resume_checkpoint = checkpoint_path != "null"

        # Download dataset
        dataset_path = get_dataset(dataset)

        # Set up output directories
        checkpoint_output_dir = job_folder / "checkpoint_output"
        logging_output_dir = job_folder / "logs"
        logging_output_dir.mkdir(parents=True, exist_ok=True)

        # Prepare config file
        dataset_args_dict = deepcopy(dataset_kwargs)

        dataset_args_dict["_component_"] = dataset_args_dict.pop("method")
        dataset_args_dict["source"] = str(dataset_path.absolute())
        dataset_args = "\n".join(f"  {key}: {value}" for key, value in dataset_args_dict.items())

        config = job_folder / "config.yaml"
        with open(config, "w") as f:
            f.write(
                CONFIG_TEMPLATE.format(
                    TOKENIZER=str(tokenizer_path),
                    MODEL=str(model_path),
                    RECIPE_CHECKPOINT=checkpoint_path,
                    RESUME_FROM_CHECKPOINT=resume_checkpoint,
                    CHECKPOINT_OUTPUT_DIR=str(checkpoint_output_dir),
                    DATASET_ARGS=dataset_args,
                    LOGGING_OUTPUT_DIR=str(logging_output_dir),
                )
            )

        # Spawn background thread to read logs and push to database
        threading.Thread(target=find_new_logs_background, args=(logging_output_dir, job_id)).start()

        print("Starting job at", job_folder)
        if num_nodes == 1:
            run(
                [
                    "tune",
                    "run",
                    "--nproc_per_node",
                    str(num_procs),
                    "lora_finetune_distributed",
                    "--config",
                    str(config),
                ]
            )
        else:
            # Fetch rank and master addr from environment variables
            raise NotImplementedError()

        global BACKGROUND_PROCESS
        BACKGROUND_PROCESS = False

        if upload_checkpoint:
            registry.upload(
                job_folder,
                EntryMetadata.from_dict(
                    {
                        "name": f"finetune-{job_id}",
                        "version": "0.0.1",
                        "description": f"Finetuned checkpoint from base mode {model} using dataset {dataset}",
                        "category": "finetune",
                        "tags": ["finetune", f"base-model-{model}", f"base-dataset-{dataset}"],
                        "details": dict(
                            model=model,
                            tokenizer=tokenizer,
                            dataset=dataset,
                            num_procs=num_procs,
                            format=format,
                            num_nodes=num_nodes,
                            checkpoint=checkpoint,
                            **dataset_kwargs,
                        ),
                        "show_entry": True,
                    }
                ),
                show_progress=True,
            )

    def inspect(self, job_id: str) -> None:  # noqa: D102
        raise NotImplementedError()


read_logs: defaultdict[str, int] = defaultdict(int)
BACKGROUND_PROCESS = True


def parse_line(line: str) -> Tuple[int, dict[str, float]]:
    """Example of line to be parsed.

    Step 33 | loss:1.5400923490524292 lr:9.9e-05 tokens_per_second_per_gpu:101.22285588141214
    """
    step_raw, metrics_raw = map(str.strip, line.strip(" \n").split("|"))
    step = int(step_raw.split(" ")[-1])
    metrics = {metric[0]: float(metric[1]) for metric in map(lambda metric: metric.split(":"), metrics_raw.split(" "))}
    return step, metrics


def find_new_logs(path: Path, experiment_id: str) -> None:
    for file in os.listdir(path):
        file_path = os.path.join(path, file)

        if not os.path.isfile(file_path):
            continue

        if not file.endswith(".txt"):
            continue

        read_lines = read_logs[file]
        num_lines = 0

        with open(file_path) as f:
            for line in f:
                num_lines += 1
                if num_lines <= read_lines:
                    continue

                try:
                    line = line.strip(" \n")
                    step, metrics = parse_line(line)
                    nearai.log(target="tensorboard", step=step, experiment_id=experiment_id, **metrics)
                except Exception:
                    continue

        read_logs[file] = num_lines


def find_new_logs_background(path: Path, experiment_id: str) -> None:
    while BACKGROUND_PROCESS:
        find_new_logs(path, experiment_id)
        time.sleep(1)
    find_new_logs(path, experiment_id)
