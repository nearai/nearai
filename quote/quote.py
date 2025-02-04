import base64
import hashlib

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from dstack_sdk import TappdClient  # type: ignore


class Quote:
    def __init__(self):
        """Initialize the quote object."""
        self.init_ed25519()
        self.get_quote()

    def init(self, force=False):
        """Initialize the quote object.

        If the signing address is already set, it will not be re-initialized.
        If force is True, the signing address will be forced to be re-initialized.
        """
        if self.signing_address is not None and not force:
            return

        self.init_ed25519()

        return dict(
            intel_quote=self.intel_quote,
            signing_address=self.signing_address,
        )

    def init_ed25519(self):
        """Initialize the ed25519 key pair."""
        self.ed25519_key = Ed25519PrivateKey.generate()
        self.public_key_bytes = self.ed25519_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.public_key = self.public_key_bytes.hex()
        self.signing_address = "0x" + hashlib.sha3_256(self.public_key_bytes).digest()[-20:].hex()

    def get_quote(self) -> str:
        """Get a quote for a public key."""
        # Initialize the client
        client = TappdClient()

        # Get quote for a message
        result = client.tdx_quote(self.public_key)
        quote = bytes.fromhex(result.quote)
        self.intel_quote = base64.b64encode(quote).decode("utf-8")
        return self.intel_quote

    def sign(self, content: str):
        """Sign content using ed25519."""
        message_bytes = content.encode("utf-8")
        signature = self.ed25519_key.sign(message_bytes)
        return signature.hex()
