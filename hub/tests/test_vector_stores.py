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
from hub.api.v1.auth import revokable_auth, AuthToken
from hub.api.v1.vector_stores import VectorStore, CreateVectorStoreRequest

class TestVectorStoresRoutes(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        app.dependency_overrides[revokable_auth] = self.override_dependency
        self.file_content = b"To list use client.beta.vector_stores.list()"
        self.in_memory_file = io.BytesIO(self.file_content)
        self.in_memory_file.name = "test_file.py"

    @staticmethod
    async def override_dependency():
        return AuthToken(account_id="unittest2.near", public_key="unittest",
                         signature="unittest", callback_url="unittest", message="unittest", nonce=generate_nonce(), )

    def create_openai_client(self):
        url = str(self.client.base_url) + "/v1"
        return openai.OpenAI(api_key="sk-test", base_url=url, http_client=self.client)        
        
    def test_create_and_get_vector_store(self):
        client = self.create_openai_client()
        
        # First, create a vector store to retrieve
        created_store = client.beta.vector_stores.create(
            name="test_retrieve_vector_store",
            file_ids=["file1", "file2"],
            metadata={"key": "value"},
            expires_after={"anchor": "last_active_at", "days": 7},
        )
        
        # Now retrieve the created vector store
        retrieved_store = client.beta.vector_stores.retrieve(created_store.id)

        # Assert that the retrieved store matches the created one
        self.assertEqual(retrieved_store.id, created_store.id)
        self.assertEqual(retrieved_store.name, "test_retrieve_vector_store")
        self.assertEqual(retrieved_store.file_counts.completed, 2)
        self.assertEqual(retrieved_store.metadata, {"key": "value"})
  
    def test_openai_upload_file(self):
        client = self.create_openai_client()
        response = client.files.create(
            file=self.in_memory_file,
            purpose="batch",
        )
        print(response)
        
        client.beta.vector_stores.files.create(
            file_id=response.id,
            purpose="batch",
        )
        
    def test_attach_file_to_vector_store(self):
        client = self.create_openai_client()
        vs = client.beta.vector_stores.create(
            name="test_retrieve_vector_store",
        )
        print(f"Vector store response: {vs}")
        
        f = client.files.create(
            file=self.in_memory_file,
            purpose="assistants",
        )
        print(f"File response: {f}")
        
        resp = client.beta.vector_stores.files.create(
          vector_store_id=vs.id,
          file_id=f.id,
        )
        print(f"File attached to vector store: {resp}")
        
        resp = self.client.post(f"/v1/vector_stores/{vs.id}/search", json={"query": "How to list my vector stores?"})
        print(f"Search response: {resp.json()}")

if __name__ == '__main__':
    unittest.main()
