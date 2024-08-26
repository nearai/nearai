import logging
from typing import Dict, List, Literal, Optional

import openai
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from openai.types.beta.vector_store import VectorStore
from openai.types.file_create_params import FileTypes
from openai.types.file_object import FileObject
from pydantic import BaseModel

from hub.api.v1.auth import AuthToken, revokable_auth
from hub.api.v1.sql import SqlClient

vector_stores_router = APIRouter(
    tags=["Vector Stores"],
)
files_router = APIRouter(
    tags=["Files"],
)

logger = logging.getLogger(__name__)

"""
OpenAI approach:
1. Create vector store
2. Upload file, returns file_id
3. Attach to vector store by file_id
4. Use vector store in assistants
"""


class ChunkingStrategy(BaseModel):
    pass


class ExpiresAfter(BaseModel):
    anchor: Literal["last_active_at"]
    """The expiration time for the vector store."""
    days: int
    """The expiration time for the vector store."""


class CreateVectorStoreRequest(BaseModel):
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


vector_stores_router = APIRouter(
    tags=["Vector Stores"],
)


@vector_stores_router.post("/vector_stores", response_model=VectorStore)
async def create_vector_store(request: CreateVectorStoreRequest, auth: AuthToken = Depends(revokable_auth)):
    """Create a vector store.

    This endpoint creates a new vector store using the provided parameters.
    """
    logger.info(f"Received request to create vector store: {request}")

    # Create SQL client
    sql_client = SqlClient()

    # Add vector store to the database
    vector_store_id = sql_client.create_vector_store(
        account_id=auth.account_id,  # You might want to get this from the authenticated user
        name=request.name or "Unnamed Vector Store",
        file_ids=request.file_ids or [],
        expires_after=request.expires_after.model_dump() if request.expires_after else None,
        chunking_strategy=request.chunking_strategy.model_dump() if request.chunking_strategy else None,
        metadata=request.metadata,
    )

    # Retrieve the created vector store from the database
    vector_store = sql_client.get_vector_store(account_id=auth.account_id, vector_store_id=vector_store_id)
    logger.info(f"Retrieved vector store: {vector_store}")

    if not vector_store:
        raise HTTPException(status_code=404, detail="Vector store not found")

    # Calculate the total bytes (this is a placeholder, you might want to implement a proper calculation)
    total_bytes = sum(len(file_id) for file_id in vector_store.file_ids)

    expires_at = None
    if vector_store.expires_after and vector_store.expires_after["days"]:
        expires_at = vector_store.created_at.timestamp() + vector_store.expires_after["days"] * 24 * 60 * 60

    return VectorStore(
        id=str(vector_store.id),
        object="vector_store",
        created_at=int(vector_store.created_at.timestamp()),
        name=vector_store.name,
        file_counts={
            "in_progress": 0,
            "completed": len(vector_store.file_ids),
            "failed": 0,
            "cancelled": 0,
            "total": len(vector_store.file_ids),
        },
        metadata=vector_store.metadata,
        last_active_at=int(vector_store.updated_at.timestamp()),
        usage_bytes=total_bytes,
        status="completed",
        expires_after=vector_store.expires_after if vector_store.expires_after else None,
        expires_at=expires_at,
    )


@vector_stores_router.get("/vector_stores")
async def list_vector_stores():
    """Returns a list of vector stores."""
    client = openai.beta.vector_stores.files.upload_and_poll()
    pass


@vector_stores_router.get("/vector_stores/{vector_store_id}")
async def get_vector_store(vector_store_id: int, auth: AuthToken = Depends(revokable_auth)):
    """Retrieves a specific vector store."""
    logger.info(f"Received request to get vector store with ID: {vector_store_id}")

    # Create SQL client
    sql_client = SqlClient()

    # Retrieve the vector store from the database
    vector_store = sql_client.get_vector_store(account_id=auth.account_id, vector_store_id=vector_store_id)
    logger.info(f"Retrieved vector store: {vector_store}")

    if not vector_store:
        raise HTTPException(status_code=404, detail="Vector store not found")

    # Calculate the total bytes (this is a placeholder, you might want to implement a proper calculation)
    total_bytes = sum(len(file_id) for file_id in vector_store.file_ids)

    expires_at = None
    if vector_store.expires_after and vector_store.expires_after["days"]:
        expires_at = vector_store.created_at.timestamp() + vector_store.expires_after["days"] * 24 * 60 * 60
    # Prepare the response
    return VectorStore(
        id=str(vector_store.id),
        object="vector_store",
        created_at=int(vector_store.created_at.timestamp()),
        name=vector_store.name,
        file_counts={
            "in_progress": 0,
            "completed": len(vector_store.file_ids),
            "failed": 0,
            "cancelled": 0,
            "total": len(vector_store.file_ids),
        },
        metadata=vector_store.metadata,
        last_active_at=int(vector_store.updated_at.timestamp()),
        usage_bytes=total_bytes,
        status="completed",
        expires_after=vector_store.expires_after if vector_store.expires_after else None,
        expires_at=expires_at,
    )


@vector_stores_router.patch("/vector_stores/{vector_store_id}")
async def update_vector_store():
    """Modifies a vector store."""
    pass


@vector_stores_router.delete("/vector_stores/{vector_store_id}")
async def delete_vector_store():
    """Delete a vector store."""
    pass


class FileUploadRequest(BaseModel):
    file: FileTypes
    purpose: Literal["assistants", "batch", "fine-tune", "vision"]

    class Config:
        arbitrary_types_allowed = True


@files_router.post("/files")
async def upload_file(
    file: UploadFile = File(...), purpose: str = Form(...), auth: AuthToken = Depends(revokable_auth)
) -> FileObject:
    """Upload a file to the vector store."""
    logger.info(f"Received file upload request from user: {auth.account_id}")

    # Validate purpose
    valid_purposes = ["assistants", "batch", "fine-tune", "vision"]
    if purpose not in valid_purposes:
        raise HTTPException(status_code=400, detail=f"Invalid purpose. Must be one of: {', '.join(valid_purposes)}")

    # Store the file temporarily
    import tempfile

    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, mode="wb") as temp_file:
        logger.info("Creating temporary file for upload")
        # Write the content of the uploaded file to the temporary file
        content = await file.read()
        temp_file.write(content)

        temp_file_path = temp_file.name
        logger.info(f"Temporary file created at: {temp_file_path}")

    sql_client = SqlClient()
    file_id = sql_client.create_file(account_id=auth.account_id, file_path=temp_file_path, purpose=purpose)
    file_details = sql_client.get_file_details(file_id=file_id, account_id=auth.account_id)

    return FileObject(
        id=str(file_id),
        bytes=file.size,
        created_at=file_details.created_at.timestamp(),
        filename=file.filename,
        object="file",
        purpose=purpose,
        status="uploaded",
        status_details="TBD",
    )
