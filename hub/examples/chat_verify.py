import openai
import json
import nearai
import httpx
from attestation.client import CvmClient

hub_url = "https://cvm.near.ai/v1"

cvm_client = CvmClient(url=hub_url)
resp = cvm_client.attest()

print(resp)

# Login to NEAR AI Hub using nearai CLI.
# Read the auth object from ~/.nearai/config.json
auth = nearai.config.load_config_file()["auth"]
signature = json.dumps(auth)

print(signature)

# Configure HTTP client to accept untrusted certificates
http_client = httpx.Client(verify=False)
client = openai.OpenAI(base_url=hub_url, api_key=signature, http_client=http_client)

# list models available from NEAR AI Hub
models = client.models.list()
print(models)

# create a chat completion
chat_completion = client.chat.completions.create(
    model="fireworks::accounts/fireworks/models/deepseek-v3",
    messages=[{"role": "user", "content": "Hello, world!"}],
)
print(chat_completion)