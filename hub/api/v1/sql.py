import json
import logging
import uuid
from datetime import datetime
from enum import Enum
from os import getenv
from typing import Any, Dict, List, Optional

import pymysql
import pymysql.cursors
from dotenv import load_dotenv
from pydantic import BaseModel, RootModel

load_dotenv()

logger = logging.getLogger(__name__)


class NonceStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"


class UserNonce(BaseModel):
    nonce: str
    account_id: str
    message: str
    recipient: str
    callback_url: Optional[str]

    nonce_status: NonceStatus
    first_seen_at: datetime

    def is_revoked(self):
        """Check if the nonce is revoked."""
        return self.nonce_status == NonceStatus.REVOKED


class UserNonces(RootModel):
    root: List[UserNonce]


class VectorStore(BaseModel):
    id: str
    account_id: str
    name: str
    file_ids: List[str]
    expires_after: Dict[str, Any]
    chunking_strategy: Dict[str, Any]
    metadata: Dict[str, str]
    created_at: datetime
    updated_at: datetime


class VectorStoreFile(BaseModel):
    id: str
    account_id: str
    file_path: str
    purpose: str
    created_at: datetime
    updated_at: datetime


class SqlClient:
    def __init__(self):  # noqa: D107
        self.db = pymysql.connect(
            host=getenv("DATABASE_HOST"),
            user=getenv("DATABASE_USER"),
            password=getenv("DATABASE_PASSWORD"),
            database=getenv("DATABASE_NAME"),
            autocommit=True,
        )

    def __fetch_all(self, query: str):
        """Fetches all matching rows from the database.

        Returns a list of dictionaries, the dicts can be used by Pydantic models.
        """
        cursor = self.db.cursor(pymysql.cursors.DictCursor)
        cursor.execute(query)
        return cursor.fetchall()

    def __fetch_one(self, query: str):
        """Fetches one row from the database.

        Returns a dictionary, the dict can be used by Pydantic models.
        """
        cursor = self.db.cursor(pymysql.cursors.DictCursor)
        cursor.execute(query)
        return cursor.fetchone()

    def add_user_usage(self, account_id: str, query: str, response: str, model: str, provider: str, endpoint: str):  # noqa: D102
        # Escape single quotes in query and response strings
        query = query.replace("'", "''")
        response = response.replace("'", "''")

        query = f"INSERT INTO completions (account_id, query, response, model, provider, endpoint) VALUES ('{account_id}', '{query}', '{response}', '{model}', '{provider}', '{endpoint}')"  # noqa: E501
        self.db.cursor().execute(query)
        self.db.commit()

    def get_user_usage(self, account_id: str):  # noqa: D102
        query = f"SELECT * FROM completions WHERE account_id = '{account_id}'"
        return self.__fetch_all(query)

    def store_nonce(self, account_id: str, nonce: bytes, message: str, recipient: str, callback_url: Optional[str]):  # noqa: D102
        logging.info(f"Storing nonce {nonce.decode()} for account {account_id}")
        query = """
        INSERT INTO nonces (nonce, account_id, message, recipient, callback_url, nonce_status)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        self.db.cursor().execute(query, (nonce.decode(), account_id, message, recipient, callback_url, "active"))
        self.db.commit()

    def get_account_nonces(self, account_id: str):  # noqa: D102
        query = f"SELECT * FROM nonces WHERE account_id = '{account_id}'"
        nonces = [UserNonce(**x) for x in self.__fetch_all(query)]
        user_nonces = UserNonces(root=nonces) if nonces else None
        return user_nonces

    def get_account_nonce(self, account_id: str, nonce: bytes):  # noqa: D102
        query = f"SELECT * FROM nonces WHERE account_id = '{account_id}' AND nonce = '{nonce.decode()}'"
        res = self.__fetch_one(query)
        user_nonce = UserNonce(**res) if res else None
        return user_nonce

    def revoke_nonce(self, account_id: str, nonce: bytes):  # noqa: D102
        logging.info(f"Revoking nonce {nonce.decode()} for account {account_id}")
        query = f"""UPDATE nonces SET nonce_status = 'revoked'
            WHERE account_id = '{account_id}' AND nonce = '{nonce.decode()}'"""
        self.db.cursor().execute(query)
        self.db.commit()

    def revoke_all_nonces(self, account_id):  # noqa: D102
        logging.info(f"Revoking all nonces  for account {account_id}")
        query = f"UPDATE nonces SET nonce_status = 'revoked' WHERE account_id = '{account_id}'"
        self.db.cursor().execute(query)
        self.db.commit()

    def create_vector_store(
        self,
        account_id: str,
        name: str,
        file_ids: List[str],
        expires_after: Optional[Dict[str, Any]] = None,
        chunking_strategy: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        vs_id = f"vs_{uuid.uuid4().hex[:24]}"

        query = """
        INSERT INTO vector_stores (id, account_id, name, file_ids, expires_after, chunking_strategy, metadata)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        print(expires_after)
        print(f"DB query: {query} params: {account_id, name, file_ids, expires_after, chunking_strategy, metadata}")
        cursor = self.db.cursor()
        try:
            cursor.execute(
                query,
                (
                    vs_id,
                    account_id,
                    name,
                    json.dumps(file_ids if file_ids else []),
                    json.dumps(expires_after if expires_after else {}),
                    json.dumps(chunking_strategy if chunking_strategy else {}),
                    json.dumps(metadata if metadata else {}),
                ),
            )
            self.db.commit()
            return vs_id
        except TypeError as e:
            if "dict can not be used as parameter" in str(e):
                raise ValueError(
                    "Invalid data type in parameters. Ensure all dictionary values are JSON serializable."
                ) from e
            raise

    def get_vector_store(self, vector_store_id: str) -> Optional[VectorStore]:  # noqa: D102
        """Get a vector store by id."""
        query = f"SELECT * FROM vector_stores WHERE id = '{vector_store_id}'"
        logger.info(f"Querying vector store: {query}")

        result = self.__fetch_one(query)
        if not result:
            return None

        result["file_ids"] = json.loads(result["file_ids"])
        result["expires_after"] = json.loads(result["expires_after"])
        result["chunking_strategy"] = json.loads(result["chunking_strategy"])
        result["metadata"] = json.loads(result["metadata"]) if result["metadata"] else None
        return VectorStore(**result)

    def get_vector_store_by_account(self, vector_store_id: str, account_id: str) -> Optional[VectorStore]:
        """Get a vector store by account id."""
        query = f"SELECT * FROM vector_stores WHERE id = '{vector_store_id}' AND account_id = '{account_id}'"

        result = self.__fetch_one(query)
        if not result:
            return None
        result["file_ids"] = json.loads(result["file_ids"])
        result["expires_after"] = json.loads(result["expires_after"])
        result["chunking_strategy"] = json.loads(result["chunking_strategy"])
        result["metadata"] = json.loads(result["metadata"]) if result["metadata"] else None

        return VectorStore(**result)

    def get_vector_stores(self, account_id: str) -> Optional[List[VectorStore]]:
        """Get all vector stores for a given account."""
        query = f"SELECT * FROM vector_stores WHERE account_id = '{account_id}'"
        return [VectorStore(**x) for x in self.__fetch_all(query)]

    def create_file(self, account_id: str, file_path: str, purpose: str) -> str:
        """Adds file details in the vector store."""
        # Generate a unique file_id with the required format
        file_id = f"file-{uuid.uuid4().hex[:24]}"  # This generates a string like "file-abc123"

        query = """
        INSERT INTO vector_store_files (id, account_id, file_path, purpose)
        VALUES (%s, %s, %s, %s)
        """
        cursor = self.db.cursor()
        cursor.execute(query, (file_id, account_id, file_path, purpose))
        self.db.commit()
        return file_id

    def get_file_details_by_account(self, file_id: str, account_id: str) -> Optional[VectorStoreFile]:
        query = "SELECT * FROM vector_store_files WHERE id = %s AND account_id = %s"
        cursor = self.db.cursor(pymysql.cursors.DictCursor)
        cursor.execute(query, (file_id, account_id))
        result = cursor.fetchone()
        return VectorStoreFile(**result) if result else None

    def get_file_details(self, file_id: str) -> Optional[VectorStoreFile]:
        query = "SELECT * FROM vector_store_files WHERE id = %s"
        cursor = self.db.cursor(pymysql.cursors.DictCursor)
        cursor.execute(query, (file_id,))
        result = cursor.fetchone()
        return VectorStoreFile(**result) if result else None

    def update_files_in_vector_store(
        self, vector_store_id: str, file_ids: List[str], account_id: str
    ) -> Optional[VectorStore]:
        query = "UPDATE vector_stores SET file_ids = %s WHERE id = %s AND account_id = %s"
        cursor = self.db.cursor()
        cursor.execute(query, (json.dumps(file_ids), vector_store_id, account_id))
        self.db.commit()
        return self.get_vector_store(vector_store_id)

    def store_embedding(
        self, id: str, vector_store_id: str, file_id: str, chunk_index: int, chunk_text: str, embedding: List[float]
    ):
        query = """
        INSERT INTO vector_store_embeddings
        (id, vector_store_id, file_id, chunk_index, chunk_text, embedding)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor = self.db.cursor()
        cursor.execute(query, (id, vector_store_id, file_id, chunk_index, chunk_text, json.dumps(embedding)))
        self.db.commit()

    def update_file_embedding_status(self, file_id: str, status: str):
        query = """
        UPDATE vector_store_files
        SET embedding_status = %s
        WHERE id = %s
        """
        cursor = self.db.cursor()
        cursor.execute(query, (status, file_id))
        self.db.commit()

    def get_vector_store_id_for_file(self, file_id: str) -> Optional[str]:
        query = """
        SELECT vector_store_id
        FROM vector_store_files
        WHERE id = %s
        """
        cursor = self.db.cursor(pymysql.cursors.DictCursor)
        cursor.execute(query, (file_id,))
        result = cursor.fetchone()
        return result["vector_store_id"] if result else None

    def update_vector_store_embedding_info(self, vector_store_id: str, embedding_model: str, embedding_dimensions: int):
        query = """
        UPDATE vector_stores
        SET embedding_model = %s, embedding_dimensions = %s
        WHERE id = %s
        """
        cursor = self.db.cursor()
        cursor.execute(query, (embedding_model, embedding_dimensions, vector_store_id))
        self.db.commit()
