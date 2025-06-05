import hashlib
import json
import os
from os import getenv
from typing import Dict

import base58
import ed25519  # type: ignore
from dotenv import load_dotenv
from nearai.shared.near.sign import (
    CompletionSignaturePayload,
    create_inference_signature,
)

ED_PREFIX = "ed25519:"  # noqa: N806

load_dotenv()


def is_trusted_runner_api_key(runner_api_key):
    trusted_runner_api_keys = os.environ.get("TRUSTED_RUNNER_API_KEYS")
    if trusted_runner_api_keys:
        trusted_runner_api_keys = json.loads(trusted_runner_api_keys)
        if (
            isinstance(trusted_runner_api_keys, list)
            and len(trusted_runner_api_keys)
            and runner_api_key in trusted_runner_api_keys
        ):
            return True

    print("Trusted runner api key not trusted, agent signature generation will be skipped")
    return False


def get_hub_key() -> str:
    return getenv("HUB_PRIVATE_KEY", "")


def get_signed_completion(
    messages: list[dict[str, str]],
    model: str,
    temperature: float,
    max_tokens: int,
    response_message_text: str,
    agent_name: str,
) -> Dict[str, str]:
    """Returns a completion for the given messages using the given model with the HUB signature."""
    hub_private_key = get_hub_key()

    payload = CompletionSignaturePayload(
        agent_name=agent_name,
        completion=response_message_text,
        model=model,
        messages=messages,
        temperature=float(temperature),
        max_tokens=int(max_tokens),
    )

    agent_key = derive_new_extended_private_key(hub_private_key, agent_name)

    signature = create_inference_signature(agent_key, payload)

    return {"response": response_message_text, "signature": signature[0], "public_key": signature[1]}


def get_public_key(extended_private_key):
    private_key_base58 = extended_private_key.replace("ed25519:", "")

    decoded = base58.b58decode(private_key_base58)
    secret_key = decoded[:32]

    signing_key = ed25519.SigningKey(secret_key)
    verifying_key = signing_key.get_verifying_key()

    base58_public_key = base58.b58encode(verifying_key.to_bytes()).decode()

    return f"ed25519:{base58_public_key}"


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
