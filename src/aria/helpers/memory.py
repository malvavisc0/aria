"""Memory estimation utilities for model requirements.

Provides functions to estimate GPU VRAM and system RAM requirements
for running models with vLLM.
"""

import platform
import subprocess
from pathlib import Path

from loguru import logger


def get_model_file_size(model_path: Path) -> int:
    """Get total size of a model directory (or single file) in MB.

    For vLLM models stored as HuggingFace snapshots, this sums all files
    in the directory. For a single file, returns that file's size.

    Args:
        model_path: Path to the model directory or file.

    Returns:
        Size in MB, or 0 if path doesn't exist.
    """
    if not model_path.exists():
        return 0

    if model_path.is_file():
        return model_path.stat().st_size // (1024 * 1024)

    if model_path.is_dir():
        total = sum(f.stat().st_size for f in model_path.rglob("*") if f.is_file())
        return total // (1024 * 1024)

    return 0


def detect_system_ram() -> tuple[int, int]:
    """Get total and available system RAM in MB.

    Returns:
        Tuple of (total_ram_mb, available_ram_mb).
        Returns (0, 0) if detection fails.
    """
    system = platform.system()

    try:
        if system == "Darwin":
            # macOS
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True,
                text=True,
                check=True,
            )
            total_mb = int(result.stdout.strip()) // (1024 * 1024)

            # Get available memory from vm_stat
            page_size_result = subprocess.run(
                ["sysctl", "-n", "hw.pagesize"],
                capture_output=True,
                text=True,
                check=True,
            )
            page_size = int(page_size_result.stdout.strip())

            vm_stat = subprocess.run(
                ["vm_stat"],
                capture_output=True,
                text=True,
                check=True,
            )
            pages_free = 0
            pages_inactive = 0
            for line in vm_stat.stdout.split("\n"):
                if "Pages free" in line:
                    pages_free = int(line.split(":")[1].strip().rstrip("."))
                elif "Pages inactive" in line:
                    pages_inactive = int(line.split(":")[1].strip().rstrip("."))

            available_mb = (pages_free + pages_inactive) * page_size // (1024 * 1024)
            return total_mb, available_mb

        else:
            # Linux - read from /proc/meminfo
            with open("/proc/meminfo") as f:
                meminfo = f.read()

            total_mb = 0
            available_mb = 0
            for line in meminfo.split("\n"):
                if line.startswith("MemTotal:"):
                    total_mb = int(line.split()[1]) // 1024
                elif line.startswith("MemAvailable:"):
                    available_mb = int(line.split()[1]) // 1024

            return total_mb, available_mb

    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        ValueError,
        OSError,
    ) as e:
        logger.warning(f"Failed to detect system RAM: {e}")
        return 0, 0
