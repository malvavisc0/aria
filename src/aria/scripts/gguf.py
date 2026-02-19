"""GGUF model download utilities for HuggingFace Hub.

This module provides functionality to download GGUF model files from
HuggingFace Hub repositories. It supports:
- Downloading by repo ID and quantization type (e.g. Q8_0, Q4_K_M)
- Checking whether a model is already downloaded
- Force re-downloading even if the file already exists
- Optional authentication token for gated/private models

Example:
    ```python
    from pathlib import Path
    from aria.scripts.gguf import download_gguf_model, is_model_downloaded

    models_dir = Path("data/models")

    # Check if already downloaded
    if not is_model_downloaded("janhq/Jan-v3-4B-base-instruct-gguf", "Q8_0", models_dir):
        download_gguf_model(
            repo_id="janhq/Jan-v3-4B-base-instruct-gguf",
            quantization="Q8_0",
            models_dir=models_dir,
        )

    # Force re-download
    download_gguf_model(
        repo_id="janhq/Jan-v3-4B-base-instruct-gguf",
        quantization="Q8_0",
        models_dir=models_dir,
        force=True,
    )
    ```
"""

import shutil
from pathlib import Path
from typing import Optional

from huggingface_hub import hf_hub_download, list_repo_files
from huggingface_hub.errors import EntryNotFoundError, RepositoryNotFoundError
from loguru import logger
from rich.console import Console

console = Console()
error_console = Console(stderr=True, style="bold red")


def _find_gguf_filename(
    repo_id: str,
    quantization: str,
    token: Optional[str] = None,
) -> str:
    """Find the GGUF filename in a HuggingFace repo matching the quantization type.

    Searches the repository file listing for a `.gguf` file whose name contains
    the quantization string (case-insensitive). Prefers exact matches over
    partial matches.

    Args:
        repo_id: HuggingFace repository ID (e.g. "janhq/Jan-v3-4B-base-instruct-gguf").
        quantization: Quantization type to look for (e.g. "Q8_0", "Q4_K_M").
        token: Optional HuggingFace API token for private/gated repos.

    Returns:
        The filename of the matching GGUF file.

    Raises:
        RepositoryNotFoundError: If the repository does not exist or is not accessible.
        FileNotFoundError: If no GGUF file matching the quantization is found.
    """
    logger.info(f"Listing files in repo: {repo_id}")
    try:
        files = list(list_repo_files(repo_id, token=token))
    except RepositoryNotFoundError as exc:
        logger.error(
            f"Repository '{repo_id}' not found. "
            "Check the repo ID and ensure HUGGINGFACE_TOKEN is set for private repos."
        )
        raise

    gguf_files = [f for f in files if f.endswith(".gguf")]
    logger.debug(f"Found {len(gguf_files)} GGUF files: {gguf_files}")

    if not gguf_files:
        raise FileNotFoundError(f"No .gguf files found in repository '{repo_id}'.")

    quant_upper = quantization.upper()

    # Prefer exact pattern match: filename contains the quantization string
    matches = [f for f in gguf_files if quant_upper in f.upper()]

    if not matches:
        available = ", ".join(gguf_files)
        raise FileNotFoundError(
            f"No GGUF file matching quantization '{quantization}' found in '{repo_id}'.\n"
            f"Available files: {available}"
        )

    if len(matches) > 1:
        logger.warning(
            f"Multiple GGUF files match '{quantization}': {matches}. "
            f"Using the first match: {matches[0]}"
        )

    return matches[0]


def get_model_path(
    repo_id: str,
    quantization: str,
    models_dir: Path,
) -> Optional[Path]:
    """Get the local path of a downloaded GGUF model file.

    Searches the models directory for a file whose name contains both the
    repository name (last segment of repo_id) and the quantization string.

    Args:
        repo_id: HuggingFace repository ID (e.g. "janhq/Jan-v3-4B-base-instruct-gguf").
        quantization: Quantization type (e.g. "Q8_0").
        models_dir: Directory where models are stored.

    Returns:
        Path to the model file if found, None otherwise.
    """
    if not models_dir.exists():
        return None

    quant_upper = quantization.upper()
    repo_name = repo_id.split("/")[-1].lower()
    # Search for any .gguf file in the models_dir that matches both the
    # quantization string and the repository name segment.
    for f in models_dir.glob("*.gguf"):
        if quant_upper in f.name.upper() and repo_name in f.name.lower():
            return f

    return None


def is_model_downloaded(
    repo_id: str,
    quantization: str,
    models_dir: Path,
) -> bool:
    """Check whether a GGUF model file is already downloaded.

    Args:
        repo_id: HuggingFace repository ID.
        quantization: Quantization type (e.g. "Q8_0").
        models_dir: Directory where models are stored.

    Returns:
        True if a matching model file exists in models_dir, False otherwise.
    """
    if not models_dir.exists():
        return False

    quant_upper = quantization.upper()
    for f in models_dir.glob("*.gguf"):
        if quant_upper in f.name.upper():
            logger.debug(f"Found existing model file: {f}")
            return True

    return False


def download_gguf_model(
    repo_id: str,
    quantization: str,
    models_dir: Path,
    token: Optional[str] = None,
    force: bool = False,
) -> Path | None:
    """Download a GGUF model file from HuggingFace Hub.

    Downloads the GGUF file matching the given quantization type from the
    specified HuggingFace repository. If the model is already downloaded,
    skips the download unless ``force=True``.

    The downloaded file is placed directly in ``models_dir`` (not in a
    HuggingFace cache subdirectory).

    Args:
        repo_id: HuggingFace repository ID (e.g. "janhq/Jan-v3-4B-base-instruct-gguf").
        quantization: Quantization type to download (e.g. "Q8_0", "Q4_K_M").
        models_dir: Directory where the model file will be saved.
        token: Optional HuggingFace API token. Required for gated/private models.
        force: If True, re-download even if the file already exists.

    Returns:
        Path to the downloaded model file.

    Raises:
        RepositoryNotFoundError: If the repository does not exist or is inaccessible.
        FileNotFoundError: If no GGUF file matching the quantization is found.
        RuntimeError: If the download fails.
    """
    models_dir.mkdir(parents=True, exist_ok=True)

    # Check if already downloaded
    if not force and is_model_downloaded(repo_id, quantization, models_dir):
        existing = get_model_path(repo_id, quantization, models_dir)
        console.print(
            f"[green]✓[/green] Model already downloaded: [dim]{existing}[/dim]"
        )
        console.print("[dim]Use --force to re-download.[/dim]")
        return existing

    # Find the filename in the repo
    console.print(f"[cyan]→[/cyan] Looking up files in [bold]{repo_id}[/bold]...")
    filename = _find_gguf_filename(repo_id, quantization, token=token)
    logger.info(f"Resolved filename: {filename}")

    console.print(
        f"[cyan]→[/cyan] Downloading [bold]{filename}[/bold] "
        f"from [bold]{repo_id}[/bold]..."
    )

    if token:
        logger.debug("Using HuggingFace token for authentication")
    else:
        logger.debug("No HuggingFace token provided (public model)")

    try:
        # hf_hub_download downloads to HF cache; we then copy to models_dir
        cached_path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            token=token,
            local_dir=str(models_dir),
        )
        cached_path = Path(cached_path)
        logger.info(f"Downloaded to: {cached_path}")

        # If hf_hub_download placed it in a subdirectory, move it to models_dir root
        dest_path = models_dir / cached_path.name
        if cached_path != dest_path and cached_path.exists():
            shutil.move(str(cached_path), str(dest_path))
            logger.info(f"Moved to: {dest_path}")
        else:
            dest_path = cached_path

        console.print(
            f"[green]✓[/green] Model downloaded successfully!\n"
            f"  [dim]Location: {dest_path}[/dim]"
        )
        return dest_path

    except EntryNotFoundError:
        raise FileNotFoundError(
            f"File '{filename}' not found in repository '{repo_id}'."
        )
    except Exception as e:
        error_console.print(f"[red]Download failed: {e}[/red]")
        raise RuntimeError(
            f"Failed to download GGUF model from '{repo_id}': {e}"
        ) from e
