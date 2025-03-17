from datetime import timedelta
from os import getenv

auth_ui_url = getenv("AUTH_UI_URL")
auth_jwt_private_key = getenv("AUTH_JWT_RSA_PRIVATE_KEY")
auth_jwt_public_key = getenv("AUTH_JWT_RSA_PUBLIC_KEY")

"""
How long an access token (JWT) is valid before a refresh is required (passed as the JWT's "exp" value).
"""
auth_access_token_expiration = timedelta(hours=1)

"""
How long a refresh token (saved in DB) is considered valid based on the "created_at" column. Once expired, the token
will be deleted from the DB and the user will be prompted to sign in again.
"""
auth_refresh_token_expiration = timedelta(days=30)
