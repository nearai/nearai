# Manual Embeddings

In the previous section we talked about chunking, and how it can help the model to better understand the document as a whole.

However, current chunking strategies are very limited, dividing the document into chunks of fixed size with a fixed overlap, without considering the document's structure.

If you know that your documents have a specific structure, you can create your own embeddings by manually dividing the document into chunks and processing them separately.

---

### Manual Embeddings

In the case of our NEAR documentation, we know that each file is divided into sections - denoted by `##` in markdown - and subsections - denoted by `###`.

We can use this information to manually divide the document into chunks, and process them separately.

```python
# BUILD VECTOR STORE FROM FILES
import json
import os
import re

from glob import glob
from urllib.parse import urlparse

import openai
import pandas as pd
import requests
import nearai


def replace_github_with_code(content: str) -> str:
    githubs = re.findall(r"<Github\s[^>]*?/>", content)
    formatted = content
    for gh in githubs:
        gh = gh.replace("'", '"')
        url = re.search(r'url="(.*?)"', gh).group(1)

        (url, *_) = url.split("#")
        (org, repo, _, branch, *pathSeg) = urlparse(url).path[1:].split("/")
        pathSeg = "/".join(pathSeg)
        raw_url = f"https://raw.githubusercontent.com/{org}/{repo}/{branch}/{pathSeg}"
        res = requests.get(raw_url)
        code = res.text

        # cut based on the line numbers
        start = re.search(r'start="(\d*)"', gh)
        end = re.search(r'end="(\d*)"', gh)

        start = max(int(start.group(1)) - 1, 0) if start else 0
        end = int(end.group(1)) + 1 if end else len(code.split("\n"))
        code = "\n".join(code.split("\n")[start:end])

        formatted = formatted.replace(gh, f"```\n{code}\n```")

    return formatted


def clean_content(content: str) -> str:
    # remove all `import ...`
    content = re.sub(r"import .*?\n", "", content)

    # Markdown has metadata at the beginning that we don't need
    groups = content.split("---")
    content = content.replace(groups[1], "").replace("------\n\n", "")

    # Load all the code blocks from Github
    content = replace_github_with_code(content)

    # Temporarily replace code blocks with placeholders
    code_blocks = re.findall(r'```.*?```', content, re.DOTALL)
    placeholders = [f"__CODE_BLOCK_{i}__" for i in range(len(code_blocks))]

    for i, block in enumerate(code_blocks):
        content = content.replace(block, placeholders[i])

    # remove HTML tags leaving only the text
    content = re.sub(r'<iframe.*?</iframe>', '', content, flags=re.DOTALL)
    content = re.sub(r'<.*?>', '', content)

    # remove ' from the summary, so Let's becomes Lets
    content = re.sub(r'\'(.)', r'\1', content)

    # Encode the summary to avoid issues with the API
    try:
        content = content.encode().decode('unicode_escape')
    except UnicodeDecodeError:
        pass

    return content


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
        content = file.read()
        processed_doc = clean_content(content)

        docs.append(f"{prefix}{processed_doc}")

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

---

### Using Manual Embeddings

After creating the embeddings, we will need to emulate the vector store's behavior by querying the embeddings and selecting the most relevant documents.

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

In the code above, we are transforming the user's query into an embedding using the model we used to create the embeddings.

After that, we manually calculate the cosine similarity between the user's query and all the embeddings we created.

Finally, we sort the documents by similarity and send the 6 most relevant documents to the model.