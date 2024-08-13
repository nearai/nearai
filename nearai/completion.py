import json
from typing import Any, Callable, Iterable, Optional, Union

from litellm import CustomStreamWrapper, ModelResponse
from litellm import completion as litellm_completion
from openai import OpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam

from .config import CONFIG, NearAiHubConfig, Config
from hub.api.near.primitives import get_provider_model


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

    def completions(
        self,
        model: str,
        messages: Iterable[ChatCompletionMessageParam],
        stream: bool = False,
        temperature: Optional[float] = None,
        **kwargs: Any,
    ) -> Union[ModelResponse, CustomStreamWrapper]:
        """Takes a model `provider:model_name` and a list of messages and returns all completions."""

        provider, model = get_provider_model(self._config.nearai_hub.default_provider, model)

        auth = self._config.auth
        bearer_data = {key: getattr(auth, key) for key in ["account_id", "public_key", "signature", "callback_url", "message", "nonce", "recipient"]}
        auth_bearer_token = json.dumps(bearer_data)

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

        result: Union[ModelResponse, CustomStreamWrapper] = self._endpoint(
            model=model, messages=messages, stream=stream, temperature=temperature, **kwargs
        )
        return result
