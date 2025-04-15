# CDP Agentkit LangChain Extension Examples - Chatbot Python

This example demonstrates an agent setup as a terminal style chatbot with access to the full set of CDP Agentkit actions. It integrates [AgentKit](https://github.com/coinbase/agentkit) to provide AI-driven interactions with on-chain capabilities.

## Ask the chatbot to engage in the Web3 ecosystem!
- "Transfer a portion of your ETH to a random address"
- "What is the price of BTC?"
- "Deploy an NFT that will go super viral!"
- "Deploy an ERC-20 token with total supply 1 billion"

## Requirements
- Python 3.10+
- [CDP API Key](https://portal.cdp.coinbase.com/access/api)

### Checking Python Version
Before using the example, ensure that you have the correct version of Python installed. The example requires Python 3.10 or higher.

## Installation
Once you created and deployed your agent using NEAR AI Hub, you can download the code to develop it locally.

### Install dependencies
- [NEAR AI CLI](https://docs.near.ai/cli/): `pip install nearai`
- `pip install coinbase_agentkit coinbase_agentkit_langchain dotenv langgraph nearai_langchain`

### Set ENV Vars
Create .env file with the following variables:
- "CDP_API_KEY_NAME"
- "CDP_API_KEY_PRIVATE_KEY"
- "NETWORK_ID" (Defaults to `base-sepolia`)

### Make changes
1. Download this agent locally: `nearai registry download YOUR_ACCOUNT_ID/YOUR_AGENT_NAME/0.0.1`
2. Navigate to the downloaded source code and make changes: `cd ~/.nearai/registry/YOUR_ACCOUNT_ID/YOUR_AGENT_NAME/0.0.1`
3. Interact with your agent locally to test changes: `nearai agent interactive ~/.nearai/registry/YOUR_ACCOUNT_ID/YOUR_AGENT_NAME/0.0.1 --local`
4. Publish your changes: `nearai registry upload .`

## How it works

### Modules

#### Coinbase AgentKit & Langchain Integration
Tools and configs for creating an agent that can interact with blockchain systems like wallets, tokens, and APIs.

- `coinbase_agentkit` - framework for easily enabling AI agents to take actions onchain. It is designed to be framework-agnostic, so you can use it with any AI framework, and wallet-agnostic, so you can use it with any wallet.
- `coinbase_agentkit_langchain` - LangChain extension of AgentKit. Enables agentic workflows to interact with onchain actions.

#### NearAI Integration

- `nearai_langchain` - the module provides seamless integration between [NearAI](https://github.com/nearai/nearai) and [LangChain](https://github.com/langchain-ai/langchain), allowing developers to use NearAI's capabilities within their LangChain applications.


#### Other

- `langgraph` - is a low-level orchestration framework for building controllable agents. While langchain provides integrations and composable components to streamline LLM application development, the LangGraph library enables agent orchestration — offering customizable architectures, long-term memory, and human-in-the-loop to reliably handle complex tasks.
- `dotenv` - the module allows using environment variables in the project.

### Wallet Setup

A local file wallet_data.txt is used to persist the MPC wallet data for reuse between sessions.

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

### LLM Setup

LLM is initiatized by NearAILangchainOrchestrator (`nearai_langchain` module). This example leverages a ChatOpenAI model.

```python
orchestrator = NearAILangchainOrchestrator(globals())

...

def initialize_agent():
    """Initialize the agent with CDP Agentkit."""
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
# Create ReAct Agent using the LLM and CDP Agentkit wrappet tools.
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
        "you must say so, and encourage them to implement it themselves using the CDP SDK + Agentkit, "
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