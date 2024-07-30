import json
import logging
from typing import Optional, Union

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from hub.api.near.sign import verify_signed_message

bearer = HTTPBearer()
logger = logging.getLogger(__name__)


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
    recipient: Optional[str] = "ai.near"
    """Message Recipient"""
    nonce: bytes = Field(default=bytes("1", "utf-8") * 32, min_length=32, max_length=32)
    plain_msg: str
    """The plain message that was signed."""

    @classmethod
    def validate_nonce(cls, value: Union[str, list[int]]):  # noqa: D102
        if isinstance(value, str):
            return bytes.fromhex(value)
        elif isinstance(value, list):
            return bytes(value)
        else:
            raise ValueError("Invalid nonce format")

    @classmethod
    def alt_model_validate_json(cls, json_str: str) -> "AuthToken":  # noqa: D102
        data = json.loads(json_str)
        if "nonce" in data:
            data["nonce"] = cls.validate_nonce(data["nonce"])
        return cls(**data)


async def get_current_user(token: HTTPAuthorizationCredentials = Depends(bearer)):
    logging.debug(f"Received token: {token.credentials}")
    auth = AuthToken.alt_model_validate_json(token.credentials)

    is_valid = verify_signed_message(
        auth.account_id, auth.public_key, auth.signature, auth.plain_msg, auth.nonce, auth.recipient, auth.callback_url
    )
    if not is_valid:
        logging.error(f"account_id {auth.account_id}: signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid token")

    logging.debug(f"account_id {auth.account_id}: signature verified")

    return auth
