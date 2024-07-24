from datetime import datetime as dt
from datetime import timezone
from pathlib import Path

from nearai.config import CONFIG
from nearai.db import db


def timestamp() -> str:
    return dt.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")


def cli_path() -> Path:
    return Path(__file__).parent.parent


def etc(file: str) -> Path:
    return cli_path() / "etc" / file


def get_origin():
    if CONFIG.origin:
        return CONFIG.origin

    if CONFIG.user_name:
        return CONFIG.user_name

    CONFIG.origin = f"anonymous_{timestamp()}"
    return CONFIG.origin


def log(*, target: str, **content):
    origin = get_origin()
    db.log(origin=origin, target=target, content=content)
