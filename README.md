# Jasnah CLI

## Setup

First install jasnah-cli by running:

```
git clone git@github.com:nearai/jasnah-cli.git
cd jasnah-cli
python3 -m pip install -e .
pip install openai
```

To install to a virtual environment, use the following command:

```bash
python3 -m poetry install --no-root --with dev
```

Check the installation worked with

```
jasnah-cli version
```

Setup basic configuration

```
jasnah-cli config set db_user <DB_USERNAME>
jasnah-cli config set db_password <DB_PASSWORD>
jasnah-cli config set user_name <YOUR_NAME>
```

The user name will be used to identify the author of the experiments.
This configuration can be manually edited at `~/.jasnah/config.json`, or per project at `.jasnah/config.json` (relative to the current directory).

To use the registry (for downloading and uploading models and datasets) you need to setup access to S3. Do it by installing [aws-cli](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html) and configuring it:

```
export AWS_ACCESS_KEY_ID=<..>
export AWS_SECRET_ACCESS_KEY="<..>"
```

## Update

To update jasnah-cli run:

```
# Go to the jasnah-cli folder
cd jasnah-cli

git pull

# The next step is only required in case some dependencies were added or updated, otherwise pulling new changes is enough
python3 -m pip install -e .
```

## Usage

### Submit an experiment

To submit a new experiment run:

```
jasnah-cli submit --command <COMMAND> --name <EXPERIMENT_NAME> [--nodes <NUMBER_OF_NODES>] [--cluster <CLUSTER>]
```

This will submit a new experiment. The command must be executed from a folder that is a git repository (public github repositories, and private github repositories on the same organization as jasnah-cli are supported).
The current commit will be used for running the command so make sure it is already available online. The diff with respect to the current commit will be applied remotely (new files are not included in the diff).

On each node the environment variable `ASSIGNED_SUPERVISORS` will be available with a comma separated list of supervisors that are running the experiment. The current supervisor can be accessed via `jasnah.CONFIG.supervisor_id`. See [examples/prepare_data.py](examples/prepare_data.py) for an example.

### Registry

Upload an element to the registry using:

```
jasnah-cli registry upload <ITEM_LOCAL_PATH> <ITEM_S3_PATH> <DESCRIPTION> [--name <NAME>] [--tags <TAGS>]
```

- The local path could be either to a file or a folder.
- The S3 path should be a non-existent folder in the registry.
- Tags is a comma separated list of tags to add to the item. This allows filtering relevant items.

There are two shortcuts to upload models and datasets. The following commands behave in the same way as `registry upload` but it adds by default the tags `model` and `dataset` respectively.

```
jasnah-cli models upload <ITEM_LOCAL_PATH> <ITEM_S3_PATH> <DESCRIPTION> [--name <NAME>] [--tags <TAGS>]
jasnah-cli datasets upload <ITEM_LOCAL_PATH> <ITEM_S3_PATH> <DESCRIPTION> [--name <NAME>] [--tags <TAGS>]
```

We recommend as a good practice to use as s3_path `@namespace/@name/@version`, but it is not mandatory.

**Examples:**

Upload an item to the registry with name quine.py and tags `quine` and `python`

```
jasnah-cli registry upload ~/quine.py test/quine/v3 "Test registry upload" quine.py --tags quine,python
```

Check the item is available by listing all elements in the registry:

```
jasnah-cli registry list
```

Show only items with the tag `quine` and `python`:

```
jasnah-cli registry list --tags quine,python
```

Download this element locally. To download you can refer to the item either by name or by s3_path. Trying to download an item that was previously downloaded is a no-op.

Note: If you start downloading and item, and cancel the download midway, you shold delete the folder at `~/.jasnah/registry/` to trigger a new download.

```
jasnah-cli registry download quine.py
```

Add one or more tags to an item using:

```
jasnah-cli registry add_tags test/quine/v3 code,multiple,tags
```

Removing tags must be done one by one:

```
jasnah-cli registry remove_tag test/quine/v3 code
```

### Agents

#### Running environment interactively

You can run agent (or a set of agents) inside a local environment that lives in a specific folder.

```
jasnah-cli environment interactive sample-agent ~/tmp/sample-agent/test1 
```

### Library

You can import `jasnah` as a library in your python code. The main features are:

- Download/upload models and datasets from the registry. See [examples/prepare_data.py](examples/prepare_data.py).
- Store log events in the database. TODO Example.
- Fetch information about running or past experiments. TODO Example.
