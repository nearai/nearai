import logging
import mimetypes
import os
from typing import Literal, Optional

import boto3
import chardet
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from openai.types.file_create_params import FileTypes
from openai.types.file_object import FileObject
from pydantic import BaseModel

from hub.api.v1.auth import AuthToken, revokable_auth
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

s3_client = boto3.client("s3")


class FileUploadRequest(BaseModel):
    """Request model for file upload."""

    file: FileTypes
    """The file to be uploaded."""
    purpose: Literal["assistants", "batch", "fine-tune", "vision"]
    """The purpose of the file upload."""

    class Config:  # noqa: D106
        arbitrary_types_allowed = True


async def upload_file_to_storage(content: bytes, object_key: str) -> str:
    """Upload file content to either S3 or local file system based on STORAGE_TYPE.

    Args:
    ----
        content (bytes): The file content to upload.
        object_key (str): The key/path for the file.

    Returns:
    -------
        str: The URI of the uploaded file.

    Raises:
    ------
        HTTPException: If the file upload fails.

    """
    if STORAGE_TYPE == "s3":
        try:
            if not S3_BUCKET:
                raise ValueError("S3_BUCKET is not set")
            s3_client.put_object(Bucket=S3_BUCKET, Key=object_key, Body=content)
            return f"{S3_URI_PREFIX}{S3_BUCKET}/{object_key}"
        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to upload file") from e
    elif STORAGE_TYPE == "file":
        try:
            os.makedirs(os.path.dirname(object_key), exist_ok=True)
            with open(object_key, "wb") as f:
                f.write(content)
            return f"{FILE_URI_PREFIX}{os.path.abspath(object_key)}"
        except IOError as e:
            logger.error(f"Failed to write file to local storage: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to upload file") from e
    else:
        raise ValueError(f"Unsupported storage type: {STORAGE_TYPE}")


@files_router.post("/files")
async def upload_file(
    file: UploadFile = File(...),
    purpose: Literal["assistants", "batch", "fine-tune", "vision"] = Form(...),
    auth: AuthToken = Depends(revokable_auth),
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
        raise HTTPException(status_code=400, detail="Unsupported file type")
    if file_extension not in SUPPORTED_MIME_TYPES[content_type]:
        raise HTTPException(status_code=400, detail="Invalid file extension for the given content type")

    # Check encoding for text files
    detected_encoding = check_text_encoding(content) if content_type.startswith("text/") else None

    # Generate a unique object key and upload to storage
    object_key = f"hub/vector-store-files/{auth.account_id}/{file.filename}"
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
    content_type = file.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    if content_type == "application/octet-stream":
        file_extension = os.path.splitext(filename)[1].lower()
        for mime_type, extensions in SUPPORTED_MIME_TYPES.items():
            if file_extension in extensions:
                return mime_type
    return content_type


def check_text_encoding(content: bytes) -> Optional[str]:
    """Check the encoding of text content.

    Args:
    ----
        content (bytes): The content to check.

    Returns:
    -------
        Optional[str]: The detected encoding if supported, None otherwise.

    Raises:
    ------
        HTTPException: If the encoding is not supported.

    """
    detected_encoding = chardet.detect(content).get("encoding")
    if not detected_encoding or detected_encoding.lower() not in SUPPORTED_TEXT_ENCODINGS:
        raise HTTPException(
            status_code=400, detail=f"Unsupported text encoding. Must be one of: {', '.join(SUPPORTED_TEXT_ENCODINGS)}"
        )
    return detected_encoding
