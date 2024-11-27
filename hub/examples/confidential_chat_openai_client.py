import openai
import json
import os
import nearai

hub_url = "https://inference-api.phala.network/v1"

# Login to NEAR AI Hub using nearai CLI.
# Read the auth object from ~/.nearai/config.json
auth = nearai.config.load_config_file()["auth"]
signature = json.dumps(auth)

client = openai.OpenAI(base_url=hub_url, api_key=signature)


# create a chat completion
chat_completion = client.chat.completions.create(
    model="meta-llama/meta-llama-3.1-8b-instruct",
    messages=[{"role": "user", "content": "Hello, world!"}],
)
print(chat_completion)
