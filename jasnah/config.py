import json
import os

from dataclasses import dataclass, field, fields
from pathlib import Path
from pydantic import BaseModel
from typing import Any, Callable, Dict, List, Optional
from typing import Any, Callable, Dict, List, Optional

DATA_FOLDER = Path.home() / ".jasnah"
DATA_FOLDER.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = DATA_FOLDER / "config.json"
LOCAL_CONFIG_FILE = Path(".jasnah") / "config.json"
REPO_FOLDER = Path(__file__).parent
PROMPTS_FOLDER = REPO_FOLDER / "prompts"


def get_config_path(local: bool = False) -> Path:
    return LOCAL_CONFIG_FILE if local else CONFIG_FILE


def load_config_file(local: bool = False) -> Dict[str, Any]:
    path = get_config_path(local)

    if not path.exists():
        return {}

    with open(path) as f:
        config = json.load(f)
    return config  # type: ignore


def save_config_file(config: Dict[str, Any], local: bool = False) -> None:
    path = get_config_path(local)

    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        json.dump(config, f, indent=4)


def update_config(key: str, value: Any, local: bool = False) -> None:
    config = load_config_file(local)
    config[key] = value
    save_config_file(config, local)


class LLMProviderConfig(BaseModel):
    base_url: str
    api_key: str


class LLMConfig(BaseModel):
    """LLM Config.
    
    Providers: {"<provider_name>": {"base_url": "<url>", "api_key": "<api_key>"}}
    
    Models: {"<model_name>": "<provider_name>:<model_path>"
    """
    providers: Dict[str, LLMProviderConfig]
    models: Dict[str, str]


@dataclass
class Config:
    s3_bucket: str = "kholinar-registry"
    s3_prefix: str = "registry"
    supervisors: List[str] = field(default_factory=list)
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    db_host: str = "35.87.119.37"
    db_port: int = 3306
    db_name: str = "jasnah"
    server_url: str = "http://ai.nearspace.info/cluster"
    origin: Optional[str] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    supervisor_id: Optional[str] = None

    inference_url: str = "http://localhost:5000/v1/"
    inference_api_key: str = "n/a"

    llm_config: LLMConfig = None

    def update_with(self, extra_config: Dict[str, Any], map_key: Callable[[str], str] = lambda x: x) -> None:
        keys = [f.name for f in fields(self)]
        for key in map(map_key, keys):
            value = extra_config.get(key, None)

            if value:
                # This will skip empty values, even if they are set in the `extra_config`
                setattr(self, key, extra_config[key])

    def get(self, key: str, default=None):
        return getattr(self, key, default)

    def get_user_name(self):
        if self.user_name is None:
            print("Please set user_name with `jasnah config set user_name <name>`")
            exit(1)
        return self.user_name


# Load default configs
CONFIG = Config()
# Update config from global config file
CONFIG.update_with(load_config_file(local=False))
# Update config from local config file
CONFIG.update_with(load_config_file(local=True))
# Update config from environment variables
CONFIG.update_with(dict(os.environ), map_key=str.upper)
