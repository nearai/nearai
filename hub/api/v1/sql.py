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
from nearai.shared.models import SimilaritySearch, SimilaritySearchFile
from pydantic import BaseModel, RootModel

from hub.api.v1.models import Completion, get_session

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

    def __fetch_one(self, query: str, args: object = None):
        """Fetches one row from the database.

        Returns a dictionary, the dict can be used by Pydantic models.
        """
        cursor = self.db.cursor(pymysql.cursors.DictCursor)
        cursor.execute(query, args)
        return cursor.fetchone()

    def add_user_usage(self, account_id: str, query: str, response: str, model: str, provider: str, endpoint: str):  # noqa: D102
        """Store completion usage data with robust JSON handling.

        Args:
        ----
            account_id: User account identifier
            query: Raw query string or JSON string
            response: Raw response or JSON string
            model: Model identifier
            provider: Provider name
            endpoint: API endpoint used

        """
        # Default usage data
        token_data = {
            "completion_tokens": 0,
            "prompt_tokens": 0,
            "total_tokens": 0,
            "completion_tokens_details": None,
            "prompt_tokens_details": None,
        }

        try:
            response_dict = json.loads(response)
        except Exception as e:
            logger.error(f"Error parsing response JSON: {e}")
            response_dict = {"value": str(response)}

        try:
            query_dict = json.loads(query)
        except Exception as e:
            logger.error(f"Error parsing response JSON: {e}")
            query_dict = {"value": query}

        if isinstance(response_dict, dict) and "usage" in response_dict:
            token_data.update(response_dict["usage"])
        else:
            logger.warning("No usage data found in response")

        completion = Completion(
            account_id=account_id,
            query=query_dict,
            response=response_dict,
            model=model,
            provider=provider,
            endpoint=endpoint,
            completion_tokens=token_data.get("completion_tokens", 0),
            prompt_tokens=token_data.get("prompt_tokens", 0),
            total_tokens=token_data.get("total_tokens", 0),
            completion_tokens_details=token_data.get("completion_tokens_details"),
            prompt_tokens_details=token_data.get("prompt_tokens_details"),
        )

        with get_session() as session:
            session.add(completion)
            session.commit()
            # Refresh to get the auto-generated ID
            session.refresh(completion)

    def get_user_usage(self, account_id: str):  # noqa: D102
        query = "SELECT * FROM completions WHERE account_id = %s"
        return self.__fetch_all(query, (account_id,))

    def store_nonce(self, account_id: str, nonce: bytes, message: str, recipient: str, callback_url: Optional[str]):  # noqa: D102
        logging.info(f"Storing nonce {nonce.decode()} for account {account_id}")
        query = """
        INSERT INTO nonces (nonce, account_id, message, recipient, callback_url, nonce_status)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        self.db.cursor().execute(query, (nonce.decode(), account_id, message, recipient, callback_url, "active"))
        self.db.commit()

    def get_account_nonces(self, account_id: str):  # noqa: D102
        query = "SELECT * FROM nonces WHERE account_id = %s"
        nonces = [UserNonce(**x) for x in self.__fetch_all(query, (account_id,))]
        user_nonces = UserNonces(root=nonces) if nonces else None
        return user_nonces

    def get_account_nonce(self, account_id: str, nonce: bytes):  # noqa: D102
        query = "SELECT * FROM nonces WHERE account_id = %s AND nonce = %s"
        res = self.__fetch_one(query, (account_id, nonce.decode()))
        user_nonce = UserNonce(**res) if res else None
        return user_nonce

    def revoke_nonce(self, account_id: str, nonce: bytes):  # noqa: D102
        logging.info(f"Revoking nonce {nonce.decode()} for account {account_id}")
        query = "UPDATE nonces SET nonce_status = 'revoked' WHERE account_id = %s AND nonce = %s"
        self.db.cursor().execute(query, (account_id, nonce.decode()))
        self.db.commit()

    def revoke_all_nonces(self, account_id):  # noqa: D102
        logging.info(f"Revoking all nonces for account {account_id}")
        query = "UPDATE nonces SET nonce_status = 'revoked' WHERE account_id = %s"
        self.db.cursor().execute(query, (account_id,))
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
        query = "SELECT * FROM vector_stores WHERE id = %s"
        logger.info(f"Querying vector store with id: {vector_store_id}")

        result = self.__fetch_one(query, (vector_store_id,))
        if not result:
            return None

        result["file_ids"] = json.loads(result["file_ids"])
        result["expires_after"] = json.loads(result["expires_after"])
        result["chunking_strategy"] = json.loads(result["chunking_strategy"])
        result["metadata"] = json.loads(result["metadata"]) if result["metadata"] else None
        return VectorStore(**result)

    def get_vector_store_by_account(self, vector_store_id: str, account_id: str) -> Optional[VectorStore]:
        """Get a vector store by account id."""
        query = "SELECT * FROM vector_stores WHERE id = %s AND account_id = %s"

        result = self.__fetch_one(query, (vector_store_id, account_id))
        if not result:
            return None
        result["file_ids"] = json.loads(result["file_ids"])
        result["expires_after"] = json.loads(result["expires_after"])
        result["chunking_strategy"] = json.loads(result["chunking_strategy"])
        result["metadata"] = json.loads(result["metadata"]) if result["metadata"] else None

        return VectorStore(**result)

    def get_vector_stores(self, account_id: str) -> Optional[List[VectorStore]]:
        """Get all vector stores for a given account."""
        query = "SELECT * FROM vector_stores WHERE account_id = %s"
        results = self.__fetch_all(query, (account_id,))

        vector_stores = []
        for result in results:
            result["file_ids"] = json.loads(result["file_ids"])
            result["expires_after"] = json.loads(result["expires_after"])
            result["chunking_strategy"] = json.loads(result["chunking_strategy"])
            result["metadata"] = json.loads(result["metadata"]) if result["metadata"] else None
            vector_stores.append(VectorStore(**result))

        return vector_stores

    def get_user_memory(self, account_id: str) -> Optional[str]:
        """Get the user memory vector store id for a given account."""
        query = "SELECT vector_store_id FROM user_memory WHERE account_id = %s"
        r = self.__fetch_one(query, (account_id,))
        return r["vector_store_id"] if r else None

    def set_user_memory(self, account_id: str, vector_store_id: str):
        """Set the user memory vector store id for a given account."""
        query = "INSERT INTO user_memory (account_id, vector_store_id) VALUES (%s, %s)"
        self.db.cursor().execute(query, (account_id, vector_store_id))
        self.db.commit()

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

    def get_file_details_by_filename(self, vector_store_id: str, filename: str) -> Optional[List[VectorStoreFile]]:
        """Get file details for a specific filename and vector_store_id.

        Args:
        ----
            filename (str): The name of the file.
            vector_store_id (str): The ID of the vector store.

        Returns:
        -------
            Optional[List[VectorStoreFile]]: A list of matching file details if found, None otherwise.

        """
        query = """SELECT * FROM vector_store_files f
                 INNER JOIN vector_store_embeddings e ON f.id = e.file_id
                 WHERE filename = %s AND e.vector_store_id = %s"""
        cursor = self.db.cursor(pymysql.cursors.DictCursor)
        cursor.execute(query, (filename, vector_store_id))
        result = cursor.fetchall()
        return [VectorStoreFile(**res) for res in result] if result else None

    def list_vector_store_files(self, vector_store_id: str) -> Optional[List[VectorStoreFile]]:
        """List file details for a Vector Store by vector_store_id.

        Args:
        ----
            vector_store_id (str): The ID of the vector store.

        Returns:
        -------
            Optional[List[VectorStoreFile]]: A list of matching file details if found, None otherwise.

        """
        query = """SELECT * FROM vector_store_files f
                 INNER JOIN vector_store_embeddings e ON f.id = e.file_id
                 WHERE e.vector_store_id = %s"""
        cursor = self.db.cursor(pymysql.cursors.DictCursor)
        cursor.execute(query, (vector_store_id,))
        result = cursor.fetchall()
        return [VectorStoreFile(**res) for res in result] if result else None

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

    def similarity_search_full_files(
        self, vector_store_id: str, query_embedding: List[float], limit: int = 1
    ) -> List[SimilaritySearchFile]:
        """Perform a similarity search in the vector store and return full files.

        Args:
        ----
            vector_store_id (str): The ID of the vector store to search in.
            query_embedding (List[float]): The query embedding vector.
            limit (int, optional): The maximum number of results to return. Defaults to 1.

        Returns:
        -------
            List[SimilaritySearchFile]: A list of similarity search results where file_content contains the full file.

        """
        query = """
        SELECT f.file_id, f.file_content, s.distance, fd.filename
        FROM (SELECT vse.file_id, max(vse.embedding <-> %s) AS distance
            FROM vector_store_embeddings vse
            WHERE vse.vector_store_id = %s
            GROUP BY vse.file_id
            ORDER BY distance
            LIMIT %s
            ) as s
        INNER JOIN (
            SELECT CONCAT_WS(' ', GROUP_CONCAT(vse.chunk_text ORDER BY vse.chunk_index ASC))
                as file_content, vse.file_id
            FROM vector_store_embeddings vse
            WHERE vse.vector_store_id = %s
            GROUP BY vse.file_id
            ) as f ON s.file_id = f.file_id
        INNER JOIN vector_store_files fd ON fd.id = f.file_id
        """
        query_embedding_json = json.dumps(query_embedding)
        results = [
            SimilaritySearchFile(**res)
            for res in self.__fetch_all(query, (query_embedding_json, vector_store_id, limit, vector_store_id))
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

    def create_hub_secret(
        self,
        owner_namespace: str,
        namespace: str,
        name: str,
        key: str,
        value: str,
        version: Optional[str] = "",
        description: Optional[str] = "",
        category: Optional[str] = "agent",
    ) -> None:
        """Create hub secret."""
        query = """
        INSERT INTO hub_secrets (`owner_namespace`, `namespace`, `name`, `version`, `key`, `value`, `description`,
        `category`)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        cursor = self.db.cursor()
        try:
            cursor.execute(
                query,
                (owner_namespace, namespace, name, version, key, value, description, category),
            )
            self.db.commit()
        except TypeError as e:
            if "dict can not be used as parameter" in str(e):
                raise ValueError(
                    "Invalid data type in parameters. Ensure all dictionary values are JSON serializable."
                ) from e
            raise

    def remove_hub_secret(
        self,
        owner_namespace: str,
        namespace: str,
        name: str,
        key: str,
        version: Optional[str] = "",
        category: Optional[str] = "agent",
    ) -> None:
        """Remove hub secrets."""
        query = """
        DELETE FROM hub_secrets
        WHERE `owner_namespace` = %s
          AND `namespace` = %s
          AND `name` = %s
          AND `version` = %s
          AND `key` = %s
          AND `category` = %s
        """

        parameters = (owner_namespace, namespace, name, version, key, category)

        cursor = self.db.cursor()
        try:
            cursor.execute(query, parameters)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise RuntimeError("Hub secret removal error: " + str(e)) from e

    def get_user_secrets(
        self, owner_namespace: str, limit: Optional[int] = 100, offset: Optional[int] = 0
    ) -> (dict)[Any, Any]:  # noqa: D102
        """Load all hub secrets of the user."""
        query = """
            SELECT `namespace`, `name`, `version`, `description`, `key`, `value`, `category`
            FROM `hub_secrets`
            WHERE `owner_namespace`= %s
             LIMIT %s OFFSET %s
        """

        cursor = self.db.cursor(pymysql.cursors.DictCursor)
        cursor.execute(query, [owner_namespace, limit, offset])
        result = cursor.fetchall()

        return result

    def get_agent_secrets(
        self, owner_namespace: str, namespace: str, name: str, version: str
    ) -> tuple[dict[Any, Any], dict[Any, Any]]:  # noqa: D102
        """Load hub secrets for an agent."""
        query = """
            SELECT `owner_namespace`, `key`, `value`
            FROM `hub_secrets`
            WHERE `owner_namespace` IN %s
              AND `namespace` = %s
              AND `name` = %s
              AND (`version` = %s OR `version` IS NULL OR version = '')
              AND category = 'agent'
        """
        # check both owner secret and agent author's secret
        owner_namespaces = [owner_namespace, namespace]
        params = [tuple(owner_namespaces), namespace, name, version]

        cursor = self.db.cursor(pymysql.cursors.DictCursor)
        cursor.execute(query, params)
        result = cursor.fetchall()

        agent_secrets = {}
        user_secrets = {}

        for secret in result:
            if secret["owner_namespace"] == owner_namespace:
                user_secrets[secret["key"]] = secret["value"]
            else:
                agent_secrets[secret["key"]] = secret["value"]

        return agent_secrets, user_secrets

    def remove_embeddings_from_vector_store(self, vector_store_id: str, file_id: str) -> bool:
        """Remove all embeddings for a specific file from a vector store.

        Args:
        ----
            vector_store_id (str): The ID of the vector store.
            file_id (str): The ID of the file whose embeddings should be removed.

        Returns:
        -------
            bool: True if embeddings were successfully removed, False otherwise.

        """
        cursor = self.db.cursor()
        try:
            query = """
            DELETE FROM vector_store_embeddings
            WHERE vector_store_id = %s AND file_id = %s
            """
            cursor.execute(query, (vector_store_id, file_id))
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error removing embeddings from vector store: {str(e)}")
            self.db.rollback()
            return False

    def remove_file_from_vector_store(
        self, vector_store_id: str, file_id: str, account_id: str
    ) -> Optional[VectorStore]:
        """Remove a file from a vector store and delete its embeddings.

        Args:
        ----
            vector_store_id (str): The ID of the vector store.
            file_id (str): The ID of the file to remove.
            account_id (str): The ID of the account that owns the vector store.

        Returns:
        -------
            Optional[VectorStore]: The updated vector store if successful, None otherwise.

        """
        # First get the current vector store to check ownership and get current file_ids
        vector_store = self.get_vector_store_by_account(vector_store_id, account_id)
        if not vector_store:
            return None

        # Remove the file_id from the list
        updated_file_ids = [fid for fid in vector_store.file_ids if fid != file_id]

        # Remove the embeddings for this file
        if not self.remove_embeddings_from_vector_store(vector_store_id, file_id):
            return None

        # Update the vector store with the new file_ids list
        return self.update_files_in_vector_store(vector_store_id, updated_file_ids, account_id)

    def delete_file(self, file_id: str, account_id: str) -> bool:
        """Delete a file and all its related records from the database.

        This includes:
        - Removing the file from any vector stores that reference it
        - Deleting all embeddings associated with the file
        - Deleting the file record itself

        Args:
        ----
            file_id (str): The ID of the file to delete.
            account_id (str): The ID of the account that owns the file.

        Returns:
        -------
            bool: True if the file was successfully deleted, False otherwise.

        """
        cursor = self.db.cursor()
        try:
            # First verify the file belongs to the account
            file = self.get_file_details_by_account(file_id, account_id)
            if not file:
                logger.warning(f"File {file_id} that belongs to account {account_id} not found")
                return False

            # Get all vector stores that contain this file
            query = """
            SELECT vector_store_id FROM vector_store_embeddings
            WHERE file_id = %s
            """

            cursor.execute(query, (file_id,))
            vector_stores = cursor.fetchall()

            # Remove file from each vector store that references it
            for vs in vector_stores:
                print(f"Removing file {file_id} from vector store {vs[0]}")
                self.remove_file_from_vector_store(vs[0], file_id, account_id)

            # Delete any remaining embeddings for this file
            query = """
            DELETE FROM vector_store_embeddings
            WHERE file_id = %s
            """
            cursor.execute(query, (file_id,))

            # Finally delete the file record
            query = """
            DELETE FROM vector_store_files
            WHERE id = %s AND account_id = %s
            """
            cursor.execute(query, (file_id, account_id))
            self.db.commit()

            # Check if any rows were affected
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {str(e)}")
            self.db.rollback()
            return False
