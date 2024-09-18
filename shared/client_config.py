from typing import Optional

from pydantic import BaseModel

from shared.auth_data import AuthData

DEFAULT_MODEL_TEMPERATURE = 1.0
DEFAULT_MODEL_MAX_TOKENS = 16384
DEFAULT_PROVIDER = "fireworks"
DEFAULT_MODEL = "llama-v3p1-405b-instruct-long"
DEFAULT_PROVIDER_MODEL = f"fireworks::accounts/fireworks/models/{DEFAULT_MODEL}"


class ClientConfig(BaseModel):
    base_url: str = "https://api.near.ai/v1"
    custom_llm_provider: str = "openai"
    auth: Optional[AuthData] = None
    default_provider: Optional[str] = None  # future: remove in favor of api decision
