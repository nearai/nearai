import json
import os
import select
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table


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


def has_pending_input():
    """Check if there's input waiting to be read without blocking."""
    if os.name == "nt":  # Windows
        import msvcrt

        return msvcrt.kbhit()
    else:  # Unix/Linux/Mac
        rlist, _, _ = select.select([sys.stdin], [], [], 0)
        return bool(rlist)
