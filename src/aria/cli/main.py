"""Main CLI entry point for the Aria application.

This module defines the root CLI application and registers all sub-commands
for managing the Aria AI assistant system.

Sub-commands:
    check: Preflight checks and agent instructions (preflight, instructions)
    config: Configuration display (show, paths, database, api, optimize)
    users: User management (list, add, reset, edit, delete)
    models: Model management (download, list, memory)
    vllm: vLLM inference engine management (install, status, info)
    lightpanda: Lightpanda browser binary management (download, status)
    server: Webserver management (run, start, stop, status)
    system: Hardware inspection and process management
    processes: Background process management
    knowledge: Persistent key-value memory (store, recall, search, list)
    web: Web search, browsing, weather, YouTube
    dev: Python code execution
    worker: Background worker agent management

Example:
    ```bash
    # Show help
    aria --help

    # Run preflight checks
    aria check preflight

    # View agent instructions
    aria check instructions
    ```
"""

import typer
from rich.console import Console
from rich.panel import Panel

from aria.cli import check as check_cli
from aria.cli import (
    config,
)
from aria.cli import dev as dev_cli
from aria.cli import knowledge as knowledge_cli
from aria.cli import (
    lightpanda,
    models,
)
from aria.cli import processes as processes_cli
from aria.cli import (
    server,
    system,
    users,
)
from aria.cli import vllm as vllm_cli
from aria.cli import web as web_cli
from aria.cli import worker as worker_cli
from aria.config import DEBUG

app = typer.Typer(
    name="aria",
    help=(
        "Aria - local AI assistant CLI\n\n"
        "Operational interface for Aria agents, workers, browsing, "
        "knowledge, models, and system management. Many commands return "
        "JSON metadata and saved artifact paths for safe follow-up reads."
    ),
    rich_markup_mode="rich",
    add_completion=False,
)
app.add_typer(check_cli.app, name="check")
app.add_typer(users.app, name="users")
app.add_typer(vllm_cli.app, name="vllm")
app.add_typer(lightpanda.app, name="lightpanda")
app.add_typer(models.app, name="models")
app.add_typer(config.app, name="config")
app.add_typer(server.app, name="server")
app.add_typer(system.app, name="system")
app.add_typer(processes_cli.app, name="processes")
app.add_typer(knowledge_cli.app, name="knowledge")
app.add_typer(web_cli.app, name="web")
app.add_typer(dev_cli.app, name="dev")
app.add_typer(worker_cli.app, name="worker")

console = Console()


def _configure_logging():
    # Rich handles CLI output formatting; set root level via DEBUG flag.
    import logging

    logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO)

    # Always silence noisy low-level loggers — never useful in CLI output.
    for _name in (
        "httpcore",
        "httpx",
        "huggingface_hub",
        "urllib3",
        "filelock",
    ):
        logging.getLogger(_name).setLevel(logging.WARNING)


def _print_banner():
    """Print the Aria banner with version info."""
    try:
        from importlib.metadata import version

        v = version("aria")
        version_text = f"v{v}"
    except Exception:
        version_text = "development"

    console.print()
    console.print(
        Panel(
            (f"[bold]ARIA CLI[/bold]\n[dim]Local AI assistant • {version_text}[/dim]"),
            border_style="cyan",
            expand=False,
            padding=(0, 2),
        )
    )
    console.print()


# Command groups for display
COMMAND_GROUPS = [
    {
        "title": "Setup",
        "commands": [
            ("check", "Preflight checks and agent instructions"),
            ("config", "Show settings, paths, and keys"),
            ("users", "Manage user accounts"),
        ],
    },
    {
        "title": "Infrastructure",
        "commands": [
            ("models", "Download and manage models"),
            ("vllm", "Install and manage vLLM"),
            ("lightpanda", "Download and manage Lightpanda browser"),
            ("server", "Start or stop the web UI"),
            ("system", "Inspect hardware and GPU"),
            ("processes", "Manage background processes"),
        ],
    },
    {
        "title": "Research",
        "commands": [
            ("web", "Search, fetch pages, get weather"),
        ],
    },
    {
        "title": "Agents",
        "commands": [
            ("worker", "Spawn background agents"),
            ("knowledge", "Store and recall facts"),
            ("dev", "Run Python code"),
        ],
    },
]


def _get_prog_name() -> str:
    """Return the CLI program name based on how it was invoked."""
    import sys
    from pathlib import Path

    return Path(sys.argv[0]).stem if sys.argv else "aria"


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Aria - AI Assistant Management CLI.

    Display banner and help when called without a command.
    """
    _configure_logging()
    if ctx.invoked_subcommand is None:
        _print_banner()
        prog = _get_prog_name()

        for group in COMMAND_GROUPS:
            console.print(f"[bold]{group['title']}[/bold]")
            for cmd, desc in group["commands"]:
                padded = f"{prog} {cmd}".ljust(18)
                console.print(f"   [cyan]{padded}[/cyan]{desc}")
            console.print()

        console.print(f"[dim]Run '{prog} <command> --help' for details.[/dim]")
