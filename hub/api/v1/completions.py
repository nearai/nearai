import json
from enum import Enum
from os import getenv
from typing import Callable, List, Union

from dotenv import load_dotenv
from nearai.shared.client_config import DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT
from openai import OpenAI
from pydantic import BaseModel, field_validator

load_dotenv()


class Provider(Enum):
    HYPERBOLIC = "hyperbolic"
    FIREWORKS = "fireworks"
    LOCAL = "local"


async def handle_stream(resp_stream, add_usage_callback: Callable):
    response_chunks = []

    async for chunk in resp_stream:
        c = json.dumps(chunk.model_dump())
        response_chunks.append(c)
        print(c)
        yield f"data: {c}\n\n"

    yield "data: [DONE]\n\n"
    full_response_text = "".join(response_chunks)

    add_usage_callback(full_response_text)


def get_llm_ai(provider: str) -> OpenAI:
    if provider == "hyperbolic":
        return OpenAI(
            base_url="https://api.hyperbolic.xyz/v1",
            api_key=getenv("HYPERBOLIC_API_KEY"),
            timeout=DEFAULT_TIMEOUT,
            max_retries=DEFAULT_MAX_RETRIES,
        )
    elif provider == "fireworks":
        return OpenAI(
            base_url="https://api.fireworks.ai/inference/v1",
            api_key=getenv("FIREWORKS_API_KEY"),
            timeout=DEFAULT_TIMEOUT,
            max_retries=DEFAULT_MAX_RETRIES,
        )
    elif provider == "local":
        return OpenAI(
            base_url=getenv("PROVIDER_LOCAL_BASE_URL"),
            api_key=getenv("PROVIDER_LOCAL_API_KEY"),
            timeout=DEFAULT_TIMEOUT,
            max_retries=DEFAULT_MAX_RETRIES,
        )
    else:
        raise NotImplementedError


class Message(BaseModel):
    """A chat message."""

    role: str
    content: Union[List, str]

    @field_validator("content", mode="before")
    @classmethod
    def ensure_string_content(cls, v):
        """Ensure content within the messages is always a string."""
        if v is None:
            return ""

        # Iterate recursively over the object, converting values to str
        if isinstance(v, list):
            return [cls.ensure_string_content(i) for i in v]
        elif isinstance(v, dict):
            return {k: cls.ensure_string_content(v) for k, v in v.items()}
        else:
            return str(v)
