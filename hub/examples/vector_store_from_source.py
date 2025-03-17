import openai
import json
import time
import nearai
import requests

# Load NEAR AI Hub configuration
config = nearai.config.load_config_file()
base_url = config.get("api_url", "https://api.near.ai/") + "v1"
auth = config["auth"]

client = openai.OpenAI(base_url=base_url, api_key=json.dumps(auth))

# Create a vector store from GitHub source
github_source = {
    "type": "github",
    "owner": "near",
    "repo": "core-contracts",
    "branch": "master"
}

create_request = {
    "name": "near_core_contracts_vector_store",
    "source": github_source,
    "source_auth": None,  # Add GitHub token here if the repo is private
    "metadata": {"description": "Vector store for NEAR Core Contracts"}
}

# Use requests to create the vector store from source
response = requests.post(
    f"{base_url}/vector_stores/from_source",
    json=create_request,
    headers={"Authorization": f"Bearer {json.dumps(auth)}"}
)
response.raise_for_status()
vs = response.json()
print(f"Vector store creation initiated: {vs}")

# Poll the vector store status until processing is complete
print("Polling vector store status...")
while True:
    status = client.vector_stores.retrieve(vs['id'])
    if status.file_counts.completed == status.file_counts.total:
        print("All files processed. Vector store is ready.")
        break
    print(f"Files processed: {status.file_counts.completed}/{status.file_counts.total}. Waiting...")
    time.sleep(5)

# Perform a search query
search_query = "What is the purpose of the fungible token contract?"
search_response = client.post(
    path=f"{base_url}/vector_stores/{vs['id']}/search",
    body={"query": search_query},
    cast_to=dict
)


print(f"Search results for '{search_query}':")
print(f"- {search_response}")

# Retrieve the vector store details
retrieved_store = client.vector_stores.retrieve(vs['id'])
print(f"\nVector store details:")
print(f"- Name: {retrieved_store.name}")
print(f"- Total files: {retrieved_store.file_counts.total}")
print(f"- Usage bytes: {retrieved_store.usage_bytes}")

# Clean up: Delete the vector store
res = client.vector_stores.delete(vs['id'])
print(f"\nVector store deleted: {res}")
