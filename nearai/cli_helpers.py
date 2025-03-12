import json
import os
import select
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from rich.console import Console
from rich.table import Table
from rich.text import Text

from nearai.registry import validate_version


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


def has_pending_input():
    """Check if there's input waiting to be read without blocking."""
    if os.name == "nt":  # Windows
        import msvcrt

        return msvcrt.kbhit()
    else:  # Unix/Linux/Mac
        rlist, _, _ = select.select([sys.stdin], [], [], 0)
        return bool(rlist)


def assert_user_auth() -> None:
    """Ensure the user is authenticated.

    Raises
    ------
        SystemExit: If the user is not authenticated

    """
    from nearai.config import CONFIG

    if CONFIG.auth is None:
        print("Please login with `nearai login` first")
        exit(1)


def display_version_check(namespace: str, name: str, version: str, exists: bool) -> None:
    """Display formatted message about version existence check.

    Args:
    ----
        namespace: The namespace
        name: The agent name
        version: The version being checked
        exists: Whether the version exists

    """
    console = Console()
    console.print(
        Text.assemble(
            ("\n🔎 Checking if version ", "white"),
            (f"{version}", "green bold"),
            (" exists for ", "white"),
            (f"{name} ", "blue bold"),
            ("in the registry under ", "white"),
            (f"{namespace}", "cyan bold"),
            ("...", "white"),
        )
    )

    if exists:
        console.print(f"\n❌ [yellow]Version [cyan]{version}[/cyan] already exists.[/yellow]")
    else:
        console.print(f"\n✅ [green]Version [cyan]{version}[/cyan] is available.[/green]")
