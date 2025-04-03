import json
import os
import select
import sys
import inspect
import re
import importlib.metadata
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.box import ROUNDED

from nearai.registry import validate_version
from nearai.banners import NEAR_AI_BANNER


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


def format_help(obj, method_name: str) -> None:
    """Format a method's docstring as a help message and display it with rich formatting.
    
    Args:
        obj: The object containing the method
        method_name: The name of the method whose docstring should be formatted as help,
                     or "__class__" to format the class's docstring
    """
    console = Console()
    
    # Get the docstring - either from the method or from the class itself
    if method_name == "__class__":
        docstring = inspect.getdoc(obj)
        if not docstring:
            console.print(f"[bold red]No documentation available for {obj.__class__.__name__}[/bold red]")
            return
        # Use the class name for the title
        class_name = obj.__class__.__name__
        # Remove "Cli" suffix if present for cleaner display
        display_name = class_name.replace("Cli", "")
        title = display_name
        
        # Special case for CLI class to show banner and version
        if class_name == "CLI":
            version = importlib.metadata.version("nearai")
            console.print(NEAR_AI_BANNER)
            console.print(f"[bold cyan]NEAR AI CLI[/bold cyan] [dim]v{version}[/dim]\n")
    else:
        # Get the method object and its docstring
        method = getattr(obj, method_name, None)
        if not method or not method.__doc__:
            console.print(f"[bold red]No documentation available for {method_name}[/bold red]")
            return
        docstring = inspect.getdoc(method)
        
        # Extract the first line as the title
        title_match = re.match(r'^(.*?)\.(?:\s|$)', docstring, re.DOTALL)
        title = title_match.group(1) if title_match else method_name.capitalize()
        
        # Remove the title from the docstring for further processing
        if title_match:
            docstring = docstring[len(title_match.group(0)):].strip()
    
    # Extract sections
    sections = {}
    current_section = "description"
    sections[current_section] = []
    
    lines = docstring.split("\n")
    for i, line in enumerate(lines):
        # Check if this line could be a section header
        if re.match(r'^[A-Za-z][A-Za-z\s]+:$', line):
            current_section = line[:-1].lower()  # Remove the colon
            sections[current_section] = []
        else:
            sections[current_section].append(line)
    
    # If it's not the CLI class (which already has a banner), print the header
    if method_name != "__class__" or obj.__class__.__name__ != "CLI":
        console.print(f"\n[bold cyan]NEAR AI {title}[/bold cyan]\n")
    
    # Print main description
    description = "\n".join(sections.get("description", [])).strip()
    if description:
        console.print(
            Panel(
                description,
                title=f"About {title}",
                border_style="blue",
                expand=False,
            )
        )
    
    # We'll handle examples separately to avoid duplication
    all_sections = list(sections.keys())
    examples_section = "examples" if "examples" in all_sections else None
    processed_sections = set()
    processed_sections.add("description")  # we already processed the description

    # Print command sections
    command_sections = []
    for section_name in sections.keys():
        if section_name == "commands":
            command_sections.append(("Commands", sections[section_name]))
            processed_sections.add(section_name)
        elif section_name in ["getting started", "agent development", "registry management", 
                             "model operations", "configuration"]:
            command_sections.append((section_name.title(), sections[section_name]))
            processed_sections.add(section_name)
    
    # Process each command section
    for section_title, section_content in command_sections:
        console.print(f"[bold green]{section_title}:[/bold green]\n")
        
        commands_table = Table(box=ROUNDED, expand=False)
        commands_table.add_column("Command", style="cyan bold", no_wrap=True)
        commands_table.add_column("Description", style="white")
        commands_table.add_column("Flags", style="dim")
        
        for line in section_content:
            if line.strip():
                # Try to parse command, description, and flags
                match = re.match(r'^\s*(\S+)\s+(.*?)(?:\s*\(([^)]*)\)|$)', line)
                if match:
                    cmd = match.group(1)
                    desc = match.group(2).strip()
                    flags = match.group(3) or ""
                    prefix = "nearai " if not cmd.startswith("nearai ") else ""
                    commands_table.add_row(f"{prefix}{cmd}", desc, flags)
        
        # For the CLI class, display in panels for each category
        if obj.__class__.__name__ == "CLI":
            console.print(Panel(commands_table, border_style="green", expand=False))
            console.print()  # Add spacing between categories
        else:
            console.print(commands_table)
            
            # Check if there are any required parameters (marked with *)
            has_required = False
            for line in section_content:
                if '*' in line:
                    has_required = True
                    break
            
            if has_required:
                console.print("\n* Required parameter\n")
    
    # Print command syntax if available
    if "usage" in sections:
        console.print("[bold green]Command Syntax:[/bold green]\n")
        for line in sections["usage"]:
            if line.strip():
                console.print(line)
        console.print("")
        processed_sections.add("usage")
    
    # Print options or flag details if available
    flag_section = None
    if "options" in sections:
        flag_section = "options"
    elif "flag details" in sections:
        flag_section = "flag details"
    
    if flag_section:
        console.print("[bold green]Flag Details:[/bold green]\n")
        
        flag_table = Table(box=None, show_header=False, padding=(0, 2), expand=False)
        flag_table.add_column(style="yellow")
        flag_table.add_column(style="white")
        
        current_flag = None
        current_desc = []
        
        for line in sections[flag_section]:
            if line.strip():
                # Check if this line defines a new flag
                flag_match = re.match(r'^\s*(-{1,2}\w+)\s+(.*?)$', line)
                if flag_match:
                    if current_flag:
                        flag_table.add_row(current_flag, " ".join(current_desc))
                    current_flag = flag_match.group(1)
                    current_desc = [flag_match.group(2).strip()]
                else:
                    # This is a continuation of the previous flag's description
                    if current_flag:
                        current_desc.append(line.strip())
        
        # Add the last flag
        if current_flag:
            flag_table.add_row(current_flag, " ".join(current_desc))
        
        console.print(flag_table)
        processed_sections.add(flag_section)
    
    # Print parameter details if available
    if "parameter details" in sections:
        console.print("\n[bold green]Parameter Details:[/bold green]\n")
        
        param_table = Table(box=None, show_header=False, padding=(0, 2), expand=False)
        param_table.add_column(style="yellow")
        param_table.add_column(style="white")
        
        current_param = None
        current_desc = []
        
        for line in sections["parameter details"]:
            if line.strip():
                # Check if this line defines a new parameter
                param_match = re.match(r'^\s*(\w+)\s+(.*?)$', line)
                if param_match:
                    if current_param:
                        param_table.add_row(current_param, " ".join(current_desc))
                    current_param = param_match.group(1)
                    current_desc = [param_match.group(2).strip()]
                else:
                    # This is a continuation of the previous parameter's description
                    if current_param:
                        current_desc.append(line.strip())
        
        # Add the last parameter
        if current_param:
            param_table.add_row(current_param, " ".join(current_desc))
        
        console.print(param_table)
        processed_sections.add("parameter details")
    
    # Print Common Configuration Keys table if available
    if "common configuration keys" in sections:
        console.print("\n[bold green]Common Configuration Keys:[/bold green]\n")
        
        keys_table = Table(box=ROUNDED, expand=False)
        keys_table.add_column("Key", style="yellow")
        keys_table.add_column("Description", style="white")
        keys_table.add_column("Default Value", style="dim")
        
        current_key = None
        current_desc = []
        current_default = ""
        
        for line in sections["common configuration keys"]:
            if line.strip():
                # Format: key Description (default: value)
                key_match = re.match(r'^\s*(\S+)\s+(.*?)(?:\(default:\s*(.*?)\))?$', line)
                if key_match:
                    if current_key:
                        keys_table.add_row(current_key, " ".join(current_desc), current_default)
                    current_key = key_match.group(1)
                    current_desc = [key_match.group(2).strip()]
                    current_default = key_match.group(3) or ""
                else:
                    # This is a continuation of the previous key's description
                    if current_key:
                        current_desc.append(line.strip())
        
        # Add the last key
        if current_key:
            keys_table.add_row(current_key, " ".join(current_desc), current_default)
        
        console.print(keys_table)
        processed_sections.add("common configuration keys")
    
    # Print Entry Location Format if available (specific to Registry)
    if "entry location format" in sections:
        console.print("\n[bold green]Entry Location Format:[/bold green]\n")
        for line in sections["entry location format"]:
            if line.strip():
                # Add cyan color to format examples
                formatted_line = re.sub(r'(\S+/\S+/\S+)', r'[cyan]\1[/cyan]', line)
                console.print(formatted_line)
        console.print("")
        processed_sections.add("entry location format")
    
    # Always process the examples section here - if there are specific examples with certain commands
    # they will be handled in the command-specific docstrings
    if examples_section and examples_section not in processed_sections:
        console.print("\n[bold green]Examples:[/bold green]\n")
        for line in sections[examples_section]:
            if line.strip():
                if line.startswith("#"):
                    console.print(f"[dim]{line}[/dim]")
                else:
                    console.print(f"[cyan]{line}[/cyan]")
            else:
                console.print("")
        processed_sections.add(examples_section)
    
    # Print footer with docs link if available
    for section_name, section_content in sections.items():
        if section_name not in processed_sections and ("documentation" in section_name.lower() or "for detailed" in " ".join(section_content).lower()):
            content = " ".join(section_content).strip()
            console.print(f"\n[bold blue]{content}[/bold blue]\n")
            processed_sections.add(section_name)


def handle_help_request(args=None):
    """Common handler for CLI help requests.
    
    Args:
        args: Command line arguments (uses sys.argv if None)
    
    Returns:
        True if help was displayed, False otherwise
    """
    import sys
    from nearai.cli import CLI
    
    if args is None:
        args = sys.argv
    
    # Create CLI instance
    cli = CLI()
    
    # Special case for agent upload, which is an alias for registry upload
    if len(args) == 4 and args[1] == "agent" and args[2] == "upload" and args[3] == "--help":
        format_help(cli.registry, "upload")
        return True
    
    # No arguments - show main help
    if len(args) == 1:
        format_help(cli, "__class__")
        return True
    
    # Help with no specific command
    if len(args) == 2 and args[1] == "--help":
        format_help(cli, "__class__")
        return True
    
    # Help for a specific command
    if len(args) == 3 and args[2] == "--help":
        command = args[1]
        if hasattr(cli, command):
            format_help(getattr(cli, command), "__class__")
            return True
    
    # Help for a specific subcommand
    if len(args) == 4 and args[3] == "--help":
        command, subcommand = args[1:3]
        if hasattr(cli, command):
            cmd_obj = getattr(cli, command)
            if hasattr(cmd_obj, subcommand):
                format_help(cmd_obj, subcommand)
                return True
    
    return False
