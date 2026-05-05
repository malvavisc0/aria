"""vLLM installation and detection utilities.

This module provides functionality to install, detect, and query the
vLLM inference engine. It handles platform-specific installation
(CUDA, ROCm, CPU) by inspecting the system's GPU drivers.

Example:
    ```python
    from aria.scripts.vllm import detect_install_target, install_vllm

    target = detect_install_target()
    print(f"Install target: {target}")  # "cu124", "rocm6", or "cpu"

    install_vllm()  # pip install vllm with the detected target
    ```
"""

import importlib.metadata
import shutil
import subprocess
import sys

from loguru import logger
from rich.console import Console

console = Console(width=200)
error_console = Console(stderr=True, style="bold red", width=200)


def detect_install_target() -> str:
    """Detect the appropriate vLLM install target for this system.

    Priority:
        1. NVIDIA CUDA — detected via CUDA version from nvidia-smi
        2. AMD ROCm — detected via ``rocm-smi`` or ``/opt/rocm`` directory
        3. CPU fallback

    Returns:
        One of ``"cu126"``, ``"cu124"``, ``"cu121"``, ``"cu118"``,
        ``"rocm6"``, or ``"cpu"``.

    Example:
        ```python
        target = detect_install_target()
        # "cu126" on an NVIDIA system with CUDA 12.6+
        ```
    """
    # --- NVIDIA CUDA ---
    try:
        from aria.helpers.nvidia import get_cuda_version

        cuda_version = get_cuda_version()
        if cuda_version:
            major, minor = cuda_version.split(".")
            major, minor = int(major), int(minor)

            # Map CUDA version to the highest compatible PyTorch wheel target.
            # PyTorch provides wheels for cu118, cu121, cu124, cu126.
            # Drivers are backward-compatible: CUDA 13.x can run cu126 wheels.
            if major >= 13:
                target = "cu126"
            elif major == 12 and minor >= 6:
                target = "cu126"
            elif major == 12 and minor >= 4:
                target = "cu124"
            elif major == 12 and minor >= 1:
                target = "cu121"
            elif major == 11 and minor >= 8:
                target = "cu118"
            else:
                target = "cu126"  # Fallback to latest

            logger.info(f"CUDA {cuda_version} detected → {target} target")
            return target
    except Exception as exc:
        logger.debug(f"NVIDIA CUDA detection failed: {exc}")

    # --- AMD ROCm ---
    try:
        if shutil.which("rocm-smi") is not None:
            logger.info("rocm-smi found → rocm6 target")
            return "rocm6"
        from pathlib import Path

        if Path("/opt/rocm").is_dir():
            logger.info("/opt/rocm directory found → rocm6 target")
            return "rocm6"
    except Exception as exc:
        logger.debug(f"ROCm detection failed: {exc}")

    # --- CPU fallback ---
    logger.info("No GPU detected → cpu target")
    return "cpu"


def is_vllm_installed() -> bool:
    """Check whether vLLM is installed and importable.

    Returns:
        True if ``importlib.metadata.version("vllm")`` succeeds,
        False otherwise.

    Example:
        ```python
        if is_vllm_installed():
            print("vLLM is ready")
        ```
    """
    try:
        importlib.metadata.version("vllm")
        return True
    except importlib.metadata.PackageNotFoundError:
        return False


def get_vllm_version() -> str:
    """Return the installed vLLM version string.

    Returns:
        Version string (e.g. ``"0.20.0"``), or ``""`` if not installed.

    Example:
        ```python
        ver = get_vllm_version()
        if ver:
            print(f"vLLM {ver}")
        ```
    """
    try:
        return importlib.metadata.version("vllm")
    except importlib.metadata.PackageNotFoundError:
        return ""


def install_vllm(extra_index_url: str | None = None) -> None:
    """Install vLLM via pip with the appropriate hardware target.

    Automatically detects the install target (CUDA, ROCm, CPU) and
    runs ``pip install vllm`` with the matching ``--extra-index-url``.

    Args:
        extra_index_url: Override the PyTorch extra-index-url.
            When *None* (default), the URL is derived from
            :func:`detect_install_target`.

    Raises:
        subprocess.CalledProcessError: If pip exits with a non-zero code.

    Example:
        ```python
        install_vllm()  # auto-detect and install
        ```
    """
    target = detect_install_target()

    # Map target → extra-index-url for PyTorch wheels.
    # vLLM v0.20.0+ ships CUDA 13.0 wheels on PyPI by default,
    # so no extra-index-url is needed for CUDA 13+.
    if extra_index_url is None:
        extra_index_url = {
            "cu126": "https://download.pytorch.org/whl/cu126",
            "cu124": "https://download.pytorch.org/whl/cu124",
            "cu121": "https://download.pytorch.org/whl/cu121",
            "cu118": "https://download.pytorch.org/whl/cu118",
            "rocm6": "https://download.pytorch.org/whl/rocm6",
        }.get(target)

        # CUDA 13+ uses default PyPI wheels — no extra-index-url needed
        if target == "cu126" and extra_index_url:
            try:
                from aria.helpers.nvidia import get_cuda_version

                cv = get_cuda_version()
                if cv and int(cv.split(".")[0]) >= 13:
                    extra_index_url = None
            except Exception:
                pass  # keep cu126 extra-index-url as fallback

    # Use uv if available, fallback to pip
    if shutil.which("uv"):
        cmd = ["uv", "pip", "install", "vllm>=0.20.0"]
    else:
        cmd = [sys.executable, "-m", "pip", "install", "vllm>=0.20.0"]

    if extra_index_url:
        cmd.extend(["--extra-index-url", extra_index_url])

    logger.info(f"Installing vLLM (target={target}): {' '.join(cmd)}")
    console.print(
        f"[cyan]→[/cyan] Installing vLLM with target [bold]{target}[/bold]..."
    )

    try:
        subprocess.run(cmd, check=True)
        ver = get_vllm_version()
        console.print(f"[green]✓[/green] vLLM {ver} installed successfully")
    except subprocess.CalledProcessError as exc:
        error_console.print(
            f"[red]✗[/red] vLLM installation failed (exit {exc.returncode})"
        )
        raise
