"""Server CLI commands for the Aria application.

This module provides CLI commands to manage the Aria webserver:
- run: Run the server in foreground (blocking)
- start: Start the server in background
- stop: Stop the server
- restart: Restart the server
- status: Show server status (PID, uptime, start time)

Example:
    ```bash
    # Run in foreground
    aria server run

    # Start in background
    aria server start

    # Check status
    aria server status

    # Stop server
    aria server stop
    ```
"""

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from aria.server import ServerManager

app = typer.Typer(
    name="server",
    help="Manage the Aria webserver",
)
console = Console()
error_console = Console(stderr=True, style="bold red")

# Global server manager instance
_manager: Optional[ServerManager] = None


def get_manager() -> ServerManager:
    """Get or create the global ServerManager instance.

    Returns:
        The global ServerManager instance.
    """
    global _manager
    if _manager is None:
        _manager = ServerManager()
    return _manager


@app.command("run")
def server_run():
    """Run the Aria webserver in the foreground (blocking).

    This command runs the server in the foreground and blocks until
    the server is stopped (Ctrl+C). Similar to running chainlit directly.

    Example:
        ```bash
        aria server run
        ```
    """
    manager = get_manager()
    console.print(
        f"[cyan]Starting server on http://{manager.host}:{manager.port}[/cyan]"
    )
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    try:
        manager.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped[/yellow]")


@app.command("start")
def server_start():
    """Start the Aria webserver in the background.

    This command starts the server as a background process and
    returns immediately. Use 'aria server status' to check if
    the server is running.

    Example:
        ```bash
        aria server start
        ```
    """
    manager = get_manager()
    if manager.start():
        console.print(
            f"[green]✓[/green] Server started on "
            f"http://{manager.host}:{manager.port}"
        )
        console.print(f"[dim]PID: {manager.pid}[/dim]")
    else:
        error_console.print("[yellow]Server is already running[/yellow]")
        raise typer.Exit(1)


@app.command("stop")
def server_stop(
    timeout: float = typer.Option(
        10.0, "--timeout", "-t", help="Seconds to wait for graceful shutdown"
    ),
):
    """Stop the Aria webserver.

    Sends SIGTERM to the server process. If it doesn't stop within
    the timeout, sends SIGKILL.

    Args:
        timeout: Seconds to wait for graceful shutdown.

    Example:
        ```bash
        aria server stop
        aria server stop --timeout 5
        ```
    """
    manager = get_manager()
    if manager.stop(timeout):
        console.print("[green]✓[/green] Server stopped")
    else:
        error_console.print("[yellow]Server is not running[/yellow]")
        raise typer.Exit(1)


@app.command("restart")
def server_restart(
    timeout: float = typer.Option(
        10.0, "--timeout", "-t", help="Seconds to wait for graceful shutdown"
    ),
):
    """Restart the Aria webserver.

    Stops the server if running, then starts it again.

    Args:
        timeout: Seconds to wait for graceful shutdown.

    Example:
        ```bash
        aria server restart
        ```
    """
    manager = get_manager()
    manager.restart(timeout)
    console.print(
        f"[green]✓[/green] Server restarted on "
        f"http://{manager.host}:{manager.port}"
    )
    console.print(f"[dim]PID: {manager.pid}[/dim]")


@app.command("status")
def server_status():
    """Show the current status of the Aria webserver.

    Displays:
    - Running status
    - Process ID (PID)
    - Host and port
    - Start time
    - Uptime

    Example:
        ```bash
        aria server status
        ```
    """
    manager = get_manager()
    status = manager.get_status()

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
        table.add_row(
            "Started", status.started_at.strftime("%Y-%m-%d %H:%M:%S")
        )
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


if __name__ == "__main__":
    app()
