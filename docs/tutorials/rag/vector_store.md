# Vector Stores

Vector Stores are a special kind of database that allows you to store and query documents based on their numerical representation. This is particularly useful when you have a large number of documents and you want to find the most relevant ones to answer a given query.

---

## How Vector Stores Work

Vector Stores by using a mathematical model to convert documents into numerical representations in a low-dimensional space. This is done by using a technique called Vectorial Representations.

![alt text](vector-space.png)

Ideally, documents and queries that are semantically similar will have similar numerical representation. Meaning that, the documents that are closer to the query in the vector space are the most relevant to answer it.

Exactly how these representations are generated is a complex topic, which exceeds the scope of this tutorial. For us, it suffices to know that these models already exist and are readily available to be used.

---

## Creating a Vector Store

Creating a vector store in NEAR AI consist in 2 main steps:

- Uploading the files to the NEAR AI platform
- Creating a Vector Store by providing one or multiple files IDs

Let's create a vector store using the official documentation, which consists of a set of markdown files.

!!! tip
    You can find the dataset and code used in this tutorial in the [vector store example](https://github.com/gagdiez/docs-ai/tree/main/docs-gpt/dataset) repository

Since NEAR AI implements an API compatible with that of OpenAI, we can use the `client` object from the `openai` library to upload the files and create the vector store.

It is important to remark that the files are being uploaded to the NEAR AI platform, and not to OpenAI.


```python
import json
from glob import glob

import openai
import nearai

# Load NEAR AI Hub configuration
config = nearai.config.load_config_file()
base_url = config.get("api_url", "https://api.near.ai/") + "v1"
auth = config["auth"]

client = openai.OpenAI(base_url=base_url, api_key=json.dumps(auth))

# Create a vector store for vector store docs
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

vs = client.beta.vector_stores.create(
    name="docs-vector-store-chunks",
    file_ids=file_ids,
    # chunking_strategy={
    #     "chunk_overlap_tokens": 400,
    #     "max_chunk_size_tokens": 800
    # }
)

print(vs.id)
```

Notice that the script simply uploads the files to NEAR AI, and after uses the `ids` of all uploads to create a vector store by calling the `client.beta.vector_stores.create` method.

All the complexity of processing the uploaded files to create their embeddings is handled by the platform.

After running the script, you will get the `id` of the vector store that was created. This `id` will be used in the next section to build an agent that leverages the knowledge contained on it.

??? note "Chunking Strategy"
    In the code above we have commented the `chunking_strategy` parameter, which allows you to specify how the documents are "split" into chunks before being processed by the model.

    Do not worry about this parameter for now, we will come back to it later in this tutorial.