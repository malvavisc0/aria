"""Configuration display commands for the Aria CLI.

This module provides commands to display and inspect the current
configuration settings for the Aria application, including database
paths, API endpoints, and storage locations.

Commands:
    show: Display all configuration settings
    paths: Show all configured file system paths
    database: Show database connection configuration

Example:
    ```bash
    # Show all configuration
    aria config show

    # Show only paths
    aria config paths

    # Show database configuration
    aria config database
    ```
"""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="config",
    help="Configuration display commands.",
)

console = Console()


@app.command("show")
def show_config():
    """Display all configuration settings.

    Shows a comprehensive view of all configuration settings including:
    - Database configuration
    - File system paths
    - API endpoints
    - Model settings

    Example:
        ```bash
        aria config show
        ```
    """
    from aria.config.api import LlamaCpp
    from aria.config.database import ChromaDB, SQLite
    from aria.config.folders import Data, Debug, Storage
    from aria.config.models import Chat, Embeddings

    # Paths table
    paths_table = Table(show_header=True, header_style="bold cyan")
    paths_table.add_column("Name", style="cyan", width=20)
    paths_table.add_column("Path", style="green")
    paths_table.add_row("Data Folder", str(Data.path))
    paths_table.add_row("Storage Path", str(Storage.path))
    paths_table.add_row("Debug Logs", str(Debug.logs_path))
    paths_table.add_row("Database File", str(SQLite.file_path))
    paths_table.add_row("ChromaDB Path", str(ChromaDB.db_path))
    paths_table.add_row("Llama.cpp Binaries", str(LlamaCpp.bin_path))

    # Database table
    db_table = Table(show_header=True, header_style="bold cyan")
    db_table.add_column("Property", style="cyan", width=20)
    db_table.add_column("Value", style="green")
    db_table.add_row("SQLite URL", SQLite.db_url)
    db_table.add_row("Async URL", SQLite.conn_info)

    # API table
    api_table = Table(show_header=True, header_style="bold cyan")
    api_table.add_column("Property", style="cyan", width=20)
    api_table.add_column("Value", style="green")
    api_table.add_row("Chat API URL", Chat.api_url)
    api_table.add_row("Max Iterations", str(Chat.max_iteration))
    api_table.add_row("Embeddings API", Embeddings.api_url)
    api_table.add_row("Embeddings Model", Embeddings.model)
    api_table.add_row("Token Limit", str(Embeddings.token_limit))
    api_table.add_row("Llama.cpp Version", LlamaCpp.version)

    console.print(
        Panel(
            paths_table,
            title="[bold]File System Paths[/bold]",
            border_style="cyan",
        )
    )
    console.print()
    console.print(
        Panel(
            db_table,
            title="[bold]Database Configuration[/bold]",
            border_style="cyan",
        )
    )
    console.print()
    console.print(
        Panel(
            api_table,
            title="[bold]API Configuration[/bold]",
            border_style="cyan",
        )
    )


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
    from aria.config.database import ChromaDB, SQLite
    from aria.config.folders import Data, Debug, Storage

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

    console.print(
        Panel(table, title="[bold]File System Paths[/bold]", border_style="cyan")
    )


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
    from aria.config.database import ChromaDB, SQLite

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

    console.print(
        Panel(
            table,
            title="[bold]Database Configuration[/bold]",
            border_style="cyan",
        )
    )


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
    from aria.config.models import Chat, Embeddings

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Property", style="cyan", width=20)
    table.add_column("Value", style="green")

    table.add_row("Chat API URL", Chat.api_url)
    table.add_row("Max Iterations", str(Chat.max_iteration))
    table.add_row("Embeddings API", Embeddings.api_url)
    table.add_row("Embeddings Model", Embeddings.model)
    table.add_row("Token Limit", str(Embeddings.token_limit))

    console.print(
        Panel(table, title="[bold]API Configuration[/bold]", border_style="cyan")
    )


if __name__ == "__main__":
    app()
