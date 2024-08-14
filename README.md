# NearAI

NearAI is a project with the goal of making open source and user-owned AGI.

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
poetry run nearai version
```

To install `nearai` as a command line tool, run:

```
python3 -m pip install -e .
nearai version
```

## Setup basic configuration

To setup configuration with a remote `nearai` database, run:

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
cd nearai
git pull # Pull the latest changes

# The next step is only required in case some dependencies were added or updated, otherwise pulling new changes is enough
python3 -m pip install -e .
```

## Usage

To learn how to use NearAI, please read the [documentation](docs.near.ai/).

## Contributing

To contribute to NearAI, please read the [contributing guide](docs.near.ai/contributing/).