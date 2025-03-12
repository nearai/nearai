import re
from functools import cached_property
from typing import Dict, List, Optional, Tuple, cast

import requests

from nearai.shared.client_config import DEFAULT_PROVIDER, ClientConfig
from nearai.shared.naming import NamespacedName

PROVIDER_MODEL_SEP = "::"


def get_provider_model(provider: Optional[str], model: str) -> Tuple[Optional[str], str]:
    """Splits the `model` string based on a predefined separator and returns the components.

    Args:
    ----
        provider (Optional[str]): The default provider name. Can be `None` if the provider
                                  is included in the `model` string.
        model (str): The model identifier, which may include the provider name separated by
                     a specific delimiter (defined by `PROVIDER_MODEL_SEP`, e.g. `::`).

    """
    if PROVIDER_MODEL_SEP in model:
        parts = model.split(PROVIDER_MODEL_SEP)
        assert len(parts) == 2
        return parts[0], parts[1]
    return provider, model


def get_provider_namespaced_model(provider_model: str, provider: Optional[str] = None) -> Tuple[str, NamespacedName]:
    """Given `provider_model` returns provider and namespaced model."""
    provider_opt, provider_model = get_provider_model(DEFAULT_PROVIDER if not provider else provider, provider_model)
    provider = cast(str, provider_opt)

    if provider.startswith("https://"):
        return provider, NamespacedName(name=provider_model)
    if provider == "local":
        return provider, NamespacedName(name=provider_model)

    provider_model = provider_model.replace("accounts/", "")
    provider_model = provider_model.replace("fireworks/", "")
    provider_model = provider_model.replace("models/", "")
    if provider == "hyperbolic":
        provider_model = re.sub(r".*/", "", provider_model)
        return provider, NamespacedName(provider_model)
    if provider == "fireworks":
        parts = provider_model.split("/")
        if len(parts) == 1:
            return provider, NamespacedName(name=parts[0])
        elif len(parts) == 2:
            return provider, NamespacedName(namespace=parts[0], name=parts[1])
        else:
            raise ValueError(f"Invalid model format for Fireworks: {provider_model}")
    raise ValueError(f"Unrecognized provider: {provider}")


class ProviderModels:
    def __init__(self, config: ClientConfig) -> None:  # noqa: D107
        self._config = config

    @cached_property
    def provider_models(self) -> Dict[NamespacedName, Dict[str, str]]:
        """Returns a mapping canonical->provider->model_full_name."""
        client = self._config.get_hub_client()

        try:
            models = client.models.list()

            assert len(models.data) > 0, "No models found"
            result: Dict[NamespacedName, Dict[str, str]] = {}
            for model in models.data:
                provider, namespaced_model = get_provider_namespaced_model(model.id)
                namespaced_model = namespaced_model.canonical()
                if namespaced_model not in result:
                    result[namespaced_model] = {}
                if provider in result[namespaced_model]:
                    raise ValueError(f"Duplicate entry for provider {provider} and model {namespaced_model}")
                result[namespaced_model][provider] = model.id

            return result

        except requests.RequestException as e:
            raise RuntimeError(f"Error fetching models: {str(e)}") from e

    def available_provider_matches(self, model: NamespacedName) -> Dict[str, str]:
        """Returns provider matches for `model`."""
        return self.provider_models.get(model.canonical(), {})

    def match_provider_model(self, model: str, provider: Optional[str] = None) -> Tuple[str, str]:
        """Returns provider and model_full_path for given `model` and optional `provider`.

        `model` may take different formats. Supported ones:
        1. model_full_path, e.g. "fireworks::accounts/yi-01-ai/models/yi-large"
        2. model_full_path without provider, e.g. "accounts/yi-01-ai/models/yi-large"
        3. model_short_name as used by provider, e.g. "llama-v3-70b-instruct"
        4. namespace/model_short_name as used by provider, e.g. "yi-01-ai/yi-large"
        5. model_name as used in registry, e.g. "llama-3-70b-instruct"
        6. namespace/model_name as used in registry, e.g. "near.ai/llama-3-70b-instruct"
        7. provider base url/model-name, e.g. "https://api.openai.com/v1::gpt-4o"
        """
        if provider == "":
            provider = None
        matched_provider, namespaced_model = get_provider_namespaced_model(model, provider)
        if matched_provider.startswith("https://"):
            return matched_provider, namespaced_model.name
        namespaced_model = namespaced_model.canonical()
        if namespaced_model not in self.provider_models:
            raise ValueError(f"Model {namespaced_model} not present in provider models {self.provider_models}")
        available_matches = self.provider_models[namespaced_model]
        if matched_provider not in available_matches:
            for match in available_matches.keys():
                matched_provider = match
                break
        if provider and provider != matched_provider:
            raise ValueError(
                f"Requested provider {provider} for model {model} does not match matched_provider {matched_provider}"
            )
        return matched_provider, available_matches[matched_provider]

    def get_unregistered_common_provider_models(
        self, registry_models: Dict[NamespacedName, NamespacedName]
    ) -> List[Dict[str, str]]:
        """Returns provider matches for unregistered provider models with default namespace."""
        result: List[Dict[str, str]] = []
        for namespaced_name, available_matches in self.provider_models.items():
            if namespaced_name.namespace != "" or namespaced_name in registry_models:
                continue
            result.append(available_matches)
        return result
