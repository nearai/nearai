import importlib.metadata
import inspect
import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from rich.box import ROUNDED
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from nearai.banners import NEAR_AI_BANNER

if TYPE_CHECKING:
    from nearai.cli import CLI


def get_docstring_info(
    obj, method_name: str = "__class__"
) -> Tuple[Optional[str], Optional[str], bool, Optional[Dict[str, List[str]]]]:
    """Get the docstring, command title, and parsed sections for a class or method.

    Args:
    ----
        obj : Any
            The object containing the docstring (class or method)
        method_name : str
            The name of the method to format, or "__class__" to format the class's docstring

    Returns:
    -------
        Tuple of (docstring, command_title, is_class, sections)

    """
    console = Console()

    # Extract basic metadata and docstring
    is_class, docstring, display_name = _extract_basic_metadata(obj, method_name, console)
    if docstring is None:
        return None, None, False, None

    # Create command title based on whether it's a class or method
    if is_class:
        cmd_title = f"NEAR AI {display_name} Commands"
    else:
        cmd_title = f"[bold white]nearai {display_name.lower()} {method_name} [/bold white]"

    # Parse docstring into sections
    sections = _parse_docstring_sections(docstring)

    return docstring, cmd_title, is_class, sections


def _extract_basic_metadata(obj: Any, method_name: str, console: Console) -> Tuple[bool, Optional[str], str]:
    """Extract basic metadata from the object or method.

    Args:
    ----
        obj: The object containing the docstring
        method_name: Name of the method or "__class__" for class docstring
        console: Console for error printing

    Returns:
    -------
        Tuple of (is_class, docstring, display_name)

    """
    if method_name == "__class__":
        docstring = inspect.getdoc(obj)
        class_name = obj.__class__.__name__
        display_name = class_name.replace("Cli", "").replace("CLI", "")
        is_class = True
    else:
        method = getattr(obj, method_name, None)
        if not method or not method.__doc__:
            console.print(f"[bold red]No documentation available for {method_name}[/bold red]")
            return False, None, ""
        docstring = inspect.getdoc(method)
        class_name = obj.__class__.__name__
        display_name = class_name.replace("Cli", "").replace("CLI", "")
        is_class = False

    if not docstring:
        console.print(f"[bold red]No documentation available for {obj.__class__.__name__}[/bold red]")
        return is_class, None, display_name

    return is_class, docstring, display_name


def _parse_docstring_sections(docstring: str) -> Dict[str, List[str]]:
    """Parse a docstring into sections.

    Args:
    ----
        docstring: The docstring to parse

    Returns:
    -------
        Dictionary mapping section names to content lines

    """
    sections = {}
    lines = docstring.split("\n")

    # First, extract the description section (special handling)
    sections["description"] = _extract_description_section(lines)

    # Then extract all other sections
    section_pattern = r"^([A-Za-z][A-Za-z\s]+):$"
    current_section = None
    section_content: List[str] = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Skip empty lines
        if not line:
            i += 1
            continue

        # Check if this is a section header
        section_match = re.match(section_pattern, line)
        if section_match:
            # Save previous section content if we had one
            if current_section and section_content:
                sections[current_section.lower()] = section_content

            # Start new section
            current_section = section_match.group(1)
            section_content = []

            # Skip decoration lines (like "-----")
            if i + 1 < len(lines) and re.match(r"^-+$", lines[i + 1].strip()):
                i += 1

        # If not a section header and we're in a section, add the line
        elif current_section:
            # For Commands section, preserve original line with indentation
            if current_section.lower() == "commands":
                section_content.append(lines[i])  # Keep original indentation
            else:
                # For other sections, just add the content if not empty
                if line:
                    section_content.append(line)

        i += 1

    # Save the last section
    if current_section and section_content:
        sections[current_section.lower()] = section_content

    return sections


def _extract_description_section(lines: List[str]) -> List[str]:
    """Extract the description section from docstring lines.

    The description is the first part of the docstring until the first
    section header or double blank line.

    Args:
    ----
        lines: Lines of the docstring

    Returns:
    -------
        List of description lines

    """
    description: List[str] = []
    if not lines:
        return description

    # First line is always part of the description
    description.append(lines[0].strip())

    # Look for continuation of description
    i = 1
    while i < len(lines):
        line = lines[i].strip()

        # If we find an empty line
        if not line:
            # Skip the blank line
            i += 1
            # Continue until we hit a second blank line or section header
            while i < len(lines):
                line = lines[i].strip()
                if not line:  # Found second blank line
                    break
                if re.match(r"^([A-Za-z][A-Za-z\s]+):$", line):  # Found section header
                    break
                description.append(line)
                i += 1
            break
        i += 1

    return description


def format_help(obj, method_name: str = "__class__") -> None:
    """Format a class or method's docstring as a help message and display it with rich formatting.

    Args:
    ----
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
    console.print(f"\n[bold green]{cmd_title}[/bold green]\n")

    # Process each type of section
    _display_description_section(console, sections)

    if is_class and "commands" in sections:
        _display_commands_section(console, sections)

    # Process parameter sections
    param_pattern = r"^\s*(\S+)\s*\((\S+)\)\s*:\s*$"
    if "args" in sections:
        _display_param_section(console, sections, "args", "Args", param_pattern, obj, method_name)

    if "options" in sections:
        _display_param_section(console, sections, "options", "Options", param_pattern, obj, method_name)

    if "examples" in sections:
        _display_examples_section(console, sections)

    if "documentation" in sections:
        _display_documentation_section(console, sections)


def _display_description_section(console: Console, sections: Dict[str, List[str]]) -> None:
    """Display the description section in a panel.

    Args:
    ----
        console: Rich console for display
        sections: Parsed sections dictionary

    """
    if "description" in sections:
        description = " ".join(sections["description"])
        if description:
            console.print(Panel(description, title="Info", expand=False, border_style="blue", width=120))


def _display_commands_section(console: Console, sections: Dict[str, List[str]]) -> None:
    """Display the commands section in a table.

    Args:
    ----
        console: Rich console for display
        sections: Parsed sections dictionary

    """
    commands_table = Table(box=ROUNDED, expand=False, width=120, style="dim")
    commands_table.add_column("Command", style="cyan bold", no_wrap=True)
    commands_table.add_column("Description", style="white")
    commands_table.add_column("Options", style="dim")

    lines = sections["commands"]
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # Command format is "command : description"
        cmd_parts = line.split(" : ", 1)
        if len(cmd_parts) == 2:
            cmd, desc = cmd_parts[0].strip(), cmd_parts[1].strip()
            options_str, next_index = _parse_command_options(lines, i)
            i = next_index  # Update index based on options parsing
            commands_table.add_row(cmd, desc, options_str)
        i += 1

    console.print(commands_table)

    # Check if any commands have required parameters (marked with *)
    if any("*" in line for line in sections["commands"]):
        console.print("* Required parameter")


def _parse_command_options(lines: List[str], current_index: int) -> Tuple[str, int]:
    """Parse options for a command from the following lines.

    Args:
    ----
        lines: All command lines
        current_index: Current position in the lines

    Returns:
    -------
        Tuple of (options_string, next_index)

    """
    options = []
    j = current_index + 1
    in_options = False
    next_index = current_index

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

        next_index = j - 1  # Skip the processed option lines

    # Join and format options
    options_str = ""
    if options:
        # Remove parentheses and join with spaces
        options_str = " ".join(options)
        options_str = options_str.strip("() ")

    return options_str, next_index


def _display_param_section(
    console: Console,
    sections: Dict[str, List[str]],
    section_name: str,
    section_title: str,
    param_pattern: str,
    obj: Any = None,
    method_name: str = "__class__",
) -> None:
    """Display a parameter section (Args or Options) in a table.

    Args:
    ----
        console: Rich console for display
        sections: Parsed sections dictionary
        section_name: Name of the section in the sections dict
        section_title: Title to display for the section
        param_pattern: Regex pattern to match parameter definitions
        obj: The object containing the method to inspect
        method_name: The name of the method to inspect, or "__class__" for class docstring

    """
    section_lines = sections.get(section_name, [])
    if not section_lines:
        return

    # Create table for parameters
    table = Table(title=section_title, show_header=True, header_style="bold magenta")
    table.add_column("Parameter", style="yellow")
    table.add_column("Type", style="cyan", justify="center")
    table.add_column("Description", style="white")
    table.add_column("Default", style="green", justify="center")

    # Get the method object for default value lookup
    method = None
    if obj and method_name:
        if method_name != "__class__":
            method = getattr(obj, method_name, None)
        else:
            method = obj

    i = 0
    while i < len(section_lines):
        line = section_lines[i].rstrip()

        # Skip empty lines
        if not line:
            i += 1
            continue

        # Check if this is a parameter line
        match = re.match(param_pattern, line)
        if match:
            param_name = match.group(1)
            param_type = match.group(2)

            # Parse parameter description
            description, next_index = _parse_param_description(section_lines, i, param_pattern)
            i = next_index  # Update index based on description parsing

            # Get default value from function signature if available
            default_value = "-"
            if method:
                try:
                    sig = inspect.signature(method)
                    if param_name in sig.parameters:
                        param = sig.parameters[param_name]
                        if param.default != inspect.Parameter.empty:
                            default_value = str(param.default)
                except (ValueError, TypeError):
                    pass

            table.add_row(param_name, param_type, description, default_value)
        else:
            i += 1

    if table.row_count > 0:
        console.print(table)
        console.print()


def _parse_param_description(section_lines: List[str], current_index: int, param_pattern: str) -> Tuple[str, int]:
    """Parse the description lines for a parameter.

    Args:
    ----
        section_lines: Lines in the current section
        current_index: Current position in the lines
        param_pattern: Pattern to identify parameter definitions

    Returns:
    -------
        Tuple of (description_text, next_index)

    """
    description_lines = []
    i = current_index + 1  # Start from next line

    # Continue collecting description lines until we hit the next parameter or the end
    while i < len(section_lines):
        next_line = section_lines[i].rstrip()

        # Skip empty lines in description
        if not next_line:
            i += 1
            continue

        # If we encounter another parameter definition, stop collecting description
        if re.match(param_pattern, next_line):
            break

        # Add the line to the description, removing excess indentation
        description_lines.append(next_line.lstrip())
        i += 1

    description = " ".join(description_lines) if description_lines else ""
    return description, i


def _display_examples_section(console: Console, sections: Dict[str, List[str]]) -> None:
    """Display examples section in a panel.

    Args:
    ----
        console: Rich console for display
        sections: Parsed sections dictionary

    """
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


def _display_documentation_section(console: Console, sections: Dict[str, List[str]]) -> None:
    """Display documentation section.

    Args:
    ----
        console: Rich console for display
        sections: Parsed sections dictionary

    """
    doc_content = " ".join(sections["documentation"])
    console.print(f"For more information see: [bold blue]{doc_content}[/bold blue]\n")


def generate_main_cli_help(cli: "CLI") -> None:
    """Format the main CLI menu help display.

    Args:
    ----
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


def handle_help_request(args: Optional[List[str]] = None) -> bool:
    """Common handler for CLI help requests.

    Args:
    ----
        args (Optional[List[str]]) :
            Command line arguments (uses sys.argv if None)

    Returns:
    -------
        bool : True if help was displayed, False otherwise

    """
    if args is None:
        import sys

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
