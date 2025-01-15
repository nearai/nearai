import asyncio
import json
import logging
import os
import re
from typing import Any

import httpx
from dotenv import load_dotenv
from nearai.shared.client_config import DEFAULT_MODEL

from hub.api.v1.auth import AuthToken
from hub.api.v1.thread_routes import RunCreateParamsBase, ThreadModel, _create_thread, create_run
from hub.tasks.scheduler import get_async_scheduler

load_dotenv()
logger = logging.getLogger(__name__)

RESET_BLOCK_ID_ON_START = True

# Base URL for fetching block data
BASE_URL = "https://mainnet.neardata.xyz/v0/block/"

# Path to store the last read blockId
BLOCK_ID_FILE = "last_block_id.txt"

# OPTION TO READ MULTIPLE BLOCKS PER RUN
NUMBER_OF_BLOCKS_TO_READ_IF_NOT_SYNCED = int(os.getenv("NEAR_EVENTS_NUMBER_OF_BLOCKS_TO_READ_PER_RUN", 2))


async def async_fetch_json(url: str) -> Any:
    headers = {}
    api_key = os.getenv("FASTNEAR_APIKEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            return None


async def get_latest_block_id():
    # DEBUG. This block has the required event
    # return 135350100

    data = await async_fetch_json("https://api.fastnear.com/status")
    if data:
        latest_block_id = data.get("sync_block_height", None)
        if latest_block_id:
            logger.info(f"Starting with the latest block ID: {latest_block_id}")
            return latest_block_id

    return 0


# Function to get the last read blockId from a file
async def get_last_block_id():
    if os.path.exists(BLOCK_ID_FILE):
        with open(BLOCK_ID_FILE, "r") as f:
            return int(f.read().strip())
    return await get_latest_block_id()


# Function to save the last blockId to a file
def save_last_block_id(block_id):
    # logger.info(f"Saving last block {block_id}")
    with open(BLOCK_ID_FILE, "w") as f:
        f.write(str(block_id))


# Asynchronous function to load a block by its ID
async def load_block(block_id, auth_token):
    # logger.info(f"Loading block {block_id}")
    data = await async_fetch_json(f"{BASE_URL}{block_id}")
    if data and data.get("shards"):
        # If data and shards are found, process them
        await process_shards(data["shards"], block_id, auth_token)
        return block_id
    else:
        return None


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

    # TODO find out how to get rid of 401 error here
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
        model=DEFAULT_MODEL,
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


async def process_blocks_in_parallel(auth_token, num_parallel=NUMBER_OF_BLOCKS_TO_READ_IF_NOT_SYNCED):
    block_id = await get_last_block_id()

    async def process_single_block(block_id):
        new_block_id = await load_block(block_id, auth_token)
        if new_block_id:
            # logger.info(f"New block found: {new_block_id}")
            save_last_block_id(new_block_id)
            return new_block_id
        else:
            logger.warning(f"Block not found: {block_id}")
            return None

    tasks = [process_single_block(block_id + i + 1) for i in range(num_parallel)]

    results = await asyncio.gather(*tasks)
    successful_blocks = [result for result in results if result is not None]

    if successful_blocks:
        logger.info(f"Successfully loaded blocks: {successful_blocks}")
        return True
    else:
        logger.warning("No new blocks were found.")
        return False


async def near_events_task(auth_token: AuthToken):
    # Try to catch up reading NUMBER_OF_BLOCKS_TO_READ_IF_NOT_SYNCED blocks per run
    # for _ in range(NUMBER_OF_BLOCKS_TO_READ_IF_NOT_SYNCED):
    #     block_found = await process_blocks_sequentially(auth_token)
    #     if not block_found:
    #         break

    await process_blocks_in_parallel(auth_token)


def process_near_events_initial_state():
    # remove last known block_id to reset the state on start
    if RESET_BLOCK_ID_ON_START:
        if os.path.exists(BLOCK_ID_FILE):
            os.remove(BLOCK_ID_FILE)
            logger.info(f"File {BLOCK_ID_FILE} has been deleted.")
