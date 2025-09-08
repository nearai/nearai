"""Wind-down mode checks for NEAR AI CLI."""

import os
from datetime import datetime

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Load environment variables
load_dotenv()


def is_wind_down_active() -> bool:
    """Check if wind-down mode is active."""
    return os.getenv("WIND_DOWN_MODE", "false").lower() == "true"


def get_wind_down_date() -> str:
    """Get the wind-down date."""
    return os.getenv("WIND_DOWN_DATE", "2025-10-01")


def check_upload_allowed() -> bool:
    """Check if uploads are allowed based on wind-down status.

    Returns:
        True if uploads are allowed, False otherwise.
    """
    if not is_wind_down_active():
        return True

    console = Console()
    wind_down_date = get_wind_down_date()

    # Format the date nicely
    try:
        date_obj = datetime.fromisoformat(wind_down_date)
        formatted_date = date_obj.strftime("%B %d, %Y")
    except:
        formatted_date = wind_down_date

    # Display wind-down message
    message = f"""
The NEAR AI Hub is winding down and will close on {formatted_date}.

As part of this process:
• New agent uploads are disabled
• Agent forking is disabled
• You can still export your existing agents

To export your agents:
1. Use the web interface at https://app.near.ai
2. Or use: nearai registry export <agent-id>

For more information, visit:
https://near.ai/blog/wind-down
"""

    console.print(
        Panel(
            Text(message.strip(), style="yellow"),
            title="[bold red]Service Wind-Down Notice[/bold red]",
            border_style="red",
            padding=(1, 2),
        )
    )

    return False


def check_create_allowed() -> bool:
    """Check if agent creation is allowed based on wind-down status.

    Returns:
        True if creation is allowed, False otherwise.
    """
    if not is_wind_down_active():
        return True

    console = Console()
    wind_down_date = get_wind_down_date()

    # Format the date nicely
    try:
        date_obj = datetime.fromisoformat(wind_down_date)
        formatted_date = date_obj.strftime("%B %d, %Y")
    except:
        formatted_date = wind_down_date

    # Display wind-down message
    message = f"""
The NEAR AI Hub is winding down and will close on {formatted_date}.

New agent creation is disabled as agents cannot be uploaded to the hub.

You can still:
• Run existing agents locally
• Export your existing agents from the hub
• Create agents for local use only (not recommended)

To export your agents:
1. Use the web interface at https://app.near.ai
2. Or use: nearai registry export <agent-id>

For more information, visit:
https://near.ai/blog/wind-down
"""

    console.print(
        Panel(
            Text(message.strip(), style="yellow"),
            title="[bold red]Service Wind-Down Notice[/bold red]",
            border_style="red",
            padding=(1, 2),
        )
    )

    return False

