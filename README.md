# NearAI

## Setup

First install nearai by running:

```
git clone git@github.com:nearai/nearai.git
cd nearai
python3 -m pip install -e .
```

To install to a virtual environment, use the following command:

```bash
python3 -m poetry install --no-root --with dev
```

Check the installation worked with

```
nearai version
```

Setup basic configuration

```
nearai config set db_user <DB_USERNAME>
nearai config set db_password <DB_PASSWORD>
nearai config set user_name <YOUR_NAME>
```

The user name will be used to identify the author of the experiments.
This configuration can be manually edited at `~/.nearai/config.json`, or per project at `.nearai/config.json` (relative to the current directory).

To use the registry (for downloading and uploading models and datasets) you need to setup access to S3. Do it by installing [aws-cli](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html) and configuring it:

```
export AWS_ACCESS_KEY_ID=<..>
export AWS_SECRET_ACCESS_KEY="<..>"
```

## Update

To update nearai run:

```
# Go to the nearai folder
cd nearai

git pull

# The next step is only required in case some dependencies were added or updated, otherwise pulling new changes is enough
python3 -m pip install -e .
```

## Usage

### Submit an experiment

To submit a new experiment run:

```
nearai submit --command <COMMAND> --name <EXPERIMENT_NAME> [--nodes <NUMBER_OF_NODES>] [--cluster <CLUSTER>]
```

This will submit a new experiment. The command must be executed from a folder that is a git repository (public github repositories, and private github repositories on the same organization as nearai are supported).
The current commit will be used for running the command so make sure it is already available online. The diff with respect to the current commit will be applied remotely (new files are not included in the diff).

On each node the environment variable `ASSIGNED_SUPERVISORS` will be available with a comma separated list of supervisors that are running the experiment. The current supervisor can be accessed via `nearai.CONFIG.supervisor_id`. See [examples/prepare_data.py](examples/prepare_data.py) for an example.

### Registry

Upload an element to the registry using:

```
nearai registry upload <ITEM_LOCAL_PATH> <ITEM_S3_PATH> <DESCRIPTION> [--name <NAME>] [--tags <TAGS>]
```

- The local path could be either to a file or a folder.
- The S3 path should be a non-existent folder in the registry.
- Tags is a comma separated list of tags to add to the item. This allows filtering relevant items.

There are two shortcuts to upload models and datasets. The following commands behave in the same way as `registry upload` but it adds by default the tags `model` and `dataset` respectively.

```
nearai models upload <ITEM_LOCAL_PATH> <ITEM_S3_PATH> <DESCRIPTION> [--name <NAME>] [--tags <TAGS>]
nearai datasets upload <ITEM_LOCAL_PATH> <ITEM_S3_PATH> <DESCRIPTION> [--name <NAME>] [--tags <TAGS>]
```

We recommend as a good practice to use as s3_path `@namespace/@name/@version`, but it is not mandatory.

**Examples:**

Upload an item to the registry with name quine.py and tags `quine` and `python`

```
nearai registry upload ~/quine.py test/quine/v3 "Test registry upload" quine.py --tags quine,python
```

Check the item is available by listing all elements in the registry:

```
nearai registry list
```

Show only items with the tag `quine` and `python`:

```
nearai registry list --tags quine,python
```

Download this element locally. To download you can refer to the item either by name or by s3_path. Trying to download an item that was previously downloaded is a no-op.

Note: If you start downloading and item, and cancel the download midway, you should delete the folder at `~/.nearai/registry/` to trigger a new download.

```
nearai registry download quine.py
```

Add one or more tags to an item using:

```
nearai registry add_tags test/quine/v3 code,multiple,tags
```

Removing tags must be done one by one:

```
nearai registry remove_tag test/quine/v3 code
```

### Agents
Agents are a python file in the local registry. Existing agents can be fetched with the download command `nearai agents download <AGENT_NAME>`.
Local agent files that have not yet been uploaded can also be run.
When uploading an agent, multiple versions can be stored by appending a version to the s3 path. The `--name` flag allows the latest agent to be fetched that matches that name.

Examples
 * Downloading an agent `nearai agents download xela-agent`
 * Uploading an agent `nearai agents upload --name langgraph-min-example ~/.nearai/registry/agents/langgraph-min-example/v1 agents/langgraph-min-example/v1 "A minimal example";`

#### Running environment interactively

You can run an agent (or a set of agents) inside a local environment that lives in a specific folder.

Agents can be run interactively. The environment_path should be a folder where the agent chat record (chat.txt) and other files can be written, usually `~/tmp/test-agents/<AGENT_NAME>`.
 * command `nearai environment interactive <AGENT> <ENVIRONMENT_PATH>`.
 * Example for a local agent `nearai environment interactive agent/my-agent/v1 ~/tmp/test-agents/my-agent-v1`.
 * Example for a downloaded agent `nearai environment interactive xela-agent ~/tmp/test-agents/xela-agent-v2`.

#### Running environment task
To run without user interaction pass the task input to the task
 * command `nearai environment task <AGENT> <INPUT> <ENVIRONMENT_PATH>`.
 * example `nearai environment task xela-agent "Build a command line chess engine" ~/tmp/test-agents/chess-engine`.

#### Saving and loading environment runs
By default each environment run is saved to the registry. You can disable this by adding the flag `--record_run=False`.

An environment run can be loaded by using the `--load_env` flag and passing it a registry identifier `--load_env=61`.

To list environment identifiers use the command `nearai registry list --tags=environment`.

A run can be named by passing a name to the record_run flag `--record_run="my special run"`.

Environment runs can be loaded by passing the name of a previous run to  the --load_env flag like `--load_env="my special run"`.

### Library

You can import `nearai` as a library in your python code. The main features are:

- Download/upload models and datasets from the registry. See [examples/prepare_data.py](examples/prepare_data.py).
- Store log events in the database. TODO Example.
- Fetch information about running or past experiments. TODO Example.
