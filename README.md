# Jasnah CLI

## Setup

First install jasnah-cli by running:

```
git clone git@github.com:nearai/jasnah-cli.git
cd jasnah-cli
python3 -m pip install -e .
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

Upload a new dataset or model to the registry:

```
jasnah-cli models upload <PATH_TO_MODEL> <MODEL_NAME> <DESCRIPTION> [--alias <ALIAS>]
jasnah-cli datasets upload <PATH_TO_DATASET> <DATASET_NAME> <DESCRIPTION> [--alias <ALIAS>]
```

The path could be either to a file or a folder.
The name is a unique identifier, and the alias is a human readable name that can be used to refer to the model or dataset.

### Library

You can import `jasnah` as a library in your python code. The main features are:

- Download/upload models and datasets from the registry. See [examples/prepare_data.py](examples/prepare_data.py).
- Store log events in the database. TODO Example.
- Fetch information about running or past experiments. TODO Example.
