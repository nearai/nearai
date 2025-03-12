import os
import shutil
import tarfile
import unittest
import uuid
import openai
import io

from fastapi.testclient import TestClient
from hub.app import app
from nearai.login import generate_nonce
from hub.api.v1.auth import get_auth, AuthToken
from hub.api.v1.vector_stores import VectorStore, CreateVectorStoreRequest
from openai.types.beta.thread_create_params import Message

class TestAgentsRoutes(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        app.dependency_overrides[get_auth] = self.override_dependency

    @staticmethod
    async def override_dependency():
        return AuthToken(account_id="unittest2.near", public_key="unittest",
                         signature="unittest", callback_url="unittest", message="unittest", nonce=generate_nonce(), )

    def create_openai_client(self):
        url = str(self.client.base_url) + "/v1"
        return openai.OpenAI(api_key="sk-test", base_url=url, http_client=self.client)

    def test_run_agent(self):
        client = self.create_openai_client()

        assistant_id = "pierre-dev.near/agents/vector-store-agent"
        thread = client.beta.threads.create(messages=[Message(role="user", content="Create vector store for near core-contracts.")])
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=assistant_id,
        )

        print(run)

if __name__ == '__main__':
    unittest.main()
