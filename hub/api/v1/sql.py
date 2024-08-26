import json
import logging
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
    id: int
    account_id: str
    name: str
    file_ids: List[str]
    expires_after: Dict[str, Any]
    chunking_strategy: Dict[str, Any]
    metadata: Optional[Dict[str, str]] = None
    created_at: datetime
    updated_at: datetime


class VectorStoreFile(BaseModel):
    id: int
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
    ) -> int:
        query = """
        INSERT INTO vector_stores (account_id, name, file_ids, expires_after, chunking_strategy, metadata)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        print(expires_after)
        print(f"DB query: {query} params: {account_id, name, file_ids, expires_after, chunking_strategy, metadata}")
        cursor = self.db.cursor()
        try:
            cursor.execute(
                query,
                (
                    account_id,
                    name,
                    json.dumps(file_ids if file_ids else []),
                    json.dumps(expires_after if expires_after else {}),
                    json.dumps(chunking_strategy if chunking_strategy else {}),
                    json.dumps(metadata if metadata else {}),
                ),
            )
            vector_store_id = cursor.lastrowid
            self.db.commit()
            return vector_store_id
        except TypeError as e:
            if "dict can not be used as parameter" in str(e):
                raise ValueError(
                    "Invalid data type in parameters. Ensure all dictionary values are JSON serializable."
                ) from e
            raise

    def get_vector_store(self, account_id: str, vector_store_id: int) -> Optional[VectorStore]:  # noqa: D102
        query = f"SELECT * FROM vector_stores WHERE id = {vector_store_id} AND account_id = '{account_id}'"
        logger.info(f"Querying vector store: {query}")

        result = self.__fetch_one(query)
        if not result:
            return None

        result["file_ids"] = json.loads(result["file_ids"])
        result["expires_after"] = json.loads(result["expires_after"])
        result["chunking_strategy"] = json.loads(result["chunking_strategy"])
        result["metadata"] = json.loads(result["metadata"]) if result["metadata"] else None
        return VectorStore(**result)

    def create_file(self, account_id: str, file_path: str, purpose: str) -> int:
        query = """
        INSERT INTO vector_store_files (account_id, file_path, purpose)
        VALUES (%s, %s, %s)
        """
        cursor = self.db.cursor()
        cursor.execute(query, (account_id, file_path, purpose))
        file_id = cursor.lastrowid
        self.db.commit()
        return file_id

    def get_file_details(self, file_id: int, account_id: str) -> Optional[VectorStoreFile]:
        query = f"SELECT * FROM vector_store_files WHERE id = {file_id} AND account_id = '{account_id}'"
        result = self.__fetch_one(query)
        return VectorStoreFile(**result) if result else None
