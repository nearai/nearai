import json

from pydantic import BaseModel


class AuthData(BaseModel):
    account_id: str
    signature: str
    public_key: str
    callback_url: str
    nonce: str
    recipient: str
    message: str

    def generate_bearer_token(self):
        """Generates a JSON-encoded bearer token containing authentication data."""
        required_keys = {"account_id", "public_key", "signature", "callback_url", "message", "nonce", "recipient"}

        for key in required_keys:
            if getattr(self, key) is None:
                raise ValueError(f"Missing required auth data: {key}")

        bearer_data = {key: getattr(self, key) for key in required_keys}

        return json.dumps(bearer_data)
