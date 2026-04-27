"""Llama.cpp binary management commands for the Aria CLI.

This module provides commands to download and manage llama.cpp binaries
from GitHub releases. It supports downloading the latest version or a
specific version tag.

Commands:
    download: Download llama.cpp binaries from GitHub releases
    status: Check installed llama.cpp version and binary status

Example:
    ```bash
    # Download latest llama.cpp release
    aria llamacpp download

    # Download specific version
    aria llamacpp download --version b4500

    # Check installation status
    aria llamacpp status
    ```
"""

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from aria.config.api import LlamaCpp
from aria.scripts.llama import download_llama_cpp

app = typer.Typer(
    name="llamacpp",
    help="Llama.cpp binary management commands.",
)

console = Console()
error_console = Console(stderr=True, style="bold red")


@app.command("download")
def download_command(
    bin_dir: Annotated[
        Path, typer.Option(help="Directory to install the binaries to")
    ] = LlamaCpp.bin_path,
    version: Annotated[
        Optional[str],
        typer.Option(help="Specific version tag to install (e.g., b4500)"),
    ] = None,
):
    """Download llama.cpp binaries from GitHub releases.

    Downloads the appropriate llama.cpp binaries for your platform from
    the official GitHub releases. By default, downloads the latest release.

    Args:
        bin_dir: Target directory for the binaries (default from config)
        version: Specific release tag to download (optional)

    Example:
        ```bash
        # Download latest to default location
        aria llamacpp download

        # Download specific version
        aria llamacpp download --version b4500

        # Download to custom directory
        aria llamacpp download --bin-dir /path/to/binaries
        ```
    """
    try:
        download_llama_cpp(bin_dir=Path(bin_dir), version=version)
        console.print(f"[green]✓[/green] Llama.cpp binaries downloaded to {bin_dir}")
    except Exception as e:
        error_console.print(f"[red]✗[/red] Installation failed: {e}")
        raise typer.Exit(1)


@app.command("status")
def check_status():
    """Check installed llama.cpp version and binary status.

    Displays information about the llama.cpp installation including:
    - Installation directory
    - Configured version
    - Available binaries

    Example:
        ```bash
        aria llamacpp status
        ```
    """
    # Check for common binaries
    binaries = ["llama-cli", "llama-server", "llama-bench", "llama-quantize"]
    installed_count = 0
    for binary in binaries:
        binary_path = LlamaCpp.bin_path / binary
        if binary_path.exists():
            installed_count += 1

    console.print(
        f"[bold]Llama.cpp Status[/bold] ({installed_count}/{len(binaries)} binaries)\n"
    )

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Property", style="cyan", width=20)
    table.add_column("Value", style="green")

    table.add_row("Binary Directory", str(LlamaCpp.bin_path))
    table.add_row("Configured Version", LlamaCpp.version)

    for binary in binaries:
        binary_path = LlamaCpp.bin_path / binary
        if binary_path.exists():
            table.add_row(f"{binary}", "[green]✓ Installed[/green]")
        else:
            table.add_row(f"{binary}", "[red]✗ Not found[/red]")

    console.print(table)
