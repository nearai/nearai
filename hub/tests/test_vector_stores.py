import os
import shutil
import tarfile
import uuid
import openai
import io
import pytest

from fastapi.testclient import TestClient
from hub.app import app
from nearai.login import generate_nonce
from hub.api.v1.auth import get_auth, AuthToken
from hub.api.v1.vector_stores import VectorStore, CreateVectorStoreRequest

@pytest.fixture
def client():
    app.dependency_overrides[get_auth] = override_dependency
    return TestClient(app)

@pytest.fixture
def auth_token():
    return AuthToken(
        account_id="unittest2.near",
        public_key="unittest",
        signature="unittest",
        callback_url="unittest",
        message="unittest",
        nonce=generate_nonce(),
    )

def override_dependency():
    return auth_token

@pytest.fixture
def file_content():
    return b"To list use client.beta.vector_stores.list()"

@pytest.fixture
def in_memory_file(file_content):
    file = io.BytesIO(file_content)
    file.name = "test_file.py"
    return file

@pytest.fixture
def openai_client(client):
    url = str(client.base_url) + "/v1"
    return openai.OpenAI(api_key="sk-test", base_url=url, http_client=client)

def test_create_and_get_vector_store(openai_client):
    # First, create a vector store to retrieve
    created_store = openai_client.beta.vector_stores.create(
        name="test_retrieve_vector_store",
        file_ids=["file1", "file2"],
        metadata={"key": "value"},
        expires_after={"anchor": "last_active_at", "days": 7},
    )

    # Now retrieve the created vector store
    retrieved_store = openai_client.beta.vector_stores.retrieve(created_store.id)

    # Assert that the retrieved store matches the created one
    assert retrieved_store.id == created_store.id
    assert retrieved_store.name == "test_retrieve_vector_store"
    assert retrieved_store.file_counts.completed == 2
    assert retrieved_store.metadata == {"key": "value"}

def test_openai_upload_file(openai_client, in_memory_file):
    response = openai_client.files.create(
        file=in_memory_file,
        purpose="batch",
    )
    print(response)

    openai_client.beta.vector_stores.files.create(
        file_id=response.id,
        purpose="batch",
    )

def test_attach_file_to_vector_store(openai_client, in_memory_file, client):
    vs = openai_client.beta.vector_stores.create(
        name="test_retrieve_vector_store",
    )
    print(f"Vector store response: {vs}")

    f = openai_client.files.create(
        file=in_memory_file,
        purpose="assistants",
    )
    print(f"File response: {f}")

    resp = openai_client.beta.vector_stores.files.create(
      vector_store_id=vs.id,
      file_id=f.id,
    )
    print(f"File attached to vector store: {resp}")

    resp = client.post(f"/v1/vector_stores/{vs.id}/search", json={"query": "How to list my vector stores?"})
    print(f"Search response: {resp.json()}")
