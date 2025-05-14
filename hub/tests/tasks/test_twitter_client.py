import unittest
from unittest.mock import patch, MagicMock
from hub.tasks.twitter_client import get_latest_mentions
import json

class TestTwitterClient(unittest.IsolatedAsyncioTestCase):


    @patch('hub.tasks.twitter_client.client.search_recent_tweets')
    async def test_get_latest_mentions_paging(self, mock_search_recent_tweets):
        with open('hub/tests/data/tasks/many_tweets.json') as f:
            example_data = json.load(f)

        # Mock the response to simulate paging
        max_results = 10
        mock_response = MagicMock()
        mock_response.data = example_data[:max_results]
        mock_response.meta = {'next_token': 'next_token_value'}

        # First call returns the first page
        mock_search_recent_tweets.return_value = mock_response

        # Second call returns the next page
        mock_response_next = MagicMock()
        mock_response_next.data = example_data[max_results:max_results*2]
        mock_response_next.meta = {} # No next token to simulate end of data

        mock_search_recent_tweets.side_effect = [mock_response, mock_response_next]

        user_name = "NearSecretAgent"
        timestamp = None

        tweets, _authors = await get_latest_mentions(user_name, timestamp, max_results)

        self.assertIsNotNone(tweets)
        self.assertEqual(len(tweets), 20)
        mock_search_recent_tweets.assert_called()


    @patch('hub.tasks.twitter_client.client.search_recent_tweets')
    async def test_get_latest_mentions_limit_per_run(self, mock_search_recent_tweets):
        with open('hub/tests/data/tasks/many_tweets.json') as f:
            example_data = json.load(f)

        # Mock the response to simulate hitting the limit_per_run
        max_results = 10
        mock_response = MagicMock()
        mock_response.data = example_data[:max_results]
        mock_response.meta = {'next_token': 'next_token_value'}

        # First call returns the first page
        mock_search_recent_tweets.return_value = mock_response

        # Second call returns the next page
        mock_response_next = MagicMock()
        mock_response_next.data = example_data[max_results:max_results*2]
        mock_response.meta = {'next_token': 'next_token_value'}

        mock_search_recent_tweets.side_effect = [mock_response, mock_response_next]

        user_name = "NearSecretAgent"
        timestamp = None
        limit_per_run = 20  # Set a low limit to test the parameter

        tweets, _authors = await get_latest_mentions(user_name, timestamp, max_results, limit_per_run)

        self.assertIsNotNone(tweets)
        self.assertEqual(len(tweets), limit_per_run)
        mock_search_recent_tweets.assert_called()

if __name__ == '__main__':
    unittest.main()