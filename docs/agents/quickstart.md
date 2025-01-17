# Quickstart a Python Agent

Welcome! NEAR AI Agents are programs that can act autonomously to solve a task, while adapting and reacting to
their environment.

NEAR AI agents can use various AI models, store data to remember past interactions, communicate with other agents,
use tools to interact with the environment, and much more.

In this Quickstart we will build our first agent on NEAR AI, and learn how to interact with it.

<iframe width="49%" height="auto" src="https://www.youtube.com/embed/q2nhgj9q2PU" frameborder="0" allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
<iframe width="49%" height="auto" src="https://www.youtube.com/embed/fqPRXxj3AoI" frameborder="0" allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

---

## Pre-Requisites

To get started, you will need to have a [Near account](https://wallet.near.org/), and install the [NEAR AI CLI](https://github.com/nearai/nearai/#setup):

=== "pip"

    ``` bash
    python3 -m pip install nearai
    ```

=== "local"

    ``` bash
    git clone git@github.com:nearai/nearai.git
    cd nearai
    pip install -e .
    ```

??? tip "NEAR Account"
    
    If you do not have a Near account yet, you can create one using any of the wallets at the [wallet portal](https://wallet.near.org/). If you do not know which one to choose, we recommend that you use [Bitte](https://wallet.bitte.ai) or [Meteor Wallet](https://wallet.meteorwallet.app/add_wallet/create_new)

??? abstract "Python Version"

    If you do not have python, or your version is not compatible, we recommend that you use [miniconda](https://docs.anaconda.com/miniconda/install/) or [pyenv](https://github.com/pyenv/pyenv)
    to manage your installations, as they both allow you to easily switch between python versions.

    === "pyenv"

        ``` bash
        pyenv install 3.11
        pyenv local 3.11 # or use global
        ```

    === "conda"

        ``` bash
        conda create -n myenv python=3.11
        conda activate myenv
        ```

---

## Login to NEAR AI

To create a new agent, you first need to login using your Near account:

``` bash
$> nearai login

# Example Response:
# Please visit the following URL to complete the login process: https://auth.near.ai?message=Welcome+to+NEAR+AI&nonce=<xyzxyzxyzxyzx>&recipient=ai.near&callbackUrl=http%3A%2F%2Flocalhost%3A63130%2Fcapture
```

You'll be prompted to visit a URL to authenticate with your Near account. Select your wallet (if you don't have a wallet, check our [prerequisites](#pre-requisites)), and login with it.

After successfully login, you should see the screen below. Close it and return to your terminal.

![alt text](../assets/agents/quickstart-login.png)

??? tip Other Login Methods

    If you have already logged in on `near-cli`, you know your account's private key, or you have the credentials on another device, you can use the following commands to login:

    ```bash
    ### Login with NEAR Account ID Only
    nearai login --accountId name.near

    ### Login with Account ID and Private Key
    nearai login --accountId name.near --privateKey key

    ### Login Remotely (only displays the login URL)
    nearai login --remote
    ```

---

## Creating a New Agent

Now that you are logged in, lets create your first AI agent, a simple agent called `hello-ai`:

```bash
nearai agent create --name hello-ai --description "My First NEAR AI Agent"

# Example Response:
# Agent created at: /Users/user/.nearai/registry/<your-account.near>/hello-ai/0.0.1
```

This will create a local folder with some `metadata` that describes the agent, and a python file with the agent's logic. Let's interact with the agent before we dive into its code!

Execute the following commands in your terminal:

```bash
nearai agent interactive ~/.nearai/registry/<your-account.near>/hello-ai/0.0.1 --local
```

An interactive session will start, where you can chat with your agent... talk to it for a while and type `exit` when you are ready to continue.

---

## The Agent

The agent is defined by two files, both located at `~/.nearai/registry/<your-account.near>/hello-ai/0.0.1`: 

1. `metadata.json`: Contains information about your agent, and can include configuration about which model to use.
2. `agent.py`: This is the code that executes each time your agent receives a prompt.

By default, the agent takes the role of a "helpful assistant", which receives the user input and responds to it using the [Llama 3.1 70B Instruct](https://huggingface.co/meta-llama/Llama-3.1-70B-Instruct) (as defined in the default metadata).

```python title="agent.py"
from nearai.agents.environment import Environment

def run(env: Environment):
    # A system message guides an agent to solve specific tasks.
    prompt = {"role": "system", "content": "You are a helpful assistant."}

    # Use the model set in the metadata to generate a response
    result = env.completion([prompt] + env.list_messages())

    # Store the result in the chat history
    env.add_reply(result)

    # Give the prompt back to the user
    env.request_user_input()

run(env)
```

??? example "Default metadata.json"

    By default, agents use the 

    ```json
    {
      "name": "hello-ai",
      "version": "1.0.0",
      "description": "My First Agent",
      "category": "agent",
      "tags": [],
      "details": {
        "agent": {
          "defaults": {
            "model": "qwen2p5-72b-instruct",
            "model_provider": "fireworks",
            "model_temperature": 1.0,
            "model_max_tokens": 16384
          }
        }
      },
      "show_entry": false
    }
    ```

!!! tip 
    You can change the model used by the agent by modifying the `metadata.json` file, check all the available models in the [NEAR AI Hub](https://app.near.ai/models).

---

## Next Steps

Congratulations! You have created your first agent on NEAR AI. Now you can modify the agent's code to help you solve a specific task. To discover everything an agent can do we recommend you to explore the following sections:

- [Registry](./registry.md): NEAR AI has an open registry, where you can find agents created by the community and even publish your own.

- [Threads](./threads.md): Agents execute in conversation threads, which can contain files, messages, and interactions with other agents.

- [The Agent Environment](./env/overview.md): Agents have access to the environment object, which allows them to [interact with the user](./env/messages_files.md), use AI models to make [inferences](./env/inference.md), [call other agents](./env/calling_other_agents.md), use [tools](./env/tools.md), and much more. 

- [Secrets](./secrets.md): Agents can store secrets to access external services, like APIs, databases, or other services.