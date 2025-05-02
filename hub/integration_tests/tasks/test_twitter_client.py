import unittest
from datetime import datetime, timedelta

from hub.tasks.twitter_client import get_latest_mentions


class TestTwitterClientIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_get_latest_mentions_real_api_call(self):
        """Test the get_latest_mentions function with a real call to the X API."""
        user_name = "ACLU"
        timestamp = (datetime.utcnow() - timedelta(weeks=1)).timestamp()
        max_results = 10
        run_limit = 25

        tweets, _authors = await get_latest_mentions(user_name, timestamp, max_results, run_limit)

        self.assertIsNotNone(tweets)
        self.assertTrue(len(tweets) > 0)
        self.assertTrue(all("id" in tweet for tweet in tweets))
        self.assertTrue(all("text" in tweet for tweet in tweets))


if __name__ == "__main__":
    unittest.main()
