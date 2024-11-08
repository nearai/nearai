import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import openai
from openapi_client import ApiClient, Configuration
from pydantic import BaseModel

from nearai.shared.shared.auth_data import AuthData
from shared.client_config import DEFAULT_PROVIDER, DEFAULT_PROVIDER_MODEL, ClientConfig

DATA_FOLDER = Path.home() / ".nearai"
DATA_FOLDER.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = DATA_FOLDER / "config.json"
LOCAL_CONFIG_FILE = Path(".nearai") / "config.json"
REPO_FOLDER = Path(__file__).parent.parent
PROMPTS_FOLDER = REPO_FOLDER / "nearai" / "prompts"
ETC_FOLDER = REPO_FOLDER / "etc"


def get_config_path(local: bool = False) -> Path:
    return LOCAL_CONFIG_FILE if local else CONFIG_FILE


def load_config_file(local: bool = False) -> Dict[str, Any]:
    path = get_config_path(local)

    if not path.exists():
        return {}

    with open(path) as f:
        config = json.load(f)
    return config


def save_config_file(config: Dict[str, Any], local: bool = False) -> None:
    path = get_config_path(local)

    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        json.dump(config, f, indent=4)


def update_config(key: str, value: Any, local: bool = False) -> None:
    config = load_config_file(local)
    config[key] = value
    save_config_file(config, local)


class NearAiHubConfig(BaseModel):
    """NearAiHub Config.

    login_with_near (Optional[bool]): Indicates whether to attempt login using Near Auth.

    api_key (Optional[str]): The API key to use if Near Auth is not being utilized

    base_url (Optional[str]): NearAI Hub url

    default_provider (Optional[str]): Default provider name

    default_model (Optional[str]): Default model name

    custom_llm_provider (Optional[str]): provider to be used by litellm proxy
    """

    base_url: str = "https://api.near.ai/v1"
    default_provider: str = DEFAULT_PROVIDER
    default_model: str = DEFAULT_PROVIDER_MODEL
    custom_llm_provider: str = "openai"
    login_with_near: Optional[bool] = True
    api_key: Optional[str] = ""


class Config(BaseModel):
    origin: Optional[str] = None
    api_url: Optional[str] = "https://api.near.ai"
    inference_url: str = "http://localhost:5000/v1/"
    inference_api_key: str = "n/a"
    nearai_hub: NearAiHubConfig = NearAiHubConfig()
    confirm_commands: bool = True
    auth: Optional[AuthData] = None
    num_inference_retries: int = 1

    def update_with(self, extra_config: Dict[str, Any], map_key: Callable[[str], str] = lambda x: x) -> "Config":
        """Update the config with the given dictionary."""
        dict_repr = self.model_dump()
        keys = list(map(map_key, dict_repr.keys()))

        for key in keys:
            value = extra_config.get(key, None)

            if value:
                # This will skip empty values, even if they are set in the `extra_config`
                dict_repr[key] = value

        return Config.model_validate(dict_repr)

    def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        """Get the value of a key in the config if it exists."""
        return getattr(self, key, default)

    def get_client_config(self) -> ClientConfig:  # noqa: D102
        return ClientConfig(
            base_url=CONFIG.nearai_hub.base_url,
            auth=CONFIG.auth,
            custom_llm_provider=CONFIG.nearai_hub.custom_llm_provider,
            default_provider=CONFIG.nearai_hub.default_provider,
            num_inference_retries=CONFIG.num_inference_retries,
        )


# Load default configs
CONFIG = Config()
# Update config from global config file
CONFIG = CONFIG.update_with(load_config_file(local=False))
# Update config from local config file
CONFIG = CONFIG.update_with(load_config_file(local=True))
# Update config from environment variables
CONFIG = CONFIG.update_with(dict(os.environ), map_key=str.upper)


def setup_api_client():
    kwargs = {"host": CONFIG.api_url}
    if CONFIG.auth is not None:
        kwargs["access_token"] = f"Bearer {CONFIG.auth.model_dump_json()}"
    configuration = Configuration(**kwargs)
    client = ApiClient(configuration)
    ApiClient.set_default(client)


def get_hub_client():
    signature = CONFIG.auth.model_dump_json()
    base_url = CONFIG.api_url + "/v1"
    return openai.OpenAI(base_url=base_url, api_key=signature)


setup_api_client()
