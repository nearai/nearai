import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from hub.tasks.near_events import run_agent
from hub.tasks.twitter_client import get_latest_mentions

logger = logging.getLogger(__name__)


RESET_BLOCK_ID_ON_START = True  # reusing setting name for now

# Path to store the last read tweet id
TWEET_STATUS_FILE = "last_tweet.txt"

scheduler = AsyncIOScheduler()

# future: pull from registry 'integration' item
EVENT_SOURCE_CONFIG = {"user_id": "1867270324649160704"}

# future: pull from agent metadata
LISTENER_CONFIG = {"agent_name": "flatirons.near/near-secret-agent/0.0.1"}


# Function to get the last read tweet timestamp from a file
async def get_last_tweet_timestamp():
    if os.path.exists(TWEET_STATUS_FILE):
        with open(TWEET_STATUS_FILE, "r") as f:
            return int(f.read().strip())
    return None


def save_last_tweet_time(tweet_timestamp):
    with open(TWEET_STATUS_FILE, "w") as f:
        f.write(str(int(tweet_timestamp)))


async def listener_function(auth_token, tweet):
    message = {
        "action": "twitter_mention",
        "mentioned_twitter_user_id": EVENT_SOURCE_CONFIG["user_id"],
        "author_id": tweet.author_id,
        "tweet_id": tweet.id,
        "tweet": tweet.data,
    }

    await run_agent(
        LISTENER_CONFIG["agent_name"],
        message,
        auth_token,
    )


async def process_tweets(auth_token, tweets):
    for tweet in tweets:
        await listener_function(auth_token, tweet)


# Main asynchronous function to process fetch and process tweets
async def x_events_task(auth_token):
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


def process_x_events_initial_state():
    # remove last known tweet timestamp to reset the state on start
    if RESET_BLOCK_ID_ON_START:
        if os.path.exists(TWEET_STATUS_FILE):
            os.remove(TWEET_STATUS_FILE)
            print(f"File {TWEET_STATUS_FILE} has been deleted.")
