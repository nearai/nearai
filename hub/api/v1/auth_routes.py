# https://pyjwt.readthedocs.io/en/latest/index.html
# https://frankie567.github.io/httpx-oauth

import logging
from datetime import datetime, timedelta, timezone
from os import getenv
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from httpx_oauth.clients.github import GitHubOAuth2
from httpx_oauth.clients.google import GoogleOAuth2
from httpx_oauth.integrations.fastapi import OAuth2AuthorizeCallback
from pydantic import BaseModel
from sqlmodel import delete, select
from starlette.responses import RedirectResponse

from hub.api.v1.models import Session, User, UserRefreshToken, get_session

v1_router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

logger = logging.getLogger(__name__)
auth_ui_url = getenv("AUTH_UI_URL")

bearer = HTTPBearer(auto_error=False)

github_oauth_client = GitHubOAuth2(getenv("GITHUB_OAUTH_CLIENT_ID"), getenv("GITHUB_OAUTH_CLIENT_SECRET"))
github_authorize_callback = OAuth2AuthorizeCallback(github_oauth_client, "callback_github")

google_oauth_client = GoogleOAuth2(getenv("GOOGLE_OAUTH_CLIENT_ID"), getenv("GOOGLE_OAUTH_CLIENT_SECRET"))
google_authorize_callback = OAuth2AuthorizeCallback(google_oauth_client, "callback_google")


# TODO: Generate secure private/public key pair and store inside of secret
mocked_jwt_private_key = """-----BEGIN RSA PRIVATE KEY-----
MIICWwIBAAKBgQCApqcgP3Xyc0M0o93imNw/sLe9mdwivvQrbOji4cN4wp8+qdfW
TQ+MAY1bAZQG8YKEsKSbrTG/3HSXUITpGzzMz6S+flmVwzkhGVty6qM/fwh+ayTL
pMLkTlpu0XeTw9TEA5rzupkYr3V9mPv4OUrfTXwyC2KNcMBviyYFXK5wDQIDAQAB
AoGAHWh7CacYCh0I/s56mSLCLhjyV3gFVzf5TrftoHdlHIS4rDVc7lLdO+7a5jO9
J70rTbOnXSLBHY+CY1h3mWWthvgPHr3vVGcQf12ijs3TQ44ZbDoopOfkRD6s3zty
fc1hhPEBOOM+4daN++N3tdPwYez71mOuauegCjpcQglQmaECQQD/brqEv1MGgb9M
QhvBzMMPDZoz9tiMbKG+XxbIeqCM4S91eHtajqLQdToPua1w1IEbuqNnbEq9LXWX
SyDyY6SJAkEAgO/R9OKOOgJxkkhGSWyQ9EuTr3vAZufz3yrD+f1A3bpYlVfWvvQK
BPCr9IMWANVHW62Bl93h8luG/h3n5DTWZQJAfv5HP0578cU6HajUcgLii65glytH
uHEd7S8Lfbrx7XjbhpTTB0/ZBLjzl/PhljIgym99ZCMD+ZALYZ/ZjokZuQJACNjr
7kLRgZeDVYdSE124wJqjAqqaNDV8XXbgxbmkBtLvmyfQ23+BZH9jPT71do8r+1V3
jAU0qN2w8KT6sYUSpQJAUEvHM6wa+ixgSZNJ/7cXsKLUeaUxVii2H4gT0lWe76lT
h4kabjU2aJgx1LHAcCPzWPSLwtn4Kl9ySXtj9yv9Gg==
-----END RSA PRIVATE KEY-----"""
mocked_jwt_public_key = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCApqcgP3Xyc0M0o93imNw/sLe9
mdwivvQrbOji4cN4wp8+qdfWTQ+MAY1bAZQG8YKEsKSbrTG/3HSXUITpGzzMz6S+
flmVwzkhGVty6qM/fwh+ayTLpMLkTlpu0XeTw9TEA5rzupkYr3V9mPv4OUrfTXwy
C2KNcMBviyYFXK5wDQIDAQAB
-----END PUBLIC KEY-----"""


class AccessTokenJwtPayload(BaseModel):
    exp: int
    user_id: str
    user_namespace: str | None


class RefreshTokenJwtPayload(BaseModel):
    id: str
    user_id: str


class RefreshInput(BaseModel):
    refresh_token: str


def parse_jwt_auth(auth: Optional[HTTPAuthorizationCredentials] = Depends(bearer)):
    if auth is None or auth.credentials == "":
        return None

    if auth.scheme != "Bearer":
        raise HTTPException(status_code=401, detail="INVALID_SCHEME")

    access_token = decode_jwt_access_token(auth.credentials.replace("Bearer ", ""))
    if access_token is None:
        raise HTTPException(status_code=401, detail="EXPIRED_TOKEN")

    return access_token


def decode_jwt_access_token(token: str):
    try:
        decoded = jwt.decode(
            token,
            mocked_jwt_public_key,
            algorithms=["RS256"],
        )

        return AccessTokenJwtPayload(
            exp=decoded.get("exp"),
            user_id=decoded.get("user_id"),
            user_namespace=decoded.get("user_namespace"),
        )

    except jwt.ExpiredSignatureError:
        return None

    except Exception as error:
        logger.error(f"Unexpected error when decoding JWT access token: {error}")
        return None


def decode_jwt_refresh_token(token: str):
    try:
        decoded = jwt.decode(
            token,
            mocked_jwt_public_key,
            algorithms=["RS256"],
            options={
                "verify_exp": False  # We rely on the user_refresh_tokens table to determine expiration
            },
        )

        return RefreshTokenJwtPayload(
            id=decoded.get("id"),
            user_id=decoded.get("user_id"),
        )

    except Exception as error:
        logger.error(f"Unexpected error when decoding JWT refresh token: {error}")
        return None


def generate_access_token(user: User):
    access_jwt_expiration = int(  # TODO: 1 hour
        (datetime.now(tz=timezone.utc) + timedelta(seconds=15)).timestamp()
    )
    access_jwt_payload = AccessTokenJwtPayload(
        exp=access_jwt_expiration, user_namespace=user.namespace, user_id=user.id
    )
    access_jwt = jwt.encode(access_jwt_payload.model_dump(), mocked_jwt_private_key, algorithm="RS256")

    return access_jwt


def generate_access_and_refresh_tokens(session: Session, user: User):
    user_refresh_token = UserRefreshToken(user_id=user.id)
    session.add(user_refresh_token)
    session.commit()

    access_jwt = generate_access_token(user)

    refresh_jwt_payload = RefreshTokenJwtPayload(id=user_refresh_token.id, user_id=user.id)
    refresh_jwt = jwt.encode(refresh_jwt_payload.model_dump(), mocked_jwt_private_key, algorithm="RS256")

    return {"access_token": access_jwt, "refresh_token": refresh_jwt}


def redirect_oauth_success(tokens: dict[str, str]):
    return RedirectResponse(
        url=f"{auth_ui_url}/callback#access_token={tokens.get('access_token')}&refresh_token={tokens.get('refresh_token')}"
    )


def redirect_oauth_failure(error: str = "unknown"):
    return RedirectResponse(url=f"{auth_ui_url}/callback#error={error}")


def find_or_create_user(session: Session, email: str, avatar_url: Optional[str]):
    user = session.exec(select(User).where(User.email == email)).first()

    if user is None:
        user = User(email=email, avatar_url=avatar_url)
        session.add(user)
        session.commit()

    return user


# @v1_router.get("/login/github")
# async def login_github(request: Request):
#     redirect_uri = f"{request.base_url}v1{v1_router.url_path_for('callback_github')}"
#     authorization_uri = await github_oauth_client.get_authorization_url(redirect_uri)
#     return RedirectResponse(url=authorization_uri)


@v1_router.get("/login/google")
async def login_google(request: Request):
    redirect_uri = f"{request.base_url}v1{v1_router.url_path_for('callback_google')}"
    authorization_uri = await google_oauth_client.get_authorization_url(redirect_uri)
    return RedirectResponse(url=authorization_uri)


# @v1_router.get("/callback/github")
# async def callback_github(request: Request, access_token_state=Depends(github_authorize_callback)):
#     try:
#         token = access_token_state[0]
#         print(token)
#         access_token = token["access_token"]
#         profile = await github_oauth_client.get_profile(access_token)

#     except Exception as e:
#         logger.error(f"Github OAuth2 callback failed with an unexpected error: {e}")
#         return redirect_oauth_failure()

#     return profile


@v1_router.get("/callback/google")
async def callback_google(access_token_state=Depends(google_authorize_callback)):
    with get_session() as session:
        try:
            token = access_token_state[0]
            profile = jwt.decode(token.get("id_token"), options={"verify_signature": False})
            user = find_or_create_user(session, profile.get("email"), profile.get("picture"))
            tokens = generate_access_and_refresh_tokens(session, user)
            return redirect_oauth_success(tokens)

        except Exception as e:
            logger.error(f"Google OAuth2 callback failed with an unexpected error: {e}")
            return redirect_oauth_failure()


@v1_router.post("/refresh")
def refresh(input: RefreshInput):
    with get_session() as session:
        refresh_token = decode_jwt_refresh_token(token=input.refresh_token)
        if refresh_token is None:
            raise HTTPException(status_code=401)

        # Delete expired refresh tokens for this user:
        session.exec(
            delete(UserRefreshToken).where(
                UserRefreshToken.user_id == refresh_token.user_id,
                UserRefreshToken.created_at < UserRefreshToken.oldest_valid_datetime(),
            )
        )
        session.commit()

        # Attempt to find a remaining, valid refresh token for this user:
        user_refresh_token = session.exec(
            select(UserRefreshToken).where(
                UserRefreshToken.id == refresh_token.id,
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


# TODO:
# - Wrap up client side retry/refresh logic
# - Test google flows thoroughly with new refresh flow logic
# - Update github flows and test
# - Add anonymous sign in flow (figure out what to do about refresh token expiration)
# - Add wallet sign in flows
# - Handle various TODO comments
# - Document all auth decisions so far
#   - EG: Refresh token forcing a user to sign in manually every X days


# Anonymous => Results in a user id
# Social => Results in a user id and an email column
# Wallet => Results in a user id and a near_account_id column


# Access token JWT would live 1 hour ("auth" secure cookie)
# Refresh token would live 1 month ("refresh-token" secure cookie)
# Store refresh tokens in table with created_at timestamp to dynamically determine if they're still valid
# If API detects expired JWT, respond 401 EXPIRED_TOKEN
# Client catches 401 and reaches back out to API with refresh token and then retries failed endpoint
