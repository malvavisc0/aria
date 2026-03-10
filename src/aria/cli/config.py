"""Configuration display commands for the Aria CLI.

This module provides commands to display and inspect the current
configuration settings for the Aria application, including database
paths, API endpoints, and storage locations.

Commands:
    show: Display all configuration settings (paths + database + api)
    paths: Show all configured file system paths
    database: Show database connection configuration
    api: Show API endpoint configuration

Example:
    ```bash
    # Show all configuration
    aria config show

    # Show only paths
    aria config paths

    # Show database configuration
    aria config database

    # Show API configuration
    aria config api
    ```
"""

import typer
from rich.console import Console
from rich.table import Table

from aria.config.database import ChromaDB, SQLite
from aria.config.folders import Data, Debug, Storage
from aria.config.models import Chat, Embeddings

app = typer.Typer(
    name="config",
    help="Configuration display commands.",
)

console = Console()


@app.command("show")
def show_config():
    """Display all configuration settings.

    Runs paths, database, and api sub-commands in sequence.

    Example:
        ```bash
        aria config show
        ```
    """
    show_paths()
    console.print()
    show_database()
    console.print()
    show_api()


@app.command("paths")
def show_paths():
    """Show all configured file system paths.

    Displays a table of all file system paths used by the application:
    - Data folder
    - Storage location
    - Debug logs
    - Database files

    Example:
        ```bash
        aria config paths
        ```
    """
    console.print("[bold]File System Paths[/bold]\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Name", style="cyan", width=20)
    table.add_column("Path", style="green")
    table.add_column("Exists", style="yellow", width=8)

    paths = [
        ("Data Folder", Data.path),
        ("Storage Path", Storage.path),
        ("Debug Logs", Debug.logs_path),
        ("Database File", SQLite.file_path),
        ("ChromaDB Path", ChromaDB.db_path),
    ]

    for name, path in paths:
        exists = "[green]✓[/green]" if path.exists() else "[red]✗[/red]"
        table.add_row(name, str(path), exists)

    console.print(table)


@app.command("database")
def show_database():
    """Show database connection configuration.

    Displays database connection details including:
    - SQLite file path
    - Connection URLs (sync and async)
    - ChromaDB path

    Example:
        ```bash
        aria config database
        ```
    """
    console.print("[bold]Database Configuration[/bold]\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Property", style="cyan", width=20)
    table.add_column("Value", style="green")

    table.add_row("SQLite File", str(SQLite.file_path))
    table.add_row("Sync URL", SQLite.db_url)
    table.add_row("Async URL", SQLite.conn_info)
    table.add_row("ChromaDB Path", str(ChromaDB.db_path))

    # Check if database exists
    db_exists = SQLite.file_path.exists()
    table.add_row(
        "Database Exists",
        "[green]✓ Yes[/green]" if db_exists else "[red]✗ No[/red]",
    )

    console.print(table)


@app.command("api")
def show_api():
    """Show API configuration.

    Displays API endpoint configuration including:
    - Chat API URL
    - Embeddings API URL and model
    - Token limits

    Example:
        ```bash
        aria config api
        ```
    """
    console.print("[bold]API Configuration[/bold]\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Property", style="cyan", width=20)
    table.add_column("Value", style="green")

    table.add_row("Chat API URL", Chat.api_url)
    table.add_row("Max Iterations", str(Chat.max_iteration))
    table.add_row("Embeddings API", Embeddings.api_url)
    table.add_row("Embeddings Model", Embeddings.model)
    table.add_row("Token Limit", str(Embeddings.token_limit))

    console.print(table)
