import logging

import boto3
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import JSONResponse
from openai.types.beta.vector_store import ExpiresAfter as OpenAIExpiresAfter
from openai.types.beta.vector_store import FileCounts, VectorStore
from pydantic import BaseModel
from shared.models import CreateVectorStoreFromSourceRequest, CreateVectorStoreRequest, GitHubSource, GitLabSource

from hub.api.v1.auth import AuthToken, revokable_auth
from hub.api.v1.sql import SqlClient
from hub.tasks.embedding_generation import (
    generate_embedding,
    generate_embeddings_for_file,
)
from hub.tasks.github_import import process_github_source

vector_stores_router = APIRouter(tags=["Vector Stores"])

logger = logging.getLogger(__name__)

s3_client = boto3.client("s3")


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

    expires_at = None
    if vector_store.expires_after and vector_store.expires_after.get("days"):
        expires_at = vector_store.created_at.timestamp() + vector_store.expires_after["days"] * 24 * 60 * 60

    in_progress_files = 0
    completed_files = 0
    total_bytes = 0
    for file_id in vector_store.file_ids:
        file_details = sql_client.get_file_details(file_id)
        if file_details:
            if file_details.embedding_status == "in_progress":
                in_progress_files += 1
            elif file_details.embedding_status == "completed":
                completed_files += 1
            total_bytes += file_details.file_size

    return VectorStore(
        id=str(vector_store.id),
        object="vector_store",
        created_at=int(vector_store.created_at.timestamp()),
        name=vector_store.name,
        file_counts=FileCounts(
            in_progress=in_progress_files,
            completed=completed_files,
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
async def delete_vector_store(vector_store_id: str, auth: AuthToken = Depends(revokable_auth)):
    """Delete a vector store.

    Args:
    ----
        vector_store_id (str): The ID of the vector store to delete.
        auth (AuthToken): The authentication token.

    Returns:
    -------
        JSONResponse: A JSON object with the deletion status.

    Raises:
    ------
        HTTPException: If the vector store is not found or deletion fails.

    """
    logger.info(f"Deleting vector store: {vector_store_id}")
    sql_client = SqlClient()

    # Check if the vector store exists and belongs to the authenticated user
    vector_store = sql_client.get_vector_store_by_account(account_id=auth.account_id, vector_store_id=vector_store_id)
    if not vector_store:
        logger.warning(f"Vector store not found: {vector_store_id}")
        raise HTTPException(status_code=404, detail="Vector store not found")

    try:
        # Delete the vector store
        deleted = sql_client.delete_vector_store(vector_store_id=vector_store_id, account_id=auth.account_id)
        if not deleted:
            raise HTTPException(status_code=500, detail="Failed to delete vector store")

        logger.info(f"Vector store deleted successfully: {vector_store_id}")
        return JSONResponse(
            content={"id": vector_store_id, "object": "vector_store.deleted", "deleted": True}, status_code=200
        )
    except Exception as e:
        logger.error(f"Error deleting vector store: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete vector store") from e


class VectorStoreFileCreate(BaseModel):
    """Request model for creating a vector store file."""

    file_id: str
    """File ID returned from upload file endpoint."""


@vector_stores_router.post("/vector_stores/{vector_store_id}/files")
async def create_vector_store_file(
    vector_store_id: str,
    file_data: VectorStoreFileCreate,
    background_tasks: BackgroundTasks,
    auth: AuthToken = Depends(revokable_auth),
):
    """Attach a file to an existing vector store and initiate embedding generation.

    Args:
    ----
        vector_store_id (str): The ID of the vector store to attach the file to.
        file_data (VectorStoreFileCreate): The file data containing the file_id to attach.
        background_tasks (BackgroundTasks): FastAPI background tasks for asynchronous processing.
        auth (AuthToken): The authentication token for the current user.

    Returns:
    -------
        VectorStore: The updated vector store object with the newly attached file.

    Raises:
    ------
        HTTPException:
            - 404 if the vector store is not found.
            - 500 if file attachment fails or if there's an error updating the vector store.

    Notes:
    -----
        - This function updates the vector store by adding the new file_id to its list of files.
        - It queues a background task to generate embeddings for the newly attached file.
        - The vector store's status is set to "in_progress" as embedding generation begins.

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

    total_bytes = 0
    in_progress_files = 0
    completed_files = 0
    for file_id in updated_vector_store.file_ids:
        file_details = sql_client.get_file_details(file_id)
        if file_details:
            total_bytes += file_details.file_size
            if file_details.embedding_status == "in_progress":
                in_progress_files += 1
            elif file_details.embedding_status == "completed":
                completed_files += 1

    expires_at = None
    if updated_vector_store.expires_after and updated_vector_store.expires_after.get("days"):
        expires_at = (
            updated_vector_store.created_at.timestamp() + updated_vector_store.expires_after["days"] * 24 * 60 * 60
        )

    logger.info(f"Queueing embedding generation for file in vector store: {vector_store_id}")
    background_tasks.add_task(generate_embeddings_for_file, file_data.file_id, vector_store_id)
    logger.info(f"Embedding generation queued for file: {file_data.file_id}")

    return VectorStore(
        id=str(updated_vector_store.id),
        object="vector_store",
        created_at=int(updated_vector_store.created_at.timestamp()),
        name=updated_vector_store.name,
        file_counts=FileCounts(
            in_progress=in_progress_files,
            completed=completed_files,
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
    vector_store_id: str, request: QueryVectorStoreRequest, _: AuthToken = Depends(revokable_auth)
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
        vector_store = sql.get_vector_store(vector_store_id)
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


@vector_stores_router.post("/vector_stores/from_source", response_model=VectorStore)
async def create_vector_store_from_source(
    request: CreateVectorStoreFromSourceRequest,
    background_tasks: BackgroundTasks,
    auth: AuthToken = Depends(revokable_auth),
):
    """Create a new vector store from a source (currently only GitHub).

    Args:
    ----
        request (CreateVectorStoreFromSourceRequest): The request containing vector store and source details.
        background_tasks (BackgroundTasks): FastAPI background tasks.
        auth (AuthToken): The authentication token.

    Returns:
    -------
        VectorStore: The created vector store object.

    Raises:
    ------
        HTTPException: If the vector store creation fails.

    """
    logger.info(f"Creating vector store from source: {request.name}")

    sql_client = SqlClient()
    vector_store_id = sql_client.create_vector_store(
        account_id=auth.account_id,
        name=request.name,
        file_ids=[],
        expires_after=request.expires_after.model_dump() if request.expires_after else None,
        chunking_strategy=request.chunking_strategy.model_dump() if request.chunking_strategy else None,
        metadata=request.metadata,
    )

    # Start the background task to process files from the source
    if isinstance(request.source, GitHubSource):
        background_tasks.add_task(
            process_github_source, request.source, vector_store_id, auth.account_id, request.source_auth
        )
    elif isinstance(request.source, GitLabSource):
        # unimplemented; example:
        # background_tasks.add_task(
        #     process_gitlab_source, request.source, vector_store_id, auth.account_id, request.source_auth
        # )
        raise HTTPException(status_code=400, detail="Unsupported source type")
    else:
        raise HTTPException(status_code=400, detail="Unsupported source type")

    vector_store = sql_client.get_vector_store(vector_store_id=vector_store_id)
    if not vector_store:
        logger.error(f"Failed to retrieve created vector store: {vector_store_id}")
        raise HTTPException(status_code=404, detail="Vector store not found")

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
            in_progress=1,  # Set to 1 as we're starting the background task
            completed=0,
            failed=0,
            cancelled=0,
            total=1,
        ),
        metadata=vector_store.metadata,
        last_active_at=int(vector_store.updated_at.timestamp()),
        usage_bytes=0,
        status="in_progress",
        expires_after=OpenAIExpiresAfter(**vector_store.expires_after) if vector_store.expires_after else None,
        expires_at=expires_at,
    )
