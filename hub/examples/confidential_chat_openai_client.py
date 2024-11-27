import openai
import json
import os
import nearai
import requests

hub_url = "https://inference-api.phala.network/v1"

# Login to NEAR AI Hub using nearai CLI.
# Read the auth object from ~/.nearai/config.json
auth = nearai.config.load_config_file()["auth"]
signature = json.dumps(auth)

client = openai.OpenAI(base_url=hub_url, api_key=signature)


# Create a chat completion
chat_completion = client.chat.completions.create(
    model="meta-llama/meta-llama-3.1-8b-instruct",
    messages=[{"role": "user", "content": "Hello, world!"}],
)
print(chat_completion)


# Get Attestation & Public Key
response = requests.get(f"{hub_url}/attestation/report")
attestation_report = response.json()
print("Attestation report:", attestation_report)

# Verify the Attestation
# The verify procedures can be found in following link:
# https://docs.phala.network/confidential-ai-inference/confidential-ai-api#verify-the-attestation
