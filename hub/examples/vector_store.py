import openai
import json
import os
import nearai
import time

# Load NEAR AI Hub configuration
config = nearai.config.load_config_file()
base_url = config.get("api_url", "https://api.near.ai/") + "v1"
auth = config["auth"]

client = openai.OpenAI(base_url=base_url, api_key=json.dumps(auth))

# Create a vector store for recipes
vs = client.vector_stores.create(name="recipe_vector_store")
print(f"Recipe vector store created: {vs}")

# Upload and attach recipe files to the vector store
recipe_dir = "vector_store_data"
for file in os.listdir(recipe_dir):
    uploaded_file = client.files.create(
        file=open(os.path.join(recipe_dir, file), "rb"),
        purpose="assistants",
    )
    attached_file = client.vector_stores.files.create(
        vector_store_id=vs.id,
        file_id=uploaded_file.id,
    )
    print(f"Recipe file uploaded and attached: {uploaded_file.filename}")

# Poll the vector store status until processing is complete
print("Polling vector store status...")
while True:
    status = client.vector_stores.retrieve(vs.id)
    if status.file_counts.completed == len(os.listdir(recipe_dir)):
        print("All files processed. Proceeding with search query.")
        break
    print(f"Files processed: {status.file_counts.completed}/{len(os.listdir(recipe_dir))}. Waiting...")
    time.sleep(1)

# Perform a search query
search_query = "How to make an orange vegetable cake?"
search_response = client.post(
    path=f"{base_url}/vector_stores/{vs.id}/search",
    body={"query": search_query},
    cast_to=dict
)

print(f"Search results for '{search_query}':")
print(f"- {search_response}")

# Retrieve the vector store details
retrieved_store = client.vector_stores.retrieve(vs.id)
print(f"Recipe vector store details:")
print(f"- Details: {retrieved_store}")

res = client.vector_stores.delete(vs.id)
print(f"Recipe vector store deleted: {res}")
