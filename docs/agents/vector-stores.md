Vector Stores are special databases that allow retrieving documents with natural language. They are very useful to provide agents with knowledge on which they have not been trained.

Internally, they use AI models to convert text into low-dimensional vectors known as `embeddings`. Similar text will shield similar `embeddings`, allowing us to find relevant documents for a query by comparing the query's `embedding` with the documents' `embeddings` in the store.

This page describes how to **create, upload, query, and manage** a Vector Store in **NEAR AI**, and how to integrate it on agents to generate context-aware responses.

!!! tip
    Read our tutorial on [**Vector Stores**](../tutorials/rag/introduction.md) to discover how you can build an agent that answers questions based on your custom data

---


## 1. Import and Configure

To use Vector Stores we need to import the NEAR AI module, load configuration settings, and initialize an OpenAI-compatible client which we will connect to the NEAR AI endpoint.

```py
import json
from glob import glob

import openai
import nearai

# Load NEAR AI Hub configuration
config = nearai.config.load_config_file()
base_url = config.get("api_url", "https://api.near.ai/") + "v1"
auth = config["auth"]

client = openai.OpenAI(base_url=base_url, api_key=json.dumps(auth))
```

---

## 2. Creating a Vector Store

Assuming you have all the files you want to add to the vector store in a local directory containing your files, you will need to upload them to NEAR AI, and assign them to a Vector Store.

Once assigned, the files will be processed by the NEAR AI platform to automatically generate the embeddings 

```python
# Load all .md files in the current directory
md_files = list(glob("./**/*.md", recursive=True))

file_ids = []
for file_path in md_files:
    print(f"Processing {file_path}")

    with open(file_path, 'r', encoding='utf-8') as file:
        uploaded_file = client.files.create(
            file=(file_path, file.read(), "text/markdown"),
            purpose="assistants"
        )
        file_ids.append(uploaded_file.id)

vs = client.vector_stores.create(
    name="my-vector-store",
    file_ids=file_ids,
    # chunking_strategy={
    #     "chunk_overlap_tokens": 400,
    #     "max_chunk_size_tokens": 800
    # }
)

print(f"Vector store created: {vs.id}")
```

!!! info "Chunking Strategy"

    Before converting documentation into vector embeddings, the NEAR AI platform segments the text into smaller, manageable chunks. The optional `chunking_strategy` parameter allows you to customize this process.

    By default, the platform will split the text into chunks of 800 tokens, with an overlap of 400 tokens. It is important to notice that chunks are not created based on the document's structure, but merely on counting tokens, which can lead to a loss of context. Feel free to adjust these values to better suit your data.

??? note "Processing single files"

    While less efficient for handling multiple files, you can upload and attach single files to the vector store.

    ```python
    # Upload file
    uploaded_file = client.files.create(
        file=(file_path, file.read(), "text/markdown"),
        purpose="assistants"
    )

    # Attach file to the vector store
    client.vector_stores.files.create(
        vector_store_id=vector_store.id,
        file_id=uploaded_file.id,
    )
    ```

---

## 3. Wait for Processing

After you attach files to a vector store they will be processed in the background. You can check the status of the vector store to see if the processing is complete.

```python
while True:
    status = client.vector_stores.retrieve(vector_store.id)
    if status.file_counts.completed == 1:
        break
    time.sleep(1)

print("File processed! The vector store is ready.")
```

---

## 4. Delete a File

You can delete a specific file from the vector store by providing both the store’s and file’s IDs. This operation removes the file and its embeddings, helping to manage and update your stored data.

```python
client.vector_stores.files.delete(
    vector_store_id=vector_store.id,
    file_id=file_id
)
```

---

## 5. Query the Vector Store

When building an agent, you can use the `env.query_vector_store()` function to retrieve documents from the vector store that are relevant to a user query.

```py title="agent.py"
def run(env: Environment):
    user_query = env.list_messages()[-1]["content"]

    # Query the Vector Store
    vector_results = env.query_vector_store(VECTOR_STORE_ID, user_query)

run(env)
```

!!! tip "Agent Example"
    Check our [Docs AI Agent](https://app.near.ai/agents/gagdiez.near/docs-gpt/latest/source) that uses a vector store to provide context-aware responses on NEAR Protocol documentation


??? note "Query Vector Store Result"

    The method returns a list of objects, each containing a `file_id`, `chunk_text`, and `distance` (similarity score), for example:

    ```python
    [
        {
          'file_id': 'file_278138cf53a245558766c31d',
          'chunk_text': 'nMachine learning and data mining often employ the same methods and overlap significantly ...',
          'distance': 0.6951444615680473
        },
        ...
    ]
    ```

---

## 6. Generate an LLM Response with Context

We can use the retrieved documents to provide a context for the AI model that generates the response.

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

Note that we are embedding the retrieved documents directly into the model's prompt, so the AI can use them to generate a more context-aware response. Furthermore, notice that we are not using all the documents retrieved, but only the first six, to reduce the amount of tokens in the prompt, and filter out less relevant documents.