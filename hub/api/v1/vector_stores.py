import logging
from typing import Dict, List, Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from openai.types.beta.vector_store import ExpiresAfter as OpenAIExpiresAfter
from openai.types.beta.vector_store import FileCounts, VectorStore
from openai.types.file_create_params import FileTypes
from openai.types.file_object import FileObject
from pydantic import BaseModel

from hub.api.v1.auth import AuthToken, revokable_auth
from hub.api.v1.sql import SqlClient
from hub.background.task_queue import set_background_tasks
from hub.tasks.embedding_generation import generate_embedding, generate_embeddings_for_vector_store

vector_stores_router = APIRouter(tags=["Vector Stores"])
files_router = APIRouter(tags=["Files"])

logger = logging.getLogger(__name__)


class ChunkingStrategy(BaseModel):
    """Defines the chunking strategy for vector stores."""

    pass


class ExpiresAfter(BaseModel):
    """Defines the expiration policy for vector stores."""

    anchor: Literal["last_active_at"]
    """The anchor point for expiration calculation."""
    days: int
    """The number of days after which the vector store expires."""


class CreateVectorStoreRequest(BaseModel):
    """Request model for creating a new vector store."""

    chunking_strategy: Optional[ChunkingStrategy] = None
    """The chunking strategy to use for the vector store."""
    expires_after: Optional[ExpiresAfter] = None
    """The expiration time for the vector store."""
    file_ids: Optional[List[str]] = None
    """The file IDs to attach to the vector store."""
    metadata: Optional[Dict[str, str]] = None
    """The metadata to attach to the vector store."""
    name: str
    """The name of the vector store."""


@vector_stores_router.post("/vector_stores", response_model=VectorStore)
async def create_vector_store(
    request: CreateVectorStoreRequest, background_tasks: BackgroundTasks, auth: AuthToken = Depends(revokable_auth)
):
    """Create a new vector store.

    Args:
    ----
        request (CreateVectorStoreRequest): The request containing vector store details.
        background_tasks (BackgroundTasks): FastAPI background tasks.
        auth (AuthToken): The authentication token.

    Returns:
    -------
        VectorStore: The created vector store object.

    Raises:
    ------
        HTTPException: If the vector store creation fails.

    """
    set_background_tasks(background_tasks)
    logger.info(f"Creating vector store: {request.name}")

    sql_client = SqlClient()
    vector_store_id = sql_client.create_vector_store(
        account_id=auth.account_id,
        name=request.name,
        file_ids=request.file_ids or [],
        expires_after=request.expires_after.model_dump() if request.expires_after else None,
        chunking_strategy=request.chunking_strategy.model_dump() if request.chunking_strategy else None,
        metadata=request.metadata,
    )

    vector_store = sql_client.get_vector_store(vector_store_id=vector_store_id)
    if not vector_store:
        logger.error(f"Failed to retrieve created vector store: {vector_store_id}")
        raise HTTPException(status_code=404, detail="Vector store not found")

    total_bytes = sum(len(file_id) for file_id in vector_store.file_ids)
    expires_at = None
    if vector_store.expires_after and vector_store.expires_after.get("days"):
        expires_at = vector_store.created_at.timestamp() + vector_store.expires_after["days"] * 24 * 60 * 60

    logger.info(f"Vector store created successfully: {vector_store_id}")
    return VectorStore(
        id=str(vector_store.id),
        object="vector_store",
        created_at=int(vector_store.created_at.timestamp()),
        name=vector_store.name,
        file_counts=FileCounts(
            in_progress=0,
            completed=len(vector_store.file_ids),
            failed=0,
            cancelled=0,
            total=len(vector_store.file_ids),
        ),
        metadata=vector_store.metadata,
        last_active_at=int(vector_store.updated_at.timestamp()),
        usage_bytes=total_bytes,
        status="in_progress",
        expires_after=OpenAIExpiresAfter(**vector_store.expires_after) if vector_store.expires_after else None,
        expires_at=expires_at,
    )


@vector_stores_router.get("/vector_stores")
async def list_vector_stores(auth: AuthToken = Depends(revokable_auth)):
    """List all vector stores for the authenticated account.

    Args:
    ----
        auth (AuthToken): The authentication token.

    Returns:
    -------
        List[VectorStore]: A list of vector stores.

    """
    logger.info(f"Listing vector stores for account: {auth.account_id}")
    sql_client = SqlClient()
    vector_stores = sql_client.get_vector_stores(account_id=auth.account_id)
    return vector_stores


@vector_stores_router.get("/vector_stores/{vector_store_id}")
async def get_vector_store(vector_store_id: str, auth: AuthToken = Depends(revokable_auth)):
    """Retrieve a specific vector store.

    Args:
    ----
        vector_store_id (str): The ID of the vector store to retrieve.
        auth (AuthToken): The authentication token.

    Returns:
    -------
        VectorStore: The requested vector store.

    Raises:
    ------
        HTTPException: If the vector store is not found.

    """
    logger.info(f"Retrieving vector store: {vector_store_id}")
    sql_client = SqlClient()
    vector_store = sql_client.get_vector_store_by_account(account_id=auth.account_id, vector_store_id=vector_store_id)

    if not vector_store:
        logger.warning(f"Vector store not found: {vector_store_id}")
        raise HTTPException(status_code=404, detail="Vector store not found")

    total_bytes = sum(len(file_id) for file_id in vector_store.file_ids)
    expires_at = None
    if vector_store.expires_after and vector_store.expires_after.get("days"):
        expires_at = vector_store.created_at.timestamp() + vector_store.expires_after["days"] * 24 * 60 * 60

    return VectorStore(
        id=str(vector_store.id),
        object="vector_store",
        created_at=int(vector_store.created_at.timestamp()),
        name=vector_store.name,
        file_counts=FileCounts(
            in_progress=0,
            completed=len(vector_store.file_ids),
            failed=0,
            cancelled=0,
            total=len(vector_store.file_ids),
        ),
        metadata=vector_store.metadata,
        last_active_at=int(vector_store.updated_at.timestamp()),
        usage_bytes=total_bytes,
        status="completed",
        expires_after=OpenAIExpiresAfter(**vector_store.expires_after) if vector_store.expires_after else None,
        expires_at=expires_at,
    )


@vector_stores_router.patch("/vector_stores/{vector_store_id}")
async def update_vector_store():
    """Update a vector store. (Not implemented).

    This endpoint is a placeholder for future implementation.
    """
    logger.info("Update vector store endpoint called")
    pass


@vector_stores_router.delete("/vector_stores/{vector_store_id}")
async def delete_vector_store():
    """Delete a vector store. (Not implemented).

    This endpoint is a placeholder for future implementation.
    """
    logger.info("Delete vector store endpoint called")
    pass


class FileUploadRequest(BaseModel):
    """Request model for file upload."""

    file: FileTypes
    """The file to be uploaded."""
    purpose: Literal["assistants", "batch", "fine-tune", "vision"]
    """The purpose of the file upload."""

    class Config:
        arbitrary_types_allowed = True


@files_router.post("/files")
async def upload_file(
    file: UploadFile = File(...),
    purpose: Literal["assistants", "batch", "fine-tune", "vision"] = Form(...),
    auth: AuthToken = Depends(revokable_auth),
) -> FileObject:
    """Upload a file to the system.

    Args:
    ----
        file (UploadFile): The file to be uploaded.
        purpose (str): The purpose of the file upload.
        auth (AuthToken): The authentication token.

    Returns:
    -------
        FileObject: The uploaded file object.

    Raises:
    ------
        HTTPException: If the purpose is invalid or file upload fails.

    """
    logger.info(f"File upload request received for user: {auth.account_id}")

    valid_purposes = ["assistants", "batch", "fine-tune", "vision"]
    if purpose not in valid_purposes:
        logger.warning(f"Invalid purpose provided: {purpose}")
        raise HTTPException(status_code=400, detail=f"Invalid purpose. Must be one of: {', '.join(valid_purposes)}")

    import tempfile

    with tempfile.NamedTemporaryFile(delete=False, mode="wb") as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_file_path = temp_file.name
        logger.debug(f"Temporary file created: {temp_file_path}")

    sql_client = SqlClient()
    file_id = sql_client.create_file(account_id=auth.account_id, file_path=temp_file_path, purpose=purpose)
    file_details = sql_client.get_file_details_by_account(file_id=file_id, account_id=auth.account_id)

    if not file_details:
        logger.error(f"File details not found for file_id: {file_id}")
        raise HTTPException(status_code=404, detail="File details not found")

    logger.info(f"File uploaded successfully: {file_id}")
    return FileObject(
        id=str(file_id),
        bytes=file.size or 0,
        created_at=int(file_details.created_at.timestamp()),
        filename=file.filename or "",
        object="file",
        purpose=purpose,
        status="uploaded",
        status_details="TBD",
    )


class VectorStoreFileCreate(BaseModel):
    """Request model for creating a vector store file."""

    file_id: str
    """File ID returned from upload file endpoint."""


@vector_stores_router.post("/vector_stores/{vector_store_id}/files")
async def create_vector_store_file(
    vector_store_id: str, file_data: VectorStoreFileCreate, auth: AuthToken = Depends(revokable_auth)
):
    """Attach a file to an existing vector store.

    Args:
    ----
        vector_store_id (str): The ID of the vector store.
        file_data (VectorStoreFileCreate): The file data to attach.
        auth (AuthToken): The authentication token.

    Returns:
    -------
        VectorStore: The updated vector store object.

    Raises:
    ------
        HTTPException: If the vector store is not found or file attachment fails.

    """
    logger.info(f"Attaching file to vector store: {vector_store_id}")

    sql_client = SqlClient()
    vector_store = sql_client.get_vector_store_by_account(vector_store_id=vector_store_id, account_id=auth.account_id)
    if not vector_store:
        logger.warning(f"Vector store not found: {vector_store_id}")
        raise HTTPException(status_code=404, detail="Vector store not found")

    file_ids = vector_store.file_ids + [file_data.file_id]
    updated_vector_store = sql_client.update_files_in_vector_store(
        vector_store_id=vector_store_id, file_ids=file_ids, account_id=auth.account_id
    )

    if not updated_vector_store:
        raise HTTPException(status_code=500, detail="Failed to attach file to vector store")

    total_bytes = sum(len(file_id) for file_id in updated_vector_store.file_ids)

    expires_at = None
    if updated_vector_store.expires_after and updated_vector_store.expires_after.get("days"):
        expires_at = (
            updated_vector_store.created_at.timestamp() + updated_vector_store.expires_after["days"] * 24 * 60 * 60
        )

    logger.info(f"Generating embeddings for vector store: {vector_store_id}")
    await generate_embeddings_for_vector_store(vector_store_id)

    return VectorStore(
        id=str(updated_vector_store.id),
        object="vector_store",
        created_at=int(updated_vector_store.created_at.timestamp()),
        name=updated_vector_store.name,
        file_counts=FileCounts(
            in_progress=0,
            completed=len(updated_vector_store.file_ids),
            failed=0,
            cancelled=0,
            total=len(updated_vector_store.file_ids),
        ),
        metadata=updated_vector_store.metadata,
        last_active_at=int(updated_vector_store.updated_at.timestamp()),
        usage_bytes=total_bytes,
        status="in_progress",
        expires_after=OpenAIExpiresAfter(**updated_vector_store.expires_after)
        if updated_vector_store.expires_after
        else None,
        expires_at=expires_at,
    )


class QueryVectorStoreRequest(BaseModel):
    """Request model for querying a vector store."""

    query: str
    """Text to run similarity search on."""


@vector_stores_router.post("/vector_stores/{vector_store_id}/search")
async def query_vector_store(
    vector_store_id: str, request: QueryVectorStoreRequest, auth: AuthToken = Depends(revokable_auth)
):
    """Perform a similarity search on the specified vector store.

    Args:
    ----
        vector_store_id (str): The ID of the vector store to search.
        request (QueryVectorStoreRequest): The request containing the query text.
        auth (AuthToken): The authentication token for the request.

    Returns:
    -------
        List[Dict]: A list of search results, each containing the document content and metadata.

    Raises:
    ------
        HTTPException: If the vector store is not found or if there's an error during the search.

    """
    sql = SqlClient()
    try:
        vector_store = sql.get_vector_store_by_account(vector_store_id, auth.account_id)
        if not vector_store:
            logger.warning(f"Vector store not found: {vector_store_id}")
            raise HTTPException(status_code=404, detail="Vector store not found")

        emb = await generate_embedding(request.query, query=True)
        results = sql.similarity_search(vector_store_id, emb)

        logger.info(f"Similarity search completed for vector store: {vector_store_id}")
        return results
    except Exception as e:
        logger.error(f"Error querying vector store: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to query vector store") from None
