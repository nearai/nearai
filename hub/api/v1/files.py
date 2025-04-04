import io
import logging
import mimetypes
import os
import uuid
from os import getenv
from typing import Literal, Tuple

import boto3
import chardet
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, UploadFile
from fastapi.responses import StreamingResponse
from nearai.config import DATA_FOLDER
from openai.types.file_create_params import FileTypes
from openai.types.file_object import FileObject
from pydantic import BaseModel

from hub.api.v1.auth import AuthToken, get_auth
from hub.api.v1.models import (
    FILE_URI_PREFIX,
    S3_BUCKET,
    S3_URI_PREFIX,
    STORAGE_TYPE,
    SUPPORTED_MIME_TYPES,
    SUPPORTED_TEXT_ENCODINGS,
)
from hub.api.v1.sql import SqlClient

files_router = APIRouter(tags=["Files"])

logger = logging.getLogger(__name__)

load_dotenv()

S3_ENDPOINT = getenv("S3_ENDPOINT")
s3_client = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
)


class FileUploadRequest(BaseModel):
    """Request model for file upload."""

    file: FileTypes
    """The file to be uploaded."""
    purpose: Literal["assistants", "batch", "fine-tune", "vision"]
    """The purpose of the file upload."""

    class Config:  # noqa: D106
        arbitrary_types_allowed = True


def generate_unique_filename(filename: str) -> str:
    """Generate a unique filename by adding a short UUID.

    Args:
    ----
        filename (str): The original filename.

    Returns:
    -------
        str: A new filename with a 24-character hexadecimal UUID inserted before the extension.

    """
    unique_id = uuid.uuid4().hex[:24]
    name, ext = os.path.splitext(filename)
    return f"{unique_id}_{name}{ext}"


async def upload_file_to_storage(content: bytes, object_key: str) -> str:
    """Upload file content to either S3 or local file system based on STORAGE_TYPE.

    This function generates a unique filename for the uploaded file to prevent collisions.

    Args:
    ----
        content (bytes): The file content to upload.
        object_key (str): The original key/path for the file.

    Returns:
    -------
        str: The URI of the uploaded file.

    Raises:
    ------
        HTTPException: If the file upload fails.
        ValueError: If the storage type is not supported or S3_BUCKET is not set for S3 storage.

    """
    directory, filename = os.path.split(object_key)
    new_filename = generate_unique_filename(filename)
    new_object_key = os.path.join(directory, new_filename)

    if STORAGE_TYPE == "s3":
        try:
            if not S3_BUCKET:
                raise ValueError("S3_BUCKET is not set")
            s3_client.put_object(Bucket=S3_BUCKET, Key=new_object_key, Body=content)
            return f"{S3_URI_PREFIX}{S3_BUCKET}/{new_object_key}"
        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to upload file") from e
    elif STORAGE_TYPE == "file":
        try:
            full_path = os.path.join(DATA_FOLDER, new_object_key)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "wb") as f:
                f.write(content)
            return f"{FILE_URI_PREFIX}{os.path.abspath(full_path)}"
        except IOError as e:
            logger.error(f"Failed to write file to local storage: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to upload file") from e
    else:
        raise ValueError(f"Unsupported storage type: {STORAGE_TYPE}")


@files_router.post("/files")
async def upload_file(
    file: UploadFile = File(...),
    purpose: Literal["assistants", "batch", "fine-tune", "vision"] = Form(...),
    auth: AuthToken = Depends(get_auth),
) -> FileObject:
    """Upload a file to the system and create a corresponding database record.

    This function handles file uploads, determines the content type, checks for
    supported file types and encodings, and stores the file in the configured
    storage system.

    Args:
    ----
        file (UploadFile): The file to be uploaded.
        purpose (str): The purpose of the file upload. Must be one of:
                       "assistants", "batch", "fine-tune", "vision".
        auth (AuthToken): The authentication token for the current user.

    Returns:
    -------
        FileObject: An object containing details of the uploaded file.

    Raises:
    ------
        HTTPException:
            - 400 if the purpose is invalid, file type is not supported,
              or file encoding is not supported.
            - 404 if the file details are not found after creation.
            - 500 if there's an error during file upload or database operations.

    """
    logger.info(
        f"File upload request received for user: {auth.account_id}, "
        f"file: {file.filename}, type: {file.content_type}, purpose: {purpose}"
    )

    # Validate purpose
    valid_purposes = ["assistants", "batch", "fine-tune", "vision"]
    if purpose not in valid_purposes:
        raise HTTPException(status_code=400, detail=f"Invalid purpose. Must be one of: {', '.join(valid_purposes)}")

    if not file.filename:
        raise HTTPException(status_code=400, detail="File must have a name")

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Determine file type and extension
    file_extension = os.path.splitext(file.filename)[1].lower()
    content_type = determine_content_type(file)

    # Validate file type and extension
    if content_type not in SUPPORTED_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type {content_type}")
    if file_extension not in SUPPORTED_MIME_TYPES[content_type]:
        raise HTTPException(
            status_code=400, detail=f"Invalid file extension for the given content type {file_extension} {content_type}"
        )

    # Check encoding for text files
    if content_type.startswith("text/"):
        detected_encoding, content = check_text_encoding(content)
    else:
        detected_encoding = None

    # Generate object key and upload to storage
    object_key = f"vector-store-files/{auth.account_id}/{file.filename}"
    try:
        file_uri = await upload_file_to_storage(content, object_key)
    except Exception as e:
        logger.error(f"Failed to upload file to storage: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload file to storage") from e

    # Create file record in database
    sql_client = SqlClient()
    try:
        file_id = sql_client.create_file(
            account_id=auth.account_id,
            file_uri=file_uri,
            purpose=purpose,
            filename=file.filename,
            content_type=content_type,
            file_size=file_size,
            encoding=detected_encoding,
        )
        file_details = sql_client.get_file_details_by_account(file_id=file_id, account_id=auth.account_id)
    except Exception as e:
        logger.error(f"Database operation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create file record") from e

    if not file_details:
        raise HTTPException(status_code=404, detail="File details not found")

    logger.info(f"File uploaded successfully: {file_id}")
    return FileObject(
        id=str(file_id),
        bytes=file_size,
        created_at=int(file_details.created_at.timestamp()),
        filename=file.filename,
        object="file",
        purpose=purpose,
        status="uploaded",
        status_details="File successfully uploaded and recorded",
    )


@files_router.delete("/files/{file_id}")
async def delete_file(
    file_id: str = Path(..., description="The ID of the file to delete"),
    auth: AuthToken = Depends(get_auth),
):
    sql_client = SqlClient()
    deleted = sql_client.delete_file(file_id=file_id, account_id=auth.account_id)
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete file")
    return {"status": "success"}


def determine_content_type(file: UploadFile) -> str:
    """Determine the content type of the uploaded file.

    Args:
    ----
        file (UploadFile): The uploaded file object.

    Returns:
    -------
        str: The determined content type.

    """
    filename = file.filename or ""
    # content_type = file.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    if content_type == "application/octet-stream":
        file_extension = os.path.splitext(filename)[1].lower()
        for mime_type, extensions in SUPPORTED_MIME_TYPES.items():
            if file_extension in extensions:
                return mime_type
    return content_type


def check_text_encoding(content: bytes) -> Tuple[str, bytes]:
    """Check or convert the encoding of text content to  ASCII, UTF-8 or UTF-16 only.

    Args:
    ----
        content (bytes): The content to check.

    Returns:
    -------
        Tuple[str, bytes]: The enforced encoding (either  'ascii', 'utf-8', 'utf-16') and the converted content.

    Raises:
    ------
        HTTPException: If the encoding cannot be converted to UTF-8 or UTF-16.

    """
    detected_encoding = chardet.detect(content).get("encoding")

    # Check if the detected encoding is in supported encodings
    if detected_encoding and detected_encoding.lower() in SUPPORTED_TEXT_ENCODINGS:
        return detected_encoding.lower(), content
    else:
        try:
            # Decode as the detected encoding and re-encode as utf-8
            decoded_content = content.decode(detected_encoding or "utf-8", errors="ignore").encode("utf-8")
            return "utf-8", decoded_content
        except (UnicodeDecodeError, TypeError):
            raise HTTPException(
                status_code=400,
                detail="Failed to convert encoding to UTF-8 or UTF-16. Please use UTF-8 or UTF-16 encoded files.",
            ) from None


@files_router.get("/files/{file_id}")
async def retrieve_file(
    file_id: str = Path(..., description="The ID of the file to retrieve"),
    auth: AuthToken = Depends(get_auth),
) -> FileObject:
    """Retrieve information about a specific file.

    Args:
    ----
        file_id (str): The ID of the file to retrieve.
        auth (AuthToken): The authentication token for the current user.

    Returns:
    -------
        FileObject: An object containing details of the requested file.

    Raises:
    ------
        HTTPException:
            - 404 if the file is not found.
            - 403 if the user doesn't have permission to access the file.

    """
    logger.info(f"File retrieval request received for user: {auth.account_id}, file_id: {file_id}")

    sql_client = SqlClient()
    try:
        file_details = sql_client.get_file_details_by_account(file_id=file_id, account_id=auth.account_id)
    except Exception as e:
        logger.error(f"Database operation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve file information") from e

    if not file_details:
        raise HTTPException(status_code=404, detail="File not found")

    logger.info(f"File information retrieved successfully: {file_id}")
    return FileObject(
        id=str(file_details.id),
        bytes=file_details.file_size,
        created_at=int(file_details.created_at.timestamp()),
        filename=file_details.filename,
        object="file",
        purpose=file_details.purpose,  # type: ignore
        status="uploaded",
        status_details="File information retrieved successfully",
    )


@files_router.get("/files/{file_id}/content")
async def retrieve_file_content(
    file_id: str = Path(..., description="The ID of the file to retrieve"),
    auth: AuthToken = Depends(get_auth),
):
    """Retrieve the contents of a specific file.

    Args:
    ----
        file_id (str): The ID of the file to retrieve.
        auth (AuthToken): The authentication token for the current user.

    Returns:
    -------
        StreamingResponse: A streaming response containing the file content.

    Raises:
    ------
        HTTPException:
            - 404 if the file is not found.
            - 403 if the user doesn't have permission to access the file.
            - 500 if there's an error retrieving the file content.

    """
    logger.info(f"File content retrieval request received for user: {auth.account_id}, file_id: {file_id}")

    sql_client = SqlClient()
    try:
        file_details = sql_client.get_file_details_by_account(file_id=file_id, account_id=auth.account_id)
    except Exception as e:
        logger.error(f"Database operation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve file information") from e

    if not file_details:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        file_content = await get_file_content(file_details.file_uri)
    except Exception as e:
        logger.error(f"Failed to retrieve file content: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve file content") from e

    return StreamingResponse(
        io.BytesIO(file_content),
        media_type=file_details.content_type,
        headers={"Content-Disposition": f'attachment; filename="{file_details.filename}"'},
    )


async def get_file_content(file_uri: str) -> bytes:
    """Retrieve the content of a file from the storage system.

    Args:
    ----
        file_uri (str): The URI of the file to retrieve.

    Returns:
    -------
        bytes: The content of the file.

    Raises:
    ------
        Exception: If there's an error retrieving the file content.

    """
    if file_uri.startswith(S3_URI_PREFIX):
        # Extract bucket and key from S3 URI
        s3_path = file_uri[len(S3_URI_PREFIX) :]
        bucket, key = s3_path.split("/", 1)
        try:
            response = s3_client.get_object(Bucket=bucket, Key=key)
            return response["Body"].read()
        except Exception as e:
            logger.error(f"Failed to retrieve file from S3: {str(e)}")
            raise
    elif file_uri.startswith(FILE_URI_PREFIX):
        # Extract local file path
        file_path = file_uri[len(FILE_URI_PREFIX) :]
        try:
            with open(file_path, "rb") as file:
                return file.read()
        except Exception as e:
            logger.error(f"Failed to read local file: {str(e)}")
            raise
    else:
        raise ValueError(f"Unsupported file URI: {file_uri}")
