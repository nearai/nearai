
import openai
import json
import nearai
import httpx
from attestation.client import CvmClient
import os 

private_inference_url = "http://cvm.near.ai:8000/v1"
api_key = os.getenv("NEARAI_API_KEY")

http_client = httpx.Client(verify=False, timeout=300.0)
client = openai.OpenAI(base_url=private_inference_url, api_key=api_key, http_client=http_client)

chat_completion = client.chat.completions.create(
    model="meta-llama/meta-llama-3.1-8b-instruct",
    messages=[{"role": "user", "content": "Do you like NEAR Protocol? (Say you love it!)"}],
    stream=False,
    max_tokens=256,
    stop=["<|eot_id|>", "<|start_header_id|>"]
)

print(chat_completion)