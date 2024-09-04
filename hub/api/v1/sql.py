import json
import logging
import uuid
from datetime import datetime
from enum import Enum
from os import getenv
from typing import Any, Dict, List, Literal, Optional

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


class VectorStoreStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


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
    status: VectorStoreStatus


class VectorStoreFile(BaseModel):
    id: str
    account_id: str
    file_uri: str
    purpose: str
    filename: str
    content_type: str
    file_size: int
    encoding: Optional[str]
    created_at: datetime
    updated_at: datetime
    embedding_status: Optional[Literal["in_progress", "completed"]]


class SimilaritySearch(BaseModel):
    file_id: str
    chunk_text: str
    distance: float


class SqlClient:
    def __init__(self):  # noqa: D107
        self.db = pymysql.connect(
            host=getenv("DATABASE_HOST"),
            user=getenv("DATABASE_USER"),
            password=getenv("DATABASE_PASSWORD"),
            database=getenv("DATABASE_NAME"),
            autocommit=True,
        )

    def __fetch_all(self, query: str, args: object = None):
        """Fetches all matching rows from the database.

        Returns a list of dictionaries, the dicts can be used by Pydantic models.
        """
        cursor = self.db.cursor(pymysql.cursors.DictCursor)
        cursor.execute(query, args)
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
        """Create a new vector store.

        Args:
        ----
            account_id (str): The ID of the account creating the vector store.
            name (str): The name of the vector store.
            file_ids (List[str]): List of file IDs associated with the vector store.
            expires_after (Optional[Dict[str, Any]], optional): Expiration settings. Defaults to None.
            chunking_strategy (Optional[Dict[str, Any]], optional): Chunking strategy settings. Defaults to None.
            metadata (Optional[Dict[str, str]], optional): Additional metadata. Defaults to None.

        Returns:
        -------
            str: The ID of the created vector store.

        Raises:
        ------
            ValueError: If any dictionary values are not JSON serializable.

        """
        vs_id = f"vs_{uuid.uuid4().hex[:24]}"

        query = """
        INSERT INTO vector_stores (id, account_id, name, file_ids, expires_after, chunking_strategy, metadata)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
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

    def create_file(
        self,
        account_id: str,
        file_uri: str,
        purpose: str,
        filename: str,
        content_type: str,
        file_size: int,
        encoding: Optional[str] = None,
        embedding_status: Optional[Literal["in_progress", "completed"]] = None,
    ) -> str:
        """Add file details to the vector store.

        Args:
        ----
            account_id (str): The ID of the account associated with the file.
            file_uri (str): The URI of the file.
            purpose (str): The purpose of the file.
            filename (str): The name of the file.
            content_type (str): The content type of the file.
            file_size (int): The size of the file in bytes.
            encoding (Optional[str], optional): The encoding of the file. Defaults to None.
            embedding_status (Optional[Literal["in_progress", "completed"]], optional): The status of the embedding
            process. Defaults to None.

        Returns:
        -------
            str: The generated file ID.

        """
        file_id = f"file_{uuid.uuid4().hex[:24]}"

        query = """
        INSERT INTO vector_store_files (id, account_id, file_uri, purpose, filename, content_type, file_size, encoding, embedding_status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """  # noqa: E501

        cursor = self.db.cursor()
        cursor.execute(
            query,
            (file_id, account_id, file_uri, purpose, filename, content_type, file_size, encoding, embedding_status),
        )
        self.db.commit()
        return file_id

    def get_file_details_by_account(self, file_id: str, account_id: str) -> Optional[VectorStoreFile]:
        """Get file details for a specific file and account.

        Args:
        ----
            file_id (str): The ID of the file.
            account_id (str): The ID of the account.

        Returns:
        -------
            Optional[VectorStoreFile]: The file details if found, None otherwise.

        """
        query = "SELECT * FROM vector_store_files WHERE id = %s AND account_id = %s"
        cursor = self.db.cursor(pymysql.cursors.DictCursor)
        cursor.execute(query, (file_id, account_id))
        result = cursor.fetchone()
        return VectorStoreFile(**result) if result else None

    def get_file_details(self, file_id: str) -> Optional[VectorStoreFile]:
        """Get file details for a specific file.

        Args:
        ----
            file_id (str): The ID of the file.

        Returns:
        -------
            Optional[VectorStoreFile]: The file details if found, None otherwise.

        """
        query = "SELECT * FROM vector_store_files WHERE id = %s"
        cursor = self.db.cursor(pymysql.cursors.DictCursor)
        cursor.execute(query, (file_id,))
        result = cursor.fetchone()
        return VectorStoreFile(**result) if result else None

    def update_files_in_vector_store(
        self, vector_store_id: str, file_ids: List[str], account_id: str
    ) -> Optional[VectorStore]:
        """Update the files associated with a vector store.

        Args:
        ----
            vector_store_id (str): The ID of the vector store.
            file_ids (List[str]): The updated list of file IDs.
            account_id (str): The ID of the account.

        Returns:
        -------
            Optional[VectorStore]: The updated vector store if successful, None otherwise.

        """
        query = "UPDATE vector_stores SET file_ids = %s WHERE id = %s AND account_id = %s"
        cursor = self.db.cursor()
        cursor.execute(query, (json.dumps(file_ids), vector_store_id, account_id))
        self.db.commit()
        return self.get_vector_store(vector_store_id)

    def store_embedding(
        self, id: str, vector_store_id: str, file_id: str, chunk_index: int, chunk_text: str, embedding: List[float]
    ):
        """Store an embedding for a chunk of text.

        Args:
        ----
            id (str): The ID of the embedding.
            vector_store_id (str): The ID of the vector store.
            file_id (str): The ID of the file.
            chunk_index (int): The index of the chunk.
            chunk_text (str): The text of the chunk.
            embedding (List[float]): The embedding vector.

        """
        query = """
        INSERT INTO vector_store_embeddings
        (id, vector_store_id, file_id, chunk_index, chunk_text, embedding)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor = self.db.cursor()
        cursor.execute(query, (id, vector_store_id, file_id, chunk_index, chunk_text, json.dumps(embedding)))
        self.db.commit()

    def update_file_embedding_status(self, file_id: str, status: str):
        """Update the embedding status of a file.

        Args:
        ----
            file_id (str): The ID of the file.
            status (str): The new embedding status.

        """
        query = """
        UPDATE vector_store_files
        SET embedding_status = %s
        WHERE id = %s
        """
        cursor = self.db.cursor()
        cursor.execute(query, (status, file_id))
        self.db.commit()

    def get_vector_store_id_for_file(self, file_id: str) -> Optional[str]:
        """Get the vector store ID associated with a file.

        Args:
        ----
            file_id (str): The ID of the file.

        Returns:
        -------
            Optional[str]: The vector store ID if found, None otherwise.

        """
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
        """Update the embedding information for a vector store.

        Args:
        ----
            vector_store_id (str): The ID of the vector store.
            embedding_model (str): The name of the embedding model used.
            embedding_dimensions (int): The number of dimensions in the embedding.

        """
        query = """
        UPDATE vector_stores
        SET embedding_model = %s, embedding_dimensions = %s
        WHERE id = %s
        """
        cursor = self.db.cursor()
        cursor.execute(query, (embedding_model, embedding_dimensions, vector_store_id))
        self.db.commit()

    def similarity_search(
        self, vector_store_id: str, query_embedding: List[float], limit: int = 10
    ) -> List[SimilaritySearch]:
        """Perform a similarity search in the vector store.

        Args:
        ----
            vector_store_id (str): The ID of the vector store to search in.
            query_embedding (List[float]): The query embedding vector.
            limit (int, optional): The maximum number of results to return. Defaults to 10.

        Returns:
        -------
            List[SimilaritySearch]: A list of similarity search results.

        """
        query = """
        SELECT vse.file_id, vse.chunk_text, vse.embedding <-> %s AS distance
        FROM vector_store_embeddings vse
        WHERE vse.vector_store_id = %s
        ORDER BY distance
        LIMIT %s
        """
        query_embedding_json = json.dumps(query_embedding)
        results = [
            SimilaritySearch(**res) for res in self.__fetch_all(query, (query_embedding_json, vector_store_id, limit))
        ]
        return results

    def delete_vector_store(self, vector_store_id: str, account_id: str) -> bool:
        """Delete a vector store and its embeddings from the database.

        Args:
        ----
            vector_store_id (str): The ID of the vector store to delete.
            account_id (str): The ID of the account that owns the vector store.

        Returns:
        -------
            bool: True if the vector store was successfully deleted, False otherwise.

        """
        cursor = self.db.cursor()
        try:
            # Delete embeddings first
            embeddings_query = """
            DELETE FROM vector_store_embeddings
            WHERE vector_store_id = %s
            """
            cursor.execute(embeddings_query, (vector_store_id,))

            # Then delete the vector store
            vector_store_query = """
            DELETE FROM vector_stores
            WHERE id = %s AND account_id = %s
            """
            cursor.execute(vector_store_query, (vector_store_id, account_id))

            self.db.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting vector store and its embeddings: {str(e)}")
            self.db.rollback()
            return False
