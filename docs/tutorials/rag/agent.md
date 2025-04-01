Let's see how simple it is to create an agent that leverages the vector store we [created in the previous section](./vector_store.md). This agent will demonstrate how to effectively use RAG (Retrieval-Augmented Generation) to provide accurate answers based on NEAR's documentation.

---

!!!tip
    You can try out a live demo of this agent by signing in with your NEAR account below!

<iframe src="https://app.near.ai/embed/near-ai-dev.near/near-protocol-docs-agent/latest?theme=light" class="agent-iframe" sandbox="allow-scripts allow-popups allow-same-origin allow-forms"></iframe>

---

## Documentation Agent

In the previous section, we created a vector store and obtained its unique `id`. This `id` is a crucial piece that allows us to reference and interact with our stored embeddings. We'll now use this `id` within our agent to:

1. Retrieve the vector store from storage
2. Query it for relevant information based on user input
3. Use the retrieved context to generate more informed responses

The vector store `id` acts as a persistent identifier, enabling our agent to access the same knowledge base across multiple sessions or interactions.

Let's update your `agent.py` file to include the vector store `id` and the RAG logic:

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

In the code above, we extract the user's question from the environment's message history and use it as a semantic search query against our vector store. This allows us to find the most relevant document chunks based on their embedding similarity to the query.

```python
vector_results = env.query_vector_store(VECTOR_STORE_ID, user_query)
```

The vector store returns a list of documents ranked by relevance to the user's query. To maintain efficiency and focus, we limit our context to the 6 most relevant document chunks:

```python
docs = [{"file": res["chunk_text"]} for res in vector_results[:6]]
```

We then construct a structured prompt with three key components:

1. The user's original query
2. The relevant documentation chunks
3. A system message that guides the model's response behavior

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

This prompt structure ensures that the model has both the necessary context from our documentation and clear instructions on how to use it. We then pass this prompt to `env.completion()` to generate a response that accurately addresses the user's question based on our documentation.

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

Let's compare the results with our previous attempts. Without the vector store, the agent was prone to hallucination - generating plausible but incorrect responses. Now, the answers are both correct and complete grounded in the actual documentation - meaning that the agent was able to retrieve the right answers from the vector store.

More impressively, the vector store was able to correctly pick up the relevant documents from the more than than 100 files that compose the official NEAR documentation.

