"""Main CLI entry point for the Aria application.

This module defines the root CLI application and core commands for managing
the Aria AI assistant system. It provides database health checks and serves
as the entry point for all sub-commands.

Commands:
    check: Verify database connectivity and write permissions

Sub-commands:
    users: User management (list, add, reset, edit, delete)
    llamacpp: Llama.cpp binary management (download, status)
    config: Configuration display (show, paths, database, api)
    system: System information (gpu, vram, nvlink, context, info)
    models: GGUF model management (download, list, memory)
    server: Webserver management (run, start, stop, status)

Example:
    ```bash
    # Check database health
    aria check

    # Get help
    aria --help
    ```
"""

import typer
from rich.console import Console
from rich.panel import Panel
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


def _print_banner():
    """Print the Aria ASCII art banner with version info."""
    try:
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
    console.print(banner_art.strip())
    console.print()
    console.print(
        Panel(
            f"[dim]AI Assistant Management CLI[/dim] • [cyan]{version_text}[/cyan]",
            border_style="cyan",
            expand=False,
            padding=(0, 2),
        )
    )


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Aria - AI Assistant Management CLI.

    Display banner and help when called without a command.
    """
    if ctx.invoked_subcommand is None:
        _print_banner()
        console.print()
        console.print("[bold]Available commands:[/bold]")
        console.print()
        console.print("  [cyan]check[/cyan]     Verify all prerequisites")
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
    """Verify all prerequisites for running the Aria web UI.

    Performs comprehensive preflight checks:
    1. Required environment variables are set
    2. Data folder exists
    3. llama-server binary is installed
    4. run-model script exists
    5. All GGUF models are downloaded
    6. Database connectivity and write permissions

    Example:
        ```bash
        aria check
        ```
    """
    from aria.preflight import run_preflight_checks

    result = run_preflight_checks()

    for check in result.checks:
        if check.passed:
            console.print(f"[green]✓[/green] {check.name}")
        else:
            console.print(f"[red]✗[/red] {check.name}")
            console.print(f"  [dim]{check.hint}[/dim]")

    try:
        with get_db_session() as session:
            session.execute(text("SELECT 1"))
            session.execute(text("CREATE TABLE IF NOT EXISTS health (id int)"))
            session.execute(text("DROP TABLE health"))
            console.print(
                "[green]✓[/green] Database connection is healthy and writable."
            )
    except Exception:
        error_console.print("[red]✗[/red] Database connection failed.")
        error_console.print_exception()

    if not result.passed:
        raise typer.Exit(1)
