# Coinbase AgentKit Example

The [Coinbase Developer Platform (CDP) AgentKit](https://github.com/coinbase/agentkit) is a powerful tool that allows developers to create AI agents that can interact with multiple blockchains. This allows agents to perform actions on the blockchain, such as transferring tokens or interacting with smart contracts.

In this page, we will showcase a [NEAR AI agent](https://app.near.ai/agents/another_one_test_account.near/first-try-agent/latest/source?file=agent.py) that uses the CDP AgentKit to perform actions such as:

- "Transfer a portion of your ETH to a random address"
- "What is the price of BTC?"
- "Deploy an NFT that will go super viral!"
- "Deploy an ERC-20 token with total supply 1 billion"

---

## Prerequisites

Before creating a NEAR AI agent, please make sure you have the met the following requisites:

- You have the [NEAR AI CLI](../../cli.md) installed and have logged in with your Near wallet.
- Obtain a [CDP API Key](https://portal.cdp.coinbase.com/access/api)
- Install extra dependencies: `pip install coinbase_agentkit coinbase_agentkit_langchain dotenv langgraph nearai_langchain`

---

## Using the Agent

Lets start by downloading the agent from the NEAR AI registry and running it locally.

```bash
nearai registry download another_one_test_account.near/first-try-agent/latest
```

Navigate to the `registry folder` (by default, `~/.nearai/registry/another_one_test_account.near/first-try-agent/latest`).

For the agent to work, you need to set up a few environment variables:

- "CDP_API_KEY_NAME"
- "CDP_API_KEY_PRIVATE_KEY"
- "NETWORK_ID" (Defaults to `base-sepolia`)

You can obtain Coinbase Developer Platform (CDP) Api Key in your CDP settings [here](https://portal.cdp.coinbase.com/projects/api-keys).

Now you can run the agent locally and pass all environment variables using NEAR AI CLI:

`nearai agent interactive ~/.nearai/registry/another_one_test_account.near/first-try-agent/latest --local --env_vars='{"CDP_API_KEY_NAME":"YOUR_API_KEY", "CDP_API_KEY_PRIVATE_KEY":"YOUR_SECRET_KEY", "NETWORK_ID":"base-sepolia"}'`

!!! warning "You can create `.env` file locally and put your variables there, but DON'T FORGET TO DELETE IT before uploading your code on Near AI Hub. There is no way to ignore it without deleting yet."

!!! tip
    Refer to the [Secrets & Environment Variables](../env/variables.md) to learn how to work with your variables locally and on Near AI Hub.

---

## How it works

Lets take a look at the imports at the beginning of the agent code:

```python
import json
import os

from coinbase_agentkit import (  # type: ignore
    AgentKit,
    AgentKitConfig,
    CdpWalletProvider,
    CdpWalletProviderConfig,
    cdp_api_action_provider,
    cdp_wallet_action_provider,
    erc20_action_provider,
    pyth_action_provider,
    wallet_action_provider,
    weth_action_provider,
)
from coinbase_agentkit_langchain import get_langchain_tools  # type: ignore
from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from nearai_langchain.orchestrator import NearAILangchainOrchestrator, RunMode
```

General packages:

- `json` is a built-in package, which can be used to work with JSON data.
- `os` provides a portable way of using operating system dependent functionality.
- `dotenv` allows using environment variables in the project.

AI related packages:

- `coinbase_agentkit` is a framework for easily enabling AI agents to take actions onchain. It is designed to be framework-agnostic, so you can use it with any AI framework, and wallet-agnostic, so you can use it with any wallet.
- `coinbase_agentkit_langchain` is the LangChain extension of AgentKit. Enables agentic workflows to interact with onchain actions.
- `nearai_langchain` provides seamless integration between [NearAI](https://github.com/nearai/nearai) and [LangChain](https://github.com/langchain-ai/langchain), allowing developers to use NearAI's capabilities within their LangChain applications.
- `langgraph` is a low-level orchestration framework for building controllable agents. While langchain provides integrations and composable components to streamline LLM application development, the LangGraph library enables agent orchestration — offering customizable architectures, long-term memory, and human-in-the-loop to reliably handle complex tasks.

### Wallet Setup
The agent will control a wallet to perform onchain actions. A local file `wallet_data.txt` is used to persist the MPC wallet data for reuse between sessions.

- If the file exists, it loads the wallet data for reinitialization
- If the file doesn't exists it's initiated using `CdpWalletProvider` from `coinbase_agentkit` module.

```python
# Initialize CDP Wallet Provider
wallet_data = None
if os.path.exists(wallet_data_file):
    with open(wallet_data_file) as f:
        wallet_data = f.read()

cdp_config = None
if wallet_data is not None:
    cdp_config = CdpWalletProviderConfig(wallet_data=wallet_data)

wallet_provider = CdpWalletProvider(cdp_config)
```

### AgentKit Setup

To initiate AgentKit, in addition to passing `wallet_provider`, it is necessary to pass the action providers it is going to work with. [Action providers](https://pypi.org/project/coinbase-agentkit/#action-providers) define the actions that an agent can take.

In this example, we're using the following ones:

- `cdp_api_action_provider` retrieves the current price of a cryptocurrency from the CDP API and fetches on-chain data from Base blockchain explorer via CDP API.
- `cdp_wallet_action_provider` deploys contracts (custom, NFT, FT) and executes trades.
- `erc20_action_provider` retrieves the token balance for a specified address and ERC-20 contract and transfers a specified amount of ERC-20 tokens to a destination address.
- `pyth_action_provider` retrieves current price data from a specified Pyth price feed and the unique price feed identifier for a given token symbol.
- `wallet_action_provider` retrieves wallet address, network info, balances, gets the native currency balance of the connected wallet, transfers native blockchain tokens (e.g., ETH) to a destination address.
- `weth_action_provider` converts native ETH to Wrapped ETH (WETH) on supported networks.

The list of all available action providers and their actions you can find [here](https://pypi.org/project/coinbase-agentkit/#action-providers). You can also create a [custom action provider](https://pypi.org/project/coinbase-agentkit/#creating-an-action-provider).

### LLM Setup

LLM is initiatized by NearAILangchainOrchestrator (`nearai_langchain` module). This example leverages a ChatOpenAI model.

```python
orchestrator = NearAILangchainOrchestrator(globals())

...

def initialize_agent():
    """Initialize the agent with CDP AgentKit."""
    # Get ChatOpenAI model.
    llm = orchestrator.chat_model.chat_open_ai_model

...
```

### Langchain Setup

In order to use AgentKit blockchain tools we have to wrap these providers into usable tools for the agent using `get_langchain_tools` method from `coinbase_agentkit_langchain` module.

```python
tools = get_langchain_tools(agentkit)
```

### Agent Setup
Eventually we create and return ReAct Agent:

```python
# Create ReAct Agent using the LLM and CDP AgentKit wrappet tools.
return create_react_agent(
    llm,
    tools=tools,
    state_modifier=(
        "You are a helpful agent that can interact onchain using the Coinbase Developer Platform AgentKit. "
        "You are empowered to interact onchain using your tools. If you ever need funds, you can request "
        "them from the faucet if you are on network ID 'base-sepolia'. If not, you can provide your wallet "
        "details and request funds from the user. Before executing your first action, get the wallet details "
        "to see what network you're on. If there is a 5XX (internal) HTTP error code, ask the user to try "
        "again later. If someone asks you to do something you can't do with your currently available tools, "
        "you must say so, and encourage them to implement it themselves using the CDP SDK + AgentKit, "
        "recommend they go to docs.cdp.coinbase.com for more information. Be concise and helpful with your "
        "responses. Refrain from restating your tools' descriptions unless it is explicitly requested."
    ),
)
```

### NearAI Environment Setup

- In remote mode thread is assigned, user messages are given, and an agent is run at least once per user message.
- In local mode an agent is responsible to get and upload user messages.

```python
env = orchestrator.env

if orchestrator.run_mode == RunMode.LOCAL:
    print("Entering chat mode...")
    user_input = input("\nPrompt: ")
    env.add_user_message(user_input)

messages = env.list_messages()
for chunk in executor.stream({"messages": messages}):
    if "agent" in chunk:
        result = chunk["agent"]["messages"][0].content
    elif "tools" in chunk:
        result = chunk["tools"]["messages"][0].content
    env.add_reply(result)

    if orchestrator.run_mode == RunMode.LOCAL:
        print(result)
        print("-------------------")

# Run once per user message.
env.mark_done()
```