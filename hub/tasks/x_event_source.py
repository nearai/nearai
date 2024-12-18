import os
from contextlib import asynccontextmanager
from functools import partial

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from nearai.shared.client_config import DEFAULT_MODEL

from hub.api.v1.auth import AuthToken
from hub.api.v1.thread_routes import RunCreateParamsBase, ThreadModel, _create_thread, create_run
from hub.tasks.twitter_client import get_latest_mentions

RESET_BLOCK_ID_ON_START = True  # reusing setting name for now

# Path to store the last read tweet id
TWEET_STATUS_FILE = "last_tweet.txt"

scheduler = AsyncIOScheduler()

# todo pull from registry 'integration' item
EVENT_SOURCE_CONFIG = {"user_id": "1867270324649160704"}

# todo pull from agent metadata
LISTENER_CONFIG = {"agent_name": "flatirons.near/nearsecretagent/0.0.1"}


# Function to get the last read tweet timestamp from a file
async def get_last_tweet_timestamp():
    if os.path.exists(TWEET_STATUS_FILE):
        with open(TWEET_STATUS_FILE, "r") as f:
            return int(f.read().strip())
    return None


# Function to save the last blockId to a file
def save_last_tweet_time(tweet_timestamp):
    print("Saving last tweet time", tweet_timestamp)
    with open(TWEET_STATUS_FILE, "w") as f:
        f.write(str(tweet_timestamp))


def user_rate_limit_exceeded(tweet):
    # todo implement
    pass


def rate_limit_reply(tweet):
    # if the user has received a rate limit reply already today, do nothing.
    # response = "So many questions, try again tomorrow."  # pull from agent metadata?
    # todo implement
    pass


async def listener_function(auth_token, tweet):
    message = tweet.text
    sender = tweet.id

    # if user_rate_limit_exceeded(tweet):
    #     rate_limit_reply(tweet)
    #     return

    # todo one thread per twitter sender

    await run_agent(
        LISTENER_CONFIG["agent_name"],
        message,
        sender,
        {},
        auth_token,
    )


# @todo change to hub authentication
def load_auth_token():
    from nearai.config import Config, load_config_file

    app_config = Config()
    # Update config from global config file
    config_data = load_config_file(local=False)
    app_config = app_config.update_with(config_data)

    return app_config.auth


async def run_agent(agent, message, sender, data, auth_token: AuthToken):
    if not (agent and message):
        return print("Missing data")

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
        # max_iterations=data.get("max_iterations", 1),
    )

    create_run(thread_id=thread.id, run=run_params, auth=auth_token, scheduler=scheduler)


async def process_tweets(auth_token, tweets):
    for tweet in tweets:
        await listener_function(auth_token, tweet)


# Main asynchronous function to process fetch and process tweets
async def periodic_task(auth_token):
    # Get the last processed tweet timestamp
    tweet_timestamp = await get_last_tweet_timestamp()

    # load latest mentions
    mentions = await get_latest_mentions(EVENT_SOURCE_CONFIG["user_id"], tweet_timestamp)
    if mentions:
        await process_tweets(auth_token, mentions)
        timestamp = mentions[0].created_at.timestamp()
        save_last_tweet_time(timestamp)
        return True

    return False


@asynccontextmanager
async def lifespan(app):
    # remove last known tweet timestamp to reset the state on start
    if RESET_BLOCK_ID_ON_START:
        if os.path.exists(TWEET_STATUS_FILE):
            os.remove(TWEET_STATUS_FILE)
            print(f"File {TWEET_STATUS_FILE} has been deleted.")

    auth_token = load_auth_token()

    job = partial(periodic_task, auth_token)

    scheduler.add_job(job, IntervalTrigger(seconds=10))
    scheduler.start()

    yield

    scheduler.shutdown()
