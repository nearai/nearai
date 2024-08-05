import json
import logging
import time
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, field_validator

from hub.api.near.sign import verify_signed_message
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
    nonce: bytes = b"1" * 32
    """Nonce of the signed message, it must be 32 bytes long."""
    plainMsg: str  # noqa: N815
    """The plain message that was signed."""

    @field_validator("nonce")
    @classmethod
    def validate_and_convert_nonce(cls, value: str):  # noqa: D102
        if len(value) != 32:
            raise ValueError("Invalid nonce, must of length 32")
        return value

    # allow auth to be passed along to other services - needs review
    def json(self):
        """Deprecated. For use by tests. Return the JSON representation of the object."""
        return json.dumps(
            {
                "account_id": self.account_id,
                "public_key": self.public_key,
                "signature": self.signature,
                "callback_url": self.callback_url,
                "recipient": self.recipient,
                "plainMsg": self.plainMsg,
            }
        )


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
        logging.error(f"Error parsing token: {e}")
        raise HTTPException(status_code=401, detail="Invalid token") from None


async def validate_signature(auth: AuthToken = Depends(get_auth)):
    logging.debug(f"account_id {auth.account_id}: verifying signature")
    is_valid = verify_signed_message(
        auth.account_id, auth.public_key, auth.signature, auth.plainMsg, auth.nonce, auth.recipient, auth.callback_url
    )
    if not is_valid:
        logging.error(f"account_id {auth.account_id}: signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")

    logging.debug(f"account_id {auth.account_id}: signature verified")

    timestamp = int(auth.nonce)
    if timestamp <= 0:
        raise HTTPException(status_code=401, detail="Invalid nonce")
    now = int(time.time() * 1000)
    if timestamp > now:
        # TODO(https://github.com/nearai/nearai/issues/106): Revoke nonces that are in the future.
        # This will break the default where nonce = b"1" * 32
        logger.info(f"account_id {auth.account_id}: nonce is in the future")
    if now - timestamp > 10 * 365 * 24 * 60 * 60 * 1000:
        """If the timestamp is older than 10 years, it is considered invalid. Forcing apps to use unique nonces."""
        logging.error(f"account_id {auth.account_id}: nonce is too old")
        raise HTTPException(status_code=401, detail="Invalid nonce, too old")

    return auth


async def revokable_auth(auth: AuthToken = Depends(validate_signature)):
    logger.debug(f"Validating auth token: {auth}")

    user_nonce = db.get_account_nonce(auth.account_id, auth.nonce)

    if user_nonce and user_nonce.is_revoked():
        logging.error(f"account_id {auth.account_id}: nonce is revoked")
        raise HTTPException(status_code=401, detail="Revoked nonce")

    if not user_nonce:
        db.store_nonce(auth.account_id, auth.nonce, auth.plainMsg, auth.recipient, auth.callback_url)

    return auth
