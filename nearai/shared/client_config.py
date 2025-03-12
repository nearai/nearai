import re
from typing import Optional

import openai
from pydantic import BaseModel

from nearai.shared.auth_data import AuthData

DEFAULT_TIMEOUT = 60 * 10
DEFAULT_MAX_RETRIES = 1
DEFAULT_MODEL_TEMPERATURE = 1.0
DEFAULT_MODEL_MAX_TOKENS = 16384
DEFAULT_PROVIDER = "fireworks"
DEFAULT_MODEL = "llama-v3p1-70b-instruct"
DEFAULT_PROVIDER_MODEL = f"fireworks::accounts/fireworks/models/{DEFAULT_MODEL}"
DEFAULT_NAMESPACE = "near.ai"

IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z0-9_\-.]+$")


class ClientConfig(BaseModel):
    base_url: str = "https://api.near.ai/v1"
    custom_llm_provider: str = "openai"
    auth: Optional[AuthData] = None
    default_provider: Optional[str] = None  # future: remove in favor of api decision
    num_inference_retries: int = 1

    def get_hub_client(self):
        """Get the hub client."""
        signature = f"Bearer {self.auth.model_dump_json()}" if self.auth else None
        base_url = self.base_url
        return openai.OpenAI(
            base_url=base_url, api_key=signature, timeout=DEFAULT_TIMEOUT, max_retries=DEFAULT_MAX_RETRIES
        )
