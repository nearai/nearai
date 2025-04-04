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


def format_main_menu_help(cli) -> None:
    """Format the main CLI menu help display.
    
    Args:
        cli: The CLI class instance
    """
    console = Console()
    
    # Display banner and version
    version = importlib.metadata.version("nearai")
    console.print(NEAR_AI_BANNER)
    console.print(f"[bold cyan]NEAR AI CLI[/bold cyan] [dim]v{version}[/dim]")
    
    # Get CLI docstring
    docstring = inspect.getdoc(cli)
    if not docstring:
        console.print("[bold red]No documentation available for the CLI[/bold red]")
        return
    
    # Single table for all commands
    table = Table(
        box=ROUNDED,
        expand=True,
        show_header=True,
        header_style="bold cyan",
        border_style="green"
    )
    table.add_column("Command", style="cyan")
    table.add_column("Description", style="white")
    
    # Parse docstring into sections
    sections = {}
    current_section = None
    current_lines = []
    
    # Process the docstring line by line
    for line in docstring.strip().split('\n'):
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
            
        # Check if this is a section header
        if line.endswith(':'):
            # Save previous section if we had one
            if current_section:
                sections[current_section.lower()] = current_lines
                
            # Start a new section
            current_section = line.rstrip(':')
            current_lines = []
        elif current_section:
            # Add content to the current section
            current_lines.append(line)
    
    # Save the last section if we have one
    if current_section:
        sections[current_section.lower()] = current_lines
    
    # Process each section in order they appeared in the docstring
    first_section = True
    for section_name, section_lines in sections.items():
        # Add separator between sections (except first one)
        if not first_section:
            table.add_row("", "")  # Blank row as separator
        else:
            first_section = False
        
        # Add section header
        table.add_row(f"[bold green]{section_name.title()}[/bold green]", "")
        
        # Add commands for this section
        for cmd_line in section_lines:
            # Process command line - split by 2+ spaces
            parts = re.split(r'\s{2,}', cmd_line, 1)
            if len(parts) == 2:
                cmd, desc = parts
                # Add 'nearai ' prefix
                cmd = cmd.strip()
                if not cmd.startswith("nearai "):
                    cmd = f"nearai {cmd}"
                table.add_row(cmd, desc.strip())
            else:
                # For single-word commands, still add the prefix
                cmd = cmd_line.strip()
                if not cmd.startswith("nearai ") and not cmd.startswith("["):
                    cmd = f"nearai {cmd}"
                table.add_row(cmd, "")

    console.print("\n")
    console.print(table)
    
    # Add link to docs
    console.print("\n[bold green]Documentation:[/bold green]")
    console.print(
        "[bold blue]At any time you can run `nearai <command> --help` to get more information about a command.[/bold blue]"
    )
    console.print(
        "[bold blue]Also, please refer to the NEAR AI documentation for more information: https://docs.near.ai/[/bold blue]\n"
    )


def format_class_help(obj) -> None:
    """Format a class's docstring as a help message and display it with rich formatting.
    
    Args:
        obj: The class object whose docstring should be formatted
    """
    console = Console()
    
    docstring = inspect.getdoc(obj)
    if not docstring:
        console.print(f"[bold red]No documentation available for {obj.__class__.__name__}[/bold red]")
        return
    
    # Use the class name for the title
    class_name = obj.__class__.__name__
    # Remove "Cli" suffix if present for cleaner display
    display_name = class_name.replace("Cli", "")
    
    # Display title (except for main CLI which has a banner)
    if class_name != "CLI":
        console.print(f"\n[bold cyan]NEAR AI {display_name} Commands[/bold cyan]\n")
    
    # Extract sections from docstring with simplified parsing
    sections = {}
    current_section = None
    current_content = []
    
    # Normalize line endings and handle indentation
    lines = docstring.split("\n")
    
    # Strip common indentation
    if len(lines) > 1:
        # Find the minimum indentation (excluding blank lines)
        indents = [len(line) - len(line.lstrip()) for line in lines if line.strip()]
        if indents:
            min_indent = min(indents)
            lines = [line[min_indent:] if line and len(line) >= min_indent else line for line in lines]
    
    # Parse sections - looking for "Section:" format headers
    for line in lines:
        # Check if this is a section header
        section_match = re.match(r'^([A-Za-z][A-Za-z\s]+):$', line.strip())
        if section_match:
            # Save the previous section if it exists
            if current_section:
                sections[current_section.lower()] = current_content
            
            # Start a new section
            current_section = section_match.group(1)
            current_content = []
        elif current_section and line.strip():
            # Add non-empty lines to the current section
            current_content.append(line.strip())
    
    # Save the last section
    if current_section:
        sections[current_section.lower()] = current_content
    
    # Process Description section
    if "description" in sections:
        description = " ".join(sections["description"])
        if description:
            console.print(
                Panel(
                    description,
                    title=f"{display_name} Info",
                    border_style="green",
                    expand=False,
                )
            )
    
    # Process Commands section
    if "commands" in sections:
        console.print("\n[bold green]Available Commands:[/bold green]\n")
        commands_table = Table(box=ROUNDED, expand=False)
        commands_table.add_column("Command", style="cyan bold", no_wrap=True)
        commands_table.add_column("Description", style="white")
        commands_table.add_column("Flags", style="dim")
        
        for line in sections["commands"]:
            if line.strip():
                # Try to parse command, description, and flags
                match = re.match(r'^\s*(\S+)\s+(.*?)(?:\s*\(([^)]*)\)|$)', line)
                if match:
                    cmd = match.group(1)
                    desc = match.group(2).strip()
                    flags = match.group(3) or ""
                    prefix = f"nearai {display_name.lower()} " if not cmd.startswith("nearai ") else ""
                    commands_table.add_row(f"{prefix}{cmd}", desc, flags)
        
        console.print(commands_table)
        
        # Check if there are any required parameters (marked with *)
        has_required = False
        for line in sections["commands"]:
            if '*' in line:
                has_required = True
                break
        
        if has_required:
            console.print("\n* Required parameter\n")
    
    # Process Options section
    if "options" in sections:
        console.print("[bold green]Options:[/bold green]\n")
        
        options_table = Table(box=None, show_header=False, padding=(0, 2), expand=False)
        options_table.add_column(style="yellow")
        options_table.add_column(style="white")
        
        current_option = None
        current_desc = []
        
        for line in sections["options"]:
            if line.strip():
                # Check if this line defines a new option
                option_match = re.match(r'^\s*(\S+)\s+(.*?)$', line)
                if option_match:
                    if current_option:
                        options_table.add_row(current_option, " ".join(current_desc))
                    current_option = option_match.group(1)
                    current_desc = [option_match.group(2).strip()]
                else:
                    # This is a continuation of the previous option's description
                    if current_option:
                        current_desc.append(line.strip())
        
        # Add the last option
        if current_option:
            options_table.add_row(current_option, " ".join(current_desc))
        
        console.print(options_table)
        console.print()
    
    # Process Examples section
    if "examples" in sections:
        console.print("[bold green]Examples:[/bold green]\n")
        for line in sections["examples"]:
            if line.strip():
                if line.startswith("#"):
                    console.print(f"[dim]{line}[/dim]")
                else:
                    console.print(f"[cyan]{line}[/cyan]")
            else:
                console.print("")
        console.print()
    
    # Process Documentation section 
    if "documentation" in sections:
        doc_content = " ".join(sections["documentation"])
        console.print(f"For more information, see: [bold blue]{doc_content}[/bold blue]\n")


def format_command_help(obj, method_name: str) -> None:
    """Format a command's docstring as a help message and display it with rich formatting.
    
    Args:
        obj: The object containing the method
        method_name: The name of the method whose docstring should be formatted as help
    """
    console = Console()
    
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
    
    console.print(f"\n[bold cyan]NEAR AI {title}[/bold cyan]\n")
    
    # Extract sections
    sections = {}
    current_section = "description"  # Default section
    sections[current_section] = []
    
    lines = docstring.split("\n")
    for line in lines:
        # Check if this line could be a section header
        if re.match(r'^[A-Za-z][A-Za-z\s]+:$', line):
            current_section = line[:-1].lower()  # Remove the colon
            sections[current_section] = []
        else:
            sections[current_section].append(line)
    
    # Process description
    description = "\n".join(sections.get("description", [])).strip()
    if description:
        console.print(
            Panel(
                description,
                title=f"description {title}",
                border_style="blue",
                expand=False,
            )
        )
    
    # Process Usage section if available
    if "usage" in sections:
        console.print("[bold green]Command Syntax:[/bold green]\n")
        for line in sections["usage"]:
            if line.strip():
                console.print(line)
        console.print("")
    
    # Process Parameter Details
    if "parameter details" in sections or "args" in sections:
        param_section = "parameter details" if "parameter details" in sections else "args"
        console.print("\n[bold green]Parameter Details:[/bold green]\n")
        
        param_table = Table(box=None, show_header=False, padding=(0, 2), expand=False)
        param_table.add_column(style="yellow")
        param_table.add_column(style="white")
        
        current_param = None
        current_desc = []
        
        for line in sections[param_section]:
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
    
    # Process Options or Flag Details
    flag_section = None
    if "options" in sections:
        flag_section = "options"
    elif "flag details" in sections:
        flag_section = "flag details"
    
    if flag_section:
        console.print("\n[bold green]Flag Details:[/bold green]\n")
        
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
    
    # Process Examples
    if "examples" in sections:
        console.print("\n[bold green]Examples:[/bold green]\n")
        for line in sections["examples"]:
            if line.strip():
                if line.startswith("#"):
                    console.print(f"[dim]{line}[/dim]")
                else:
                    console.print(f"[cyan]{line}[/cyan]")
            else:
                console.print("")
    
    # Process Returns if available
    if "returns" in sections:
        console.print("\n[bold green]Returns:[/bold green]\n")
        returns_text = "\n".join(sections["returns"]).strip()
        console.print(returns_text)
        console.print("")
    
    # Process Documentation or other footer sections
    for section_name, section_content in sections.items():
        if section_name not in ["description", "usage", "parameter details", "args", "options", 
                               "flag details", "examples", "returns"] and section_content:
            # Format the section header with proper capitalization
            header = section_name.title()
            content = "\n".join(section_content).strip()
            if "documentation" in section_name.lower():
                console.print(f"\n[bold blue]{content}[/bold blue]\n")
            else:
                console.print(f"\n[bold green]{header}:[/bold green]\n")
                console.print(content)
                console.print("")


def format_subcommand_help(obj, method_name: str) -> None:
    """Format a subcommand's docstring as a help message and display it with rich formatting.
    
    Args:
        obj: The object containing the method
        method_name: The name of the method whose docstring should be formatted as help
    """
    # For now, subcommand help uses the same processing as command help
    format_command_help(obj, method_name)


def format_help(obj, method_name: str) -> None:
    """Format a method's docstring as a help message and display it with rich formatting.
    
    Args:
        obj: The object containing the method
        method_name: The name of the method whose docstring should be formatted as help,
                     or "__class__" to format the class's docstring
    """
    # Special case for CLI main menu
    if method_name == "__class__" and obj.__class__.__name__ == "CLI":
        format_main_menu_help(obj)
    elif method_name == "__class__":
        format_class_help(obj)
    else:
        format_command_help(obj, method_name)


def handle_class_help(cli):
    """Display help for the CLI class itself.
    
    Args:
        cli: CLI instance
        
    Returns:
        True indicating help was displayed
    """
    format_help(cli, "__class__")
    return True


def handle_command_help(cli, command):
    """Display help for a specific command.
    
    Args:
        cli: CLI instance
        command: Command name
        
    Returns:
        True if help was displayed, False otherwise
    """
    if hasattr(cli, command):
        format_class_help(getattr(cli, command))
        return True
    return False


def handle_subcommand_help(cli, command, subcommand):
    """Display help for a specific subcommand.
    
    Args:
        cli: CLI instance
        command: Command name
        subcommand: Subcommand name
        
    Returns:
        True if help was displayed, False otherwise
    """
    if hasattr(cli, command):
        cmd_obj = getattr(cli, command)
        if hasattr(cmd_obj, subcommand):
            format_subcommand_help(cmd_obj, subcommand)
            return True
    return False


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
        return handle_subcommand_help(cli, "registry", "upload")
    
    # No arguments - show main help
    if len(args) == 1:
        return handle_class_help(cli)
    
    # Help with no specific command
    if len(args) == 2 and args[1] == "--help":
        return handle_class_help(cli)
    
    # Help for a specific command
    if len(args) == 3 and args[2] == "--help":
        return handle_command_help(cli, args[1])
    
    # Help for a specific subcommand
    if len(args) == 4 and args[3] == "--help":
        return handle_subcommand_help(cli, args[1], args[2])
    
    return False
