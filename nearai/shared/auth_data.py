import json
from typing import Optional

from pydantic import BaseModel


class AuthData(BaseModel):
    account_id: str
    signature: str
    public_key: str
    callback_url: str
    nonce: str
    recipient: str
    message: str
    on_behalf_of: Optional[str] = None

    def generate_bearer_token(self):
        """Generates a JSON-encoded bearer token containing authentication data."""
        required_keys = {"account_id", "public_key", "signature", "callback_url", "message", "nonce", "recipient"}

        for key in required_keys:
            if getattr(self, key) is None:
                raise ValueError(f"Missing required auth data: {key}")

        if self.on_behalf_of is not None:
            required_keys.add("on_behalf_of")

        bearer_data = {key: getattr(self, key) for key in required_keys}

        return json.dumps(bearer_data)

    @property
    def namespace(self):
        """Get the account ID for the auth data.

        In case you are running a request on behalf of another account, this will return the account ID of the account.
        """
        if self.on_behalf_of is not None:
            return self.on_behalf_of
        return self.account_id
