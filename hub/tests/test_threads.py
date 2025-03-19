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

    def test_thread_permissions(self):
        # Create a thread first
        thread_data = {
            "messages": [
                {
                    "content": "Test message",
                    "role": "user",
                    "metadata": {}
                }
            ]
        }
        response = self.client.post("/v1/threads", json=thread_data)
        self.assertEqual(response.status_code, 200)
        thread_id = response.json()["id"]

        # Override auth with a different user
        async def different_user_auth():
            return AuthToken(
                account_id="different.near",
                public_key="unittest",
                signature="unittest",
                callback_url="unittest",
                message="unittest",
                nonce=TestThreadRoutes.generate_nonce(),
            )

        # Try to access thread with different user
        original_override = app.dependency_overrides[get_auth]
        app.dependency_overrides[get_auth] = different_user_auth
        response = self.client.get(f"/v1/threads/{thread_id}")
        self.assertEqual(response.status_code, 403)

        # Restore original auth and verify access
        app.dependency_overrides[get_auth] = original_override
        response = self.client.get(f"/v1/threads/{thread_id}")
        self.assertEqual(response.status_code, 200)

    def test_thread_message_permissions(self):
        # Create a thread
        thread_data = {
        }
        response = self.client.post("/v1/threads", json=thread_data)
        self.assertEqual(response.status_code, 200)
        thread_id = response.json()["id"]

        # Add a message to the thread
        new_message = {
            "content": "Another test message",
            "role": "user",
            "metadata": {"test": "data"}
        }
        response = self.client.post(f"/v1/threads/{thread_id}/messages", json=new_message)
        self.assertEqual(response.status_code, 200)

        # Override auth with a different user
        async def different_user_auth():
            return AuthToken(
                account_id="different.near",
                public_key="unittest",
                signature="unittest",
                callback_url="unittest",
                message="unittest",
                nonce=TestThreadRoutes.generate_nonce(),
            )

        # Try to access thread messages with different user
        original_override = app.dependency_overrides[get_auth]
        app.dependency_overrides[get_auth] = different_user_auth
        response = self.client.get(f"/v1/threads/{thread_id}/messages")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "You don't have permission to access messages from this thread")

        # Restore original auth and verify messages can be accessed
        app.dependency_overrides[get_auth] = original_override
        response = self.client.get(f"/v1/threads/{thread_id}/messages")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.json()['data']) > 0)


if __name__ == '__main__':
    unittest.main()