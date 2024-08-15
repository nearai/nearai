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

To perform write operations you will need to log in with your Near account.

```
nearai login
```

## Usage

To learn how to use NearAI, please read the [documentation](https://docs.near.ai/).


## Update

To update nearai run:

```
cd nearai
git pull # Pull the latest changes

# The next step is only required in case some dependencies were added or updated, otherwise pulling new changes is enough
python3 -m pip install -e .
```

## Contributing

To contribute to NearAI, please read the [contributing guide](https://docs.near.ai/contributing/).