import re
from datetime import datetime as dt
from datetime import timezone
from pathlib import Path
from typing import Any

from openapi_client.models.entry_location import EntryLocation

from nearai.config import CONFIG

entry_location_pattern = re.compile("^(?P<namespace>[^/]+)/(?P<name>[^/]+)/(?P<version>[^/]+)$")


def parse_location(entry_location: str) -> EntryLocation:
    """Create a EntryLocation from a string in the format namespace/name/version."""
    match = entry_location_pattern.match(entry_location)

    if match is None:
        raise ValueError(f"Invalid entry format: {entry_location}. Should have the format <namespace>/<name>/<version>")

    return EntryLocation(
        namespace=match.group("namespace"),
        name=match.group("name"),
        version=match.group("version"),
    )


def plain_location(entry_location: EntryLocation) -> str:
    return f"{entry_location.namespace}/{entry_location.name}/{entry_location.version}"


def timestamp() -> str:
    return dt.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")


def cli_path() -> Path:
    return Path(__file__).parent.parent


def etc(file: str) -> Path:
    return cli_path() / "etc" / file


def get_origin() -> str:
    if CONFIG.origin:
        return CONFIG.origin

    if CONFIG.user_name:
        return CONFIG.user_name

    CONFIG.origin = f"anonymous_{timestamp()}"
    return CONFIG.origin


def log(*, target: str, **content: Any) -> None:
    # TODO: Push logs to the API
    # origin = get_origin()
    # db.log(origin=origin, target=target, content=content)
    print("WARNING: Logging is disabled")


def _check_metadata(path: Path):
    if not path.exists():
        print(f"Metadata file not found: {path.absolute()}")
        print("Create a metadata file with `nearai registry metadata_template`")
        exit(1)
