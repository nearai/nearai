import asyncio
import json
import logging
import os
import re
from typing import Any, Set

import httpx
from dotenv import load_dotenv
from nearai.shared.models import RunMode

from hub.api.v1.auth import AuthToken
from hub.api.v1.thread_routes import RunCreateParamsBase, ThreadModel, _create_thread, create_run
from hub.tasks.scheduler import get_async_scheduler

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("naerai-neardata")

logging.getLogger("httpx").setLevel(logging.WARNING)

RESET_BLOCK_ID_ON_START = True

# Base URL for fetching block data
BASE_URL = "https://mainnet.neardata.xyz/v0/block/"

# Path to store the last read blockId
BLOCK_ID_FILE = "last_block_id.txt"

# OPTION TO READ MULTIPLE BLOCKS PER RUN
NUMBER_OF_BLOCKS_TO_READ_IF_NOT_SYNCED = int(os.getenv("NEAR_EVENTS_NUMBER_OF_BLOCKS_TO_READ_PER_RUN", 2))

# Number of blocks to remember for duplicate protection
MAX_HISTORY_SIZE = 100

# Global state for in-memory block tracking
_current_block_id: int = 0
# Track recent blocks to avoid duplicates
_processed_blocks: Set[int] = set()
# Ensures single-threaded execution
processing_lock = asyncio.Lock()


async def async_fetch_json(url: str) -> Any:
    """Fetch JSON data from URL with API key authentication and error handling."""
    headers = {}
    api_key = os.getenv("FASTNEAR_APIKEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, headers=headers, timeout=3)
            response.raise_for_status()
            if response.status_code == 200:
                return response.json()
    except httpx.HTTPStatusError as exc:
        print(f"HTTP error occurred in near_events source: {exc}")
    except httpx.RequestError as exc:
        print(f"Request error occurred in near_events source: {exc}")
    except httpx.TimeoutException as exc:
        print(f"Timeout error occurred in near_events source: {exc}")

    return None


async def get_latest_block_id():
    """Fetch the current blockchain height from network."""
    # DEBUG. This block has the required event
    # return 135350100

    data = await async_fetch_json("https://api.fastnear.com/status")
    if data:
        latest_block_id = data.get("sync_block_height", None)
        if latest_block_id:
            logger.info(f"Starting with the latest block ID: {latest_block_id}")
            return latest_block_id

    return 0


async def initialize_block_state():
    """Initialize state with history tracking."""
    global _current_block_id, _processed_blocks
    try:
        if os.path.exists(BLOCK_ID_FILE):
            with open(BLOCK_ID_FILE, "r") as f:
                data = json.load(f)
                _current_block_id = data["current_block"]
                _processed_blocks = set(data["processed_blocks"][-MAX_HISTORY_SIZE:])
        else:
            _current_block_id = await get_latest_block_id()
            _processed_blocks = set()
    except Exception as e:
        logger.error(f"State initialization failed: {str(e)}")
        _current_block_id = await get_latest_block_id()
        _processed_blocks = set()


# Function to get the last read blockId from a file
async def get_last_block_id():
    if _current_block_id:
        return _current_block_id
    else:
        return await get_latest_block_id()


# Function to save the last blockId to a file
def save_last_block_id(new_block_id: int):
    """Update block ID state in memory and persistent storage."""
    global _current_block_id, _processed_blocks

    if new_block_id <= _current_block_id:
        # logger.warning(f"Ignoring saving of the older block {new_block_id} (current: {_current_block_id})")
        return

    # Add to processed set and maintain size
    _processed_blocks.add(new_block_id)
    while len(_processed_blocks) > MAX_HISTORY_SIZE:
        _processed_blocks.remove(min(_processed_blocks))

    # Update current block to maximum processed
    _current_block_id = max(_processed_blocks)

    # Persist state
    asyncio.create_task(_persist_block_state())


async def _persist_block_state():
    """Save state with history using atomic write."""
    try:
        temp_path = f"{BLOCK_ID_FILE}.tmp"
        with open(temp_path, "w") as f:
            json.dump({"current_block": _current_block_id, "processed_blocks": sorted(_processed_blocks)}, f)

        os.replace(temp_path, BLOCK_ID_FILE)
    except Exception as e:
        logger.error(f"Failed to save block state: {str(e)}")


# Asynchronous function to load a block by its ID
async def load_block(block_id: int, auth_token: AuthToken) -> bool:
    """Process block with duplicate check."""
    if block_id in _processed_blocks:
        logger.debug(f"Block {block_id} already processed")
        return False

    try:
        # Service will keep connection open until block exists
        data = await async_fetch_json(f"{BASE_URL}{block_id}")
        if data and data.get("shards"):
            await process_shards(data["shards"], block_id, auth_token)
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to process block {block_id}: {e}")
        return False


# Function to process shards in the block
async def process_shards(shards, block_id, auth_token):
    for shard in shards:
        if shard.get("receipt_execution_outcomes"):
            for receipt_execution_outcome in shard["receipt_execution_outcomes"]:
                logs = receipt_execution_outcome.get("execution_outcome", {}).get("outcome", {}).get("logs", [])
                for log in logs:
                    # Process each log and extract the event
                    await process_log(log, receipt_execution_outcome, auth_token)


# Function to process the logs in the shard
async def process_log(log, receipt_execution_outcome, auth_token):
    # Regex pattern to match EVENT_JSON data in the log
    regex = r"EVENT_JSON:(.*?)$"
    match = re.search(regex, log)
    if match:
        event = json.loads(match.group(1))
        if event.get("standard") == "nearai" and event.get("data"):
            for data in event["data"]:
                # Check the event type and call the appropriate save_event function

                if event.get("event") == "run_agent":
                    await run_agent(
                        data.get("agent", ""),
                        {
                            "event": event.get("event"),
                            "message": data.get("message", ""),
                            "signer_id": data.get("signer_id", ""),
                            "request_id": data.get("request_id", None),
                            "env_vars": data.get("env_vars", None),
                            "referral_id": data.get("referral_id", ""),
                            "amount": data.get("amount", ""),
                            "receipt_id": receipt_execution_outcome["execution_outcome"]["id"],
                        },
                        auth_token,
                    )


async def run_agent(agent, content, auth_token: AuthToken):
    if not agent or not content:
        return logger.error("Missing data in scheduled call to run_agent")

    # auth_token.on_behalf_of = signer_id

    thread_model = ThreadModel(
        meta_data={
            "agent_ids": f"{agent}",
        },
        tool_resources=None,
        owner_id=auth_token.account_id,
    )

    thread = _create_thread(thread_model, auth=auth_token)

    run_params = RunCreateParamsBase(
        assistant_id=agent,
        # provide model="" to use the agent's model later
        model="",
        instructions=None,
        tools=None,
        metadata=None,
        include=[],
        additional_instructions=None,
        additional_messages=[{"content": json.dumps(content), "role": "user"}],
        max_completion_tokens=None,
        max_prompt_tokens=None,
        parallel_tool_calls=None,
        response_format=None,
        temperature=None,
        tool_choice=None,
        top_p=None,
        truncation_strategy=None,
        stream=False,
        schedule_at=None,
        delegate_execution=False,
        parent_run_id=None,
        run_mode=RunMode.SIMPLE,
    )

    logger.warning(f"Scheduling agent run: {agent}")

    create_run(thread_id=thread.id, run=run_params, auth=auth_token, scheduler=get_async_scheduler())


# Main asynchronous function to process blocks
# async def process_blocks_sequentially(auth_token):
#     # Get the last processed blockId
#     block_id = await get_last_block_id()
#
#     # Try to load the next block
#     new_block_id = await load_block(block_id + 1, auth_token)
#     if new_block_id:
#         # If block is found, save the new blockId
#         logger.info(f"New block found: {new_block_id}")
#         save_last_block_id(new_block_id)
#         return True
#     else:
#         logger.warning(f"Block not found: {block_id}")
#         return False


async def near_events_task(auth_token: AuthToken):
    """Main processing workflow with duplicate protection."""
    async with processing_lock:
        await initialize_block_state()  # Ensure state is initialized

        # Calculate start block AFTER initialization
        start_block = _current_block_id + 1

        tasks = [
            process_block_wrapper(start_block + i, auth_token) for i in range(NUMBER_OF_BLOCKS_TO_READ_IF_NOT_SYNCED)
        ]

        for task in asyncio.as_completed(tasks):
            if (block_id := await task) is not None:
                save_last_block_id(block_id)
                logger.info(f"Processed block {block_id}")


async def process_block_wrapper(block_id, auth_token):
    """Wrapper for block processing with error handling."""
    retries = 3
    for attempt in range(retries):
        try:
            if await load_block(block_id, auth_token):
                return block_id
        except Exception:
            if attempt == retries - 1:
                logger.error(f"Block {block_id} failed after {retries} attempts")
    return None


def process_near_events_initial_state():
    """Reset state including history."""
    global _current_block_id, _processed_blocks
    if RESET_BLOCK_ID_ON_START:
        _current_block_id = 0
        _processed_blocks = set()
        if os.path.exists(BLOCK_ID_FILE):
            os.remove(BLOCK_ID_FILE)
            logger.info("Reset processing state")
