import openai
import json
import nearai
import time
from hub.api.v1.vector_stores import AddUserMemoryResponse
# Load NEAR AI Hub configuration
config = nearai.config.load_config_file()
base_url = config.get("api_url", "https://api.near.ai/") + "v1"
auth = config["auth"]

client = openai.OpenAI(base_url=base_url, api_key=json.dumps(auth))

# Add some memories
memories = [
    "I live in San Francisco!",
    "My favorite color is blue",
    "I have a black cat named Luna",
    "I enjoy hiking on weekends"
]
files_ids = []

print("Adding memories...")
for memory in memories:
    result = client.post(
        path=f"{base_url}/vector_stores/memory",
        body={"memory": memory},
        cast_to=AddUserMemoryResponse
    )
    files_ids.append(result.memory_id)
    print(f"Added memory: {memory}")
    print(f"Response: {result}")
    time.sleep(1)  # Small delay between additions

# Now let's query our memories
search_queries = [
    "Where do I live?",
    "What color do I like?",
    "Tell me about my pet",
    "What are my hobbies?"
]

print("\nQuerying memories...")
for query in search_queries:
    search_response = client.post(
        path=f"{base_url}/vector_stores/memory/query",
        body={"query": query},
        cast_to=dict
    )
    print(f"\nQuery: {query}")
    print(f"Relevant memories: {search_response}")
    time.sleep(1)  # Small delay between queries

print(f"Files ids: {files_ids}")

# delete memories
for file_id in files_ids:
    client.files.delete(file_id)

time.sleep(10)

# query memories again
for query in search_queries:
    search_response = client.post(
        path=f"{base_url}/vector_stores/memory/query",
        body={"query": query},
        cast_to=dict
    )
    print(f"\nQuery: {query}")
    print(f"Relevant memories: {search_response}")
    time.sleep(1)  # Small delay between queries