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
2. [Web Usage Guide](#web-usage-guide)
3. [Library Usage Guide](#library-usage-guide)

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

The registry is a place to store models, datasets, agents, and environments (more types to come). You can upload and download items from the registry using the `nearai registry` command.

!!! note "About the registry"
    The registry is backed by an S3 bucket with metadata stored in a database.

To upload an item to the registry, you need a directory containing a metadata.json file. The metadata.json file describes
the item, and all the other files in the directory make up the item. For an agent that is one `agent.py` file, for a 
dataset it may be hundreds of files.

The metadata_template command will create a template for you to fill in.
```
nearai registry metadata_template <ITEM_LOCAL_DIRECTORY_PATH>
```
Fill in name, version, category and any other fields for which you have values. 
The current categories are: `model`, `dataset`, `agent`, `environment`.

```json
{
  "category": "agent",
  "description": "An example agent",
  "tags": [
    "python"
  ],
  "details": {},
  "show_entry": true,
  "name": "example-agent",
  "version": "1"
}
```

Upload an element to the registry using:

```shell
nearai registry upload <ITEM_LOCAL_DIRECTORY_PATH>
```

Check the item is available by listing all elements in the registry of that category:

```
nearai registry list --category agent
```

Show only items with the tag `quine` and `python`:

```
nearai registry list --tags quine,python
```

Download this element locally. To download refer to the item by <author>/<name>/<version>. Trying to download an item that was previously downloaded is a no-op.

```
nearai registry download zavodil.near/hello-world-agent/1
```

!!! tip 
    If you start downloading and item, and cancel the download midway, you should delete the folder at `~/.nearai/registry/` to trigger a new download.

Update the metadata of an item with the registry update command
```
nearai registry update <ITEM_LOCAL_DIRECTORY_PATH>
```
View info about an item with the registry info command
```shell
nearai registry info <ITEM_FULL_NAME>
```
```shell
nearai registry info zavodil.near/hello-world-agent/1
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

# Web Usage Guide

https://app.near.ai allows you to use NEAR AI Hub directly from your broweser. It currently offers a subset of the features available from the Hub.

Features:

- NEAR AI Login
  - Login with your NEAR account using your favourite wallet provider.
- Inference using the provider of your choice
  - Chose between the best open source models.
- Read the [registry](#registry):
  - Datasets - https://app.near.ai/datasets
  - Benchmarks - https://app.near.ai/benchmarks
  - Models - https://app.near.ai/models
  - Agents - https://app.near.ai/agents
- View and manage your NEAR AI access keys.

  - https://app.near.ai/settings

Source code in: [demo](/hub/demo/)

# Library Usage Guide

You can import `nearai` as a library in your python code. The main features are:

- Download/upload models and datasets from the registry. See [examples/prepare_data.py](examples/prepare_data.py).
