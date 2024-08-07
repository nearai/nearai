import os
import shutil
import tarfile
import unittest
import uuid

from fastapi.testclient import TestClient
from hub.app import app
from hub.api.v1.auth import revokable_auth, AuthToken


class TestRegistryRoutes(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        app.dependency_overrides[revokable_auth] = self.override_dependency

    @staticmethod
    async def override_dependency():
        return AuthToken(account_id="unittest.near", public_key="unittest",
                         signature="unittest", callback_url="unittest", plainMsg="unittest")

    def test_fetch_agent(self):
        response = self.client.get("/v1/registry/agents/xela-agent")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.text and "PROMPT_COMMON" in response.text)

    def test_download_registry_directory_returns_first_file(self):
        response = self.client.get("/v1/registry/download/xela-agent")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.text and "PROMPT_COMMON" in response.text)

    def test_fetch_environment(self):
        env_id = "environment_run_xela-tools-agent_541869e6753c41538c87cb6f681c6932"
        response = self.client.get(f"/v1/registry/environments/{env_id}")
        assert response.status_code == 200
        file = response.content
        os.makedirs("/tmp/near-ai-unittest", exist_ok=True)
        try:
            with open("/tmp/near-ai-unittest/test.tar.gz", "wb") as f:
                f.write(file)
            with tarfile.open("/tmp/near-ai-unittest/test.tar.gz", mode="r:gz") as tar:
                tar.extractall("/tmp/near-ai-unittest/output")
        finally:
            shutil.rmtree("/tmp/near-ai-unittest")

    def test_save_environment(self):
        with open("data/test.tar.gz", "rb") as file:
            response = self.client.post(
                "/v1/registry/environments",
                files={"file": ("test.tar.gz", file, "application/gzip")},
                params={
                    "env_id": uuid.uuid4().hex,
                    "name": "test-env",
                    "description": "test-env",
                    "details": '{"test": "test"}',
                    "tags": '["test"]',
                }
            )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["info"] == "Environment saved successfully"
        assert response_data["registry_id"] is not None


if __name__ == '__main__':
    unittest.main()
