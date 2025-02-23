Let's see how simple it is to create an agent that leverages the vector store we [created in the previous section](./vector_store.md). This agent will demonstrate how to effectively use RAG (Retrieval-Augmented Generation) to provide accurate answers based on NEAR's documentation.

!!! tip
    Try out this code directly in the [NEAR AI platform](https://app.near.ai/agents/gagdiez.near/docs-gpt/latest/run)

---

## Documentation Agent

The script we created in the previous section was returning us the `id` of the vector store we created. We will use this `id` within the agent to retrieve the store, so we can query it.

```python
import json
from nearai.agents.environment import Environment

MODEL = "llama-v3p3-70b-instruct"
VECTOR_STORE_ID = "vs_cb8d5537f64d4f4aa6cbc95f"


def run(env: Environment):
    user_query = env.list_messages()[-1]["content"]

    # Query the Vector Store
    vector_results = env.query_vector_store(VECTOR_STORE_ID, user_query)
    docs = [{"file": res["chunk_text"]} for res in vector_results[:6]]

    prompt = [
        {
            "role": "user query",
            "content": user_query,
        },
        {
            "role": "documentation",
            "content": json.dumps(docs),
        },
        {
            "role": "system",
            "content": "Give a brief but complete answer to the user's query, staying as true as possible to the documentation SPECIALLY when dealing with code."
        }
    ]

    answer = env.completion(model=MODEL, messages=prompt)
    env.add_reply(answer)


run(env)
```

<hr class="subsection" />

### How it works?

In the code above, we are retrieving the user's query from the list of messages in the environment, and using it to **directly query the vector store**.

```python
vector_results = env.query_vector_store(VECTOR_STORE_ID, user_query)
```

The results is a list of the documents that are the most relevant to answer the user's query. In order to make the model's job easier, we are only sending the 6 most relevant documents to the model.

```python
docs = [{"file": res["chunk_text"]} for res in vector_results[:6]]
```

After, we create a prompt that includes the user's query, the documents, and a system message that instructs the model to generate a response.

```python
prompt = [
    {
        "role": "user query",
        "content": user_query,
    },
    {
        "role": "documentation",
        "content": json.dumps(docs),
    },
    {
        "role": "system",
        "content": "Give a brief but complete answer to the user's query, staying as true as possible to the documentation SPECIALLY when dealing with code."
    }
]
```

Finally, we use the `env.completion` method to generate the response and show it to the user.

```python
answer = env.completion(model=MODEL, messages=prompt)
env.add_reply(answer)
```

---

## Did it work?

Let's try it out! Lets ask the agent the same questions we used when [talking about hallucination](./problem.md):

<div class="grid" markdown>

??? note "What types of access keys are there in NEAR?"
    **Assistant:** There are two types of access keys in NEAR: 

    1. `Full Access` keys: Have full control over an account and should never be shared.
    2. `Function-Call` keys: Can only sign calls for specific contracts, are meant to be shared, and do not allow transferring NEAR tokens. 

    `Function-Call` keys are defined by three attributes: 
    - `receiver_id`: The only contract that the key allows to call.
    - `method_names` (Optional): The contract's methods the key allows to call.
    - `allowance` (Optional): The amount of NEAR allowed to be spent on gas.

??? note "How can I create an account using the NEAR CLI?"
    **Assistant:** To create an account using the NEAR CLI, you can use the following command:

    ```bash
    near account create-account sponsor-by-faucet-service <your-account-id.testnet> autogenerate-new-keypair save-to-keychain network-config testnet create
    ```

    Replace `<your-account-id.testnet>` with the desired name for your account. This will create a new account with a generated key pair and save it to your keychain. 

    Alternatively, you can also create an account using the `near create-account` command with the `--useFaucet` option:

    ```bash
    near create-account <accountId> --useFaucet
    ```
</div>

Lets remember that the agent was hallucinating when asked the same questions without the vector store.

Now, the answers are both correct and complete, which means that the agent was able to retrieve the right answers from the vector store.

More impressively, the vector store was able to correctly pick up the relevant documents from the more than than 100 files that compose the official NEAR documentation.
