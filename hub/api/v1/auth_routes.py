# https://docs.authlib.org/en/latest/client/fastapi.html
# https://github.com/authlib/demo-oauth-client/blob/master/fastapi-google-login/app.py
# https://docs.authlib.org/en/latest/jose/jwt.html

import logging
import urllib
import urllib.parse
from os import getenv
from typing import Optional

from authlib.integrations.starlette_client import OAuth, OAuthError
from authlib.jose import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from starlette.responses import RedirectResponse

v1_router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

auth_ui_url = getenv("AUTH_UI_URL")

bearer = HTTPBearer(auto_error=False)

oauth = OAuth()
oauth.register(
    name="google",
    client_id=getenv("GOOGLE_OAUTH_CLIENT_ID"),
    client_secret=getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


class AuthJwtToken(BaseModel):
    # TODO: Determine proper JWT fields
    email: str
    user_id: str


def parse_jwt_auth(auth: Optional[HTTPAuthorizationCredentials] = Depends(bearer)):
    if auth is None:
        return None

    if auth.credentials == "":
        raise HTTPException(status_code=401, detail="Invalid token")
    if auth.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid token scheme")

    token = jwt.decode(auth.credentials.replace("Bearer ", ""), mocked_jwt_public_key)

    return AuthJwtToken(email=token["email"], user_id=token["user_id"])


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


def redirect_oauth_error(error: OAuthError):
    return RedirectResponse(url=f"{auth_ui_url}/callback#error={error.error}")


def redirect_oauth_success(token: str):
    encoded = urllib.parse.quote(token)
    """
        NOTE: Whatever token value (string) is passed will be saved as a cookie on the client.
        This string value will then be included in all client requests to the API as a header:

        Authorization: Bearer {token}
    """
    return RedirectResponse(url=f"{auth_ui_url}/callback#token={encoded}")


@v1_router.get("/login/google")
async def login_google(request: Request):
    redirect_uri = f"{request.base_url}v1{v1_router.url_path_for('callback_google')}"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@v1_router.get("/callback/google")
async def callback_google(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as error:
        logging.error(f"Google access token verification failed: {error}")
        return redirect_oauth_error(error)

    """
        TODO: Determine what to do with Google's "token" object. Do we create a
        User and Session DB table to save their username, email, session, etc?
        Then we probably want to generate and return some form of session or JWT
        token to redirect_oauth_success().
    """

    # This log statement should be removed once we determine what to do with "token"
    logging.info(f"Google access token verification success: {token}")

    mocked_user_id = "123"
    mocked_token_payload = AuthJwtToken(email=token["userinfo"]["email"], user_id=mocked_user_id)
    print(mocked_token_payload.model_dump())
    mocked_jwt_token = jwt.encode({"alg": "RS256"}, mocked_token_payload.model_dump(), mocked_jwt_private_key)

    return redirect_oauth_success(mocked_jwt_token.decode("utf-8"))


@v1_router.get("/test")
async def test(token: Optional[AuthJwtToken] = Depends(parse_jwt_auth)):
    if token is None:
        return {}
    return token.model_dump()


# TODO: Add github flow
# TODO: Clean up and publish draft PR with info on new ENV vars
