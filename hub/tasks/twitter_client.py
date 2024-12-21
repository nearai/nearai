import os
import time

import tweepy  # type: ignore

bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
client = tweepy.Client(bearer_token)

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


async def get_latest_mentions(user_id, timestamp, max_results=5):
    try:
        # todo: pass timestamp to get only new mentions
        response = client.get_users_mentions(user_id, max_results=max_results, tweet_fields=TWEET_FIELDS)
        data = response.data
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


# Example usage
# user_id = 1867270324649160704
# get_latest_mentions(user_id)
