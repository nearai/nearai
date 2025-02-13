# NEAR AI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Build Status](https://github.com/nearai/nearai/workflows/CI/badge.svg)](https://github.com/nearai/nearai/actions)
[![Release](https://img.shields.io/github/v/release/nearai/nearai)](https://github.com/nearai/nearai/releases)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://docs.near.ai/contributing)
[![Telegram](https://img.shields.io/badge/Dev_Support-2CA5E0?style=flat&logo=telegram&logoColor=white)](https://t.me/nearaialpha)

NEAR AI is a distributed system for building, deploying, and managing AI agents with the goal of making open source and user-owned AGI.

## NEAR AI Components

- [**NEAR AI Hub**](./hub/README.md): Central HUB for model serving, agent registry, and running agents
- [**TEE Runner**](https://github.com/nearai/private-ml-sdk): TEE-based execution environment for NEAR AI agents
- [**AWS Runner**](./aws_runner/README.md): Lambda-based execution environment for NEAR AI agents
- **Agent System**: Build and run AI agents with built-in tools and environment isolation
- **Worker System**: Distributed job execution and scheduling
- **Model Fine-tuning**: Support for fine-tuning LLMs


## Directory Structure

```
nearai/
├── aws_runner/          # Lambda-based AI agent execution
│   ├── Dockerfile         # Container for running agents
│   └── frameworks/        # Framework-specific requirements
├── hub/                 # Central HUB for registering and running agents
│   ├── alembic/           # Database migrations
│   └── api/               # API endpoints
├── nearai/              # Core library
│   ├── agents/            # Agent system implementation
│   │   ├── agent.py         # Base agent class
│   │   └── environment.py   # Agent environment
│   ├── cli.py             # Command-line interface
│   └── config.py          # Configuration management
├── worker/              # Distributed job execution
├── etc/                 # Configuration and setup
│   ├── finetune/          # Model fine-tuning configs
│   └── hosts_lambda.txt   # Cluster configuration
└── e2e/                 # End-to-end tests
```

## Quick Start

### Requirements

- [Python 3.11 or higher](https://www.python.org/downloads/)
- [Git](https://github.com/git-guides/install-git)
- [Docker](https://docs.docker.com/get-docker/) (for local agent testing)

---

### Installation

<details>
<summary>pip</summary>

```bash
python3 -m pip install nearai
```

Verify installation:

```bash
nearai version
```

</details>

<details>
<summary>local</summary>

```bash
git clone git@github.com:nearai/nearai.git && cd nearai && ./install.sh
```
Or, to install to a virtual environment with poetry:

```bash
python3 -m poetry install --no-root --with dev
poetry run nearai version
```

Verify installation:

```bash
nearai version
```

</details>

---

### Log In

Login to NEAR AI with your NEAR Account. If you don't have one, you can create one [here](https://wallet.near.org/).

Currently supported NEAR wallets:
- My NEAR Wallet
- Sender
- Meteor
- Bitte

```bash
nearai login  # Login with your NEAR account
```

---

### Useful Commands

1. Create an agent:
```bash
nearai agent create
```

2. Run agent locally:
```bash
nearai agent interactive
```

3. Deploy to NEAR AI Hub:
```bash
nearai registry upload <path-to-agent>
```

## Documentation

- [Official Documentation](https://docs.near.ai)
- [Agent Development Guide](https://docs.near.ai/agents/quickstart)
- [Contributing Guide](https://docs.near.ai/contributing)

## Updating 

```bash
cd nearai
git pull
python3 -m pip install -e .  # If dependencies changed
```