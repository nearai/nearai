import logging
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, field_validator

from hub.api.near.sign import validate_nonce, verify_signed_message
from hub.api.v1.exceptions import TokenValidationError
from hub.api.v1.sql import SqlClient

bearer = HTTPBearer()
logger = logging.getLogger(__name__)
db = SqlClient()


class AuthToken(BaseModel):
    """Model for auth callback."""

    account_id: str
    """The account ID."""
    public_key: str
    """The public key."""
    signature: str
    """The signature."""
    callback_url: Optional[str] = None
    """The callback URL."""
    recipient: str = "ai.near"
    """Message Recipient"""
    nonce: bytes
    """Nonce of the signed message, it must be 32 bytes long."""
    message: str  # noqa: N815
    """The plain message that was signed."""

    @field_validator("nonce")
    @classmethod
    def validate_and_convert_nonce(cls, value: str):  # noqa: D102
        return validate_nonce(value)


async def get_auth(token: HTTPAuthorizationCredentials = Depends(bearer)):
    if token.credentials == "":
        raise HTTPException(status_code=401, detail="Invalid token")
    if token.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid token scheme")
    try:
        token.credentials = token.credentials.replace("Bearer ", "")
        logger.debug(f"Token: {token.credentials}")
        return AuthToken.model_validate_json(token.credentials)
    except Exception as e:
        raise TokenValidationError(detail=str(e)) from None


async def validate_signature(auth: AuthToken = Depends(get_auth)):
    logging.debug(f"account_id {auth.account_id}: verifying signature")
    is_valid = verify_signed_message(
        auth.account_id,
        auth.public_key,
        auth.signature,
        auth.message,
        auth.nonce,
        auth.recipient,
        auth.callback_url,
    )
    if not is_valid:
        logging.error(f"account_id {auth.account_id}: signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")

    logging.debug(f"account_id {auth.account_id}: signature verified")

    return auth


async def revokable_auth(auth: AuthToken = Depends(validate_signature)):
    logger.debug(f"Validating auth token: {auth}")

    user_nonce = db.get_account_nonce(auth.account_id, auth.nonce)

    if user_nonce and user_nonce.is_revoked():
        logging.error(f"account_id {auth.account_id}: nonce is revoked")
        raise HTTPException(status_code=401, detail="Revoked nonce")

    if not user_nonce:
        db.store_nonce(auth.account_id, auth.nonce, auth.message, auth.recipient, auth.callback_url)

    return auth
