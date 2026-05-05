"""Model management commands for the Aria CLI.

This module provides commands to download and inspect HuggingFace model
snapshots used by the vLLM inference engine. Models are configured via
environment variables and stored as local snapshot directories.

Commands:
    download: Download a model snapshot from HuggingFace Hub
    list: Show configured models and their download status
    memory: Show memory requirements for all configured models

Example:
    ```bash
    # Download the chat model
    aria models download --model chat

    # Download the embeddings model
    aria models download --model embeddings

    # Force re-download of the chat model
    aria models download --model chat --force

    # List all configured models and their status
    aria models list

    # Show memory requirements
    aria models memory
    ```
"""

from pathlib import Path
from typing import Annotated, Optional

import typer
from huggingface_hub import snapshot_download
from rich.console import Console
from rich.table import Table

from aria.config.huggingface import HuggingFace
from aria.config.models import Chat, Embeddings

app = typer.Typer(
    name="models",
    help="Model management commands (download, list, memory).",
)

console = Console()
error_console = Console(stderr=True, style="bold red")

# Maps alias -> (config_class, env_var)
_MODEL_CONFIGS: dict[str, tuple] = {
    "chat": (Chat, "CHAT_MODEL_PATH"),
    "embeddings": (Embeddings, "EMBED_MODEL_PATH"),
}


def _is_model_downloaded(model_path: str) -> bool:
    """Check if a model directory exists under DATA_FOLDER/models/.

    All models must reside under DATA_FOLDER/models/. This function
    checks for local directory existence only — HF cache is not used.

    Args:
        model_path: Resolved absolute path to the model directory.

    Returns:
        True if the model directory exists locally.
    """
    if not model_path:
        return False
    path = Path(model_path)
    return path.is_absolute() and path.exists() and path.is_dir()


def _resolve_model_config(alias: str) -> tuple[str, str]:
    """Resolve a model alias to (repo_id, local_path) using config classes.

    Args:
        alias: One of 'chat', 'embeddings'.

    Returns:
        Tuple of (repo_id, local_path) where repo_id is the raw env var
        value (HuggingFace repo ID) and local_path is the resolved path
        under DATA_FOLDER/models/.

    Raises:
        typer.BadParameter: If the alias is unknown or config is not set.
    """
    if alias not in _MODEL_CONFIGS:
        raise typer.BadParameter(
            f"Unknown model alias '{alias}'. "
            f"Choose from: {', '.join(_MODEL_CONFIGS)}"
        )

    config_cls, env_var = _MODEL_CONFIGS[alias]
    model_path = config_cls.model_path

    if not model_path:
        raise typer.BadParameter(
            f"{env_var} is not set. Please configure it in your .env file."
        )

    # Get the raw value (HF repo ID) from the env var
    from os import getenv

    repo_id = getenv(env_var, "")

    return repo_id, model_path


@app.command("download")
def download_command(
    model: Annotated[
        str,
        typer.Option(
            "--model",
            "-m",
            help="Model alias: 'chat' or 'embeddings'.",
        ),
    ],
    token: Annotated[
        Optional[str],
        typer.Option(
            "--token",
            help="HuggingFace API token. Falls back to HUGGINGFACE_TOKEN env var.",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-F",
            help="Force re-download even if the model already exists.",
        ),
    ] = False,
):
    """Download a model snapshot from HuggingFace Hub to DATA_FOLDER/models/.

    Reads the HF repo ID from the .env config and downloads to the
    resolved local path under DATA_FOLDER/models/.

    Example:
        ```bash
        aria models download --model chat
        aria models download --model embeddings
        aria models download --model embeddings --force
        ```
    """
    try:
        repo_id, local_dir = _resolve_model_config(model)
    except typer.BadParameter as e:
        error_console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    resolved_token = token or HuggingFace.token

    console.print("[bold]Model Download[/bold]")
    console.print(f"  Repo: {repo_id}")
    console.print(f"  Destination: {local_dir}")
    token_status = (
        "[green]set[/green]"
        if resolved_token
        else "[yellow]not set (public only)[/yellow]"
    )
    console.print(f"  Token: {token_status}")
    if force:
        console.print("  [yellow]Force: yes[/yellow]")
    console.print()

    try:
        download_kwargs: dict = {
            "repo_id": repo_id,
            "local_dir": local_dir,
            "token": resolved_token,
        }
        if force:
            download_kwargs["force_download"] = True

        dest = snapshot_download(**download_kwargs)
        console.print(f"[green]✓[/green] Model ready at: [dim]{dest}[/dim]")
    except Exception as e:
        error_console.print(f"[red]✗[/red] Download failed: {e}")
        raise typer.Exit(1)


@app.command("list")
def list_command():
    """Show configured models and their download status.

    Displays a table of all models configured in the environment, showing
    the model path and whether the model has been downloaded.

    Example:
        ```bash
        aria models list
        ```
    """
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Alias", style="cyan", width=12)
    table.add_column("Model Path", style="white")
    table.add_column("Downloaded", style="green", width=12)

    model_configs = [
        ("chat", Chat.model_path),
        ("embeddings", Embeddings.model_path),
    ]

    for alias, model_path in model_configs:
        if not model_path:
            table.add_row(
                alias,
                "[dim]not configured[/dim]",
                "[dim]N/A[/dim]",
            )
            continue

        downloaded = _is_model_downloaded(model_path)
        status = "[green]✓ Yes[/green]" if downloaded else "[red]✗ No[/red]"
        table.add_row(alias, model_path, status)

    console.print("[bold]Configured Models[/bold]\n")
    console.print(table)


@app.command("memory")
def memory_command():
    """Show memory requirements for all configured models.

    Displays GPU VRAM requirements and RAM requirements for the configured
    models. Estimates are approximate and depend on the specific model
    architecture and quantization.

    Example:
        ```bash
        aria models memory
        ```
    """
    from aria.helpers.memory import detect_system_ram
    from aria.helpers.nvidia import (
        detect_gpus_with_details,
        get_free_vram_per_gpu,
    )

    # Model configurations
    model_configs = [
        ("chat", Chat.model_path),
        ("embeddings", Embeddings.model_path),
    ]

    # Build model info table
    model_table = Table(show_header=True, header_style="bold cyan")
    model_table.add_column("Model", style="cyan")
    model_table.add_column("Path", style="white")
    model_table.add_column("Status", style="green", width=14)

    for alias, model_path in model_configs:
        if not model_path:
            model_table.add_row(
                alias,
                "[dim]not configured[/dim]",
                "[dim]Not configured[/dim]",
            )
            continue

        downloaded = _is_model_downloaded(model_path)
        status = (
            "[green]✓ Downloaded[/green]"
            if downloaded
            else "[red]✗ Not downl.[/red]"
        )
        model_table.add_row(alias, model_path[:60], status)

    console.print("[bold]Model Status[/bold]\n")
    console.print(model_table)

    # Hardware availability
    gpus = detect_gpus_with_details()
    total_ram_mb, avail_ram_mb = detect_system_ram()

    hw_table = Table(show_header=True, header_style="bold cyan")
    hw_table.add_column("Resource", style="cyan")
    hw_table.add_column("Total", style="white", width=12)
    hw_table.add_column("Available", style="green", width=12)

    if gpus:
        free_vram = get_free_vram_per_gpu()
        for i, gpu in enumerate(gpus):
            free_mb = free_vram[i] if i < len(free_vram) else 0
            hw_table.add_row(
                f"GPU {i}: {gpu.name}",
                f"{gpu.total_memory} MB",
                f"{free_mb} MB",
            )
    else:
        hw_table.add_row(
            "GPU",
            "[dim]N/A[/dim]",
            "[dim]N/A[/dim]",
        )

    if total_ram_mb > 0:
        hw_table.add_row(
            "System RAM",
            f"{total_ram_mb} MB",
            f"{avail_ram_mb} MB",
        )
    else:
        hw_table.add_row(
            "System RAM",
            "[dim]N/A[/dim]",
            "[dim]N/A[/dim]",
        )

    console.print("\n[bold]Hardware Availability[/bold]\n")
    console.print(hw_table)
