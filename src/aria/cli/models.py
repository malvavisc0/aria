"""GGUF model management commands for the Aria CLI.

This module provides commands to download and inspect GGUF model files
from HuggingFace Hub. Models are configured via environment variables
and stored in the configured models directory.

Commands:
    download: Download a GGUF model from HuggingFace Hub
    list: Show configured models and their download status

Example:
    ```bash
    # Download the chat model
    aria models download --model chat

    # Download the vision-language model
    aria models download --model vl

    # Download the embeddings model
    aria models download --model embeddings

    # Force re-download of the chat model
    aria models download --model chat --force

    # Download a custom model by repo ID and quantization
    aria models download --repo-id "org/model-gguf" --quantization Q4_K_M

    # List all configured models and their status
    aria models list
    ```
"""

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from aria.config.api import LlamaCpp as LlamaCppConfig
from aria.config.huggingface import HuggingFace
from aria.scripts.gguf import download_gguf_model, is_model_downloaded

app = typer.Typer(
    name="models",
    help="GGUF model management commands (download, list).",
)

console = Console()
error_console = Console(stderr=True, style="bold red")

# Mapping of model aliases to (repo_id_env_var, quantization_env_var) pairs
_MODEL_ALIASES = {
    "chat": ("CHAT_MODEL", "CHAT_MODEL_TYPE"),
    "vl": ("VL_MODEL", "VL_MODEL_TYPE"),
    "embeddings": ("EMBEDDINGS_MODEL", "EMBEDDINGS_MODEL_TYPE"),
}


def _resolve_model_config(alias: str) -> tuple[str, str]:
    """Resolve a model alias to (repo_id, quantization).

    Args:
        alias: One of 'chat', 'vl', or 'embeddings'.

    Returns:
        Tuple of (repo_id, quantization).

    Raises:
        typer.BadParameter: If the alias is unknown or env vars are not set.
    """
    import os

    if alias not in _MODEL_ALIASES:
        raise typer.BadParameter(
            f"Unknown model alias '{alias}'. Choose from: {', '.join(_MODEL_ALIASES)}"
        )

    repo_env, quant_env = _MODEL_ALIASES[alias]

    repo_id = os.getenv(repo_env)
    if not repo_id:
        raise typer.BadParameter(
            f"Environment variable '{repo_env}' is not set. "
            f"Please configure it in your .env file."
        )

    quantization = os.getenv(quant_env, "Q8_0")

    return repo_id, quantization


@app.command("download")
def download_command(
    model: Annotated[
        Optional[str],
        typer.Option(
            "--model",
            "-m",
            help="Model alias to download: 'chat', 'vl', or 'embeddings'.",
        ),
    ] = None,
    repo_id: Annotated[
        Optional[str],
        typer.Option(
            "--repo-id",
            help="HuggingFace repository ID (e.g. 'org/model-gguf'). "
            "Used when not specifying --model.",
        ),
    ] = None,
    quantization: Annotated[
        Optional[str],
        typer.Option(
            "--quantization",
            "-q",
            help="Quantization type to download (e.g. Q8_0, Q4_K_M). "
            "Used together with --repo-id.",
        ),
    ] = None,
    models_dir: Annotated[
        Optional[Path],
        typer.Option(
            "--models-dir",
            help="Directory to save the model file. Defaults to GGUF_MODELS_DIR.",
        ),
    ] = None,
    token: Annotated[
        Optional[str],
        typer.Option(
            "--token",
            help="HuggingFace API token. Overrides HUGGINGFACE_TOKEN env var.",
            envvar="HUGGINGFACE_TOKEN",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Force re-download even if the model file already exists.",
        ),
    ] = False,
):
    """Download a GGUF model file from HuggingFace Hub.

    You can specify a model by alias (--model chat|vl|embeddings) which reads
    the repo ID and quantization from your .env configuration, or provide
    a custom --repo-id and --quantization directly.

    If the model is already downloaded, the command skips the download unless
    --force is specified.

    Args:
        model: Alias for a configured model ('chat', 'vl', 'embeddings').
        repo_id: Custom HuggingFace repo ID (used without --model).
        quantization: Quantization type (used with --repo-id).
        models_dir: Override the default models directory.
        token: HuggingFace API token for gated/private models.
        force: Re-download even if already present.

    Example:
        ```bash
        # Download configured chat model
        aria models download --model chat

        # Force re-download
        aria models download --model chat --force

        # Custom repo
        aria models download --repo-id "org/model-gguf" --quantization Q4_K_M
        ```
    """
    # Resolve repo_id and quantization
    if model:
        try:
            resolved_repo_id, resolved_quantization = _resolve_model_config(model)
        except typer.BadParameter as e:
            error_console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)
    elif repo_id:
        resolved_repo_id = repo_id
        resolved_quantization = quantization or "Q8_0"
    else:
        error_console.print(
            "[red]Error: Specify either --model (chat|vl|embeddings) "
            "or --repo-id with optional --quantization.[/red]"
        )
        raise typer.Exit(1)

    # Resolve models directory
    target_dir = models_dir or LlamaCppConfig.models_path

    # Resolve token
    resolved_token = token or HuggingFace.token

    console.print(
        Panel(
            f"[bold]Repo:[/bold] {resolved_repo_id}\n"
            f"[bold]Quantization:[/bold] {resolved_quantization}\n"
            f"[bold]Destination:[/bold] {target_dir}\n"
            f"[bold]Token:[/bold] {'[green]set[/green]' if resolved_token else '[yellow]not set (public only)[/yellow]'}\n"
            f"[bold]Force:[/bold] {'[yellow]yes[/yellow]' if force else 'no'}",
            title="[bold]GGUF Model Download[/bold]",
            border_style="cyan",
        )
    )

    try:
        dest = download_gguf_model(
            repo_id=resolved_repo_id,
            quantization=resolved_quantization,
            models_dir=target_dir,
            token=resolved_token,
            force=force,
        )
        console.print(
            Panel(
                f"[green]✓[/green] Model ready at: [dim]{dest}[/dim]",
                title="[bold]Done[/bold]",
                border_style="green",
            )
        )
    except FileNotFoundError as e:
        error_console.print(
            Panel(
                f"[red]File not found: {e}[/red]",
                title="[bold]Error[/bold]",
                border_style="red",
            )
        )
        raise typer.Exit(1)
    except Exception as e:
        error_console.print(
            Panel(
                f"[red]Download failed: {e}[/red]",
                title="[bold]Error[/bold]",
                border_style="red",
            )
        )
        raise typer.Exit(1)


@app.command("list")
def list_command(
    models_dir: Annotated[
        Optional[Path],
        typer.Option(
            "--models-dir",
            help="Directory to check for downloaded models. Defaults to GGUF_MODELS_DIR.",
        ),
    ] = None,
):
    """Show configured models and their download status.

    Displays a table of all models configured in the environment, showing
    the repository ID, quantization type, and whether the model file has
    been downloaded to the models directory.

    Example:
        ```bash
        aria models list
        ```
    """
    import os

    target_dir = models_dir or LlamaCppConfig.models_path

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Alias", style="cyan", width=12)
    table.add_column("Repo ID", style="white")
    table.add_column("Quantization", style="yellow", width=14)
    table.add_column("Downloaded", style="green", width=12)

    for alias, (repo_env, quant_env) in _MODEL_ALIASES.items():
        repo_id_val = os.getenv(repo_env, "")
        quant_val = os.getenv(quant_env, "Q8_0")

        if not repo_id_val:
            table.add_row(
                alias,
                f"[dim]not configured ({repo_env})[/dim]",
                quant_val,
                "[dim]N/A[/dim]",
            )
            continue

        downloaded = is_model_downloaded(repo_id_val, quant_val, target_dir)
        status = "[green]✓ Yes[/green]" if downloaded else "[red]✗ No[/red]"

        table.add_row(alias, repo_id_val, quant_val, status)

    console.print(
        Panel(
            table,
            title=f"[bold]Configured GGUF Models[/bold] — [dim]{target_dir}[/dim]",
            border_style="cyan",
        )
    )
