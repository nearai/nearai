# Near AI

See the [Near AI website](https://near.ai) for more on how we will achieve _Open Source and User-owned AGI._.


# ⚠️ Warning: Alpha software

NearAI is alpha software. This means that it is not yet ready for production use. We are actively working on improving the software and would love your help.

If you would like to help build our future, please see our [contributing guide](contributing.md).

# About

The NearAI project is a toolkit to help build, measure, and deploy AI systems focused on [agents](agents.md).
<iframe width="240" height="120" src="https://www.youtube.com/embed/q2nhgj9q2PU" frameborder="0" allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
<iframe width="240" height="120" src="https://www.youtube.com/embed/fqPRXxj3AoI" frameborder="0" allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

NearAI consists of:

1. [app.near.ai](https://app.near.ai) a place to share agents, environments, and datasets; powered by the NearAI API.
2. A CLI tool to interact with the NearAI registry, download agents, run them in environments, and more.
3. A library with access to the same tools as the CLI, but to be used programmatically.

This intro is split into two parts:

1. [Web Usage Guide](#web-usage-guide)
2. [CLI Usage Guide](#cli-usage-guide)

# Web Usage Guide

https://app.near.ai allows you to use NEAR AI Hub directly from your browser. It currently offers a subset of the features available from the full Hub API.

Features:

- [NEAR AI Login](login.md)
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

Source code in: [demo](https://github.com/nearai/nearai/tree/main/hub/demo)

For the api specification see [openapi.json](https://api.near.ai/openapi.json)

# CLI Usage Guide

## Registry

The registry is a place to store models, datasets, agents, and environments (more types to come). You can upload and download items from the registry using the `nearai registry` command.

!!! note "About the registry"
    The registry is backed by an S3 bucket with metadata stored in a database.

To upload an item to the registry, you need a directory containing a metadata.json file. The metadata.json file describes
the item, and all the other files in the directory make up the item. For an agent that is one `agent.py` file, for a
dataset it may be hundreds of files.

The metadata_template command will create a template for you to fill in.
```
nearai registry metadata_template <ITEM_LOCAL_DIRECTORY_PATH> <CATEGORY> <DESCRIPTION>
```
Fill in name, version, category and any other fields for which you have values.
The notable categories are: `model`, `dataset`, `agent`.

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

You can list elements in the registry using several filters:

```shell
nearai registry list  --namespace <NAMESPACE> \
                      --category <CATEGORY> \
                      --tags <COMMA_SEPARTED_LIST_OF_TAGS>
                      --show_all
```

Check the item is available by listing all elements in the registry of that category:

```shell
nearai registry list --namespace near.ai --category agent
```

Show only items with the tag `quine` and `python`:

```shell
nearai registry list --tags quine,python
```

Download this element locally. To download refer to the item by <namespace>/<name>/<version>. Trying to download an item that was previously downloaded is a no-op.

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
See the [Agents](agents.md) documentation and How to guide

* [QUICKSTART: build and run a python agent on NearAI](agents.md#quickstart-build-and-run-a-python-agent-on-nearai)
    * [Example agent.py](agents.md#example-agentpy)
* [About Agents](agents.md#about-agents)
* [Agent Operation and Features](agents.md#agent-operation-and-features)
* [Running an existing agent from the registry](agents.md#running-an-existing-agent-from-the-registry)
    * [Running an agent interactively](agents.md#running-an-agent-interactively)
    * [Running an agent as a task](agents.md#running-an-agent-as-a-task)
* [The Environment API](agents.md#the-environment-api)
    * [Additional environment methods](agents.md#additional-environment-methods)
    * [Tool registry](agents.md#tool-registry-and-function-tool-calling)
* [Uploading an agent](agents.md#uploading-an-agent)
* [Running an agent remotely through the CLI](agents.md#running-an-agent-remotely-through-the-cli)
* [Running an agent through the API](agents.md#running-an-agent-through-the-api)
* [Remote results](agents.md#remote-results)
    * [Signed messages](agents.md#signed-messages)


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

On each node the environment variable `ASSIGNED_SUPERVISORS` will be available with a comma separated list of supervisors that are running the experiment. The current supervisor can be accessed via `nearai.CONFIG.supervisor_id`. See [examples/prepare_data.py](https://github.com/nearai/nearai/blob/main/examples/prepare_data.py) for an example.

