import openai
import json
import logging
from nearai.config import load_config_file

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define the base URL for the API
hub_url = "http://localhost:8000/v1"

logger.info("Starting the streaming agent execution process")

# Load authentication data from the configuration file
auth = load_config_file()["auth"]
signature = json.dumps(auth)

logger.info("Authenticated with NEAR AI Hub")

# Initialize the OpenAI client with the base URL and API key
client = openai.OpenAI(base_url=hub_url, api_key=signature)

# Create a new thread
logger.info("Creating a new thread")
thread = client.beta.threads.create()
logger.info(f"Thread created with ID: {thread.id}")

## Create a streaming run
logger.info("Creating a streaming run")
run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id="streaming.near/helloworldstreaming/0.0.1",
    instructions="Please provide a helpful response.",
    model="fireworks::llama-v3p1-70b-instruct",
    stream=True
)

# Process the event stream
logger.info("Processing the event stream")
run_id = ""
for event in run:
    if event.event == "thread.run.queued":
        logger.info("Run queued")
    elif event.event == "thread.run.created":
        logger.info("Run started")
        run_id = event.data.id
    elif event.event == "thread.run.in_progress":
        logger.info("Run in progress")
    elif event.event == "thread.run.requires_action":
        logger.info("Run requires action")
    elif event.event == "thread.run.completed":
        logger.info("Run completed")
    elif event.event == "thread.run.failed":
        logger.info("Run failed")
    elif event.event == "thread.run.cancelled":
        logger.info("Run cancelled")
    elif event.event == "thread.run.expired":
        logger.info("Run expired")
    elif event.event == "thread.message.delta":
        content = event.data.delta.content
        if content and len(content) > 0 and hasattr(content[0], 'text') and content[0].text is not None:
            delta = content[0].text.value
            logger.info(f"Streamed content: {delta}", extra={'no_newline': True})
    elif event.event == "done":
        logger.info("Streaming finished")
    else:
        logger.info(f"Event: {event.event}")

# Retrieve the run details after streaming is complete
logger.info("Retrieving the run details")
run_details = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run_id)
logger.info(f"Run details: {run_details}")

logger.info("Streaming agent execution process completed")
