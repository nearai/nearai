# NEAR AI CLI Command Reference

This document provides a detailed reference of all available CLI commands in NEAR AI, including their syntax, options, and example usage.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Agent Development](#agent-development)
3. [Registry Management](#registry-management)
4. [Model Operations](#model-operations)
5. [Configuration](#configuration)


## Getting Started

**Login Commands**

- [login](#login)
- [login status](#login-status)
- [login save](#login-save)
- [logout](#logout)

**Miscellaneous Commands**

- [location](#location)
- [version](#version)

### `login`

Login with NEAR Mainnet account.

Syntax:
```
nearai login [--remote] [--auth_url=<auth_url>] [--accountId=<accountId>] [--privateKey=<privateKey>]
```

Example:
```
nearai login --accountId my_near_account.near
```

### `login status`

Load NEAR account authorization data.

Syntax:
```
nearai login status
```

### `login save`

Save NEAR account authorization data.

Syntax:
```
nearai login save --accountId=<accountId> --signature=<signature> --publicKey=<publicKey> --callbackUrl=<callbackUrl> --nonce=<nonce>
```

### `logout`

Clear NEAR account auth data.

Syntax:
```
nearai logout
```

### `location`

Show location where nearai is installed.

Syntax:
```
nearai location
```

### `version`

Show nearai version.

Syntax:
```
nearai version
```


---




## Miscellaneous Commands

### `submit`

Submit a task to be executed by a worker.

Syntax:
```
nearai submit [--path=<path>] [--worker_kind=<worker_kind>]
```

Example:
```
nearai submit --path=./my_task --worker_kind=GPU_8_A100
```


---

## Agent Development

### `agent dev`

Run local UI for development of agents that have their own UI.

Syntax:
```
nearai agent dev
```

### `agent inspect`

Inspect environment from a given path.

Syntax:
```
nearai agent inspect <path>
```

Example:
```
nearai agent inspect ./my_agent
```

### `agent interactive`

Runs an agent interactively.

Syntax:
```
nearai agent interactive [--agent=<agent>] [--thread_id=<thread_id>] [--tool_resources=<tool_resources>] [--local] [--verbose] [--env_vars=<env_vars>]
```

Example:
```
nearai agent interactive --agent=namespace/agent_name/1.0.0 --local --verbose
```

### `agent task`

Runs an agent non-interactively with a single task.

Syntax:
```
nearai agent task <agent> <task> [--thread_id=<thread_id>] [--tool_resources=<tool_resources>] [--file_ids=<file_ids>] [--local] [--verbose] [--env_vars=<env_vars>]
```

Example:
```
nearai agent task namespace/agent_name/1.0.0 "Summarize this text" --local --verbose
```

### `agent create`

Create a new agent or fork an existing one.

Syntax:
```
nearai agent create [--name=<name>] [--description=<description>] [--fork=<fork>]
```

Example:
```
nearai agent create --name my_new_agent --description "A new AI agent"
```

### `agent upload`

Upload an agent to the registry (alias for 'nearai registry upload').

Syntax:
```
nearai agent upload [--local_path=<path>] [--bump] [--minor_bump] [--major_bump]
```

Example:
```
nearai agent upload --local_path=./my_agent --bump
```

---

## Registry Management

### `registry info`

Show information about an item in the registry.

Syntax:
```
nearai registry info <entry>
```

Example:
```
nearai registry info namespace/agent_name/1.0.0
```

### `registry metadata-template`

Create a metadata template for a registry item.

Syntax:
```
nearai registry metadata-template [--local_path=<path>] [--category=<category>] [--description=<description>]
```

Example:
```
nearai registry metadata-template --local_path=./my_agent --category=agent --description="My new agent"
```

### `registry list`

List available items in the registry.

Syntax:
```
nearai registry list [--namespace=<namespace>] [--category=<category>] [--tags=<tags>] [--total=<total>] [--offset=<offset>] [--show_all] [--show_latest_version] [--star=<star>]
```

Example:
```
nearai registry list --category=agent --tags=nlp,chatbot --total=10
```

### `registry update`

Update metadata of a registry item.

Syntax:
```
nearai registry update [--local_path=<path>]
```

Example:
```
nearai registry update --local_path=./my_agent
```

### `registry upload-unregistered-common-provider-models`

Creates new registry items for unregistered common provider models.

Syntax:
```
nearai registry upload-unregistered-common-provider-models [--dry_run=<bool>]
```

Example:
```
nearai registry upload-unregistered-common-provider-models --dry_run=False
```

### `registry upload`

Upload an item to the registry.

Syntax:
```
nearai registry upload [--local_path=<path>] [--bump] [--minor_bump] [--major_bump]
```

Example:
```
nearai registry upload --local_path=./my_agent --bump
```

### `registry download`

Download an item from the registry.

Syntax:
```
nearai registry download <entry_location> [--force]
```

Example:
```
nearai registry download namespace/agent_name/1.0.0 --force
```

---

## Model Operations



**Benchmark Commands**

- [benchmark run](#benchmark-run)
- [benchmark list](#benchmark-list)

**Evaluation Commands**

- [evaluation table](#evaluation-table)
- [evaluation read-solutions](#evaluation-read-solutions)

**Hub Commands**

- [hub chat](#)

**Permission Commands**

- [permission grant](#)
- [permission revoke](#)

**Tensorboard Commands**

- tensorboard start

### `benchmark run`

Run a benchmark on a dataset with a solver strategy.

Syntax:
```
nearai benchmark run <dataset> <solver_strategy> [--max_concurrent=<int>] [--force] [--subset=<subset>] [--check_compatibility] [--record] [--num_inference_retries=<int>] [--solver_args...]
```

Example:
```
nearai benchmark run my_dataset my_solver --max_concurrent=4 --force --record
```

### `benchmark list`

List all executed benchmarks.

Syntax:
```
nearai benchmark list [--namespace=<namespace>] [--benchmark=<benchmark>] [--solver=<solver>] [--args=<args>] [--total=<total>] [--offset=<offset>]
```

Example:
```
nearai benchmark list --namespace=my_namespace --total=20
```

### `evaluation table`

Prints table of evaluations.

Syntax:
```
nearai evaluation table [--all_key_columns] [--all_metrics] [--num_columns=<int>] [--metric_name_max_length=<int>]
```

Example:
```
nearai evaluation table --all_metrics --num_columns=8
```

### `evaluation read-solutions`

Reads solutions.json from an evaluation entry.

Syntax:
```
nearai evaluation read-solutions <entry> [--status=<bool>] [--verbose]
```

Example:
```
nearai evaluation read-solutions namespace/evaluation_name/1.0.0 --status=True
```


### `hub chat`

Chat with a model from NEAR AI hub.

Syntax:
```
nearai hub chat [--query=<query>] [--endpoint=<endpoint>] [--model=<model>] [--provider=<provider>] [--info]
```

Example:
```
nearai hub chat --query="What is AI?" --model=gpt-3.5-turbo
```


### `permission grant`

Grant permission to an account.

Syntax:
```
nearai permission grant <account_id> <permission>
```

Example:
```
nearai permission grant alice.near read_access
```

### `permission revoke`

Revoke permission from an account.

Syntax:
```
nearai permission revoke <account_id> [--permission=<permission>]
```

Example:
```
nearai permission revoke bob.near --permission=write_access
```

### `tensorboard start`

TensorBoard integration.

Syntax:
```
nearai tensorboard start <logdir> [--limit=<limit>] [--timeout=<timeout>]
```

Example:
```
nearai tensorboard start /tmp/log --limit=200
```

### `vllm run`

Run VLLM server with OpenAI-compatible API.

Syntax:
```
nearai vllm run
```

Example:
```
nearai vllm run
```

### `finetune inspect`

Commands for fine-tuning models.

Syntax:
```
nearai finetune inspect <job_id>
```

Example:
```
nearai finetune inspect myJobId
```

### `finetune start`

Start a fine-tuning job on the current node.

Syntax:
```
nearai finetune start
```

Example:
```
nearai finetune start
```

---

## Configuration

### `config set`

Add a key-value pair to the config file.

Syntax:
```
nearai config set <key> <value> [--local]
```

Example:
```
nearai config set api_url https://api.example.com
```

### `config get`

Get the value of a key from the config file.

Syntax:
```
nearai config get <key>
```

Example:
```
nearai config get api_url
```

### `config show`

Show all configuration settings.

Syntax:
```
nearai config show
```
