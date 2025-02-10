import logging
import os
import time
from datetime import datetime, timedelta

import tweepy  # type: ignore

logger = logging.getLogger(__name__)

bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
client = tweepy.Client(bearer_token)

TWEET_LIMIT_PER_RUN = 1000

TWEET_FIELDS = [
    "article",
    "attachments",
    "author_id",
    "card_uri",
    "community_id",
    "context_annotations",
    "conversation_id",
    "created_at",
    "display_text_range",
    # "edit_controls",  contains unserializable datetime
    "edit_history_tweet_ids",
    "entities",
    "geo",
    "id",
    "in_reply_to_user_id",
    "lang",
    "media_metadata",
    "note_tweet",
    "possibly_sensitive",
    "public_metrics",
    "referenced_tweets",
    "reply_settings",
    "scopes",
    "source",
    "text",
    "withheld",
]


async def get_latest_mentions(user_name, timestamp, max_results=10, limit_per_run=TWEET_LIMIT_PER_RUN):
    try:
        if not timestamp:
            timestamp = datetime.utcnow() - timedelta(hours=1)
            start_time = timestamp.isoformat() + "Z"
        else:
            start_time = datetime.utcfromtimestamp(timestamp).isoformat() + "Z"

        tweets = []
        response = client.search_recent_tweets(
            query=f"@{user_name}", tweet_fields=TWEET_FIELDS, max_results=max_results, start_time=start_time
        )

        if response.data:
            tweets.extend(response.data)

        while "next_token" in response.meta:
            if len(tweets) >= limit_per_run:
                logger.error(f"Reached the limit of {limit_per_run} tweets per run. Stopping retrieval until next run.")
                break
            try:
                response = client.search_recent_tweets(
                    query=f"@{user_name}",
                    tweet_fields=TWEET_FIELDS,
                    max_results=max_results,
                    start_time=start_time,
                    next_token=response.meta["next_token"],
                )
                if response.data:
                    tweets.extend(response.data)
                else:
                    break
            except Exception as e:  # most likely rate limit, but we'll stop on any error
                logger.error(f"Error fetching tweets during pagination: {e}")
                break

        data = tweets
        if data:
            return data
        else:
            return None
    except tweepy.TooManyRequests as e:
        print("Rate limit exceeded. Headers:")
        for header in e.response.headers:
            if header.lower().startswith("x-rate-limit-"):
                if header == "x-rate-limit-reset":
                    print(
                        f"{header}: at {e.response.headers[header]} "
                        f"which is in ({float(e.response.headers[header]) - time.time()})"
                    )
                else:
                    print(f"{header}: {e.response.headers[header]}")
    except Exception as e:
        logger.error(f"Error fetching tweets: {e}")
        return None


# Example usage
# user_id = 1867270324649160704
# get_latest_mentions(user_id)
