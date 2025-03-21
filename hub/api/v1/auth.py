import logging
from datetime import datetime, timezone
from os import getenv
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from httpx_oauth.clients.github import GitHubOAuth2
from httpx_oauth.clients.google import GoogleOAuth2
from httpx_oauth.integrations.fastapi import OAuth2AuthorizeCallback
from nearai.shared.cache import mem_cache_with_timeout
from nearai.shared.near.sign import validate_nonce, verify_signed_message
from pydantic import BaseModel, field_validator
from sqlmodel import delete, select
from starlette.responses import RedirectResponse

from hub.api.v1.auth_config import (
    auth_access_token_expiration,
    auth_jwt_private_key,
    auth_jwt_public_key,
    auth_ui_url,
)
from hub.api.v1.exceptions import TokenValidationError
from hub.api.v1.models import Delegation, Session, User, UserRefreshToken, get_session
from hub.api.v1.sql import SqlClient

"""
Helpful documentation:

https://docs.google.com/document/d/1sU7klfWO2ENHU9yaW90oRszJCU3RSNMHAG9mTGxO5J4/edit?tab=t.8fvrtyp9fe0u
https://pyjwt.readthedocs.io/en/stable/index.html
https://frankie567.github.io/httpx-oauth/

TODO:

[] Force user to set unique namespace on sign in if none
    - UX idea: suggest/autofill default input value based on email, near account id, or github username
[] Update parse_auth() and validate_signature() to account for new JWT token structure
    - This will lead to a lot code updates wherever get_optional_auth() or get_auth() is relied on
[] Handle various TODO comments
"""

bearer = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)

v1_router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


class AccessTokenJwtPayloadUser(BaseModel):
    id: str
    namespace: Optional[str]


class AccessTokenJwtPayload(BaseModel):
    exp: int
    user: AccessTokenJwtPayloadUser


class RefreshTokenJwtPayload(BaseModel):
    refresh_id: str
    user_id: str


class RefreshInput(BaseModel):
    refresh_token: str


# TODO: This code is duplicated from shared/auth_data.py (remove duplication)
class NearAuthToken(BaseModel):
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


class RawNearAuthToken(NearAuthToken):
    on_behalf_of: Optional[str] = None
    """The account ID on behalf of which the request is made."""

    def unwrap(self) -> NearAuthToken:
        """Unwrap the raw auth token."""
        return NearAuthToken(
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

        access_jwt = decode_access_jwt(token.credentials)

        if access_jwt is not None:
            # TODO: Continue refactoring down stream methods to expect potential AccessTokenJwtPayload
            # return access_jwt
            raise HTTPException(status_code=501, detail="TODO: JWT auth token")

        return RawNearAuthToken.model_validate_json(token.credentials)
    except Exception as e:
        raise TokenValidationError(detail=str(e)) from None


def validate_signature(auth: Optional[RawNearAuthToken] = Depends(parse_auth)):
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
def revokable_auth(auth: Optional[NearAuthToken] = Depends(validate_signature)):
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


def get_optional_auth(auth: Optional[NearAuthToken] = Depends(revokable_auth)):
    """Returns the validated auth token in case it was provided, otherwise returns None."""
    # This method is the last layer of the middleware the builds the auth token, it
    # should be used instead of any previous method in the chain (e.g. `revokable_auth`).
    # This way it is easier to add new layers of validation without changing the existing code.
    #
    # If the auth token is required, use `get_auth` instead.
    return auth


def get_auth(auth: Optional[NearAuthToken] = Depends(get_optional_auth)):
    if auth is None:
        raise HTTPException(status_code=403, detail="Authorization required")
    return auth


github_oauth_client = GitHubOAuth2(getenv("GITHUB_OAUTH_CLIENT_ID", ""), getenv("GITHUB_OAUTH_CLIENT_SECRET", ""))
github_authorize_callback = OAuth2AuthorizeCallback(github_oauth_client, "callback_github")

google_oauth_client = GoogleOAuth2(getenv("GOOGLE_OAUTH_CLIENT_ID", ""), getenv("GOOGLE_OAUTH_CLIENT_SECRET", ""))
google_authorize_callback = OAuth2AuthorizeCallback(google_oauth_client, "callback_google")


def parse_jwt_auth(auth: Optional[HTTPAuthorizationCredentials] = Depends(bearer)):
    if auth is None or auth.credentials == "":
        return None

    if auth.scheme != "Bearer":
        raise HTTPException(status_code=401, detail="INVALID_SCHEME")

    access_token = decode_access_jwt(auth.credentials.replace("Bearer ", ""))
    if access_token is None:
        raise HTTPException(status_code=401, detail="EXPIRED_TOKEN")

    return access_token


def decode_access_jwt(token: str):
    try:
        decoded = jwt.decode(
            token,
            auth_jwt_public_key,
            algorithms=["RS256"],
        )

        user = decoded.get("user")

        return AccessTokenJwtPayload(
            exp=decoded.get("exp"), user=AccessTokenJwtPayloadUser(id=user.get("id"), namespace=user.get("namespace"))
        )

    except jwt.ExpiredSignatureError:
        return None

    except Exception as error:
        logger.error(f"Unexpected error when decoding JWT access token: {error}")
        return None


def decode_refresh_jwt(token: str):
    try:
        decoded = jwt.decode(
            token,
            auth_jwt_public_key,
            algorithms=["RS256"],
            options={
                "verify_exp": False  # We rely on the user_refresh_tokens db table to determine expiration
            },
        )

        return RefreshTokenJwtPayload(
            refresh_id=decoded.get("refresh_id"),
            user_id=decoded.get("user_id"),
        )

    except Exception as error:
        logger.error(f"Unexpected error when decoding JWT refresh token: {error}")
        return None


def generate_access_token(user: User):
    access_jwt_expiration = int((datetime.now(tz=timezone.utc) + auth_access_token_expiration).timestamp())
    access_jwt_payload = AccessTokenJwtPayload(
        exp=access_jwt_expiration, user=AccessTokenJwtPayloadUser(id=user.id, namespace=user.namespace)
    )
    access_jwt = jwt.encode(access_jwt_payload.model_dump(), auth_jwt_private_key, algorithm="RS256")

    return access_jwt


def generate_access_and_refresh_tokens(session: Session, user: User):
    access_jwt = generate_access_token(user)

    user_refresh_token = UserRefreshToken(user_id=user.id)
    session.add(user_refresh_token)
    session.commit()
    refresh_jwt_payload = RefreshTokenJwtPayload(refresh_id=user_refresh_token.id, user_id=user.id)
    refresh_jwt = jwt.encode(refresh_jwt_payload.model_dump(), auth_jwt_private_key, algorithm="RS256")

    return {"access_token": access_jwt, "refresh_token": refresh_jwt}


def redirect_oauth_success(tokens: dict[str, str]):
    return RedirectResponse(
        url=f"{auth_ui_url}/callback#access_token={tokens.get('access_token')}&refresh_token={tokens.get('refresh_token')}"
    )


def redirect_oauth_failure(error: str = "unknown"):
    return RedirectResponse(url=f"{auth_ui_url}/callback#error={error}")


def find_or_create_user_by_email(session: Session, email: str, avatar_url: Optional[str]):
    user = session.exec(select(User).where(User.email == email)).first()

    if user is None:
        user = User(email=email, avatar_url=avatar_url)
        session.add(user)
        session.commit()

    return user


def find_or_create_user_by_near_account(session: Session, near_account_id: str):
    user = session.exec(select(User).where(User.near_account_id == near_account_id)).first()

    if user is None:
        user = User(near_account_id=near_account_id)
        session.add(user)
        session.commit()

    return user


def create_anonymous_user(session: Session):
    user = User(is_anonymous=True)
    session.add(user)
    session.commit()

    return user


@v1_router.post("/login/anonymous")
def login_anonymous():
    with get_session() as session:
        user = create_anonymous_user(session=session)
        tokens = generate_access_and_refresh_tokens(session, user)

        return tokens


@v1_router.post("/login/near")
def login_near_wallet(auth: RawNearAuthToken):
    with get_session() as session:
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
            raise HTTPException(status_code=401, detail="Invalid signature")

        user = find_or_create_user_by_near_account(session=session, near_account_id=auth.account_id)
        tokens = generate_access_and_refresh_tokens(session, user)

        return tokens


@v1_router.get("/login/github")
async def login_github(request: Request):
    redirect_uri = f"{request.base_url}v1{v1_router.url_path_for('callback_github')}"
    authorization_uri = await github_oauth_client.get_authorization_url(redirect_uri)
    return RedirectResponse(url=authorization_uri)


@v1_router.get("/login/google")
async def login_google(request: Request):
    redirect_uri = f"{request.base_url}v1{v1_router.url_path_for('callback_google')}"
    authorization_uri = await google_oauth_client.get_authorization_url(redirect_uri)
    return RedirectResponse(url=authorization_uri)


@v1_router.get("/callback/github")
async def callback_github(access_token_state=Depends(github_authorize_callback)):
    with get_session() as session:
        try:
            token = access_token_state[0]
            access_token = token["access_token"]
            profile = await github_oauth_client.get_profile(access_token)

            user = find_or_create_user_by_email(
                session=session, email=profile.get("email"), avatar_url=profile.get("avatar_url")
            )
            tokens = generate_access_and_refresh_tokens(session, user)

            return redirect_oauth_success(tokens)

        except Exception as e:
            logger.error(f"Github OAuth2 callback failed with an unexpected error: {e}")
            return redirect_oauth_failure()


@v1_router.get("/callback/google")
async def callback_google(access_token_state=Depends(google_authorize_callback)):
    with get_session() as session:
        try:
            token = access_token_state[0]
            profile = jwt.decode(token.get("id_token"), options={"verify_signature": False})

            user = find_or_create_user_by_email(
                session=session, email=profile.get("email"), avatar_url=profile.get("picture")
            )
            tokens = generate_access_and_refresh_tokens(session, user)

            return redirect_oauth_success(tokens)

        except Exception as e:
            logger.error(f"Google OAuth2 callback failed with an unexpected error: {e}")
            return redirect_oauth_failure()


@v1_router.post("/refresh")
def refresh(input: RefreshInput):
    with get_session() as session:
        refresh_token = decode_refresh_jwt(token=input.refresh_token)
        if refresh_token is None:
            raise HTTPException(status_code=401)

        # Delete expired refresh tokens for this user:
        session.exec(  # type: ignore
            # https://github.com/fastapi/sqlmodel/discussions/831
            delete(UserRefreshToken).where(
                UserRefreshToken.user_id == refresh_token.user_id,
                UserRefreshToken.created_at < UserRefreshToken.oldest_valid_datetime(),
            )
        )
        session.commit()

        # Attempt to find a remaining, valid refresh token for this user:
        user_refresh_token = session.exec(
            select(UserRefreshToken).where(
                UserRefreshToken.id == refresh_token.refresh_id,
                UserRefreshToken.user_id == refresh_token.user_id,
            )
        ).first()

        if user_refresh_token is None:
            raise HTTPException(status_code=401)

        user = session.exec(select(User).where(User.id == user_refresh_token.user_id)).first()
        if user is None:
            raise HTTPException(status_code=401)

        access_jwt = generate_access_token(user)  # Generate a new access token
        refresh_jwt = input.refresh_token  # Continue to use the same refresh token until it expires

        return {"access_token": access_jwt, "refresh_token": refresh_jwt}


@v1_router.get("/test")
def test(token: Optional[AccessTokenJwtPayload] = Depends(parse_jwt_auth)):
    if token is None:
        return {}
    return token.model_dump()
