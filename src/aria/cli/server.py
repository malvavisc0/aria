"""Server CLI commands for the Aria application.

This module provides CLI commands to manage the Aria webserver:
- run: Run the server in foreground (blocking)
- start: Start the server in background
- stop: Stop the server
- restart: Restart the server
- status: Show server status (PID, uptime, start time)

Example:
    ```bash
    # Run in foreground (starts llama-server processes + Chainlit)
    aria server run

    # Run with a larger context window
    aria server run --context-size 32768

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
def server_run(
    context_size: int = typer.Option(
        8192,
        "--context-size",
        "-c",
        help="Context window size (tokens) for chat and VL llama-server instances",
    ),
):
    """Run the Aria webserver in the foreground (blocking).

    Starts the three llama-server inference processes (chat, VL, embeddings),
    waits for them to be ready, then starts the Chainlit web UI. Blocks until
    Ctrl+C is pressed, then stops all processes cleanly.

    Before starting, verifies that the llama-server binary and all configured
    GGUF models are present. Exits with an error if any prerequisite is missing.

    Args:
        context_size: Token context window for chat and VL servers (default 8192).

    Example:
        ```bash
        aria server run
        aria server run --context-size 32768
        ```
    """
    from aria.preflight import run_preflight_checks
    from aria.server.llama import LlamaCppServerManager

    result = run_preflight_checks()
    if not result.passed:
        error_console.print(
            "[bold red]Cannot start server — prerequisites missing:[/bold red]"
        )
        for failure in result.failures:
            error_console.print(f"  [red]✗[/red] {failure.error}")
            console.print(f"    [dim]→ {failure.hint}[/dim]")
        raise typer.Exit(1)

    llama_manager = LlamaCppServerManager(context_size=context_size)
    console.print("[cyan]Starting LlamaCPP inference servers...[/cyan]")
    try:
        llama_manager.start_all()
        console.print("[green]✓[/green] All inference servers ready.")
    except Exception as e:
        error_console.print(
            f"[red]Failed to start inference servers: {e}[/red]"
        )
        raise typer.Exit(1)

    manager = get_manager()
    console.print(
        f"[cyan]Starting server on http://{manager.host}:{manager.port}[/cyan]"
    )
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    try:
        manager.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped[/yellow]")
    finally:
        console.print("[cyan]Stopping inference servers...[/cyan]")
        llama_manager.stop_all()
        console.print("[green]✓[/green] Inference servers stopped.")


@app.command("start")
def server_start(
    context_size: int = typer.Option(
        8192,
        "--context-size",
        "-c",
        help="Context window size (tokens) for chat and VL llama-server instances",
    ),
):
    """Start the Aria webserver in the background.

    Starts the three llama-server inference processes (chat, VL, embeddings),
    waits for them to be ready, then starts the Chainlit web UI as a background
    process and returns immediately.

    Before starting, verifies that the llama-server binary and all configured
    GGUF models are present. Exits with an error if any prerequisite is missing.

    Args:
        context_size: Token context window for chat and VL servers (default 8192).

    Example:
        ```bash
        aria server start
        aria server start --context-size 16384
        ```
    """
    from aria.preflight import run_preflight_checks
    from aria.server.llama import LlamaCppServerManager

    result = run_preflight_checks()
    if not result.passed:
        error_console.print(
            "[bold red]Cannot start server — prerequisites missing:[/bold red]"
        )
        for failure in result.failures:
            error_console.print(f"  [red]✗[/red] {failure.error}")
            console.print(f"    [dim]→ {failure.hint}[/dim]")
        raise typer.Exit(1)

    llama_manager = LlamaCppServerManager(context_size=context_size)
    console.print("[cyan]Starting LlamaCPP inference servers...[/cyan]")
    try:
        llama_manager.start_all()
        console.print("[green]✓[/green] All inference servers ready.")
    except Exception as e:
        error_console.print(
            f"[red]Failed to start inference servers: {e}[/red]"
        )
        raise typer.Exit(1)

    manager = get_manager()
    if manager.start():
        console.print(
            f"[green]✓[/green] Server started on "
            f"http://{manager.host}:{manager.port}"
        )
        console.print(f"[dim]PID: {manager.pid}[/dim]")
    else:
        error_console.print("[yellow]Server is already running[/yellow]")
        llama_manager.stop_all()
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
    from aria.server.llama import LlamaCppServerManager

    manager = get_manager()
    if manager.stop(timeout):
        console.print("[green]✓[/green] Server stopped")
    else:
        error_console.print("[yellow]Server is not running[/yellow]")
        raise typer.Exit(1)

    # Also stop any llama-server processes tracked in the PID file
    llama_manager = LlamaCppServerManager()
    llama_manager.stop_all()
    console.print("[green]✓[/green] Inference servers stopped.")


@app.command("restart")
def server_restart(
    timeout: float = typer.Option(
        10.0, "--timeout", "-t", help="Seconds to wait for graceful shutdown"
    ),
    context_size: int = typer.Option(
        8192,
        "--context-size",
        "-c",
        help="Context window size (tokens) for chat and VL llama-server instances",
    ),
):
    """Restart the Aria webserver.

    Stops the server if running, then starts it again.

    Args:
        timeout: Seconds to wait for graceful shutdown.
        context_size: Token context window for chat and VL servers (default 8192).

    Example:
        ```bash
        aria server restart
        ```
    """
    from aria.server.llama import LlamaCppServerManager

    # Stop existing llama-server processes
    llama_manager = LlamaCppServerManager()
    llama_manager.stop_all()

    # Restart Chainlit
    manager = get_manager()
    manager.restart(timeout)
    console.print(
        f"[green]✓[/green] Server restarted on "
        f"http://{manager.host}:{manager.port}"
    )
    console.print(f"[dim]PID: {manager.pid}[/dim]")

    # Start new llama-server processes
    new_llama_manager = LlamaCppServerManager(context_size=context_size)
    console.print("[cyan]Starting LlamaCPP inference servers...[/cyan]")
    try:
        new_llama_manager.start_all()
        console.print("[green]✓[/green] All inference servers ready.")
    except Exception as e:
        error_console.print(
            f"[red]Failed to start inference servers: {e}[/red]"
        )
        raise typer.Exit(1)


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
