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

#
result = client.completions.create(
    prompt="write a short story about penguins",
    model="hyperbolic::meta-llama/Llama-3.3-70B-Instruct",
    stream=True,
    temperature=0
)

for event in result:
    print(event, flush=True)

logger.info("Streaming completion process completed")
