import unittest
import time

from fastapi.testclient import TestClient
from hub.app import app
from hub.api.v1.auth import get_auth, AuthToken

class TestThreadRoutes(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        app.dependency_overrides[get_auth] = self.override_dependency

    @staticmethod
    def generate_nonce():
        """Generates a nonce based on the current time in milliseconds."""
        return str(int(time.time() * 1000))


    @staticmethod
    async def override_dependency():
        return AuthToken(
            account_id="unittest2.near",
            public_key="unittest",
            signature="unittest",
            callback_url="unittest",
            message="unittest",
            nonce=TestThreadRoutes.generate_nonce(),
        )
    def test_create_subthread(self):
        # Create a parent thread first
        parent_thread = {
            "messages": [
                {
                    "content": "Message on Parent Thread",
                    "role": "user",
                    "metadata": {}
                }
            ]
        }
        parent_response = self.client.post("/v1/threads", json=parent_thread)
        self.assertEqual(parent_response.status_code, 200)
        parent_id = parent_response.json()["id"]

        subthread_params = {
            "messages_to_copy": [1],
            "new_messages": [
                {
                    "content": "New message content",
                    "role": "user",
                    "metadata": {"key": "value"}
                }
            ]
        }
        response = self.client.post(f"/v1/threads/{parent_id}/subthread", json=subthread_params)
        print(response.json())
        self.assertEqual(response.status_code, 200)
        self.assertIn("id", response.json())
        self.assertIn("object", response.json())
        self.assertEqual(response.json()["object"], "thread")

if __name__ == '__main__':
    unittest.main()