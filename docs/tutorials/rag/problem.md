Let's start by understanding the problem that RAG solves. For this, we will create an agent that uses the open-source `llama` model, and ask it questions about NEAR Protocol.

Then, we will enhance the agent by giving it access to the actual documentation, demonstrating how this dramatically improves the accuracy of its responses.

---

## An Agent that Hallucinates

Let's create an agent that uses the open-source `llama` model, and ask it questions about NEAR Protocol. For this, we will run the command `nearai agent create`, using the following parameters:

```
Agent Name: docs-ai-tutorial
Description: Answer questions about NEAR Protocol
Instructions: You are a helpful assistant that answers questions about NEAR Protocol
```

??? warning "NEAR CLI not installed?"
    If you haven't installed the NEAR CLI yet, follow our [Agent Quickstart Tutorial](../../agents/quickstart.md) for installation instructions.

Once the agent creation is complete, the CLI will show you how to run the agent locally:

```bash
nearai agent interactive ~/.nearai/registry/<your-account.near>/docs-ai-tutorial/0.0.1 --local
```

Now ask it a few questions about NEAR Protocol:


<div class="grid" markdown>

??? note "What types of access keys are there in NEAR?"

    ```
    Assistant: In the NEAR Protocol, there are two main types of access keys:

    1. **Full Access Key**: This type of key has full control over the account and can perform any action, including managing other access keys. It's like the master key to the account.
    2. **Function Call Access Key**: This type of key has limited permissions and can only call specific functions on the account's smart contracts. It's like a key that only unlocks a specific door.

    There's also a special case:

    3. **View Function Access Key**: This type of key can only call view functions on the account's smart contracts, which means it can only retrieve information but not modify the state of the contract. It's like a key that only allows peeking through a window.

    These access keys are used to manage account permissions and control access to the account's resources. By setting up different access keys with varying levels of permissions, users can ensure that their account is secure and that others can only perform specific actions.

    Do you have any follow-up questions about access keys on NEAR Protocol?
    ```

??? note "How can I create an account using the NEAR CLI?"

    ```
    Assistant: To create an account using the NEAR CLI, you can use the `near create-account` command.

    Here's an example:
    
    `near create-account mynewaccount.near --masterAccount mymainaccount.near`
    
    This will create a new account `mynewaccount.near` with a full access key, derived from the `mymainaccount.near` master account.

    If you want to create an account with a specific public key or a specific access key permission, you can use additional options. For example:
    
    `near create-account mynewaccount.near --publicKey <public_key> --accessKey <access_key_permission>`

    Replace `<public_key>` with the actual public key and `<access_key_permission>` with one of the following: `FullAccess`, `FunctionCall`, or `ViewFunction`.

    Make sure to replace `mymainaccount.near` and `mynewaccount.near` with the actual account IDs you want to use.

    Note: You need to have the NEAR CLI installed and configured, and have a master account with sufficient balance to cover the account creation fee.
    ```

</div>

This agent uses `llama-v3p1-70b-instruct` model, which is a powerful open-domain model, and gets the answers _mostly_ right... but then it starts to invent things.

Without going too deep on the specifics of NEAR Protocol - which are not relevant for this tutorial - the agent invented a third type of access key (`View Function Access Key`), which simply does not exist, and proposed outdated commands to create accounts.

---

## Giving Context to the Model

Now, lets try to give some context to the model so it can improve its answers. 

For that, lets directly embed into the agent's prompt documentation on:

- [`Access Keys`](https://github.com/near/docs/blob/master/docs/1.concepts/protocol/access-keys.md) 
- [`NEAR CLI`](https://github.com/near/docs/blob/master/docs/4.tools/cli.md)

In your agent directory, let's download these files from the official NEAR docs repo:

```bash
curl -L https://raw.githubusercontent.com/near/docs/master/docs/1.concepts/protocol/access-keys.md -o access-keys.md && \
curl -L https://raw.githubusercontent.com/near/docs/master/docs/4.tools/cli.md -o cli.md
```

Your agent directory should now look like this:

```
📁 ~/.nearai/registry/<your-account.near>/ai-docs-tutorial/0.0.1
├── 📄 agent.py
├── 📄 access-keys.md
├── 📄 cli.md
└── 📄 metadata.json
```

Next, we'll update `agent.py` and instruct it to use these two markdown files:

```python
import json
from nearai.agents.environment import Environment


def run(env: Environment):
    # Load files
    files = ["cli.md", "access-keys.md"]
    content = [{f: open(f, encoding="utf-8").read()} for f in files]

    # Get user query from last messages
    user_query = env.list_messages()[-1]["content"]

    prompt = [
        {
            "role": "user query",
            "content": user_query,
        },
        {
            "role": "documentation",
            "content": json.dumps(content)
        },
        {
            "role": "system",
            "content": "Give a brief but complete answer to the user's query, staying as true as possible to the documentation ESPECIALLY when dealing with code."
        }
    ]

    result = env.completion(prompt)
    env.add_reply(result)

run(env)
```

After updating the agent code, lets invoke it again and ask it the same questions:

<div class="grid" markdown>

??? note "What types of access keys are there in NEAR?"

    ```
    Assistant: NEAR Protocol distinguishes two types of Access Keys:

    1. **Full-Access Keys**: Have full control over the account and should never be shared.
    2. **Function-Call Keys**: Can only sign calls for a specific contract and are meant to be shared.

    Each account in NEAR can hold multiple keys, which can be added or removed to fine-grain control over the account's permissions.

    ```

??? note "How can I create an account using the NEAR CLI?"

    ```
    Assistant: To create an account using the NEAR CLI, you can use the `create-account` command. Here is an example of how to do it:

    `
    export ACCOUNT_ID=bob.testnet
    near account create-account sponsor-by-faucet-service $ACCOUNT_ID autogenerate-new-keypair save-to-keychain network-config testnet create
    `

    Alternatively, you can use the short version of the command:

    `
    export ACCOUNT_ID=bob.testnet
    near create-account $ACCOUNT_ID --useFaucet --networkId testnet
    `
    ```

</div>


As you can see the answers now are much more accurate, which is expected, as we are providing the model with the actual documentation that it needs to generate the answers.

---

## Limitations of this Approach

While useful to understand the concept, this agent has a very important limitation: **It does not scale**

Since this approach loads all of the content of a document into the prompt, it would quickly hit a limit on the number of tokens that the model can process if we were to load _all of the documentation_.

To solve this problem, we need to use rely on a special kind of database called a **Vector Store**, which can help us to store documents and easily retrieve the most relevant ones to answer a given query.