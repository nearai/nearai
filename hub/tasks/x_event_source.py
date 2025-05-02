import datetime
import logging
import os
import threading
from typing import Dict, List

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from hub.api.v1.registry import EntryInformation
from hub.tasks.near_events import run_agent
from hub.tasks.triggers import agents_with_x_accounts_to_track
from hub.tasks.twitter_client import get_latest_mentions

logger = logging.getLogger(__name__)

RESET_TWEET_TIMESTAMP_ON_START = os.environ.get("RESET_TWEET_TIMESTAMP_ON_START", "false").lower() == "true"

# Path to store the last read tweet id
TWEET_STATUS_FILE = "last_tweet.txt"

x_scheduler = AsyncIOScheduler()


def get_user_last_tweet_filename(user_name=""):
    return TWEET_STATUS_FILE.replace(".txt", f"_{user_name}.txt")


X_ACCOUNTS_BEING_TRACKED: Dict[str, List[EntryInformation]] = {}
x_accounts_lock = threading.Lock()  # synchronize access to X_ACCOUNTS_BEING_TRACKED in case scheduled tasks overlap


def load_x_accounts_to_track() -> Dict[str, List[EntryInformation]]:
    x_accounts_to_track: Dict[str, List[EntryInformation]] = {}
    registry_items_with_x_accounts_to_track = agents_with_x_accounts_to_track()
    for registry_item in registry_items_with_x_accounts_to_track:
        x_accounts_to_add = registry_item.details.get("triggers", {}).get("events", {}).get("x_mentions", [])
        if isinstance(x_accounts_to_add, list):
            for x_account_to_add in x_accounts_to_add:
                # normalize x_account (remove preceding @)
                x_account_to_add = x_account_to_add.strip().lower().lstrip("@")

                # check if this agent already tracking this x account
                agent_already_track_this_x_account = False
                for agent_entry_data in x_accounts_to_track.get(x_account_to_add, []):
                    if (
                        agent_entry_data.namespace == registry_item.namespace
                        and agent_entry_data.name == registry_item.name
                    ):
                        agent_already_track_this_x_account = True
                        break

                if not agent_already_track_this_x_account:
                    if x_account_to_add in x_accounts_to_track.keys():
                        x_accounts_to_track[x_account_to_add].append(registry_item)
                    else:
                        x_accounts_to_track[x_account_to_add] = [registry_item]
    return x_accounts_to_track


# Function to get the last read tweet timestamp from a file
async def get_last_tweet_timestamp(user_name=""):
    filename = get_user_last_tweet_filename(user_name)
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return int(f.read().strip())
    return None


def save_last_tweet_time(tweet_timestamp, user_name=""):
    filename = get_user_last_tweet_filename(user_name)
    with open(filename, "w") as f:
        f.write(str(int(tweet_timestamp)))


async def listener_function(auth_token, tweet, tweet_author, agents_entries):
    message = {
        "action": "twitter_mention",
        "author_id": tweet.author_id,
        "tweet_id": tweet.id,
        "tweet": tweet.data,
        "text": tweet.text,
        "replied_to": [],
        "author": {
            "username": tweet_author.username if tweet_author else None,
            "name": tweet_author.name if tweet_author else None,
            "profile_image_url": tweet_author.profile_image_url if tweet_author else None,
        }
        if tweet_author
        else None,
    }

    # add replied_to
    if "referenced_tweets" in tweet.data:
        for referenced_tweet in tweet.data["referenced_tweets"]:
            if referenced_tweet["type"] == "replied_to":
                message["replied_to"].append(referenced_tweet["id"])

    # convert urls (t.co/ => url text)
    if "entities" in tweet.data:
        if "urls" in tweet.data["entities"]:
            for url_data in tweet.data["entities"]["urls"]:
                # Replace URLs in text
                if "://t.co/" in url_data["url"]:
                    message["text"] = tweet.text.replace(url_data["url"], url_data["display_url"])
                else:
                    message["text"] = tweet.text.replace(url_data["url"], url_data["expanded_url"])

    for agent_entry in agents_entries:
        agent = f"{agent_entry.namespace}/{agent_entry.name}/{agent_entry.version}"
        logger.info(f"Scheduling agent {agent} run for message {tweet.text}")
        await run_agent(
            agent,
            message,
            auth_token,
        )


# Main asynchronous function to process fetch and process tweets
async def x_events_task(auth_token):
    # Get the last processed tweet timestamp
    x_accounts_to_track = load_x_accounts_to_track()
    global X_ACCOUNTS_BEING_TRACKED
    with x_accounts_lock:
        if x_accounts_to_track and x_accounts_to_track != X_ACCOUNTS_BEING_TRACKED:
            X_ACCOUNTS_BEING_TRACKED = x_accounts_to_track
            x_accounts_list = ", ".join(X_ACCOUNTS_BEING_TRACKED.keys())
            logger.info(f"Updating X accounts to track: {x_accounts_list}")

    x_tasks = []
    for user_name in x_accounts_to_track.keys():
        one_week_ago = int((datetime.datetime.now() - datetime.timedelta(weeks=1)).timestamp())
        last_from_file = await get_last_tweet_timestamp(user_name)
        last_tweet_timestamp = max(last_from_file or 0, one_week_ago)

        # load latest mentions
        tweets, tweet_authors = await get_latest_mentions(user_name, last_tweet_timestamp)

        if tweets:
            # sort tweets by tweet.created_at ascending
            tweets = sorted(tweets, key=lambda _tweet: _tweet.created_at)

            for tweet in reversed(tweets):
                tweet_timestamp = int(tweet.created_at.timestamp())
                #  Check if the tweet is newer than the last processed tweet
                if not last_tweet_timestamp or tweet_timestamp > int(last_tweet_timestamp):
                    # Ensure the tweet is not already in x_tasks by checking its ID
                    if not any(existing_task.get("tweet").id == tweet.id for existing_task in x_tasks):
                        tweet_author = tweet_authors.get(tweet.author_id)
                        x_tasks.append(
                            {"tweet": tweet, "tweet_author": tweet_author, "agents": x_accounts_to_track[user_name]}
                        )

                    last_tweet_timestamp = tweet_timestamp

                    # local_mode supports only single task
                    # return True
                else:
                    logger.info(f"Tweet is too old: {tweet_timestamp} < {last_tweet_timestamp}")

        if last_tweet_timestamp:
            save_last_tweet_time(last_tweet_timestamp, user_name)

    for task in x_tasks:
        tweet = task.get("tweet")
        tweet_author = task.get("tweet_author")
        await listener_function(auth_token, tweet, tweet_author, task.get("agents"))


# remove last known tweet timestamp to reset the state on start
if RESET_TWEET_TIMESTAMP_ON_START:
    logger.info("Resetting tweet timestamp on start")
    x_accounts_to_reset = load_x_accounts_to_track()

    for x_account_to_reset in x_accounts_to_reset:
        filename = get_user_last_tweet_filename(x_account_to_reset)
        if os.path.exists(filename):
            os.remove(filename)
            logger.info(f"File {filename} has been deleted.")
