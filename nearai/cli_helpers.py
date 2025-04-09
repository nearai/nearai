import importlib.metadata
import inspect
import json
import os
import re
import select
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rich.box import ROUNDED
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from nearai.banners import NEAR_AI_BANNER
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


def generate_main_cli_help(cli) -> None:
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
        expand=False,
        show_header=True,
        header_style="bold cyan",
        border_style="green",
    )
    table.add_column("Command", style="cyan")
    table.add_column("Description", style="white")
    # Parse docstring into sections
    sections = {}
    current_section = None
    current_lines: List[str] = []
    # Process the docstring line by line
    for line in docstring.strip().split("\n"):
        line = line.strip()
        # Skip empty lines
        if not line:
            continue
        # Check if this is a section header
        if line.endswith(":"):
            # Save previous section if we had one
            if current_section:
                sections[current_section.lower()] = current_lines
            # Start a new section
            current_section = line.rstrip(":")
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
            parts = re.split(r"\s{2,}", cmd_line, maxsplit=1)
            if len(parts) == 2:
                cmd, desc = parts
                # Use the command as is without adding prefix
                cmd = cmd.strip()
                table.add_row(cmd, desc.strip())
            else:
                # For single-word commands, use as is
                cmd = cmd_line.strip()
                if not cmd.startswith("["):
                    table.add_row(cmd, "")
    console.print(table)
    console.print(
        "[bold white] Run [bold green]`nearai <command> --help`[/bold green] for more info about a command.\n[/bold white]"  # noqa: E501
    )
    console.print(
        "[white] - Docs: [bold blue]https://docs.near.ai/[/bold blue][/white]\n"
        "[white] - Dev Support: [bold blue]https://t.me/nearaialpha[/bold blue][/white]\n"
    )


def get_docstring_info(
    obj, method_name: str = "__class__"
) -> Tuple[Optional[str], Optional[str], bool, Optional[Dict[str, List[str]]]]:
    """Get the docstring, command title, and parsed sections for a class or method.

    Args:
        obj : Any
            The object containing the docstring (class or method)
        method_name : str
            The name of the method to format, or "__class__" to format the class's docstring

    Returns:
        Tuple of (docstring, command_title, is_class, sections)

    """
    console = Console()

    if method_name == "__class__":
        docstring = inspect.getdoc(obj)
        class_name = obj.__class__.__name__
        display_name = class_name.replace("Cli", "").replace("CLI", "")
        is_class = True
        cmd_title = f"NEAR AI {display_name} Commands"
    else:
        method = getattr(obj, method_name, None)
        if not method or not method.__doc__:
            console.print(f"[bold red]No documentation available for {method_name}[/bold red]")
            return None, None, False, None
        docstring = inspect.getdoc(method)
        class_name = obj.__class__.__name__
        display_name = class_name.replace("Cli", "").replace("CLI", "")
        is_class = False
        cmd_title = f"[bold white]nearai {display_name.lower()} {method_name} [/bold white]"

    if not docstring:
        console.print(f"[bold red]No documentation available for {obj.__class__.__name__}[/bold red]")
        return None, None, False, None

    # Parse docstring into sections
    sections = {}
    lines = docstring.split("\n")

    # First line is always the main description
    description = [lines[0].strip()] if lines else []

    # Process the rest of the docstring to find sections
    current_section = None
    section_content: List[str] = []

    for i in range(1, len(lines)):
        line = lines[i]
        line_stripped = line.strip()

        # Check if this is a section header (ends with colon)
        if line_stripped and re.match(r"^([A-Za-z][A-Za-z\s]+):$", line_stripped):
            # Save previous section if it exists
            if current_section:
                sections[current_section.lower()] = section_content

            # Start new section
            current_section = line_stripped.rstrip(":")
            section_content = []

            # Skip decoration lines (like "-----")
            if i + 1 < len(lines) and re.match(r"^-+$", lines[i + 1].strip()):
                i += 1

        # If not a section header and we're in a section, add the line
        elif current_section:
            # For Commands section, preserve original line with indentation
            if current_section.lower() == "commands":
                section_content.append(line)  # Keep original indentation
            else:
                # For other sections, just add the content
                if line_stripped:  # Skip empty lines except in Commands section
                    section_content.append(line_stripped)

        # If not a section header and not in a section yet, add to description
        elif line_stripped:
            description.append(line_stripped)

    # Save the last section
    if current_section:
        sections[current_section.lower()] = section_content

    # Store the description section
    if description:
        sections["description"] = description

    return docstring, cmd_title, is_class, sections


def format_help(obj, method_name: str = "__class__") -> None:
    """Format a class or method's docstring as a help message and display it with rich formatting.

    Args:
        obj : Any
            The object containing the docstring (class or method)
        method_name : str
            The name of the method to format, or "__class__" to format the class's docstring

    """
    console = Console()
    # Special case for CLI main menu
    if method_name == "__class__" and obj.__class__.__name__ == "CLI":
        generate_main_cli_help(obj)
        return
    # Get docstring info from class or method
    docstring, cmd_title, is_class, sections = get_docstring_info(obj, method_name)
    if docstring is None or sections is None:
        return

    # Display command group / name
    console.print(f"\n[bold green]{cmd_title}[/bold green\n\n]")

    # Process Description section
    if "description" in sections:
        description = " ".join(sections["description"])
        if description:
            console.print(Panel(description, title="Info", expand=False, border_style="blue", width=120))

    # Process Commands section for classes
    if is_class and "commands" in sections:
        commands_table = Table(box=ROUNDED, expand=False, width=120, style="dim")
        commands_table.add_column("Command", style="cyan bold", no_wrap=True)
        commands_table.add_column("Description", style="white")
        commands_table.add_column("Options", style="dim")

        i = 0
        lines = sections["commands"]

        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue

            # Command format is "command : description"
            cmd_parts = line.split(" : ", 1)
            if len(cmd_parts) == 2:
                cmd = cmd_parts[0].strip()
                desc = cmd_parts[1].strip()

                # Look for options on the next line(s)
                options = []
                j = i + 1
                in_options = False

                # Check if next line starts with options
                if j < len(lines) and lines[j].strip().startswith("("):
                    in_options = True
                    # Process option lines until we find the closing parenthesis
                    while j < len(lines) and in_options:
                        opt_line = lines[j].strip()
                        options.append(opt_line)

                        if opt_line.endswith(")"):
                            in_options = False
                        j += 1

                # Join and format options
                options_str = ""
                if options:
                    # Remove parentheses and join with spaces
                    options_str = " ".join(options)
                    options_str = options_str.strip("() ")
                    i = j - 1  # Skip the processed option lines

                commands_table.add_row(cmd, desc, options_str)

            i += 1

        console.print(commands_table)
        # Check if any commands have required parameters (marked with *)
        if any("*" in line for line in sections["commands"]):
            console.print("* Required parameter")

    # Helper function to process parameter sections (Args and Options)
    def process_param_section(section_name, section_title, param_regex, name_idx=1, type_idx=2):
        if section_name not in sections:
            return

        # Create table for parameters
        table = Table(box=ROUNDED, expand=False, style="dim", width=120)
        table.add_column("Parameter", style="yellow bold")
        table.add_column("Type", style="cyan")
        table.add_column("Description", style="white")

        # Direct regex to extract parameters from docstring
        method = getattr(obj, method_name, None)
        if method and method.__doc__:
            doc_lines = inspect.getdoc(method).split("\n")

            # Find the section
            section_start = -1
            for i, line in enumerate(doc_lines):
                # Make section matching case-insensitive
                line_lower = line.strip().lower()
                if line_lower == f"{section_title.lower()}:" or line_lower == f"{section_name.lower()}:":
                    section_start = i + 1
                    break

            if section_start >= 0:
                i = section_start
                while i < len(doc_lines):
                    line = doc_lines[i].strip()

                    # End of section (another section starts)
                    if line.endswith(":") and not line.startswith(" "):
                        break

                    # Parameter line (indented, contains parameter name)
                    param_match = re.match(param_regex, line)
                    if param_match:
                        param_name = param_match.group(name_idx)
                        # Get type if available and valid
                        has_valid_type_index = type_idx < len(param_match.groups()) + 1
                        type_value = param_match.group(type_idx) if has_valid_type_index else None
                        param_type = type_value if type_value else ""
                        param_desc = []

                        # Look for description (should be on the next line and indented)
                        j = i + 1
                        while j < len(doc_lines):
                            next_line = doc_lines[j].strip()

                            # If empty line or end of section, break
                            if not next_line or (next_line.endswith(":") and not next_line.startswith(" ")):
                                break

                            # If this is another parameter, break
                            if re.match(param_regex, next_line):
                                break

                            # Add description line
                            param_desc.append(next_line)
                            j += 1

                        # Add parameter to table
                        desc_text = " ".join(param_desc).strip()
                        table.add_row(param_name, param_type, desc_text)

                        # Move to next parameter
                        i = j
                    else:
                        i += 1
            else:
                # Use the pre-parsed sections if we can't find the section in the docstring
                for param_line in sections[section_name]:
                    param_match = re.match(param_regex, param_line)
                    if param_match:
                        param_name = param_match.group(name_idx)
                        # Get type if available and valid
                        has_valid_type_index = type_idx < len(param_match.groups()) + 1
                        type_value = param_match.group(type_idx) if has_valid_type_index else None
                        param_type = type_value if type_value else ""
                        desc_text = ""

                        # Search for description in the next lines
                        param_index = sections[section_name].index(param_line)
                        if param_index + 1 < len(sections[section_name]):
                            next_line = sections[section_name][param_index + 1]
                            if not re.match(param_regex, next_line):
                                desc_text = next_line

                        table.add_row(param_name, param_type, desc_text)

        # Display table if parameters were found
        if table.row_count > 0:
            console.print(table)
        console.print()

    # Process Args section for method parameters
    if not is_class and "args" in sections:
        process_param_section("args", "OPTIONS", r"^\s*(\S+)\s*:\s*(\S+)\s*$")

    # Process Options section
    if "options" in sections:
        process_param_section("options", "Options", r"^\s*(-{0,2}\S+)\s*(?::\s*(\S+))?\s*$")

    # Process Examples section
    if "examples" in sections:
        examples_text = []
        current_example: List[str] = []

        for line in sections["examples"]:
            line_stripped = line.strip()

            if not line_stripped:
                # Empty line separates examples
                if current_example:
                    examples_text.append("\n".join(current_example))
                    examples_text.append("")  # Add spacing
                    current_example = []
                continue

            if line_stripped.startswith("#"):
                # This is a comment/description for an example
                current_example.append(f"[dim]{line_stripped}[/dim]")
            else:
                # This is a command
                current_example.append(f"[cyan]{line_stripped}[/cyan]")

        # Add the last example
        if current_example:
            examples_text.append("\n".join(current_example))

        # Display examples in a panel
        if examples_text:
            console.print(
                Panel("\n".join(examples_text), title="Examples", border_style="cyan", expand=False, padding=(1, 2))
            )
            console.print()

    # Process Documentation section
    if "documentation" in sections:
        doc_content = " ".join(sections["documentation"])
        console.print(f"For more information see: [bold blue]{doc_content}[/bold blue]\n")


def handle_help_request(args: Optional[List[str]] = None) -> bool:
    """Common handler for CLI help requests.

    Args:
        args (Optional[List[str]]) :
            Command line arguments (uses sys.argv if None)

    Returns:
        bool : True if help was displayed, False otherwise

    """
    if args is None:
        args = sys.argv
    # Create CLI instance
    from nearai.cli import CLI

    cli = CLI()
    # Special case for agent upload, which is an alias for registry upload
    if len(args) == 4 and args[1] == "agent" and args[2] == "upload" and args[3] == "--help":
        # Display help for registry upload subcommand
        if hasattr(cli, "registry"):
            registry_obj = cli.registry
            if hasattr(registry_obj, "upload"):
                format_help(registry_obj, "upload")
                return True
        return False
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
            format_help(getattr(cli, command))
            return True
        return False
    # Help for a specific subcommand
    if len(args) == 4 and args[3] == "--help":
        command = args[1]
        subcommand = args[2]
        if hasattr(cli, command):
            cmd_obj = getattr(cli, command)
            if hasattr(cmd_obj, subcommand):
                format_help(cmd_obj, subcommand)
                return True
        return False
    return False
