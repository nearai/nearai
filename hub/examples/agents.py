import openai
import json
import nearai
import logging
import time
from datetime import datetime, timedelta
from hub.api.v1.thread_routes import ThreadForkResponse

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

hub_url = "http://localhost:8000/v1"

logger.info("Starting the agent execution process")

# Login to NEAR AI Hub using nearai CLI.
# Read the auth object from ~/.nearai/config.json
auth = nearai.config.load_config_file()["auth"]
signature = json.dumps(auth)

logger.info("Authenticated with NEAR AI Hub")

client = openai.OpenAI(base_url=hub_url, api_key=signature)



# Create a new thread
logger.info("Creating a new thread")
thread = client.beta.threads.create()
logger.info(f"Thread created with ID: {thread.id}")

# Add a message to the thread
logger.info("Adding a message to the thread")
message = client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="Hello! Can you help me with planning my trip to Lisbon?"
)

messages = client.beta.threads.messages.list(thread.id)
logger.info(f"Messages in thread: {messages}")

# Schedule a run
logger.info("Scheduling a run")
run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id="badisland7754.near/inter-agents/0.0.1",
    extra_body={"schedule_at": (datetime.now() + timedelta(seconds=10)).isoformat()}
)

logger.info(f"Run scheduled with ID: {run.id}")
logger.info(f"Initial run status: {run.status}")

# get run
run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
logger.info(f"Run retrieved with ID: {run.id}")
logger.info(f"Retrieved run status: {run.status}")


# Execute a run on the assistant
logger.info("Executing a run on the assistant")
run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id="badisland7754.near/inter-agents/0.0.1",
    instructions="Please provide a helpful response.",
    model="fireworks::llama-v3p1-70b-instruct",
    additional_messages=[
        {
            "role": "user",
            "content": "What is the weather in Lisbon?"
        }
    ]
)

logger.info(f"Run created with ID: {run.id}")
logger.info(f"Initial run status: {run.status}")

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


attachments = [a for m in messages if m.attachments for a in m.attachments]
file_ids = [a.file_id for a in attachments]

if file_ids and file_ids[0] is not None:
    file = client.files.retrieve(file_ids[0])
    logger.info(f"File retrieved: {file}")


    content_response = client.files.content(file_ids[0])
    content = content_response.read().decode('utf-8')
    logger.info(f"File content: {content}")
else:
    logger.warning("No valid file IDs found in the attachments.")

threads = client.get(
    path=f"{hub_url}/threads",
    cast_to=dict
)

logger.info(f"Threads: {threads}")

thread_update = client.beta.threads.update(thread_id=thread.id, metadata={"test": "test"})
logger.info(f"Thread updated: {thread_update}")

# Retrieve the thread
retrieved_thread = client.beta.threads.retrieve(thread_id=thread.id)
logger.info(f"Retrieved thread: {retrieved_thread}")

forked_thread = client.post(path=f"{hub_url}/threads/{thread.id}/fork", cast_to=ThreadForkResponse)
logger.info(f"Forked thread: {forked_thread}")


thread_delete = client.beta.threads.delete(thread.id)
logger.info(f"Thread deleted: {thread_delete}")

#messages in forked thread
messages = client.beta.threads.messages.list(forked_thread.id)
logger.info(f"Messages in forked thread: {messages}")
