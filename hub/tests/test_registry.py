import unittest
from fastapi.testclient import TestClient
from hub.app import app
from hub.api.v1.auth import get_current_user


class TestRegistryRoutes(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        app.dependency_overrides[get_current_user] = self.override_dependency

    @staticmethod
    async def override_dependency():
        return {"account_id": "unittest.near"}

    def test_fetch_agent(self):
        response = self.client.get("/v1/registry/agents/xela-agent")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.text and "PROMPT_COMMON" in response.text)

    def test_download_registry_directory_gives_404(self):
        response = self.client.get("/v1/registry/download/xela-agent")
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
