# NEAR AI

NEAR AI is a project with the goal of making open source and user-owned AGI.

## Setup

<b>Requirements: [python](https://www.python.org/downloads/), [git](https://github.com/git-guides/install-git)</b>

One line installation with a venv virtual env:

```shell
git clone git@github.com:nearai/nearai.git && cd nearai && ./install.sh;
```
<hr/>
Or, install nearai by running:

```shell
git clone git@github.com:nearai/nearai.git
cd nearai
python3 -m pip install -e .
```
Check that `nearai` was installed as a command line tool:

```shell
nearai version
```

<hr/>
Or, to install to a virtual environment with poetry, use the following command:

```bash
python3 -m poetry install --no-root --with dev
```

Check the installation worked with

```
poetry run nearai version
```

## Usage
To perform write operations you will need to log in with your Near account.

```
nearai login
```

<b>To learn how to use NEAR AI, please read the [documentation](https://docs.near.ai/).</b>


## Update

To update nearai run:

```
cd nearai
git pull # Pull the latest changes

# The next step is only required in case some dependencies were added or updated, otherwise pulling new changes is enough
python3 -m pip install -e .
```

## Contributing

To contribute to NEAR AI, please read the [contributing guide](https://docs.near.ai/contributing/).