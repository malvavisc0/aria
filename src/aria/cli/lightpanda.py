"""Lightpanda browser binary management commands for the Aria CLI.

This module provides commands to download and manage Lightpanda browser
binaries from GitHub releases. Lightpanda is a lightweight headless
browser with CDP support for Playwright automation.

Commands:
    download: Download Lightpanda binary from GitHub releases
    status: Check installed Lightpanda version and status

Example:
    ```bash
    # Download latest Lightpanda nightly release
    aria lightpanda download

    # Check installation status
    aria lightpanda status
    ```
"""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from aria.config.api import Lightpanda
from aria.scripts.lightpanda import download_lightpanda

app = typer.Typer(
    name="lightpanda",
    help="Lightpanda browser binary management commands.",
)

console = Console()
error_console = Console(stderr=True, style="bold red")


@app.command("download")
def download_command(
    bin_dir: Annotated[
        Path, typer.Option(help="Directory to install the binary to")
    ] = Lightpanda.get_bin_path(),
    version: Annotated[
        str | None,
        typer.Option(help="Specific version tag to install (default: nightly)"),
    ] = None,
):
    """Download Lightpanda binary from GitHub releases.

    Downloads the appropriate Lightpanda binary for your platform from
    the official GitHub releases. Lightpanda is a single binary with
    no additional dependencies (no Chromium download needed).

    Args:
        bin_dir: Target directory for the binary (default from config)
        version: Specific release tag to download (default: nightly)

    Example:
        ```bash
        # Download nightly to default location
        aria lightpanda download

        # Download to custom directory
        aria lightpanda download --bin-dir /path/to/binaries
        ```
    """
    try:
        binary_path = download_lightpanda(bin_dir=Path(bin_dir), version=version)
        console.print(f"[green]✓[/green] Lightpanda binary installed at {binary_path}")
    except Exception as e:
        error_console.print(f"[red]✗[/red] Installation failed: {e}")
        raise typer.Exit(1)


@app.command("status")
def check_status():
    """Check installed Lightpanda version and status.

    Displays information about the Lightpanda installation including:
    - Installation directory
    - Binary path and existence
    - Whether browser tools are available

    Example:
        ```bash
        aria lightpanda status
        ```
    """
    binary_path = Lightpanda.get_binary_path()
    bin_dir = Lightpanda.get_bin_path()

    console.print("[bold]Lightpanda Browser Status[/bold]\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Property", style="cyan", width=20)
    table.add_column("Value", style="green")

    table.add_row("Binary Directory", str(bin_dir))
    table.add_row("Configured Version", Lightpanda.version)
    table.add_row("CDP Port", str(Lightpanda.port))

    if binary_path:
        table.add_row("Binary Path", str(binary_path))
        table.add_row("Status", "[green]✓ Installed[/green]")
        table.add_row("Browser Tools", "[green]Available[/green]")
    else:
        table.add_row("Status", "[yellow]✗ Not installed[/yellow]")
        table.add_row("Browser Tools", "[yellow]Disabled[/yellow]")
        table.add_row("Install Command", "aria lightpanda download")

    console.print(table)
