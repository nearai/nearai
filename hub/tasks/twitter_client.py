import os
import time

import tweepy  # type: ignore

bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
client = tweepy.Client(bearer_token)


async def get_latest_mentions(user_id, timestamp, max_results=5):
    try:
        # todo: pass timestamp to get only new mentions
        response = client.get_users_mentions(user_id, max_results=max_results)
        data = response.data
        if data:
            for tweet in data:
                print("text", tweet.text)
                print("id", tweet.id)
                print("===================")
            return data
        else:
            print(f"No data, response status code: {response.status_code}")
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
