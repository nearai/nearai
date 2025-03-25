import chardet # type: ignore
import json
import openai
import os
import tempfile
import time
from typing import Any, Dict, List

from nearai.shared.client_config import ClientConfig
from nearai.shared.inference_client import InferenceClient
from nearai.config import Config, load_config_file

# BUILD VECTOR STORE FROM FILES + USE IT FOR LLM RESPONSE

# Load NEAR AI Hub configuration
CONFIG = Config()
# Update config from global config file
config_data = load_config_file(local=False)
CONFIG = CONFIG.update_with(config_data)
if CONFIG.api_url is None:
    raise ValueError("CONFIG.api_url is None")

base_url = CONFIG.api_url + "/v1"
client_config = ClientConfig(base_url=base_url, auth=CONFIG.auth)

client = openai.OpenAI(base_url=base_url, api_key=json.dumps(config_data["auth"]))

vs_id = None
# Specify existing vector store id to skip files uploading
# vs_id = "vs_df7438fde61241349439f747"

# Upload and attach add files to the vector store, skip existing vector-store doc file
md_files = [
    os.path.join(root, file)
    for root, _, files in os.walk(os.path.abspath("../../docs"))
    for file in files
    if file.endswith(".md") and os.path.basename(file) != "vector-store.md"
]
# Upload python examples
py_files = [
    os.path.join(os.getcwd(), file)
    for file in ["vector_store.py", "vector_store_from_source.py", "vector_store_build_doc.py"]
]

all_files = md_files + py_files


def detect_encoding(file_path):
    with open(file_path, "rb") as f:
        result = chardet.detect(f.read())
        return result["encoding"]


def convert_to_utf8(file_path, temp_dir):
    try:
        encoding = detect_encoding(file_path)
        if not encoding:
            raise ValueError("Wrong encoding")

        with open(file_path, "rb") as f:
            content = f.read()

        text = content.decode(encoding)
        utf8_content = text.encode("utf-8")

        temp_file_path = os.path.join(temp_dir, os.path.basename(file_path))
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(utf8_content)

        return temp_file_path

    except Exception as e:
        print(f"Error with {file_path}: {e}")
        return None


if vs_id is None:
    # Create a vector store for vector store docs
    vs = client.vector_stores.create(name="vector_store_docs")
    print(f"Vector store created: {vs}")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_files = []

        for file_path in all_files:
            temp_file_path = convert_to_utf8(file_path, temp_dir)
            if temp_file_path:
                temp_files.append(temp_file_path)

                print(f"Processing {os.path.basename(temp_file_path)}")
                uploaded_file = client.files.create(
                    file=open(temp_file_path, "rb"),
                    purpose="assistants",
                )
                attached_file = client.vector_stores.files.create(
                    vector_store_id=vs.id,
                    file_id=uploaded_file.id,
                )
                print(f"File uploaded and attached: {uploaded_file.filename}")

    # Poll the vector store status until processing is complete
    print("Polling vector store status...")
    while True:
        status = client.vector_stores.retrieve(vs.id)
        if status.file_counts.completed == len(all_files):
            print("All files processed. Proceeding with search query.")
            break
        print(f"Files processed: {status.file_counts.completed}/{len(all_files)}. Waiting...")
        time.sleep(1)

    vs_id = vs.id


def process_vector_results(results) -> List[Dict[str, Any]]:
    flattened_results = [item for sublist in results for item in sublist]
    # print("flattened_results", flattened_results)
    return flattened_results[:20]


def generate_llm_response(messages, processed_results):
    system_prompt = """
    You're an AI assistant that writes technical documentation. You can search a vector store for information relevant
    to the user's query.
    Use the provided vector store results to inform your response, but don't mention the vector store directly.
    """

    model = "qwen2p5-72b-instruct"

    vs_results = "\n=========\n".join(
        [f"{result.get('chunk_text', 'No text available')}" for result in processed_results]
    )
    messages = [
        {"role": "system", "content": system_prompt},
        *messages,
        {
            "role": "system",
            "content": f"User query: {messages[-1]['content']}\n\nRelevant information:\n{vs_results}",
        },
    ]
    return inference.completions(model=model, messages=messages, max_tokens=16000)


# Retrieve the vector store details
retrieved_store = client.vector_stores.retrieve(vs_id)
print(f"Vector Store details: {retrieved_store}")

# Let's run a LLM completions using vector store we just created
search_query = """Create markdown documentation for the new NEAR AI feature: Vector Stores. Provide a general
explanation of what Vector Stores are and how they function.
- Explain how to create a Vector Store, including uploading files, retrieving them, and deleting them.
- Describe how to search within the Vector Store.
- Explain how to obtain LLM responses using the Vector Store.

Always include Python examples with comments. Ensure that all necessary functions used in the examples are included.
Please generalize the examples."""

inference = InferenceClient(client_config)
vector_results = inference.query_vector_store(vs_id, search_query)
processed_results = process_vector_results([vector_results])
# Create chat history for LLM
messages = [{"role": "user", "content": search_query}]
llm_response = generate_llm_response(messages, processed_results)
response_message = llm_response["choices"][0]["message"]["content"]

print(response_message)

# with open("doc.md", 'w') as file:
#     file.write(response_message)
