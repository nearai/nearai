from typing import Any, Callable, Dict, Iterable, Optional

from litellm import completion as litellm_completion
from openai import OpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam

from .config import CONFIG, Config, LLMConfig


def create_completion_fn(model: str) -> Callable[..., ChatCompletion]:
    client = OpenAI(base_url=CONFIG.inference_url, api_key=CONFIG.inference_api_key)

    def complete(**kwargs: Any) -> ChatCompletion:
        completion: ChatCompletion = client.chat.completions.create(model=model, **kwargs)
        return completion

    return complete


class InferenceRouter(object):
    def __init__(self, config: LLMConfig) -> None:  # noqa: D107
        self._config = config
        self._endpoints: Any = {}

    def completions(
        self,
        model: str,
        messages: Iterable[ChatCompletionMessageParam],
        stream: bool = False,
        temperature: Optional[float] = None,
        **kwargs: Any,
    ) -> ChatCompletion:
        """Takes a model `provider:model_name` and a list of messages and returns all completions."""
        assert hasattr(self._config, "models") and model in self._config.models, f"Model {model} not found in config."
        provider_name: str
        model_path: str
        provider_name, model_path = self._config.models[model].split(":")
        if provider_name not in self._endpoints:
            assert (
                hasattr(self._config, "providers") and provider_name in self._config.providers
            ), f"Provider {provider_name} not found in config."
            provider_config = self._config.providers[provider_name]
            self._endpoints[provider_name] = lambda model, messages, stream, temperature, **kwargs: litellm_completion(
                model,
                messages,
                stream=stream,
                # TODO: move this to config
                custom_llm_provider="antropic" if "antropic" in provider_config.base_url else "openai",
                input_cost_per_token=0,
                output_cost_per_token=0,
                temperature=temperature,
                base_url=provider_config.base_url,
                api_key=provider_config.api_key if provider_config.api_key else "not-needed",
                **kwargs,
            )
        result: ChatCompletion = self._endpoints[provider_name](
            model=model_path, messages=messages, stream=stream, temperature=temperature, **kwargs
        )
        return result
