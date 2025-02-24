import openai
import json
import nearai
import httpx
from attestation.client import CvmClient
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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


# Create a new thread
logger.info("Creating a new thread")
thread = client.beta.threads.create()
logger.info(f"Thread created with ID: {thread.id}")

# Add a message to the thread
logger.info("Adding a message to the thread")
message = client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="Lava"
)

messages = client.beta.threads.messages.list(thread.id)
logger.info(f"Messages in thread: {messages}")

# Schedule a run
logger.info("Scheduling a run")
run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id="zavodil.near/what-beats-rock/0.19",
)

logger.info(f"Run scheduled with ID: {run.id}")

# Get the run status
logger.info("Getting run status")
run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
logger.info(f"Run status: {run_status}")

# Wait for the run to complete
logger.info("Waiting for the run to complete")
while run.status != "completed":
    time.sleep(5)
    run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
    logger.info(f"Current run status: {run.status}")

logger.info("Run completed")

# Retrieve the assistant's response
logger.info("Retrieving the assistant's response")
messages = client.beta.threads.messages.list(thread_id=thread.id)
logger.info(f"Messages in thread: {messages}")


logger.info("Agent execution process completed")
