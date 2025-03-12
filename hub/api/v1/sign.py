import json
import os
from os import getenv
from typing import Dict

from dotenv import load_dotenv
from nearai.shared.near.sign import (
    CompletionSignaturePayload,
    create_inference_signature,
    derive_new_extended_private_key,
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


def derive_private_key_from_string(original_pk: str, addition: str = "") -> str:
    return derive_new_extended_private_key(original_pk, addition)
