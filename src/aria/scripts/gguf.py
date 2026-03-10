"""GGUF model download utilities for HuggingFace Hub.

This module provides functionality to download GGUF model files from
HuggingFace Hub repositories. It supports:
- Downloading by repo ID and exact filename
- Checking whether a model is already downloaded
- Force re-downloading even if the file already exists
- Optional authentication token for gated/private models

Example:
    ```python
    from pathlib import Path
    from aria.scripts.gguf import download_gguf_model, is_model_downloaded

    models_dir = Path("data/models")

    # Check if already downloaded
    if not is_model_downloaded("granite-docling-258M-Q8_0.gguf", models_dir):
        download_gguf_model(
            repo_id="ggml-org/granite-docling-258M-GGUF",
            filename="granite-docling-258M-Q8_0.gguf",
            models_dir=models_dir,
        )

    # Force re-download
    download_gguf_model(
        repo_id="ggml-org/granite-docling-258M-GGUF",
        filename="granite-docling-258M-Q8_0.gguf",
        models_dir=models_dir,
        force=True,
    )
    ```
"""

from pathlib import Path
from typing import Optional

from huggingface_hub import hf_hub_download
from huggingface_hub.errors import EntryNotFoundError, RepositoryNotFoundError
from loguru import logger
from rich.console import Console

console = Console(width=200)
error_console = Console(stderr=True, style="bold red", width=200)


def get_model_path(
    filename: str,
    models_dir: Path,
) -> Optional[Path]:
    """Get the local path of a downloaded GGUF model file.

    Args:
        filename: Exact filename to look for (e.g. "granite-docling-258M-Q8_0.gguf").
        models_dir: Directory where models are stored.

    Returns:
        Path to the model file if found, None otherwise.
    """
    if not models_dir.exists():
        return None

    path = models_dir / filename
    return path if path.exists() else None


def is_model_downloaded(
    filename: str,
    models_dir: Path,
) -> bool:
    """Check whether a GGUF model file is already downloaded.

    Args:
        filename: Exact filename to check for.
        models_dir: Directory where models are stored.

    Returns:
        True if the file exists in models_dir, False otherwise.
    """
    return get_model_path(filename, models_dir) is not None


def download_gguf_model(
    repo_id: str,
    filename: str,
    models_dir: Path,
    token: Optional[str] = None,
    force: bool = False,
) -> Path:
    """Download a GGUF model file from HuggingFace Hub.

    Downloads the specified GGUF file from the HuggingFace repository.
    If the model is already downloaded, skips the download unless ``force=True``.

    The downloaded file is placed directly in ``models_dir`` (not in a
    HuggingFace cache subdirectory).

    Args:
        repo_id: HuggingFace repository ID (e.g. "ggml-org/granite-docling-258M-GGUF").
        filename: Exact filename to download (e.g. "granite-docling-258M-Q8_0.gguf").
        models_dir: Directory where the model file will be saved.
        token: Optional HuggingFace API token. Required for gated/private models.
        force: If True, re-download even if the file already exists.

    Returns:
        Path to the downloaded model file.

    Raises:
        RepositoryNotFoundError: If the repository does not exist or is inaccessible.
        FileNotFoundError: If the file is not found in the repository.
        RuntimeError: If the download fails.
    """
    models_dir.mkdir(parents=True, exist_ok=True)

    # Check if already downloaded
    if not force and is_model_downloaded(filename, models_dir):
        existing = get_model_path(filename, models_dir)
        assert existing is not None  # We just checked it exists
        console.print(
            f"[green]✓[/green] Model already downloaded: [dim]{existing}[/dim]"
        )
        console.print("[dim]Use --force to re-download.[/dim]")
        return existing

    console.print(
        f"[cyan]→[/cyan] Downloading [bold]{filename}[/bold] "
        f"from [bold]{repo_id}[/bold]..."
    )

    if token:
        logger.debug("Using HuggingFace token for authentication")
    else:
        logger.debug("No HuggingFace token provided (public model)")

    try:
        # hf_hub_download with local_dir places the file directly in models_dir.
        # force_download mirrors the caller's force flag so HF's own cache logic
        # also re-downloads when requested.
        dest_path = Path(
            hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                token=token,
                local_dir=str(models_dir),
                force_download=force,
            )
        )
        logger.info(f"Downloaded to: {dest_path}")

        console.print(
            f"[green]✓[/green] Model downloaded successfully!\n"
            f"  [dim]Location: {dest_path}[/dim]"
        )
        return dest_path

    except EntryNotFoundError:
        raise FileNotFoundError(
            f"File '{filename}' not found in repository '{repo_id}'."
        )
    except RepositoryNotFoundError:
        logger.error(
            f"Repository '{repo_id}' not found. "
            "Check the repo ID and ensure HUGGINGFACE_TOKEN is set for private repos."
        )
        raise
    except Exception as e:
        error_console.print(f"[red]Download failed: {e}[/red]")
        raise RuntimeError(
            f"Failed to download GGUF model from '{repo_id}': {e}"
        ) from e
