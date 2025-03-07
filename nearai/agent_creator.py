import json
import platform
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.text import Text

from nearai.banners import NEAR_AI_BANNER
from nearai.registry import get_registry_folder, parse_location, registry
from nearai.shared.client_config import (
    DEFAULT_MODEL,
    DEFAULT_MODEL_MAX_TOKENS,
    DEFAULT_MODEL_TEMPERATURE,
    DEFAULT_PROVIDER,
)


def prompt_agent_details() -> Tuple[str, str, str, str]:
    """Prompt user for agent details and return them."""
    console = Console()

    # Get namespace from CONFIG, with null check
    from nearai.config import CONFIG

    if CONFIG.auth is None:
        raise ValueError("Not logged in. Please run 'nearai login' first.")
    namespace = CONFIG.auth.namespace

    # Welcome message
    console.print(NEAR_AI_BANNER)
    welcome_panel = Panel(
        Text.assemble(
            ("Let's create a new agent! 🦾 \n", "bold green"),
            ("We'll need some basic information to get started.", "dim"),
        ),
        title="Agent Creator",
        border_style="green",
    )
    console.print(welcome_panel)
    console.print("\n")

    # Name prompt with explanation
    name_info = Panel(
        Text.assemble(
            ("Choose a unique name for your agent using only:\n\n", ""),
            ("• letters\n", "dim"),
            ("• numbers\n", "dim"),
            ("• dots (.)\n", "dim"),
            ("• hyphens (-)\n", "dim"),
            ("• underscores (_)\n\n", "dim"),
            ("Examples: 'code-reviewer', 'data.analyzer', 'text_summarizer'", "green"),
        ),
        title="Agent Name Rules",
        border_style="blue",
    )
    console.print(name_info)

    while True:
        name = Prompt.ask("[bold blue]Enter agent name").strip()
        # Validate name format
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$", name):
            console.print(
                "[red]❌ Invalid name format. Please use only letters, numbers, dots, hyphens, or underscores."
            )
            continue
        if " " in name:
            console.print("[red]❌ Spaces are not allowed. Use dots, hyphens, or underscores instead.")
            continue
        break

    console.print("\n")

    # Description prompt
    description_info = Panel(
        "Describe what your agent will do in a few words...", title="Description Info", border_style="blue"
    )
    console.print(description_info)
    description = Prompt.ask("[bold blue]Enter description")

    console.print("\n")

    # Initial instructions prompt
    init_instructions_info = Panel(
        Text.assemble(
            ("Provide initial instructions for your AI agent...\n\n", ""),
            ("This will be used as the system message to guide the agent's behavior.\n", "dim"),
            ("You can edit these instructions later in the `agent.py` file.\n\n", "dim"),
            (
                "Example: You are a helpful humorous assistant. Use puns or jokes to make the user smile.",
                "green",
            ),
        ),
        title="Instructions",
        border_style="blue",
    )
    console.print(init_instructions_info)
    init_instructions = Prompt.ask("[bold blue]Enter instructions")

    # Confirmation
    console.print("\n")
    summary_panel = Panel(
        Text.assemble(
            ("Summary of your new agent:\n\n", "bold"),
            ("Namespace/Account:    ", "dim"),
            (f"{namespace}\n", "green"),
            ("Agent Name:           ", "dim"),
            (f"{name}\n", "green"),
            ("Description:          ", "dim"),
            (f"{description}\n", "green"),
            ("Instructions:         ", "dim"),
            (f"{init_instructions}", "green"),
        ),
        title="📋 Review",
        border_style="green",
    )
    console.print(summary_panel)
    console.print("\n")

    if not Confirm.ask("[bold]Would you like to proceed?", default=True):
        console.print("[red]❌ Agent creation cancelled")
        raise SystemExit(0)

    return namespace, name, description, init_instructions


def create_new_agent(namespace: str, name: Optional[str], description: Optional[str]) -> None:
    """Create a new agent from scratch with interactive options."""
    # If no name/description provided, use interactive prompts
    init_instructions = ""
    if name is None and description is None:
        _, name, description, init_instructions = prompt_agent_details()

    # Set the agent path
    registry_folder = get_registry_folder()
    if registry_folder is None:
        raise ValueError("Registry folder path cannot be None")

    # Narrow the type of namespace & name from Optional[str] to str
    namespace_str: str = namespace if namespace is not None else ""
    if namespace_str == "":
        raise ValueError("Namespace cannot be None or empty")

    name_str: str = name if name is not None else ""
    if name_str == "":
        raise ValueError("Name cannot be None or empty")

    agent_path = registry_folder / namespace_str / name_str / "0.0.1"
    agent_path.mkdir(parents=True, exist_ok=True)

    metadata: Dict[str, Any] = {
        "name": name_str,
        "version": "0.0.1",
        "description": description or "",
        "category": "agent",
        "tags": [],
        "details": {
            "agent": {
                "defaults": {
                    "model": DEFAULT_MODEL,
                    "model_provider": DEFAULT_PROVIDER,
                    "model_temperature": DEFAULT_MODEL_TEMPERATURE,
                    "model_max_tokens": DEFAULT_MODEL_MAX_TOKENS,
                }
            }
        },
        "show_entry": True,
    }

    metadata_path = agent_path / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    # Create a default agent.py with the provided initial instructions
    agent_py_content = f"""from nearai.agents.environment import Environment


def run(env: Environment):
    # Your agent code here
    prompt = {{"role": "system", "content": "{init_instructions}"}}
    result = env.completion([prompt] + env.list_messages())
    env.add_reply(result)
    env.request_user_input()

run(env)

"""
    agent_py_path = agent_path / "agent.py"
    with open(agent_py_path, "w") as f:
        f.write(agent_py_content)

    # Display success message and options
    display_success_and_options(agent_path)


def display_success_and_options(agent_path: Path) -> None:
    """Display success message and interactive options for next steps."""
    console = Console()
    success_title = Text(" 🎉 SUCCESS!", style="bold green")
    path_text = Text.assemble(("\n  • New AI Agent created at: ", "bold green"), (f"{agent_path}", "bold"))

    files_panel = Panel(
        Text.assemble(
            ("Edit agent code here:\n\n", "yellow"),
            (f"📄 - {agent_path}/agent.py\n", "bold blue"),
            (f"📄 - {agent_path}/metadata.json", "bold blue"),
        ),
        title="Agent Files",
        border_style="yellow",
    )

    commands_panel = Panel(
        Text.assemble(
            ("Run this agent locally:\n", "light_green"),
            (f"  nearai agent interactive {agent_path} --local\n\n", "bold"),
            ("Upload this agent to NEAR AI's public registry:\n", "light_green"),
            (f"  nearai registry upload {agent_path}\n\n", "bold"),
            ("Run ANY agent from your local registry:\n", "light_green"),
            ("  nearai agent interactive --local", "bold"),
        ),
        title="Useful Commands",
        border_style="green",
    )

    console.print("\n")
    console.print(success_title)
    console.print(path_text)
    console.print("\n")
    console.print(files_panel)
    console.print("\n")
    console.print(commands_panel)
    console.print("\n")

    # Create next steps options with proper markup
    options = ["Upload agent to NEAR AI registry 🚀", "Run agent 💬", "Open agent code in editor 🧑‍💻", "Exit 👋"]

    # Create the panel with direct markup
    next_steps_panel = Panel(
        f"""[bold blue]What would you like to do next?[/bold blue]

[bold blue]1.[/bold blue] {options[0]}
[bold blue]2.[/bold blue] {options[1]}
[bold blue]3.[/bold blue] {options[2]}
[bold blue]4.[/bold blue] {options[3]}""",
        title="[bold blue]Next Steps[/bold blue]",
        border_style="blue",
    )
    console.print(next_steps_panel)
    console.print("\n")

    # Main options loop
    while True:
        try:
            choice = int(Prompt.ask("[bold]Choose an option", default="4")) - 1
            if not (0 <= choice < len(options)):
                console.print("[red]Invalid choice. Please try again.")
                continue
        except ValueError:
            console.print("[red]Please enter a valid number.")
            continue

        # Exit option
        if choice == 3:  # Exit
            break

        # Handle user choice
        if choice == 0:  # Upload agent
            console.print("\n[green]Uploading agent to registry...[/green]")
            try:
                registry.upload(agent_path, show_progress=True)
                console.print("[green bold]✓ Agent uploaded successfully![/green bold]\n")

                # Extract namespace and name from agent_path
                namespace = agent_path.parts[-3]
                agent_name = agent_path.parts[-2]

                # Generate and display link to the agent
                agent_url = f"https://app.near.ai/agents/{namespace}/{agent_name}/latest"
                console.print("[yellow]View your agent in the NEAR AI Developer Hub:[/yellow]")
                console.print(f"[link={agent_url}]{agent_url}[/link]\n")

                break  # Exit after successful upload
            except Exception as e:
                console.print(f"[red bold]✗ Error uploading agent: {str(e)}[/red bold]\n")

        elif choice == 1:  # Run agent
            console.print("\n[green]Running agent...[/green]")
            try:
                from nearai.cli import AgentCli

                agent_cli = AgentCli()
                agent_cli.interactive(str(agent_path), local=True)
                break  # Exit after running agent
            except Exception as e:
                console.print(f"[red bold]✗ Error running agent: {str(e)}[/red bold]\n")

        elif choice == 2:  # Code agent
            console.print("\n[green]Attempting to open agent in a code editor...[/green]")
            try:
                # Check for common editors
                editors = [
                    ("Visual Studio Code", "code"),
                    ("PyCharm", "charm"),
                    ("Atom", "atom"),
                    ("IntelliJ IDEA", "idea"),
                ]

                # Try each editor
                editor_found = False
                for editor_name, command in editors:
                    cmd_path = shutil.which(command)
                    if cmd_path:
                        subprocess.run([command, str(agent_path)], check=False)
                        console.print(f"[green bold]✓ Agent opened in {editor_name}![/green bold]\n")
                        editor_found = True
                        break

                # If no code editor found, try opening in file explorer
                if not editor_found:
                    console.print("[yellow]Could not find any common code editors. Trying file explorer...[/yellow]")
                    system = platform.system()
                    explorer_opened = False

                    if system == "Windows":
                        subprocess.run(["explorer", str(agent_path)], check=False)
                        explorer_opened = True
                    elif system == "Darwin":  # macOS
                        subprocess.run(["open", str(agent_path)], check=False)
                        explorer_opened = True
                    elif system == "Linux":
                        subprocess.run(["xdg-open", str(agent_path)], check=False)
                        explorer_opened = True

                    if explorer_opened:
                        console.print("[green bold]✓ Agent directory opened in file explorer![/green bold]\n")
                    else:
                        console.print("[yellow]Could not open directory automatically.[/yellow]")
                        console.print("[yellow]Your agent is located at:[/yellow]")
                        console.print(f"[bold cyan]{agent_path}[/bold cyan]\n")

                break  # Exit after attempt
            except Exception as e:
                console.print(f"[red bold]✗ Error opening agent: {str(e)}[/red bold]")
                console.print(f"[yellow]Your agent is located at: {agent_path}[/yellow]\n")


def fork_agent(fork: str, namespace: str, new_name: Optional[str]) -> None:
    """Fork an existing agent."""
    import shutil

    # Parse the fork parameter
    try:
        entry_location = parse_location(fork)
        fork_namespace = entry_location.namespace
        fork_name = entry_location.name
        fork_version = entry_location.version
    except ValueError:
        print("Invalid fork parameter format. Expected format: <namespace>/<agent-name>/<version>")
        return

    # Download the agent from the registry
    agent_location = f"{fork_namespace}/{fork_name}/{fork_version}"
    print(f"Downloading agent '{agent_location}'...")
    registry.download(agent_location, force=False, show_progress=True)
    source_path = get_registry_folder() / fork_namespace / fork_name / fork_version

    # Prompt for the new agent name if not provided
    if not new_name:
        new_name = input("Enter the new agent name: ").strip()
        if not new_name:
            print("Agent name cannot be empty.")
            return

        # confirm pattern is ok
        identifier_pattern = re.compile(r"^[a-zA-Z0-9_\-.]+$")
        if identifier_pattern.match(new_name) is None:
            print("Invalid Name, please choose something different")
            return

    # Set the destination path
    dest_path = get_registry_folder() / namespace / new_name / "0.0.1"

    # Copy the agent files
    shutil.copytree(source_path, dest_path)

    # Update metadata.json
    metadata_path = dest_path / "metadata.json"
    with open(metadata_path, "r") as file:
        metadata = json.load(file)

    metadata["name"] = new_name
    metadata["version"] = "0.0.1"

    with open(metadata_path, "w") as file:
        json.dump(metadata, file, indent=2)

    print(f"\nForked agent '{agent_location}' to '{dest_path}'")
    print(f"Agent '{new_name}' created at '{dest_path}' with updated metadata.")

    # Display success and interactive options
    display_success_and_options(dest_path)
