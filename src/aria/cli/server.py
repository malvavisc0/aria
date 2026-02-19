"""Server CLI commands for the Aria application.

This module provides CLI commands to manage the Aria webserver:
- run: Run the server in foreground (blocking)
- start: Start the server in background
- stop: Stop the server
- status: Show server status (web_ui and llama servers)

LlamaCpp servers are managed internally by the web_ui via Chainlit lifecycle hooks.

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

from aria.server import ServerManager

app = typer.Typer(
    name="server",
    help="Manage the Aria webserver",
)
console = Console()
error_console = Console(stderr=True, style="bold red")


@app.command("run")
def server_run():
    """Run the Aria webserver in foreground (blocking).

    Llama-server processes are started automatically by the web_ui.
    Press Ctrl+C to stop.
    """
    manager = ServerManager()
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
    """Start the Aria webserver in background.

    Llama-server processes are started automatically by the web_ui.
    """
    manager = ServerManager()
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
def server_stop():
    """Stop the Aria webserver.

    Also stops all llama-server processes managed by the web_ui.
    """
    manager = ServerManager()
    if manager.stop():
        console.print("[green]✓[/green] Server stopped")
    else:
        error_console.print("[yellow]Server is not running[/yellow]")
        raise typer.Exit(1)


@app.command("status")
def server_status():
    """Show the current status of the Aria webserver and llama servers."""
    from aria.config.models import Chat, Embeddings, Vision

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

    # Llama servers status (only if web_ui is running)
    if status.running:
        console.print()
        llama_table = Table(title="Llama Servers", show_header=True)
        llama_table.add_column("Role", style="cyan", width=12)
        llama_table.add_column("Port", style="yellow")
        llama_table.add_column("Status", style="green")

        for role, get_port in [
            ("chat", Chat.get_port),
            ("vl", Vision.get_port),
            ("embeddings", Embeddings.get_port),
        ]:
            port = get_port()
            try:
                with urlopen(f"http://localhost:{port}/health", timeout=2) as resp:
                    is_running = resp.status == 200
            except (URLError, OSError):
                is_running = False

            llama_table.add_row(
                role, str(port), "● Running" if is_running else "○ Stopped"
            )

        console.print(llama_table)
