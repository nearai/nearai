import logging
from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from nearai.shared.cache import mem_cache_with_timeout
from nearai.shared.near.sign import validate_nonce, verify_signed_message
from pydantic import BaseModel, field_validator
from sqlmodel import select

from hub.api.v1.exceptions import TokenValidationError
from hub.api.v1.models import Delegation, get_session
from hub.api.v1.sql import SqlClient

bearer = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


# TODO: This code is duplicated from shared/auth_data.py (remove duplication)
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

    runner_data: Optional[str] = None

    @field_validator("nonce")
    @classmethod
    def validate_and_convert_nonce(cls, value: str):  # noqa: D102
        return validate_nonce(value)

    def __hash__(self):
        """Hash the object for caching purposes."""
        return hash((type(self),) + tuple(self.__dict__.values()))


class RawAuthToken(AuthToken):
    on_behalf_of: Optional[str] = None
    """The account ID on behalf of which the request is made."""

    def unwrap(self) -> AuthToken:
        """Unwrap the raw auth token."""
        return AuthToken(
            account_id=self.account_id,
            public_key=self.public_key,
            signature=self.signature,
            callback_url=self.callback_url,
            recipient=self.recipient,
            nonce=self.nonce,
            message=self.message,
            runner_data=self.runner_data,
        )


def parse_auth(token: Optional[HTTPAuthorizationCredentials] = Depends(bearer)):
    if token is None:
        return None

    if token.credentials == "":
        raise HTTPException(status_code=401, detail="Invalid token")
    if token.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid token scheme")
    try:
        token.credentials = token.credentials.replace("Bearer ", "")
        logger.debug(f"Token: {token.credentials}")
        return RawAuthToken.model_validate_json(token.credentials)
    except Exception as e:
        raise TokenValidationError(detail=str(e)) from None


def validate_signature(auth: Optional[RawAuthToken] = Depends(parse_auth)):
    if auth is None:
        return None

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

    if auth.on_behalf_of is not None:
        # Query is trying to perform an action on behalf of another account. Check if it has permission to do so.

        query = (
            select(Delegation)
            .where(Delegation.original_account_id == auth.on_behalf_of)
            .where(Delegation.delegation_account_id == auth.account_id)
            .limit(1)
        )

        with get_session() as session:
            result = session.exec(query).first()

            if result is None:
                err_msg = f"{auth.account_id} don't have permission to execute action on behalf of {auth.on_behalf_of}."
                raise HTTPException(status_code=401, detail=err_msg)

            if result.expires_at is not None and result.expires_at < datetime.now():
                err_msg = f"{auth.account_id} permission to operate on behalf of {auth.on_behalf_of} expired."
                raise HTTPException(status_code=401, detail=err_msg)

        # TODO(517): Instead of altering the account_id we should keep the object as is.
        auth.account_id = auth.on_behalf_of

    return auth.unwrap()


@mem_cache_with_timeout(timeout=60)
def revokable_auth(auth: Optional[AuthToken] = Depends(validate_signature)):
    if auth is None:
        return None

    logger.debug(f"Validating auth token: {auth}")

    db = SqlClient()  # TODO(https://github.com/nearai/nearai/issues/545): Use SQLAlchemy
    user_nonce = db.get_account_nonce(auth.account_id, auth.nonce)

    if user_nonce and user_nonce.is_revoked():
        logging.error(f"account_id {auth.account_id}: nonce is revoked")
        raise HTTPException(status_code=401, detail="Revoked nonce")

    if not user_nonce:
        db.store_nonce(auth.account_id, auth.nonce, auth.message, auth.recipient, auth.callback_url)

    return auth


def get_optional_auth(auth: Optional[AuthToken] = Depends(revokable_auth)):
    """Returns the validated auth token in case it was provided, otherwise returns None."""
    # This method is the last layer of the middleware the builds the auth token, it
    # should be used instead of any previous method in the chain (e.g. `revokable_auth`).
    # This way it is easier to add new layers of validation without changing the existing code.
    #
    # If the auth token is required, use `get_auth` instead.
    return auth


def get_auth(auth: Optional[AuthToken] = Depends(get_optional_auth)):
    if auth is None:
        raise HTTPException(status_code=403, detail="Authorization required")
    return auth
