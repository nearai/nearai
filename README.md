# ⚠️ DEPRECATED - NEAR AI Agent Framework

> [!WARNING]
> This project is **deprecated**.  Server components will be shut down on **October 31, 2025**.
>
> ## FAQ:
> 
> > Why deprecate NEAR AI Agent Framework and Developer Hub?
> 
> As AI agents have become more popular and more advanced, they've also become more integrated into 'regular' software.
> There's not that much need (or demand) anymore for a special hosted framework for chat-based AI agents.  More often,
> we're seeing agentic workflows integrated into new or existing applications.  For that, existing frameworks like
> LangChain, AutoGen, and many others are more than sufficient.
> 
> > What's NEAR AI doing?
> 
> [NEAR AI](https://near.ai/) has built a new platform for private & confidential AI, consisting of:
>  * NEAR AI Private Chat (https://private.near.ai/)
>  * NEAR AI Cloud (https://cloud.near.ai/)
> 
> These new products are in active development and as of October 2025 they have not been publicly launched yet; we are 
> disclosing them to the NEAR AI community to maintain service continuity and show you what's coming soon.
> 
> > What will happen to the NEAR AI Developer Hub?
>
> The NEAR AI Developer Hub at https://app.near.ai/ will shut down on October 31, 2025 and replaced with this notice.
> After that date, all agents, threads, models, vector stores, datasets, and evaluations will be unavailable.  We will
> delete all user-specific data pertaining to threads, logins, environment variables, secrets, vector stores, and evaluations 
> shortly after the website shuts down.  Most agent code and datasets have always been public on NEAR AI; as such, we will
> keep paying for the S3 bucket that stores that information for the foreseeable future, and can serve individual requests for that 
> data at our discretion upon request.
>
> > What will happen to my NEAR AI agents?
>
> When the NEAR AI Hub goes offline on October 31, 2025, you'll lose access to your agents.  Please use the
> `nearai registry download` or the "Export" button to download a copy of your agent code.  From there, we recommend
> adapting it into the AI framework of your choice and hosting it using the infrastructure of your choice.  Please reach
> out on the [the NEAR AI Telegram group](https://t.me/nearaialpha) if you'd like migration advice, as we've been working with many users to
> help migrate their agents to other frameworks.
>
> > What will happen to NEAR AI inference/completions API?
> 
> The old NEAR AI completions APIs will go offline on October 31, 2025.  We recommend [NEAR AI Cloud](https://cloud.near.ai/),
> our new, fully private & confidential AI API, with a similar OpenAI-compatible API.  NEAR AI Cloud is in active alpha 
> development and as of October 2025 has not been publicly launched yet; we are disclosing it to the NEAR AI community 
> to maintain service continuity and show you what's coming soon.
> 
> If you urgently need production-ready AI services in advance of the NEAR AI Cloud launch, we also like:
>  * [Fireworks AI](https://fireworks.ai/), which was powering NEAR AI Hub
>  * [RedPill](https://redpill.ai/), another confidential AI API
> 
> > What will happen to NEAR AI Chat and NEAR AI Assistant?
> 
> The NEAR AI Assistant at https://chat.near.ai has been redirected to our new private, confidential AI chat interface.
> 
> > Who can I contact for more information or complaints?
> 
> We're available on [the NEAR AI Telegram group](https://t.me/nearaialpha).
>

![Status: Deprecated](https://img.shields.io/badge/status-deprecated-critical)

The NEAR AI hub & agent framework has been deprecated, and the server components will be shut off on October 31, 2025.  

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Build Status](https://github.com/nearai/nearai/workflows/CI/badge.svg)](https://github.com/nearai/nearai/actions)
[![Release](https://img.shields.io/github/v/release/nearai/nearai)](https://github.com/nearai/nearai/releases)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://docs.near.ai/contributing)
[![Telegram](https://img.shields.io/badge/Dev_Support-2CA5E0?style=flat&logo=telegram&logoColor=white)](https://t.me/nearaialpha)

NEAR AI ~is~ was a distributed system for building, deploying, and managing AI agents with the goal of making open source and user-owned AGI.

## NEAR AI Components

- [**NEAR AI Hub**](./hub/README.md): Central hub for model serving, agent registry, and running agents
- [**TEE Runner**](https://github.com/nearai/private-ml-sdk): Confidential execution environment for NEAR AI agents and inference
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
├── hub/                 # Central hub for registering and running agents and models
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

## Agent Creation Quick Start

### Requirements

- [Python 3.11](https://www.python.org/downloads/) _(3.12+ currently not supported)_
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
python3 -m uv sync
uv run nearai version
```

Or you can use pip:

```bash
python3 -m pip install -e .
```

Verify installation:

```bash
nearai version
```

</details>

---

### Log In

Login to NEAR AI with your NEAR Account. If you don't have one, we recommend creating a free account with [Meteor Wallet](https://wallet.meteorwallet.app).

```bash
nearai login 
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

3. Deploy to [NEAR AI Developer Hub](https://hub.near.ai):

```bash
nearai registry upload <path-to-agent>
```

## Documentation

- [Official Documentation](https://docs.near.ai)
- [Agent Development Guide](https://docs.near.ai/agents/quickstart)

## Updating

```bash
cd nearai
git pull
python3 -m pip install -e .  # If dependencies changed
```

## Contributing

Want to help shape the future of AI? Join our community and contribute! 🚀

- 🐛 [Report bugs and suggest features](https://github.com/nearai/nearai/issues)
- 💻 [Submit pull requests](https://github.com/nearai/nearai/pulls)
- 📖 [Improve documentation](https://docs.near.ai/contributing/#contribute-documentation)
- 🤝 [Help other users in the community](https://t.me/nearaialpha)
- 🌟 [Star our repository](https://github.com/nearai/nearai)

Check out our [contributing guide](https://docs.near.ai/contributing) to get started.
