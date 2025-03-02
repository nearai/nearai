import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from rich.console import Console
from rich.table import Table

from nearai.config import CONFIG
from nearai.registry import parse_location, registry


def display_agents_in_columns(agents: list[Path]) -> None:
    """Display agents in a rich table format.

    Args:
    ----
        agents: List of Path objects pointing to agent locations (pre-sorted)

    """
    # Create table
    table = Table(title="Available Agents", show_header=True, header_style="bold", show_lines=True, expand=True)

    # Add columns
    table.add_column("#", style="bold", width=4)
    table.add_column("Namespace", style="blue")
    table.add_column("Agent Name", style="cyan")
    table.add_column("Version", style="green")
    table.add_column("Description", style="white")
    table.add_column("Tags", style="yellow")

    # Add rows
    for idx, agent_path in enumerate(agents, 1):
        try:
            # Read metadata for additional info
            with open(agent_path / "metadata.json") as f:
                metadata = json.load(f)
                description = metadata.get("description", "No description")
                tags = metadata.get("tags", [])
        except (FileNotFoundError, json.JSONDecodeError):
            description = "Unable to load metadata"
            tags = []

        # Add row to table with separated path components
        table.add_row(
            str(idx),
            agent_path.parts[-3],  # namespace
            agent_path.parts[-2],  # agent name
            agent_path.parts[-1],  # version
            description,
            ", ".join(tags) if tags else "—",
        )

    # Display table
    console = Console()
    console.print("\n")
    console.print(table)
    console.print("\n")


def increment_version(version_str: str) -> str:
    """Increment the patch version of a semver string.

    Args:
    ----
        version_str: The version string to increment

    Returns:
    -------
        The incremented version string

    """
    try:
        return increment_version_by_type(version_str, "patch")
    except ValueError:
        # If version doesn't follow semver, append .1
        return f"{version_str}.1"


def load_and_validate_metadata(metadata_path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Load and validate metadata.json file.

    Args:
    ----
        metadata_path: Path to the metadata.json file

    Returns:
    -------
        Tuple of (metadata dict, error message)
        If validation fails, metadata will be None and error will contain the error message

    """
    if not metadata_path.exists():
        return None, f"Error: metadata.json not found in {metadata_path.parent}"

    try:
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        name = metadata.get("name")
        version = metadata.get("version")

        if not name or not version:
            return None, "Error: metadata.json must contain 'name' and 'version' fields"

        # Get namespace from auth
        if CONFIG.auth is None or CONFIG.auth.namespace is None:
            return None, "Please login with `nearai login` before uploading"

        return metadata, None
    except json.JSONDecodeError:
        return None, f"Error: {metadata_path} is not a valid JSON file"


def check_version_exists(namespace: str, name: str, version: str) -> Tuple[bool, Optional[str]]:
    """Check if a version already exists in the registry.

    Args:
    ----
        namespace: The namespace
        name: The agent name
        version: The version to check

    Returns:
    -------
        Tuple of (exists, error)
        If exists is True, the version exists
        If error is not None, an error occurred during checking

    """
    entry_location = f"{namespace}/{name}/{version}"
    try:
        print(f"Checking if version {version} exists in the registry...")
        existing_entry = registry.info(parse_location(entry_location))

        if existing_entry:
            return True, None
        return False, None
    except Exception as e:
        # Only proceed if the error indicates the entry doesn't exist
        if "not found" in str(e).lower() or "does not exist" in str(e).lower():
            return False, None
        return False, f"Error checking registry: {str(e)}"


def increment_version_by_type(version_str: str, increment_type: str = "patch") -> str:
    """Increment a version string based on the specified increment type.

    Args:
    ----
        version_str: The version string to increment
        increment_type: Type of increment: 'patch', 'minor', or 'major'

    Returns:
    -------
        The incremented version string

    Raises:
    ------
        ValueError: If increment_type is not one of 'patch', 'minor', 'major'

    """
    if increment_type not in ["patch", "minor", "major"]:
        raise ValueError(f"Invalid increment type: {increment_type}")

    # Parse version components
    parts = version_str.split(".")

    # Ensure we have at least 3 parts (major.minor.patch)
    while len(parts) < 3:
        parts.append("0")

    # Convert to integers
    try:
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError as err:
        # Properly chain the exception with the original error
        raise ValueError(f"Invalid version format: {version_str}. Expected semver format (e.g., 1.2.3)") from err

    # Increment based on type
    if increment_type == "patch":
        patch += 1
    elif increment_type == "minor":
        minor += 1
        patch = 0
    elif increment_type == "major":
        major += 1
        minor = 0
        patch = 0

    # Reconstruct version string
    return f"{major}.{minor}.{patch}"
