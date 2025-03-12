import os
import shutil
import tarfile
import uuid

import pytest
from fastapi.testclient import TestClient
from hub.app import app
from hub.api.v1.auth import get_auth, AuthToken

def auth_token():
    return AuthToken(
        account_id="unittest.near",
        public_key="unittest",
        signature="unittest",
        callback_url="unittest",
        plainMsg="unittest"
    )

async def override_dependency():
    return auth_token()

app.dependency_overrides[get_auth] = override_dependency
client = TestClient(app)

def test_fetch_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_download_registry_directory_returns_first_file():
    response = client.get("/v1/registry/download_metadata/xela-agent")
    assert response.status_code == 200
    assert "PROMPT_COMMON" in response.text

def test_fetch_environment():
    env_id = "environment_run_xela-tools-agent_541869e6753c41538c87cb6f681c6932"
    response = client.get(f"/v1/registry/environments/{env_id}")
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

def test_save_environment(client):
    with open("data/test.tar.gz", "rb") as file:
        response = client.post(
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
