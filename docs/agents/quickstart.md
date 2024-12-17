# Quickstart a Python Agent

Welcome! Agents are programs that can act autonomously to achieve a predefined goal, while
understanding and reacting to their environment.

NearAI agents can communicate with each other, and have access to a wide range of capabilities, including
authentication, tools, apis, smart contract calls, and more.

Let's build our first agent on Near AI!

---

## Pre-Requisites

To get started, you will need to have a [Near account](https://wallet.near.org/), and install the [Near AI CLI](https://github.com/nearai/nearai/#setup):

=== "pip"

    ``` bash
    python -m pip install nearai
    ```

=== "local"

    ``` bash
    git clone git@github.com:nearai/nearai.git
    cd nearai
    pip install -e .
    ```

??? tip "NEAR Account"
    
    If you do not have a Near account yet, you can create one using any of the wallets at the [wallet portal](https://wallet.near.org/). If you do not
    know which one to choose, we recommend you to use [Bitte]([bitte.ai](https://wallet.bitte.ai)) or [Meteor Wallet](https://wallet.meteorwallet.app/add_wallet/create_new)

??? abstract "Python Version"

    If you do not have python, or your version is not compatible, we recommend you to use [miniconda](https://docs.anaconda.com/miniconda/install/) or [pyenv](https://github.com/pyenv/pyenv)
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

## Login to NearAI

To create a new agent, you first need to login using your Near account:

``` bash
$> nearai login

# Example Response:
# Please visit the following URL to complete the login process: https://auth.near.ai?message=Welcome+to+NEAR+AI&nonce=<xyzxyzxyzxyzx>&recipient=ai.near&callbackUrl=http%3A%2F%2Flocalhost%3A63130%2Fcapture
```

You'll be prompted to visit a URL to authenticate with your Near account. Select your wallet (if you don't have a wallet, check our [prerequisites](#pre-requisites)), and login with it.

After successfully login, you should see the screen below. Close it and return to your terminal.

![alt text](../assets/agents/quickstart-login.png)

---

## Creating a New Agent

Now that you have logged in, lets create your first AI agent, a simple agent called `hello-ai`:

```bash
nearai agent create --name hello-ai --description "My First AI Agent"

# Example Response:
# Agent created at: /Users/user/.nearai/registry/<your-account.near>/hello-ai/0.0.1
```

This will create a local folder with the agent's metadata and a python file. The metadata file describes the agent, and the python file is where you will write the agent's logic.

Before we dive into the code, let's run the agent!

```bash
nearai agent interactive ~/.nearai/registry/<your-account.near>/hello-ai/0.0.1 --local
```

An interactive session will start, where you can chat with your agent... talk to it for a while and use `exit` when you are ready to continue.

---

## The Agent

The agent is defined by two files, both located at `~/.nearai/registry/<your-account.near>/hello-ai/0.0.1`: 

1. `metadata.json`: Contains information about your agent, including its underlying model
2. `agent.py`: This is the code that executes each time your agent receives a prompt

By default, the agent takes the role of a "helpful assistant", which receives the user input and responds to it using the [Llama 3.1 70B Instruct](https://huggingface.co/meta-llama/Llama-3.1-70B-Instruct) (as defined in the default metadata).

```python title="agent.py"
from nearai.agents.environment import Environment

def run(env: Environment):
    # A system message guides an agent to solve specific tasks.
    prompt = {"role": "system", "content": "You are a travel agent that helps users plan trips."}

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
    You can change the model used by the agent by modifying the `metadata.json` file, check all the available models in the [NearAI Hub](https://app.near.ai/models).

---

## The Environment

Agents have access to a local message history through the Environment, which they receive as input on the `run` function. We will cover the Environment API in more detail later, but for now it's important to remark that agents can actively store messages there using the [`env.add_reply()`](api.md#nearai.agents.environment.Environment.add_message) function. 

By default, the history is stored in the `chat.txt` file, in the local agent directory.

Besides this, while an agent is operating, its creates a temporary file named `.next_agent`, which stores the role of the next participant expected in the dialogue (either `user` or `agent`) during the next iteration of the loop. The agent can control this value using [`env.set_next_actor()`](api.md#nearai.agents.environment.Environment.set_next_actor).

Agents can also use local imports from the home folder or its subfolders, which will be executed within a temporary folder, and in a temporary environment.

---

## Next Steps

Congratulations! You have created your first agent on Near AI. As a next step, we will learn how to deploy your agent in the NEAR AI Hub, and how you can download and run agents created by other users.