import logging
from typing import Optional

import boto3
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from pydantic import BaseModel

from hub.api.v1.auth import AuthToken, get_auth
from hub.api.v1.sql import SqlClient

hub_secrets_router = APIRouter(tags=["Hub Secrets"])

logger = logging.getLogger(__name__)

s3_client = boto3.client("s3")


class CreateHubSecretRequest(BaseModel):
    """Request model for creating a new hub secret."""

    namespace: str
    name: str
    version: Optional[str]
    description: Optional[str]

    key: str
    value: str

    category: Optional[str] = "agent"


class RemoveHubSecretRequest(BaseModel):
    namespace: str
    name: str
    version: Optional[str]

    key: str

    category: Optional[str] = "agent"


@hub_secrets_router.post("/create_hub_secret")
async def create_hub_secret(
    request: CreateHubSecretRequest, background_tasks: BackgroundTasks, auth: AuthToken = Depends(get_auth)
):
    """Create a hub secret."""
    logger.info(f"Creating hub secret for: {request.name}")

    # Full security (secure even from Infrastructure admins) comes from running the Hub in a TEE
    # Confirmation of this security level can be performed by developers and end users by verifying the
    # TEE security quote.

    sql_client = SqlClient()
    sql_client.create_hub_secret(
        owner_namespace=auth.account_id,
        namespace=request.namespace,
        name=request.name,
        version=request.version,
        description=request.description,
        key=request.key,
        value=request.value,
        category=request.category,
    )

    logger.info("Hub secret created successfully")

    return True


@hub_secrets_router.post("/remove_hub_secret")
async def remove_hub_secret(
    request: RemoveHubSecretRequest, background_tasks: BackgroundTasks, auth: AuthToken = Depends(get_auth)
):
    """Remove a hub secret."""
    logger.info(f"Removing hub secret for: {request.name}")

    sql_client = SqlClient()
    sql_client.remove_hub_secret(
        owner_namespace=auth.account_id,
        namespace=request.namespace,
        name=request.name,
        version=request.version,
        key=request.key,
        category=request.category,
    )

    logger.info("Hub secret removed successfully")

    return True


@hub_secrets_router.get("/get_user_secrets")
async def get_user_secrets(
    background_tasks: BackgroundTasks,
    auth: AuthToken = Depends(get_auth),
    limit: Optional[int] = Query(100, description="Limit of the results"),
    offset: Optional[int] = Query(0, description="Offset for pagination"),
):
    """Get hub secrets for a given user."""
    sql_client = SqlClient()
    result = sql_client.get_user_secrets(
        owner_namespace=auth.account_id,
        limit=limit,
        offset=offset,
    )

    return result
