"""Agent-browser binary management commands for the Aria CLI.

This module provides commands to download and manage agent-browser binaries
from GitHub releases. Agent-browser is a Rust CLI for headless browser
automation designed for AI agents.

Commands:
    download: Download agent-browser binary from GitHub releases
    status: Check installed agent-browser version and status

Example:
    ```bash
    # Download latest agent-browser release
    aria agentbrowser download

    # Check installation status
    aria agentbrowser status
    ```
"""

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from aria.config.api import AgentBrowser
from aria.scripts.agentbrowser import download_agent_browser

app = typer.Typer(
    name="agentbrowser",
    help="Agent-browser binary management commands.",
)

console = Console()
error_console = Console(stderr=True, style="bold red")


@app.command("download")
def download_command(
    bin_dir: Annotated[
        Path, typer.Option(help="Directory to install the binary to")
    ] = AgentBrowser.get_bin_path(),
    version: Annotated[
        Optional[str],
        typer.Option(help="Specific version tag to install (e.g., v0.1.0)"),
    ] = None,
):
    """Download agent-browser binary from GitHub releases.

    Downloads the appropriate agent-browser binary for your platform from
    the official GitHub releases. Also runs `agent-browser install` to
    download Chromium.

    Note: On Linux, system dependencies may need to be installed manually
    if Chromium fails to start. See error message for installation commands.

    Args:
        bin_dir: Target directory for the binary (default from config)
        version: Specific release tag to download (optional)

    Example:
        ```bash
        # Download latest to default location
        aria agentbrowser download

        # Download specific version
        aria agentbrowser download --version v0.1.0

        # Download to custom directory
        aria agentbrowser download --bin-dir /path/to/binaries
        ```
    """
    try:
        binary_path = download_agent_browser(bin_dir=Path(bin_dir), version=version)
        console.print(
            f"[green]✓[/green] Agent-browser binary installed at {binary_path}"
        )
    except Exception as e:
        error_console.print(f"[red]✗[/red] Installation failed: {e}")
        raise typer.Exit(1)


@app.command("status")
def check_status():
    """Check installed agent-browser version and status.

    Displays information about the agent-browser installation including:
    - Installation directory
    - Binary path and existence
    - Whether browser tools are available

    Example:
        ```bash
        aria agentbrowser status
        ```
    """
    binary_path = AgentBrowser.get_binary_path()
    bin_dir = AgentBrowser.get_bin_path()

    console.print("[bold]Agent-browser Status[/bold]\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Property", style="cyan", width=20)
    table.add_column("Value", style="green")

    table.add_row("Binary Directory", str(bin_dir))
    table.add_row("Configured Version", AgentBrowser.version)

    if binary_path:
        table.add_row("Binary Path", str(binary_path))
        table.add_row("Status", "[green]✓ Installed[/green]")
        table.add_row("Browser Tools", "[green]Available[/green]")
    else:
        table.add_row("Status", "[yellow]✗ Not installed[/yellow]")
        table.add_row("Browser Tools", "[yellow]Disabled[/yellow]")
        table.add_row("Install Command", "aria agentbrowser download")

    console.print(table)
