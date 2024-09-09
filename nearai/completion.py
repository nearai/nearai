import json
from typing import Any, Callable, Iterable, List, Optional, Union

import requests
from litellm import CustomStreamWrapper, ModelResponse
from litellm import completion as litellm_completion
from openai import OpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam

from hub.api.near.primitives import get_provider_model
from hub.api.v1.sql import SimilaritySearch

from .config import CONFIG, AuthData, Config, NearAiHubConfig


def create_completion_fn(model: str) -> Callable[..., ChatCompletion]:
    client = OpenAI(base_url=CONFIG.inference_url, api_key=CONFIG.inference_api_key)

    def complete(**kwargs: Any) -> ChatCompletion:
        completion: ChatCompletion = client.chat.completions.create(model=model, **kwargs)
        return completion

    return complete


class InferenceRouter(object):
    def __init__(self, config: Config) -> None:  # noqa: D107
        self._config = config
        if self._config.nearai_hub is None:
            self._config.nearai_hub = NearAiHubConfig()
        self._endpoint: Any

    def get_auth_str(self, auth: Optional[AuthData] = None) -> str:
        """Get authentication string from provided auth or config object.

        Args:
        ----
            auth (Optional[AuthData]): Authentication data. If None, uses config auth.

        Returns:
        -------
            str: JSON string containing authentication data.

        """
        _auth = auth
        if auth is None:
            _auth = self._config.auth

        bearer_data = {
            key: getattr(_auth, key)
            for key in ["account_id", "public_key", "signature", "callback_url", "message", "nonce", "recipient"]
        }

        return json.dumps(bearer_data)

    def completions(
        self,
        model: str,
        messages: Iterable[ChatCompletionMessageParam],
        stream: bool = False,
        temperature: Optional[float] = None,
        auth: Optional[AuthData] = None,
        **kwargs: Any,
    ) -> Union[ModelResponse, CustomStreamWrapper]:
        """Takes a model `provider:model_name` and a list of messages and returns all completions."""
        if self._config.nearai_hub is None:
            raise ValueError("Missing NearAI Hub config")
        provider, model = get_provider_model(self._config.nearai_hub.default_provider, model)

        auth_bearer_token = self.get_auth_str(auth)

        self._endpoint = lambda model, messages, stream, temperature, **kwargs: litellm_completion(
            model,
            messages,
            stream=stream,
            custom_llm_provider=self._config.nearai_hub.custom_llm_provider,
            input_cost_per_token=0,
            output_cost_per_token=0,
            temperature=temperature,
            base_url=self._config.nearai_hub.base_url,
            provider=provider,
            api_key=auth_bearer_token,
            **kwargs,
        )

        try:
            result: Union[ModelResponse, CustomStreamWrapper] = self._endpoint(
                model=model, messages=messages, stream=stream, temperature=temperature, **kwargs
            )
        except Exception as e:
            raise ValueError(f"Bad request: {e}") from None

        return result

    def query_vector_store(
        self, vector_store_id: str, query: str, auth: Optional[AuthData] = None
    ) -> List[SimilaritySearch]:
        """Query a vector store."""
        if self._config.nearai_hub is None:
            raise ValueError("Missing NearAI Hub config")

        auth_bearer_token = self.get_auth_str(auth)

        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {auth_bearer_token}"}

        data = {"query": query}

        endpoint = f"{self._config.nearai_hub.base_url}/vector_stores/{vector_store_id}/search"

        try:
            response = requests.post(endpoint, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise ValueError(f"Error querying vector store: {e}") from None
