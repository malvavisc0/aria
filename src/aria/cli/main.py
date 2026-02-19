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


# Category display configuration
CATEGORY_CONFIG = {
    "environment": {"icon": "📦", "label": "Environment Variables"},
    "storage": {"icon": "📁", "label": "Data & Storage"},
    "binaries": {"icon": "⚙️ ", "label": "Binaries"},
    "models": {"icon": "🧠", "label": "Models"},
    "hardware": {"icon": "🖥️ ", "label": "Hardware"},
}


def _print_check_header():
    """Print the check command header panel."""
    console.print()
    console.print(
        Panel(
            "[bold]🔍 ARIA SYSTEM CHECK[/bold]",
            border_style="cyan",
            expand=False,
            padding=(0, 2),
        )
    )
    console.print()


def _print_category(category: str, checks: list) -> tuple[int, int]:
    """Print a category and its checks.

    Returns:
        Tuple of (passed_count, failed_count) for this category.
    """
    config = CATEGORY_CONFIG.get(category, {"icon": "•", "label": category.title()})
    passed = sum(1 for c in checks if c.passed)
    failed = len(checks) - passed

    # Category header
    if failed == 0:
        status = f"[green]{passed}/{len(checks)}[/green]"
    else:
        status = f"[red]{passed}/{len(checks)}[/red]"
    console.print(f"{config['icon']} {config['label']} {status}")

    # Individual checks
    for check in checks:
        if check.passed:
            details = f" [dim]({check.details})[/dim]" if check.details else ""
            console.print(f"   [green]✓[/green] {check.name}{details}")
        else:
            console.print(f"   [red]✗[/red] {check.name} - [red]{check.error}[/red]")
            if check.hint:
                console.print(f"      [dim]→ {check.hint}[/dim]")

    console.print()
    return passed, failed


def _print_summary_panel(total_passed: int, total_failed: int, hints: list):
    """Print the final summary panel."""
    total = total_passed + total_failed

    if total_failed == 0:
        content = f"[green]✅ All {total} checks passed - System ready![/green]"
        style = "green"
    else:
        lines = [
            f"[red]❌ {total_failed} check{'s' if total_failed > 1 else ''} failed - Fix issues before starting[/red]",
        ]
        if hints:
            lines.append("")
            lines.append("[bold]Quick fixes:[/bold]")
            for i, hint in enumerate(hints[:3], 1):
                lines.append(f"  {i}. {hint}")
        content = "\n".join(lines)
        style = "red"

    console.print(
        Panel(
            content,
            border_style=style,
            expand=False,
            padding=(0, 1),
        )
    )


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
    from aria.preflight import CheckResult, run_preflight_checks

    _print_check_header()

    result = run_preflight_checks()
    grouped = result.group_by_category()

    # Track totals
    total_passed = 0
    total_failed = 0
    all_hints = []

    # Print each category in defined order
    for category in CATEGORY_CONFIG.keys():
        if category in grouped:
            passed, failed = _print_category(category, grouped[category])
            total_passed += passed
            total_failed += failed
            for check in grouped[category]:
                if not check.passed and check.hint:
                    all_hints.append(check.hint)

    # Database check (special case - not in preflight)
    db_check = CheckResult(name="Database", passed=True, category="storage")
    try:
        with get_db_session() as session:
            session.execute(text("SELECT 1"))
            session.execute(text("CREATE TABLE IF NOT EXISTS health (id int)"))
            session.execute(text("DROP TABLE health"))
            db_check.details = "connection healthy (writable)"
    except Exception as e:
        db_check.passed = False
        db_check.error = "connection failed"
        db_check.hint = "Check that aria.db exists and is writable"
        all_hints.append(db_check.hint)

    # Print database under storage category if it exists
    if "storage" in grouped:
        console.print(f"📁 Data & Storage")
        for check in grouped["storage"]:
            if check.passed:
                details = f" [dim]({check.details})[/dim]" if check.details else ""
                console.print(f"   [green]✓[/green] {check.name}{details}")
            else:
                console.print(
                    f"   [red]✗[/red] {check.name} - [red]{check.error}[/red]"
                )
                if check.hint:
                    console.print(f"      [dim]→ {check.hint}[/dim]")

        if db_check.passed:
            console.print(
                f"   [green]✓[/green] {db_check.name} [dim]({db_check.details})[/dim]"
            )
            total_passed += 1
        else:
            console.print(
                f"   [red]✗[/red] {db_check.name} - [red]{db_check.error}[/red]"
            )
            if db_check.hint:
                console.print(f"      [dim]→ {db_check.hint}[/dim]")
            total_failed += 1
        console.print()

    # Print summary
    _print_summary_panel(total_passed, total_failed, all_hints)

    if total_failed > 0:
        raise typer.Exit(1)
