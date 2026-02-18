"""Main CLI entry point for the Aria application.

This module defines the root CLI application and core commands for managing
the Aria AI assistant system. It provides database health checks, version
information, and serves as the entry point for all sub-commands.

Commands:
    check: Verify database connectivity and write permissions
    version: Display the current Aria CLI version
    info: Show system overview including GPU and configuration status

Sub-commands:
    users: User management (list, add, reset, edit)
    llamacpp: Llama.cpp binary management (download, status)
    config: Configuration display (show, paths, database)
    system: System information (gpu, vram, nvlink)

Example:
    ```bash
    # Check database health
    aria check

    # Show version
    aria version

    # Get help
    aria --help
    ```
"""

from typing import Type

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from sqlalchemy import text

from aria.cli import (
    config,
    get_db_session,
    llamacpp,
    models,
    server,
    system,
    users,
)
from aria.config.api import LlamaCpp as LlamaCppConfig
from aria.config.database import SQLite as SQLiteConfig
from aria.config.folders import Data as DataConfig
from aria.config.folders import Debug as DebugConfig
from aria.config.folders import Storage as StorageConfig
from aria.helpers.nvidia import check_nvidia_smi_available, detect_gpu_count

app = typer.Typer(
    name="aria",
    help="Aria - AI Assistant Management CLI\n\nManage users, configuration, and system resources for the Aria AI assistant.",
    rich_markup_mode="rich",
    add_completion=False,
)
app.add_typer(users.app, name="users")
app.add_typer(llamacpp.app, name="llamacpp")
app.add_typer(models.app, name="models")
app.add_typer(config.app, name="config")
app.add_typer(server.app, name="server")
app.add_typer(system.app, name="system")

console = Console()
error_console = Console(stderr=True, style="bold red")


def print_banner():
    """Print the Aria ASCII art banner with version info."""
    try:
        # Use importlib.metadata for a cleaner version check in modern Python
        from importlib.metadata import version

        v = version("aria")
        version_text = f"v{v}"
    except Exception:
        version_text = "development"

    banner_art = r"""
[bold cyan]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣠⣤⣤⣄⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[bold cyan]⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⠾⠛⠉⠉⠉⠉⠉⠉⠛⠳⣦⡀⠀⠀⠀⠀⠀⠀⠀⠀[/]
[bold cyan]⠀⠀⠀⠀⠀⠀⢀⣴⠟⠁⣠⣄⣀⣴⡦⠀⠀⠀⠀⠀⠀⠹⣦⡀⠀⠀⠀⠀⠀⠀[/]
[bold cyan]⠀⠀⠀⠀⠀⢠⣾⠏⠀⠀⣸⡿⠛⠻⣷⣤⡄⠀⠀⠀⠀⠀⠘⣷⡄⠀⠀⠀⠀⠀[/]
[bold cyan]⠀⠀⠀⠀⢀⣾⡟⠀⠀⠿⢿⣧⣀⣠⣿⠛⠃⠀⢠⣤⠀⠀⠀⢸⣷⡀⠀⠀⠀⠀[/]
[bold cyan]⠀⠀⠀⠀⣸⣿⡇⠀⠀⠀⠰⣿⠛⠛⠿⢿⣷⣤⣾⣿⣦⣤⡇⢸⣿⣇⠀⠀⠀⠀[/]
[bold cyan]⠀⠀⠀⠀⣿⣿⣷⠀⠀⠀⠀⠀⢰⣷⣴⣿⣿⣿⣿⣿⣿⣿⠃⣸⣿⣿⠀⠀⠀⠀[/]
[bold cyan]⠀⠀⠀⠀⣿⣿⣿⣧⡀⠀⠀⠀⠀⣼⣿⣿⣿⡿⠋⠉⠻⠃⣰⣿⣿⣿⠀⠀⠀⠀[/]
[bold cyan]⠀⠀⠀⠀⣿⣿⣿⣿⣷⣄⡀⠸⠿⣿⣿⣿⣿⠇⠀⠀⣠⣾⣿⣿⣿⣿⠀⠀⠀⠀[/]
[bold cyan]⠀⠀⠀⠀⢹⣿⣿⣿⣿⠿⠿⣶⣤⣬⣭⣭⣥⣤⣶⠿⢿⣿⣿⣿⣿⡏⠀⠀⠀⠀[/]
[bold cyan]⠀⠀⠀⠀⠈⢿⣿⣿⠃⠀⠀⠘⣿⣿⣿⣿⣿⣿⠁⠀⠀⢹⣿⣿⡿⠁⠀⠀⠀⠀[/]
[bold cyan]⠀⠀⠀⠀⠀⠘⢿⣿⣧⣀⣀⣼⣿⣿⣿⣿⣿⣿⣦⣀⣠⣾⣿⡿⠃⠀⠀⠀⠀⠀[/]
[bold cyan]⠀⠀⠀⠀⠀⠀⠀⠀⣉⠙⠛⠛⠻⠿⠿⠿⠿⠟⠛⠛⠋⢉⠁⠀⠀⠀⠀⠀⠀⠀[/]
[bold cyan]⠀⠀⠀⠀⠀⠀⠀⠀⠈⠁⠀⣷⣶⠀⣶⣶⡆⢀⣾⠃⠈⠁⠀⠀⠀⠀⠀⠀⠀⠀[/]
[bold cyan]⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠀⠛⠛⠃⠈⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀[/]
"""
    console.print()
    # The strip() call removes the leading/trailing newline from the raw string
    console.print(banner_art.strip())
    console.print()

    console.print(
        Panel(
            f"[dim]AI Assistant Management CLI[/dim] • [cyan]{version_text}[/cyan]",
            border_style="cyan",
            expand=False,  # Keeps the panel tight around the text
            padding=(0, 2),
        )
    )


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Aria - AI Assistant Management CLI.

    Display banner and help when called without a command.
    """
    if ctx.invoked_subcommand is None:
        print_banner()
        console.print()
        console.print("[bold]Available commands:[/bold]")
        console.print()
        console.print("  [cyan]check[/cyan]     Verify database connectivity")
        console.print("  [cyan]version[/cyan]   Display CLI version")
        console.print("  [cyan]info[/cyan]      Show system overview")
        console.print()
        console.print("  [cyan]users[/cyan]     User management commands")
        console.print("  [cyan]llamacpp[/cyan]  Llama.cpp binary management")
        console.print("  [cyan]models[/cyan]    GGUF model download and status")
        console.print("  [cyan]config[/cyan]    Configuration display")
        console.print("  [cyan]server[/cyan]    Webserver management")
        console.print("  [cyan]system[/cyan]    System information (GPU, VRAM)")
        console.print()
        console.print("[dim]Run 'aria --help' for more information.[/dim]")


@app.command("check")
def health_check():
    """Verify database connectivity and write permissions.

    Performs a comprehensive health check of the database connection:
    1. Tests basic connectivity with a SELECT query
    2. Verifies write permissions by creating and dropping a test table

    This command is useful for diagnosing database issues and ensuring
    the application can properly interact with its data store.

    Example:
        ```bash
        aria check
        ```
    """
    try:
        with get_db_session() as session:
            # Check if we can talk to the engine
            session.execute(text("SELECT 1"))

            # Check if we can actually WRITE
            session.execute(text("CREATE TABLE IF NOT EXISTS health (id int)"))
            session.execute(text("DROP TABLE health"))

            console.print(
                "[green]✓[/green] Database connection is healthy and writable."
            )

    except Exception:
        error_console.print_exception()

    llama_server_path = LlamaCppConfig.bin_path / "llama-server"
    if not llama_server_path.exists():
        error_console.print("[red]✗[/red] llama-server not found.")
        console.print(
            "[dim]Run 'aria llamacpp download' to download llama.cpp binaries.[/dim]"
        )

        raise typer.Exit(1)

    console.print("[green]✓[/green] llama-server found.")


@app.command("version")
def show_version():
    """Display the current Aria CLI version.

    Shows the installed version of the Aria package as defined in
    the package metadata.

    Example:
        ```bash
        aria version
        ```
    """
    print_banner()


@app.command("info")
def system_info():
    """Display system overview including GPU and configuration status.

    Shows a summary of:
    - Database status and location
    - GPU availability and basic info
    - Key configuration paths

    Example:
        ```bash
        aria info
        ```
    """

    table = Table(title="Aria System Information", show_header=True)
    table.add_column("Component", style="cyan", width=20)
    table.add_column("Status", style="green")

    # Database info
    table.add_row("Data Folder", str(DataConfig.path))
    table.add_row("Database Path", str(SQLiteConfig.file_path))
    table.add_row("Storage Path", str(StorageConfig.path))
    table.add_row("Debug Logs", str(DebugConfig.logs_path))

    # GPU info
    if check_nvidia_smi_available():
        gpu_count = detect_gpu_count()
        table.add_row("NVIDIA GPU", f"✓ Available ({gpu_count} detected)")
    else:
        table.add_row("NVIDIA GPU", "✗ Not available")

    console.print(
        Panel(
            table,
            title="[bold]System Overview[/bold]",
            border_style="cyan",
        )
    )


if __name__ == "__main__":
    app()
