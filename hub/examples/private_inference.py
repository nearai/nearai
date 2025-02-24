
import openai
import json
import nearai
import httpx
from attestation.client import CvmClient

private_inference_url = "http://cvm.near.ai:8000/v1"

http_client = httpx.Client(verify=False, timeout=300.0)
client = openai.OpenAI(base_url=private_inference_url, api_key="PHALA@2025", http_client=http_client)

chat_completion = client.chat.completions.create(
    model="meta-llama/meta-llama-3.1-8b-instruct",
    messages=[{"role": "user", "content": "Hello, world!"}],
    stream=False,
    max_tokens=256,
    stop=["<|eot_id|>", "<|start_header_id|>"]  # Add stop sequences
)

print(chat_completion)