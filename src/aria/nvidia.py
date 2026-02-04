import re
import subprocess
from typing import List, Optional, Tuple


def detect_gpu_count() -> int:
    """
    Execute nvidia-smi -L | wc -l via subprocess
    Return GPU count or 0 if nvidia-smi fails
    Handle subprocess errors gracefully
    """
    try:
        result = subprocess.run(
            ["nvidia-smi", "-L"], capture_output=True, text=True, check=True
        )
        # Filter empty lines to get accurate count
        lines = [
            line.strip()
            for line in result.stdout.strip().split("\n")
            if line.strip()
        ]
        return len(lines)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return 0


def get_total_vram_mb() -> int:
    """
    Execute nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits
    Parse output and sum all GPU VRAM values
    Return total VRAM in MiB
    """
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        # Filter empty lines before processing
        vram_values = [
            vram.strip()
            for vram in result.stdout.strip().split("\n")
            if vram.strip()
        ]
        total_vram = sum(int(vram) for vram in vram_values)
        return total_vram
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return 0


def check_gpu_memory_usage(gpu_index: int, usage_threshold: float) -> bool:
    """
    Check if current GPU memory usage is below the threshold.

    Args:
        gpu_index: Index of the GPU to check (0-based)
        usage_threshold: Memory usage threshold in percentage (0.0-100.0)

    Returns:
        bool: True if usage is below threshold, False otherwise
    """
    # Input validation
    if gpu_index < 0:
        return False
    if not (0.0 <= usage_threshold <= 100.0):
        return False

    try:
        # Query both memory.used and memory.total in a single call
        result = subprocess.run(
            [
                "nvidia-smi",
                f"--id={gpu_index}",
                "--query-gpu=memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        # Parse the output
        values = result.stdout.strip().split(",")
        if len(values) != 2:
            return False

        used_mb = int(values[0].strip())
        total_mb = int(values[1].strip())

        # Protect against division by zero
        if total_mb == 0:
            return False

        usage_percentage = (used_mb / total_mb) * 100
        return usage_percentage < usage_threshold

    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        ValueError,
        IndexError,
    ):
        return False


def get_free_vram_per_gpu() -> List[int]:
    """
    Execute nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits
    Return list of free VRAM per GPU in MiB
    Used for tensor split ratio calculation
    """
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.free",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        free_vram_values = [
            int(vram.strip())
            for vram in result.stdout.strip().split("\n")
            if vram.strip()
        ]
        return free_vram_values
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return []


def detect_nvlink() -> Tuple[bool, Optional[str]]:
    """
    Execute nvidia-smi topo -m
    Search for NVLink indicators (NV1-NV9 pattern)
    Return (has_nvlink, bond_type)
    """
    try:
        result = subprocess.run(
            ["nvidia-smi", "topo", "-m"],
            capture_output=True,
            text=True,
            check=True,
        )

        # Search for NVLink patterns in the output
        nvlink_pattern = re.compile(r"NV\d")
        bond_pattern = re.compile(r"Bonded")

        has_nvlink = bool(nvlink_pattern.search(result.stdout))
        bond_type = "Bonded" if bond_pattern.search(result.stdout) else None

        return (has_nvlink, bond_type)

    except (subprocess.CalledProcessError, FileNotFoundError):
        return (False, None)


def check_nvidia_smi_available() -> bool:
    """
    Check if nvidia-smi is available and executable.

    Returns:
        bool: True if nvidia-smi is available, False otherwise
    """
    try:
        subprocess.run(
            ["nvidia-smi", "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_nvidia_smi_version() -> str:
    """
    Get the nvidia-smi version.

    Returns:
        str: The nvidia-smi version string (e.g., "535.104.05")
             Returns empty string if version cannot be retrieved
    """
    try:
        result = subprocess.run(
            ["nvidia-smi", "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        # Use regex for more robust version parsing
        # Handles both "NVIDIA-SMI 535.104.05" and "NVIDIA-SMI version  : 590.48.01"
        match = re.search(
            r"NVIDIA-SMI\s+(?:version\s*:\s*)?(\d+\.\d+(?:\.\d+)?)",
            result.stdout,
        )
        return match.group(1) if match else ""
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""
