import openai
import json
import os
import nearai

hub_url = "https://api.near.ai/v1"

# Login to NEAR AI Hub using nearai CLI.
# Read the auth object from ~/.nearai/config.json
auth = nearai.config.load_config_file()["auth"]
signature = json.dumps(auth)

client = openai.OpenAI(base_url=hub_url, api_key=signature)

# list models available from NEAR AI Hub
models = client.models.list()
print(models)

# create a chat completion
chat_completion = client.chat.completions.create(
    model="fireworks::accounts/fireworks/models/qwen2p5-72b-instruct",
    messages=[{"role": "user", "content": "Hello, world!"}],
)
print(chat_completion)