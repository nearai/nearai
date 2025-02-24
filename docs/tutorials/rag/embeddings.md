# Manual Embeddings

In the previous section we talked about chunking, and how it can help the model to better understand the document as a whole.

However, current chunking strategies are very limited, dividing the document into chunks of fixed size with a fixed overlap, without considering the document's structure.

If you know that your documents have a specific structure, you can create your own embeddings by manually dividing the document into chunks and processing them separately.

!!! warning
    As with chunking, there are high chances that you do NOT need to create your own embeddings. We recommend to read this section only to gain understanding on how vector stores are implemented.

---

### Manual Embeddings

Instead of using a vector store, you can directly call the [Nomic v1.5 model](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5) so it creates the embedding vector for our documents:

**Example:**

```python
import json
import os
import re

from glob import glob
from urllib.parse import urlparse

import openai
import pandas as pd
import requests
import nearai

# Load NEAR AI Hub configuration
config = nearai.config.load_config_file()
base_url = config.get("api_url", "https://api.near.ai/") + "v1"
auth = config["auth"]

client = openai.OpenAI(base_url=base_url, api_key=json.dumps(auth))

# Create embeddings for all files
embeddings_model = "fireworks::nomic-ai/nomic-embed-text-v1.5"
prefix = "classification: "

docs = []
md_files = list(glob("./**/*.md", recursive=True))

for file_path in md_files:
    print(f"Processing {file_path}")

    with open(file_path, 'r') as file:
        docs.append(f"{prefix}{file.read()}")

embeddings = client.embeddings.create(
    input=docs,
    model=embeddings_model
)

df = pd.DataFrame.from_dict({
    "docs": docs,
    "embeddings": [e.embedding for e in embeddings.data]
})

df.to_csv("embeddings.csv", index=False)
```

Notice that we are manually storing the embeddings into a `CSV` file. This is because the platform does not support uploading embeddings directly into a vector store.

!!! tip Prefix
    The [Nomic v1.5 model](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5) uses `prefixes` (e.g. `classification:`, `search-document:`) to better guide the model on how to transform the documents. Make sure to read your model's documentation before using it to make the most of the embeddings

---

### Using Manual Embeddings

After creating the embeddings, you will need to emulate the vector store's behavior by querying the embeddings and selecting the most relevant documents.

**Example:**

```python
import json

import openai
import nearai
import numpy as np
import pandas as pd
from nearai.agents.environment import Environment

# Load NEAR AI Hub configuration
config = nearai.config.load_config_file()
base_url = config.get("api_url", "https://api.near.ai/") + "v1"
auth = config["auth"]

client = openai.OpenAI(base_url=base_url, api_key=json.dumps(auth))

MODEL = "llama-v3p3-70b-instruct"

df = pd.read_csv('./embeddings.csv')
EMBEDDING_MODEL = "fireworks::nomic-ai/nomic-embed-text-v1.5"
PREFIX = "classification: "


def cosine_similarity(a, b):
    a = np.matrix(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def run(env: Environment):
    user_query = env.list_messages()[-1]["content"]

    embedding = client.embeddings.create(
                input=[f"{PREFIX}{user_query}"],
                model=EMBEDDING_MODEL,
            ).data[0].embedding

    df['similarities'] = df.embeddings.apply(
        lambda x: cosine_similarity(x, embedding)
    )

    res = df.sort_values('similarities', ascending=False).head(6)

    prompt = [
        {
            "role": "user query",
            "content": user_query,
        },
        {
            "role": "documentation",
            "content": json.dumps(res.docs.tolist()),
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

In the code above, we transform the user's query into a vector embedding using the same model that created our documentation embeddings. 

The system then calculates the cosine similarity between the query embedding and all stored document embeddings to find the most relevant matches.

Finally, we rank the documents by their similarity scores and select the 6 most relevant chunks to provide context for the model's response.