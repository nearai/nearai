After you have [created a vector store](./creating.md), you can use it to build an agent that leverages the knowledge contained on it.

!!! tip
    You can test the code below in the [NEAR AI platform](https://app.near.ai/agents/gagdiez.near/docs-gpt/latest/run)

---

## Documentation Agent

Let's create an agent that uses the vector store we created in the previous section to answer questions about NEAR Protocol tools.

The script we created in the previous section was returning us the `id` of the vector store we created. We will use this `id` to build the agent.

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

In the code above, we are retrieving the user's query from the list of messages in the environment, and using it to **directly query the vector store**.

The results is a list of documents that are the most relevant to answer the user's query. In order to make the model's job easier, we are only sending the 6 most relevant documents to the model.

After, we create a prompt that includes the user's query, the documents, and a system message that instructs the model to generate a response.

Finally, we use the `env.completion` method to generate the response and add it to the environment.