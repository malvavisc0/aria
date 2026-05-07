"""Server CLI commands for the Aria application.

This module provides CLI commands to manage the Aria webserver:
- run: Run the server in foreground (blocking)
- start: Start the server in background
- stop: Stop the server
- status: Show server status (web_ui and vLLM servers)

vLLM servers are managed internally by the web_ui via Chainlit lifecycle hooks.

Example:
    ```bash
    # Run in foreground (Ctrl+C to stop)
    aria server run

    # Start in background
    aria server start

    # Check status
    aria server status

    # Stop server
    aria server stop
    ```
"""

from urllib.error import URLError
from urllib.request import urlopen

import typer
from rich.console import Console
from rich.table import Table

from aria.preflight import run_preflight_checks
from aria.server import ServerManager

app = typer.Typer(
    name="server",
    help="Manage the Aria webserver",
)
console = Console()
error_console = Console(stderr=True, style="bold red")

# Health check settings
HEALTH_CHECK_TIMEOUT = 180  # seconds (vLLM model loading can take 30s+)
HEALTH_CHECK_INTERVAL = 0.5  # seconds


def _print_preflight_result(result) -> bool:
    """Print preflight results in grouped format and return True if all pass."""
    grouped = result.group_by_category()

    # Category icons and labels
    category_config = {
        "environment": {"icon": "📦", "label": "Environment Variables"},
        "storage": {"icon": "📁", "label": "Data & Storage"},
        "binaries": {"icon": "⚙️ ", "label": "Binaries"},
        "models": {"icon": "🧠", "label": "Models"},
        "hardware": {"icon": "🖥️ ", "label": "Hardware"},
    }

    for category in category_config.keys():
        if category not in grouped:
            continue

        config = category_config[category]
        checks = grouped[category]
        passed = sum(1 for c in checks if c.passed)

        if passed == len(checks):
            console.print(
                f"{config['icon']} {config['label']} [green]{passed}/{len(checks)}[/green]"
            )
        else:
            console.print(
                f"{config['icon']} {config['label']} [red]{passed}/{len(checks)}[/red]"
            )

        for check in checks:
            if check.passed:
                details = f" [dim]({check.details})[/dim]" if check.details else ""
                console.print(f"   [green]✓[/green] {check.name}{details}")
            else:
                console.print(
                    f"   [red]✗[/red] {check.name} - [red]{check.error}[/red]"
                )

    return result.passed


def _wait_for_health(host: str, port: int, timeout: float) -> bool:
    """Wait for server to become healthy.

    Args:
        host: Server host address.
        port: Server port.
        timeout: Maximum seconds to wait.

    Returns:
        True if server is healthy, False if timeout.
    """
    import time

    url = f"http://{host}:{port}/health"
    deadline = time.time() + timeout

    while time.time() < deadline:
        try:
            with urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except (URLError, OSError):
            pass
        time.sleep(HEALTH_CHECK_INTERVAL)

    return False


@app.command("run")
def server_run():
    """Run the Aria webserver in foreground (blocking).

    vLLM server processes are started automatically by the web_ui.
    Press Ctrl+C to stop.
    """
    # Run preflight checks
    result = run_preflight_checks()
    if not _print_preflight_result(result):
        error_console.print(
            "\n[red]✗ Preflight checks failed. Fix the issues above.[/red]"
        )
        raise typer.Exit(1)

    manager = ServerManager()
    console.print(
        f"\n[cyan]Starting server on http://{manager.host}:{manager.port}[/cyan]"
    )
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    try:
        manager.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped[/yellow]")


@app.command("start")
def server_start(
    force_restart_vllm: bool = typer.Option(
        False,
        "--force-restart-vllm",
        help="Stop any running vLLM servers before starting the web UI.",
    ),
):
    """Start the Aria webserver in background.

    vLLM server processes are started automatically by the web_ui.
    """
    # Run preflight checks
    result = run_preflight_checks()
    if not _print_preflight_result(result):
        error_console.print(
            "\n[red]✗ Preflight checks failed. Fix the issues above.[/red]"
        )
        raise typer.Exit(1)

    if force_restart_vllm:
        from aria.server.vllm import VllmServerManager

        vllm = VllmServerManager()
        if vllm._pids:
            console.print("[dim]Stopping existing vLLM servers...[/dim]")
            vllm.stop_all()

    manager = ServerManager()
    if manager.is_running():
        error_console.print("[yellow]Server is already running[/yellow]")
        raise typer.Exit(1)

    console.print(
        f"\n[cyan]Starting server on http://{manager.host}:{manager.port}[/cyan]"
    )

    if not manager.start():
        error_console.print("[red]Failed to start server process[/red]")
        raise typer.Exit(1)

    # Wait for health check
    console.print("[dim]Waiting for server to be ready...[/dim]")
    if _wait_for_health(manager.host, manager.port, HEALTH_CHECK_TIMEOUT):
        console.print(
            f"[green]✓[/green] Server started on http://{manager.host}:{manager.port}"
        )
        console.print(f"[dim]PID: {manager.pid}[/dim]")
    else:
        error_console.print("[red]Server failed to start within timeout[/red]")
        manager.stop()
        raise typer.Exit(1)


@app.command("stop")
def server_stop(
    skip_vllm: bool = typer.Option(
        False,
        "--skip-vllm",
        help="Keep vLLM servers running (only stop the web UI).",
    ),
):
    """Stop the Aria webserver.

    Also stops all vLLM server processes managed by the web_ui,
    unless --skip-vllm is specified.
    """
    if skip_vllm:
        from aria.config.folders import Data as DataConfig

        sentinel = DataConfig.path / "skip_vllm_shutdown"
        sentinel.touch()
        console.print("[dim]vLLM servers will be left running[/dim]")

    manager = ServerManager()
    if manager.stop():
        console.print("[green]✓[/green] Server stopped")
    else:
        error_console.print("[yellow]Server is not running[/yellow]")
        raise typer.Exit(1)


@app.command("status")
def server_status():
    """Show the current status of the Aria webserver and vLLM servers."""
    from aria.config.models import Chat

    manager = ServerManager()
    status = manager.get_status()

    # WebUI status table
    table = Table(title="Aria Webserver Status", show_header=True)
    table.add_column("Property", style="cyan", width=12)
    table.add_column("Value", style="green")

    # Status with colored indicator
    if status.running:
        table.add_row("Status", "● Running")
    else:
        table.add_row("Status", "○ Stopped")

    # PID
    table.add_row("PID", str(status.pid) if status.pid else "N/A")

    # Host and port
    table.add_row("Host", status.host)
    table.add_row("Port", str(status.port))

    # URL
    url = f"http://{status.host}:{status.port}"
    table.add_row("URL", url)

    # Start time
    if status.started_at:
        table.add_row("Started", status.started_at.strftime("%Y-%m-%d %H:%M:%S"))
    else:
        table.add_row("Started", "N/A")

    # Uptime
    if status.uptime_seconds is not None:
        hours, remainder = divmod(int(status.uptime_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"
        table.add_row("Uptime", uptime_str)
    else:
        table.add_row("Uptime", "N/A")

    console.print(table)

    # vLLM servers status (always show, not just when web_ui is running)
    console.print()
    vllm_table = Table(title="vLLM Servers", show_header=True)
    vllm_table.add_column("Role", style="cyan", width=12)
    vllm_table.add_column("Port", style="yellow")
    vllm_table.add_column("Status", style="green")

    for role, get_port in [
        ("chat", Chat.get_port),
    ]:
        port = get_port()
        try:
            with urlopen(f"http://localhost:{port}/health", timeout=2) as resp:
                is_running = resp.status == 200
        except (URLError, OSError):
            is_running = False

        vllm_table.add_row(role, str(port), "● Running" if is_running else "○ Stopped")

    console.print(vllm_table)
