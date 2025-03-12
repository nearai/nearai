import base64
import hashlib
import logging
import time
from enum import Enum
from typing import Any, List, Optional, Union

import base58
import ed25519
import nacl.signing
import requests

from nearai.shared.cache import mem_cache_with_timeout
from nearai.shared.near.serializer import BinarySerializer

ED_PREFIX = "ed25519:"  # noqa: N806
logger = logging.getLogger(__name__)


class Payload:
    def __init__(  # noqa: D107
        self, message: str, nonce: Union[bytes, str, List[int]], recipient: str, callback_url: Optional[str] = None
    ):
        self.tag = 2147484061
        self.message = message
        self.nonce = validate_nonce(nonce)
        self.recipient = recipient
        self.callbackUrl = callback_url


PAYLOAD_SCHEMA: list[list[Any]] = [
    [
        Payload,
        {
            "kind": "struct",
            "fields": [
                ["tag", "u32"],
                ["message", "string"],
                ["nonce", [32]],
                ["recipient", "string"],
                [
                    "callbackUrl",
                    {
                        "kind": "option",
                        "type": "string",
                    },
                ],
            ],
        },
    ]
]


def convert_nonce(value: Union[str, bytes, list[int]]):
    """Converts a given value to a 32-byte nonce."""
    if isinstance(value, bytes):
        if len(value) > 32:
            raise ValueError("Invalid nonce length")
        if len(value) < 32:
            value = value.rjust(32, b"0")
        return value
    elif isinstance(value, str):
        nonce_bytes = value.encode("utf-8")
        if len(nonce_bytes) > 32:
            raise ValueError("Invalid nonce length")
        if len(nonce_bytes) < 32:
            nonce_bytes = nonce_bytes.rjust(32, b"0")
        return nonce_bytes
    elif isinstance(value, list):
        if len(value) != 32:
            raise ValueError("Invalid nonce length")
        return bytes(value)
    else:
        raise ValueError("Invalid nonce format")


def validate_nonce(value: Union[str, bytes, list[int]]):
    """Ensures that the nonce is a valid timestamp."""
    nonce = convert_nonce(value)
    nonce_int = int(nonce.decode("utf-8"))

    now = int(time.time() * 1000)

    if nonce_int > now:
        raise ValueError("Nonce is in the future")
    if now - nonce_int > 10 * 365 * 24 * 60 * 60 * 1000:
        """If the timestamp is older than 10 years, it is considered invalid. Forcing apps to use unique nonces."""
        raise ValueError("Nonce is too old")

    return nonce


class SignatureVerificationResult(Enum):
    TRUE = True
    FALSE = False
    VERIFY_ACCESS_KEY_OWNER_SERVICE_NOT_AVAILABLE = "verify_access_key_owner_not_available"

    @classmethod
    def from_bool(cls, value: bool):
        """Gets VerificationResult based on a boolean value."""
        return cls.TRUE if value else cls.FALSE

    def __bool__(self):
        """Overrides the behavior when checking for truthiness."""
        return self == SignatureVerificationResult.TRUE


def verify_signed_message(
    account_id, public_key, signature, message, nonce, recipient, callback_url
) -> SignatureVerificationResult:
    """Verifies a signed message and ensures the public key belongs to the specified account."""
    is_valid = validate_signature(public_key, signature, Payload(message, nonce, recipient, callback_url))

    if not is_valid and callback_url is not None:
        is_valid = validate_signature(public_key, signature, Payload(message, nonce, recipient, None))

    if is_valid:
        # verify that key belongs to `account_id`
        return verify_access_key_owner(public_key, account_id)

    # TODO verifies that key is a FULL ACCESS KEY

    return SignatureVerificationResult.FALSE


@mem_cache_with_timeout(300)
def verify_access_key_owner(public_key, account_id) -> SignatureVerificationResult:
    """Verifies if a given public key belongs to a specified account ID using FastNEAR API."""
    try:
        logger.info(f"Verifying access key owner for public key: {public_key}, account_id: {account_id}")
        url = f"https://api.fastnear.com/v0/public_key/{public_key}"
        response = requests.get(url)
        response.raise_for_status()
        content = response.json()
        account_ids = content.get("account_ids", [])
        key_owner_verified = account_id in account_ids
        if not key_owner_verified:
            logger.info("Key's owner verification failed. Only NEAR Mainnet accounts are supported.")
        return SignatureVerificationResult.from_bool(key_owner_verified)
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err}")
    except Exception as err:
        logger.error(f"Other error occurred: {err}")

    return SignatureVerificationResult.VERIFY_ACCESS_KEY_OWNER_SERVICE_NOT_AVAILABLE


def create_signature(private_key: str, payload: Payload) -> tuple[str, str]:
    """Creates a cryptographic signature for a given payload using a specified private key."""
    borsh_payload = BinarySerializer(dict(PAYLOAD_SCHEMA)).serialize(payload)

    to_sign = hashlib.sha256(borsh_payload).digest()

    # Extract and decode the private key
    private_key_base58 = private_key[len(ED_PREFIX) :]
    private_key_bytes = base58.b58decode(private_key_base58)

    if len(private_key_bytes) != 64:
        raise ValueError("The private key must be exactly 64 bytes long")

    # Use only the first 32 bytes as the seed
    private_key_seed = private_key_bytes[:32]

    signing_key = nacl.signing.SigningKey(private_key_seed)
    public_key = signing_key.verify_key

    signed = signing_key.sign(to_sign)
    signature = base64.b64encode(signed.signature).decode("utf-8")

    public_key_base58 = base58.b58encode(public_key.encode()).decode("utf-8")
    full_public_key = ED_PREFIX + public_key_base58

    return signature, full_public_key


def validate_signature(public_key: str, signature: str, payload: Payload):
    """Validates a cryptographic signature for a given payload using a specified public key."""
    borsh_payload = BinarySerializer(dict(PAYLOAD_SCHEMA)).serialize(payload)
    to_sign = hashlib.sha256(borsh_payload).digest()
    real_signature = base64.b64decode(signature)

    verify_key: nacl.signing.VerifyKey = nacl.signing.VerifyKey(base58.b58decode(public_key[len(ED_PREFIX) :]))

    try:
        verify_key.verify(to_sign, real_signature)
        # print("Signature is valid.")
        return True
    except nacl.exceptions.BadSignatureError:
        # print("Signature was forged or corrupt.")
        return False


class CompletionSignaturePayload:
    def __init__(  # noqa: D107
        self,
        agent_name: str,
        completion: str,
        model: str,
        messages: list[dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        temperature = round(float(temperature or 0) * 1000)

        self.agent_name = agent_name
        self.model = model
        self.messages = messages
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.completion = completion


COMPLETION_PAYLOAD_SCHEMA: list[list[Any]] = [
    [
        CompletionSignaturePayload,
        {
            "kind": "struct",
            "fields": [
                ["agent_name", "string"],
                ["model", "string"],
                [
                    "messages",
                    [
                        {
                            "kind": "struct",
                            "fields": [
                                ["role", "string"],
                                ["content", "string"],
                            ],
                        }
                    ],
                ],
                [
                    "temperature",
                    {
                        "kind": "option",
                        "type": "u32",
                    },
                ],
                [
                    "max_tokens",
                    {
                        "kind": "option",
                        "type": "u32",
                    },
                ],
                ["completion", "string"],
            ],
        },
    ]
]


def validate_completion_signature(public_key: str, signature: str, payload: CompletionSignaturePayload):
    """Validates a cryptographic signature for a given payload using a specified public key."""
    borsh_payload = BinarySerializer(dict(COMPLETION_PAYLOAD_SCHEMA)).serialize(payload)
    to_sign = hashlib.sha256(borsh_payload).digest()
    real_signature = base64.b64decode(signature)

    verify_key: nacl.signing.VerifyKey = nacl.signing.VerifyKey(base58.b58decode(public_key[len(ED_PREFIX) :]))

    try:
        verify_key.verify(to_sign, real_signature)
        return True
    except nacl.exceptions.BadSignatureError:
        return False


def derive_new_extended_private_key(extended_private_key: str, addition: str) -> str:
    private_key_base58 = extended_private_key.replace("ed25519:", "")

    decoded = base58.b58decode(private_key_base58)
    secret_key = decoded[:32]

    combined = secret_key + addition.encode()
    derived_secret_key = hashlib.sha256(combined).digest()[:32]  # 32 bytes

    new_signing_key = ed25519.SigningKey(derived_secret_key)

    new_secret_key_bytes = new_signing_key.to_bytes() + new_signing_key.get_verifying_key().to_bytes()

    new_private_key_base58 = base58.b58encode(new_secret_key_bytes[:64]).decode()

    return f"ed25519:{new_private_key_base58}"


def create_inference_signature(private_key: str, payload: CompletionSignaturePayload) -> tuple[str, str]:
    """Creates a cryptographic signature for a given extended inference payload using a specified private key."""
    borsh_payload = BinarySerializer(dict(COMPLETION_PAYLOAD_SCHEMA)).serialize(payload)

    to_sign = hashlib.sha256(borsh_payload).digest()

    private_key_base58 = private_key[len(ED_PREFIX) :]
    private_key_bytes = base58.b58decode(private_key_base58)

    if len(private_key_bytes) != 64:
        raise ValueError("The private key must be exactly 64 bytes long")

    private_key_seed = private_key_bytes[:32]

    signing_key = nacl.signing.SigningKey(private_key_seed)
    public_key = signing_key.verify_key

    signed = signing_key.sign(to_sign)
    signature = base64.b64encode(signed.signature).decode("utf-8")

    public_key_base58 = base58.b58encode(public_key.encode()).decode("utf-8")
    full_public_key = ED_PREFIX + public_key_base58

    return signature, full_public_key


def get_public_key(extended_private_key):
    private_key_base58 = extended_private_key.replace("ed25519:", "")

    decoded = base58.b58decode(private_key_base58)
    secret_key = decoded[:32]

    signing_key = ed25519.SigningKey(secret_key)
    verifying_key = signing_key.get_verifying_key()

    base58_public_key = base58.b58encode(verifying_key.to_bytes()).decode()

    return f"ed25519:{base58_public_key}"
