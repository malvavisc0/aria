"""GGUF model management commands for the Aria CLI.

This module provides commands to download and inspect GGUF model files
from HuggingFace Hub. Models are configured via environment variables
and stored in the configured models directory.

Commands:
    download: Download a GGUF model from HuggingFace Hub
    list: Show configured models and their download status
    memory: Show memory requirements for all configured models

Example:
    ```bash
    # Download the chat model
    aria models download --model chat

    # Download the vision-language model (includes mmproj)
    aria models download --model vl

    # Download the embeddings model
    aria models download --model embeddings

    # Force re-download of the chat model
    aria models download --model chat --force

    # Download a custom model by repo ID and filename
    aria models download --repo-id "org/model-gguf" --filename "model-Q8_0.gguf"

    # List all configured models and their status
    aria models list

    # Show memory requirements
    aria models memory
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
from aria.config.models import Chat, Embeddings, Vision
from aria.scripts.gguf import download_gguf_model, is_model_downloaded

app = typer.Typer(
    name="models",
    help="GGUF model management commands (download, list, memory).",
)

console = Console()
error_console = Console(stderr=True, style="bold red")

# Maps alias -> (repo_id, filename, repo_env_var, filename_env_var)
_MODEL_CONFIGS: dict[str, tuple[str | None, str | None, str, str]] = {
    "chat": (Chat.repo_id, Chat.filename, "CHAT_MODEL_REPO", "CHAT_MODEL"),
    "vl": (Vision.repo_id, Vision.filename, "VL_MODEL_REPO", "VL_MODEL"),
    "embeddings": (
        Embeddings.repo_id,
        Embeddings.filename,
        "EMBEDDINGS_MODEL_REPO",
        "EMBEDDINGS_MODEL",
    ),
}


def _resolve_model_config(alias: str) -> tuple[str, str]:
    """Resolve a model alias to (repo_id, filename) using config classes.

    Args:
        alias: One of 'chat', 'vl', or 'embeddings'.

    Returns:
        Tuple of (repo_id, filename).

    Raises:
        typer.BadParameter: If the alias is unknown or config is not set.
    """
    if alias not in _MODEL_CONFIGS:
        raise typer.BadParameter(
            f"Unknown model alias '{alias}'. Choose from: {', '.join(_MODEL_CONFIGS)}"
        )

    repo_id, filename, repo_env, filename_env = _MODEL_CONFIGS[alias]

    if not repo_id:
        raise typer.BadParameter(
            f"{repo_env} is not set. Please configure it in your .env file."
        )
    if not filename:
        raise typer.BadParameter(
            f"{filename_env} is not set. Please configure it in your .env file."
        )

    return repo_id, filename


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
    filename: Annotated[
        Optional[str],
        typer.Option(
            "--filename",
            "-f",
            help="Exact filename to download (e.g. 'model-Q8_0.gguf'). "
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
            "-F",
            help="Force re-download even if the model file already exists.",
        ),
    ] = False,
):
    """Download a GGUF model file from HuggingFace Hub.

    You can specify a model by alias (--model chat|vl|embeddings) which reads
    the repo ID and filename from your .env configuration, or provide
    a custom --repo-id and --filename directly.

    If the model is already downloaded, the command skips the download unless
    --force is specified.

    For VL models, the mmproj file is also downloaded automatically.

    Args:
        model: Alias for a configured model ('chat', 'vl', 'embeddings').
        repo_id: Custom HuggingFace repo ID (used without --model).
        filename: Exact filename to download (used with --repo-id).
        models_dir: Override the default models directory.
        token: HuggingFace API token for gated/private models.
        force: Re-download even if already present.

    Example:
        ```bash
        # Download configured chat model
        aria models download --model chat

        # Download VL model (includes mmproj)
        aria models download --model vl

        # Force re-download
        aria models download --model chat --force

        # Custom repo
        aria models download --repo-id "org/model-gguf" --filename "model-Q8_0.gguf"
        ```
    """
    # Resolve repo_id and filename
    if model:
        try:
            resolved_repo_id, resolved_filename = _resolve_model_config(model)
        except typer.BadParameter as e:
            error_console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)
    elif repo_id and filename:
        resolved_repo_id = repo_id
        resolved_filename = filename
    else:
        error_console.print(
            "[red]Error: Specify either --model (chat|vl|embeddings) "
            "or both --repo-id and --filename.[/red]"
        )
        raise typer.Exit(1)

    # Resolve models directory
    target_dir = models_dir or LlamaCppConfig.models_path

    # Resolve token
    resolved_token = token or HuggingFace.token

    console.print(
        Panel(
            f"[bold]Repo:[/bold] {resolved_repo_id}\n"
            f"[bold]Filename:[/bold] {resolved_filename}\n"
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
            filename=resolved_filename,
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

    # For VL models, also download mmproj
    if model == "vl":
        mmproj_filename = Vision.mmproj_filename
        if mmproj_filename:
            console.print(
                Panel(
                    f"[bold]Repo:[/bold] {resolved_repo_id}\n"
                    f"[bold]Filename:[/bold] {mmproj_filename}\n"
                    f"[bold]Destination:[/bold] {target_dir}",
                    title="[bold]MMPROJ Download (Vision Projector)[/bold]",
                    border_style="magenta",
                )
            )
            try:
                mmproj_dest = download_gguf_model(
                    repo_id=resolved_repo_id,
                    filename=mmproj_filename,
                    models_dir=target_dir,
                    token=resolved_token,
                    force=force,
                )
                console.print(
                    Panel(
                        f"[green]✓[/green] MMPROJ ready at: [dim]{mmproj_dest}[/dim]",
                        title="[bold]MMPROJ Done[/bold]",
                        border_style="green",
                    )
                )
            except FileNotFoundError as e:
                error_console.print(
                    Panel(
                        f"[red]MMPROJ file not found: {e}[/red]\n"
                        "[yellow]VL model may not have vision capabilities without mmproj.[/yellow]",
                        title="[bold]Warning[/bold]",
                        border_style="yellow",
                    )
                )
            except Exception as e:
                error_console.print(
                    Panel(
                        f"[red]MMPROJ download failed: {e}[/red]\n"
                        "[yellow]VL model may not have vision capabilities without mmproj.[/yellow]",
                        title="[bold]Warning[/bold]",
                        border_style="yellow",
                    )
                )


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
    the repository ID, filename, and whether the model file has been
    downloaded to the models directory.

    For VL models, also shows the mmproj file status.

    Example:
        ```bash
        aria models list
        ```
    """
    target_dir = models_dir or LlamaCppConfig.models_path

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Alias", style="cyan", width=12)
    table.add_column("Repo ID", style="white")
    table.add_column("Filename", style="yellow")
    table.add_column("Downloaded", style="green", width=12)
    table.add_column("MMPROJ", style="magenta", width=10)

    # Build model list from config classes
    model_configs = [
        ("chat", Chat.repo_id, Chat.filename),
        ("vl", Vision.repo_id, Vision.filename),
        ("embeddings", Embeddings.repo_id, Embeddings.filename),
    ]

    for alias, repo_id_val, filename_val in model_configs:
        if not repo_id_val:
            table.add_row(
                alias,
                "[dim]not configured[/dim]",
                filename_val or "[dim]N/A[/dim]",
                "[dim]N/A[/dim]",
                "",
            )
            continue

        if not filename_val:
            table.add_row(
                alias,
                repo_id_val,
                "[dim]not configured[/dim]",
                "[dim]N/A[/dim]",
                "",
            )
            continue

        downloaded = is_model_downloaded(filename_val, target_dir)
        status = "[green]✓ Yes[/green]" if downloaded else "[red]✗ No[/red]"

        # Check mmproj for VL model
        mmproj_status = ""
        if alias == "vl":
            mmproj_file = Vision.mmproj_filename
            if mmproj_file:
                mmproj_ok = is_model_downloaded(mmproj_file, target_dir)
                mmproj_status = "[green]✓[/green]" if mmproj_ok else "[red]✗[/red]"

        table.add_row(alias, repo_id_val, filename_val, status, mmproj_status)

    console.print(
        Panel(
            table,
            title=f"[bold]Configured GGUF Models[/bold] — [dim]{target_dir}[/dim]",
            border_style="cyan",
        )
    )


@app.command("memory")
def memory_command():
    """Show memory requirements for all configured models.

    Displays GPU VRAM requirements (model sizes) and RAM requirements
    (KV cache sizes) for the chat, VL, and embeddings models.

    Example:
        ```bash
        aria models memory
        ```
    """
    from aria.helpers.memory import (
        detect_system_ram,
        estimate_kv_cache_mb,
        get_model_file_size,
    )
    from aria.helpers.nvidia import (
        detect_gpus_with_details,
        get_free_vram_per_gpu,
    )
    from aria.scripts.gguf import get_model_path

    models_dir = LlamaCppConfig.models_path

    # Model configurations with context sizes from config classes
    model_configs = [
        (
            "chat",
            Chat.repo_id,
            Chat.filename,
            LlamaCppConfig.chat_context_size,
        ),
        (
            "vl",
            Vision.repo_id,
            Vision.filename,
            LlamaCppConfig.vl_context_size,
        ),
        (
            "embeddings",
            Embeddings.repo_id,
            Embeddings.filename,
            LlamaCppConfig.embeddings_context_size,
        ),
    ]

    # Collect model info
    models_info = []
    total_model_size = 0
    total_kv_cache = 0

    for alias, repo_id, filename, ctx_size in model_configs:
        if not repo_id or not filename:
            models_info.append(
                {
                    "alias": alias,
                    "repo_id": repo_id or "[dim]not configured[/dim]",
                    "filename": filename or "[dim]not configured[/dim]",
                    "size_mb": 0,
                    "ctx_size": ctx_size,
                    "kv_cache_mb": 0,
                    "downloaded": False,
                }
            )
            continue

        model_path = get_model_path(filename, models_dir)
        if model_path:
            size_mb = get_model_file_size(model_path)
            kv_cache_mb = estimate_kv_cache_mb(ctx_size, size_mb)
            total_model_size += size_mb
            total_kv_cache += kv_cache_mb
            models_info.append(
                {
                    "alias": alias,
                    "repo_id": repo_id,
                    "filename": filename,
                    "size_mb": size_mb,
                    "ctx_size": ctx_size,
                    "kv_cache_mb": kv_cache_mb,
                    "downloaded": True,
                }
            )
        else:
            models_info.append(
                {
                    "alias": alias,
                    "repo_id": repo_id,
                    "filename": filename,
                    "size_mb": 0,
                    "ctx_size": ctx_size,
                    "kv_cache_mb": 0,
                    "downloaded": False,
                }
            )

    # Build model requirements table
    model_table = Table(show_header=True, header_style="bold cyan")
    model_table.add_column(
        "Model",
        style="cyan",
    )
    model_table.add_column("Size", style="white", width=10)
    model_table.add_column("Context", style="yellow", width=8)
    model_table.add_column("KV Cache", style="magenta", width=10)
    model_table.add_column("Status", style="green", width=14)

    for info in models_info:
        if info["downloaded"]:
            size_str = f"{info['size_mb'] / 1024:.1f} GB"
            kv_str = f"~{info['kv_cache_mb']} MB"
            status = "[green]✓ Downloaded[/green]"
        elif info["size_mb"] == 0 and "not configured" in str(info["repo_id"]):
            size_str = "[dim]N/A[/dim]"
            kv_str = "[dim]N/A[/dim]"
            status = "[dim]Not configured[/dim]"
        else:
            size_str = "[dim]N/A[/dim]"
            kv_str = "[dim]N/A[/dim]"
            status = "[red]✗ Not downl.[/red]"

        model_table.add_row(
            f"{info['alias']} ({info['filename'][:30]}{'...' if len(info['filename']) > 30 else ''})",
            size_str,
            str(info["ctx_size"]),
            kv_str,
            status,
        )

    # Add totals row
    model_table.add_row()
    model_table.add_row(
        "[bold]Total Model Size (GPU VRAM):[/bold]",
        f"[bold]{total_model_size / 1024:.1f} GB[/bold]",
        "",
        "",
        "",
    )
    model_table.add_row(
        "[bold]Total KV Cache (RAM):[/bold]",
        "",
        "",
        f"[bold]~{total_kv_cache} MB[/bold]",
        "",
    )

    console.print(
        Panel(
            model_table,
            title="[bold]Model Memory Requirements[/bold]",
            border_style="cyan",
        )
    )

    # Hardware availability
    gpus = detect_gpus_with_details()
    total_ram_mb, avail_ram_mb = detect_system_ram()

    hw_table = Table(show_header=True, header_style="bold cyan")
    hw_table.add_column("Resource", style="cyan")
    hw_table.add_column("Total", style="white", width=12)
    hw_table.add_column("Available", style="green", width=12)
    hw_table.add_column("Required", style="yellow", width=12)
    hw_table.add_column("Status", style="bold", width=12)

    # GPU info
    if gpus:
        free_vram = get_free_vram_per_gpu()
        for i, gpu in enumerate(gpus):
            free_mb = free_vram[i] if i < len(free_vram) else 0
            fits = total_model_size <= free_mb
            status = "[green]✓ Fits[/green]" if fits else "[red]✗ Insufficient[/red]"
            hw_table.add_row(
                f"GPU {i}: {gpu.name}",
                f"{gpu.total_memory} MB",
                f"{free_mb} MB",
                f"{total_model_size} MB",
                status,
            )
    else:
        hw_table.add_row(
            "GPU",
            "[dim]N/A[/dim]",
            "[dim]N/A[/dim]",
            f"{total_model_size} MB",
            "[yellow]No GPU detected[/yellow]",
        )

    # RAM info
    if total_ram_mb > 0:
        fits = total_kv_cache <= avail_ram_mb * 0.5
        status = "[green]✓ Fits[/green]" if fits else "[yellow]⚠ Tight[/yellow]"
        hw_table.add_row(
            "System RAM",
            f"{total_ram_mb} MB",
            f"{avail_ram_mb} MB",
            f"~{total_kv_cache} MB",
            status,
        )
    else:
        hw_table.add_row(
            "System RAM",
            "[dim]N/A[/dim]",
            "[dim]N/A[/dim]",
            f"~{total_kv_cache} MB",
            "[dim]Unknown[/dim]",
        )

    console.print(
        Panel(
            hw_table,
            title="[bold]Hardware Availability[/bold]",
            border_style="cyan",
        )
    )

    # Tips
    if gpus and total_model_size > 0:
        free_vram = get_free_vram_per_gpu()
        total_free = sum(free_vram) if free_vram else 0
        if total_model_size <= total_free:
            console.print(
                "\n[green]💡 Tips:[/green]\n"
                "  • Models fit in GPU VRAM - all layers will be offloaded\n"
                "  • Use 'aria server start' to launch with current configuration\n"
            )
        else:
            console.print(
                "\n[yellow]💡 Tips:[/yellow]\n"
                "  • Models exceed available VRAM - consider smaller quantization\n"
                "  • Or split models across multiple GPUs\n"
                "  • Use 'aria server start' to launch with current configuration\n"
            )
    else:
        console.print(
            "\n[dim]💡 Tips:[/dim]\n"
            "  • Download models first: aria models download --model <chat|vl|embeddings>\n"
            "  • Use 'aria server start' to launch with current configuration\n"
        )
