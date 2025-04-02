import json
import os
import re
from contextlib import asynccontextmanager
from functools import partial
from typing import Any

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from nearai.shared.client_config import DEFAULT_MODEL
from nearai.shared.models import RunMode

from hub.api.v1.auth import AuthToken
from hub.api.v1.thread_routes import RunCreateParamsBase, ThreadModel, _create_thread, create_run

RESET_BLOCK_ID_ON_START = True

# Base URL for fetching block data
BASE_URL = "https://mainnet.neardata.xyz/v0/block/"

# Path to store the last read blockId
BLOCK_ID_FILE = "last_block_id.txt"

# OPTION TO READ MULTIPLE BLOCKS PER RUN
NUMBER_OF_BLOCKS_TO_READ_IF_NOT_SYNCED = 1

near_scheduler = AsyncIOScheduler()


async def async_fetch_json(url: str) -> Any:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            return None


async def get_latest_block_id():
    # DEBUG. This block has the required event
    # return 134822056

    data = await async_fetch_json("https://api.fastnear.com/status")
    if data:
        latest_block_id = data.get("sync_block_height", None)
        if latest_block_id:
            print(f"Starting with the latest block ID: {latest_block_id}")
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
    print("Saving last block id", block_id)
    with open(BLOCK_ID_FILE, "w") as f:
        f.write(str(block_id))


# Asynchronous function to load a block by its ID
async def load_block(block_id, auth_token):
    print(f"Loading block {block_id}")
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

                max_iterations = data.get("max_iterations", 1)
                if max_iterations:
                    if isinstance(max_iterations, (int, float)) and max_iterations > 0:
                        max_iterations = int(max_iterations)
                    else:
                        max_iterations = 1
                else:
                    max_iterations = 1

                if event.get("event") == "run_agent":
                    await run_agent(
                        data.get("agent", ""),
                        data.get("message", ""),
                        data.get("signer_id", ""),
                        {
                            "max_iterations": max_iterations,
                            "env_vars": data.get("env_vars", "{}"),
                            "referral_id": data.get("referral_id", ""),
                            "amount": data.get("amount", ""),
                            "receipt_id": receipt_execution_outcome["execution_outcome"]["id"],
                        },
                        auth_token,
                    )


def load_auth_token():
    from nearai.config import Config, load_config_file

    app_config = Config()
    # Update config from global config file
    config_data = load_config_file(local=False)
    app_config = app_config.update_with(config_data)

    return app_config.auth


async def run_agent(agent, message, signer_id, data, auth_token: AuthToken):
    if not (agent and message):
        return print("Missing data")

    # TODO find out how to ret fid of 401 error here
    # auth_token.on_behalf_of = signer_id

    thread_model = ThreadModel(
        meta_data={
            "agent_ids": [agent],
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
        additional_messages=[{"content": message, "role": "user"}],
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
        # max_iterations=data.get("max_iterations", 1),
    )

    create_run(thread_id=thread.id, run=run_params, auth=auth_token, scheduler=near_scheduler)


# Main asynchronous function to process blocks
async def process_blocks(auth_token):
    # Get the last processed blockId
    block_id = await get_last_block_id()

    # Try to load the next block
    new_block_id = await load_block(block_id + 1, auth_token)
    if new_block_id:
        # If block is found, save the new blockId
        print(f"New block found: {new_block_id}")
        save_last_block_id(new_block_id)
        return True
    else:
        print(f"Block not found: {block_id}")
        return False


async def periodic_task(auth_token: AuthToken):
    # Try to catch up reading NUMBER_OF_BLOCKS_TO_READ_IF_NOT_SYNCED blocks per run
    for _ in range(NUMBER_OF_BLOCKS_TO_READ_IF_NOT_SYNCED):
        block_found = await process_blocks(auth_token)
        if not block_found:
            break


@asynccontextmanager
async def lifespan(app):
    # remove last known block_id to reset the state on start
    if RESET_BLOCK_ID_ON_START:
        if os.path.exists(BLOCK_ID_FILE):
            os.remove(BLOCK_ID_FILE)
            print(f"File {BLOCK_ID_FILE} has been deleted.")

    auth_token = load_auth_token()

    job = partial(periodic_task, auth_token)

    near_scheduler.add_job(job, IntervalTrigger(seconds=1))
    near_scheduler.start()

    yield

    near_scheduler.shutdown()
