import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from packaging.version import InvalidVersion, Version
from rich.console import Console
from rich.table import Table
from rich.text import Text

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


def validate_version(version: str) -> Tuple[bool, Optional[str]]:
    """Validate version string according to PEP 440.

    Args:
    ----
        version: Version string to validate

    Returns:
    -------
        Tuple of (is_valid, error_message)

    """
    try:
        Version(version)
        return True, None
    except InvalidVersion as e:
        return False, f"Invalid version format: {str(e)}. Version must follow PEP 440:https://peps.python.org/pep-0440."


def increment_version_by_type(version: str, increment_type: str) -> str:
    """Increment version according to PEP 440.

    Args:
    ----
        version: Current version string
        increment_type: Type of increment ('major', 'minor', or 'patch')

    Returns:
    -------
        New version string

    Raises:
    ------
        ValueError: If increment_type is invalid or version is invalid

    """
    try:
        v = Version(version)
        major, minor, micro = v.release[:3]

        if increment_type == "major":
            return f"{major + 1}.0.0"
        elif increment_type == "minor":
            return f"{major}.{minor + 1}.0"
        elif increment_type == "patch":
            return f"{major}.{minor}.{micro + 1}"
        else:
            raise ValueError(f"Invalid increment type: {increment_type}")
    except InvalidVersion as e:
        raise ValueError(f"Invalid version format: {str(e)}") from e


def load_and_validate_metadata(metadata_path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Load and validate metadata file, including version format.

    Args:
    ----
        metadata_path: Path to metadata.json file

    Returns:
    -------
        Tuple of (metadata_dict, error_message)

    """
    try:
        with open(metadata_path) as f:
            metadata = json.load(f)

        # Validate version format
        if "version" not in metadata:
            return None, "Metadata file must contain a 'version' field"

        is_valid, error = validate_version(metadata["version"])
        if not is_valid:
            return None, error

        return metadata, None
    except FileNotFoundError:
        return None, f"Metadata file not found at {metadata_path}"
    except json.JSONDecodeError:
        return None, f"Invalid JSON in metadata file at {metadata_path}"
    except Exception as e:
        return None, f"Error reading metadata file: {str(e)}"


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
        console = Console()
        console.print(
            Text.assemble(
                ("\nChecking if version ", "white"),
                (f"{version}", "green bold"),
                (" exists for ", "dim"),
                (f"{name} ", "cyan bold"),
                ("in the registry under ", "white"),
                (f"{namespace}", "bold"),
                ("...", "white"),
            )
        )
        existing_entry = registry.info(parse_location(entry_location))

        if existing_entry:
            return True, None
        return False, None
    except Exception as e:
        # Only proceed if the error indicates the entry doesn't exist
        if "not found" in str(e).lower() or "does not exist" in str(e).lower():
            return False, None
        return False, f"Error checking registry: {str(e)}"
