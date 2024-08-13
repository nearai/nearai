# Near AI

See the [Near AI website](https://near.ai) for more information about how we will achieve _Open Source and User-owned AGI._.

# ⚠️ Warning: Alpha software

NearAI is alpha software. This means that it is not yet ready for production use. We are actively working on improving the software and would love your help.

If you would like to help build our future, please see our [contributing guide](contributing.md).

# About

The NearAI project is a toolkit to help build, measure, and deploy AI systems focused on agents.

NearAI consists of:

1. A CLI tool to interact with the NearAI registry, download agents, run them in environments, and more.
2. A library with access to the same tools as the CLI, but to be used programmatically.
3. `nearai` hub, a place to share agents, environments, and datasets.

This intro is split into two parts:

1. [CLI Usage Guide](#cli-usage-guide)
2. [Library Usage Guide](#library-usage-guide)

# CLI Usage Guide

## Benchmarking

`nearai` includes a benchmarking tool to compare different agents and solvers on sets of reference evals (like [`mpbb`](https://paperswithcode.com/dataset/mbpp)).

???+ note "Requirements for benchmarking with `nearai`"
    To create a benchmark, you need two things:

    1. A dataset in your `nearai` dataset registry.
    2. A solver for the dataset implemented in the `nearai` library for said dataset.

    If you have a dataset and a solver, you can run a benchmark.

To run a benchmark, you can use the `nearai benchmark` command. For example, to run the `mpbb` benchmark on the `llama-v3-70b-instruct`, you can use:

```bash
nearai benchmark run mbpp MBPPSolverStrategy \
    --model llama-v3-70b-instruct \
    --subset=train \
    --max_concurrent=1
```

## Registry

The registry is a place to store models, datasets, agents, and environments (more to come). You can upload and download items from the registry using the `nearai registry` command.

!!! note "About the registry"
    The registry is backed by an S3 bucket with metadata stored in a database.

Upload an element to the registry using:

```shell
nearai registry upload <ITEM_LOCAL_PATH> <ITEM_S3_PATH> <DESCRIPTION> [--name <NAME>] [--tags <TAGS>]
```

- The local path could be either to a file or a folder.
- The S3 path should be a non-existent folder in the registry.
- Tags is a comma separated list of tags to add to the item. This allows filtering relevant items.

There are two shortcuts to upload models and datasets. The following commands behave in the same way as `registry upload` but it adds by default the tags `model` and `dataset` respectively.

```shell
nearai models upload <ITEM_LOCAL_PATH> <ITEM_S3_PATH> <DESCRIPTION> [--name <NAME>] [--tags <TAGS>]
nearai datasets upload <ITEM_LOCAL_PATH> <ITEM_S3_PATH> <DESCRIPTION> [--name <NAME>] [--tags <TAGS>]
```

We recommend as a good practice to use as s3_path `<namespace>/<name>/<version>`, but it is not mandatory.

To upload an item to the registry with name quine.py and tags `quine` and `python` is the command:

```
nearai registry upload ~/quine.py test/quine/v3 "Test registry upload" quine.py --tags quine,python
```

To check the item is available by listing all elements in the registry:

```
nearai registry list
```

Show only items with the tag `quine` and `python`:

```
nearai registry list --tags quine,python
```

Download this element locally. To download you can refer to the item either by name or by s3_path. Trying to download an item that was previously downloaded is a no-op.

```
nearai registry download quine.py
```

!!! tip 
    If you start downloading and item, and cancel the download midway, you should delete the folder at `~/.nearai/registry/` to trigger a new download.

Add one or more tags to an item using:

```
nearai registry add_tags test/quine/v3 code,multiple,tags
```

Removing tags must be done one by one:

```
nearai registry remove_tag test/quine/v3 code
```

## Agents

Agents are a python file in the local registry. Existing agents can be fetched with the download command:

```
nearai agents download <AGENT_NAME>
```

Local agent files that have not yet been uploaded can also be run.

When uploading an agent, multiple versions can be stored by appending a version to the s3 path. The `--name` flag allows the latest agent to be fetched that matches that name.

To upload an agent:

```
nearai agents upload --name langgraph-min-example ~/.nearai/registry/agents/langgraph-min-example/v1 agents/langgraph-min-example/v1 "A minimal example"
```

## Running environment interactively

You can run an agent (or a set of agents) inside a local environment that lives in a specific folder.

Agents can be run interactively. The environment_path should be a folder where the agent chat record (chat.txt) and other files can be written, usually `~/tmp/test-agents/<AGENT_NAME>`.

Environments can be run like so:

```
nearai environment interactive <AGENT> <ENVIRONMENT_PATH>
```

Example calling a local agent:

```
nearai environment interactive agent/my-agent/v1 ~/tmp/test-agents/my-agent-v1/env0
```

Example calling a downloaded agent:

```
nearai environment interactive xela-agent ~/tmp/test-agents/xela-agent-v2/env0
```

## Running environment task
To run without user interaction pass the task input to the task
 * command `nearai environment task <AGENT> <INPUT> <ENVIRONMENT_PATH>`.
 * example `nearai environment task xela-agent "Build a command line chess engine" ~/tmp/test-agents/chess-engine/env0`.

## Saving and loading environment runs
By default each environment run is saved to the registry. You can disable this by adding the flag `--record_run=False`.

An environment run can be loaded by using the `--load_env` flag and passing it a registry identifier `--load_env=61`.

To list environment identifiers use the command `nearai registry list --tags=environment`.

A run can be named by passing a name to the record_run flag `--record_run="my special run"`.

Environment runs can be loaded by passing the name of a previous run to the --load_env flag like `--load_env="my special run"`.

## Fine tuning

We use [`torchtune`](https://github.com/pytorch/torchtune) for fine tuning models. The following command will start a fine tuning process using the `llama-3-8b-instruct` model and the `llama3` tokenizer.

```bash
poetry run python3 -m nearai finetune start \
    --model llama-3-8b-instruct \
    --format llama3-8b \
    --tokenizer tokenizers/llama-3 \
    --dataset <your-dataset> \
    --method nearai.finetune.text_completion.dataset \
    --column text \
    --split train \
    --num_procs 8
```

## Submit an experiment

To submit a new experiment run:

```
nearai submit --command <COMMAND> --name <EXPERIMENT_NAME> [--nodes <NUMBER_OF_NODES>] [--cluster <CLUSTER>]
```

This will submit a new experiment. The command must be executed from a folder that is a git repository (public github repositories, and private github repositories on the same organization as nearai are supported).
The current commit will be used for running the command so make sure it is already available online. The diff with respect to the current commit will be applied remotely (new files are not included in the diff).

On each node the environment variable `ASSIGNED_SUPERVISORS` will be available with a comma separated list of supervisors that are running the experiment. The current supervisor can be accessed via `nearai.CONFIG.supervisor_id`. See [examples/prepare_data.py](examples/prepare_data.py) for an example.

# Library Usage Guide

You can import `nearai` as a library in your python code. The main features are:

- Download/upload models and datasets from the registry. See [examples/prepare_data.py](examples/prepare_data.py).
