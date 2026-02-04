import re
import subprocess
from typing import List, Optional, Tuple

from pydantic import BaseModel


class GPUMetadata(BaseModel):
    """
    Pydantic model to store detailed information about a GPU.
    """

    index: int
    name: str
    uuid: str
    total_memory: int  # in MiB
    used_memory: int  # in MiB
    free_memory: int  # in MiB
    memory_utilization: float  # percentage
    power_limit: int  # in watts
    power_draw: int  # in watts
    temperature: int  # in Celsius
    fan_speed: int  # in percent
    driver_version: str
    display_active: bool
    compute_mode: str


def detect_gpus_with_details() -> List[GPUMetadata]:
    """
    Detect all installed NVIDIA GPUs with detailed information.

    Executes nvidia-smi query to gather comprehensive GPU information
    including memory, power, temperature, fan speed, and more.

    Returns:
        List[GPUMetadata]: A list of GPUMetadata objects, one for each detected GPU.
                          Returns empty list if nvidia-smi is unavailable or fails.

    Raises:
        None: All exceptions are caught and handled internally
    """
    try:
        # Query for comprehensive GPU information
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,uuid,memory.total,memory.used,memory.free,"
                "compute_mode,driver_version,power.limit,power.draw,temperature.gpu,"
                "fan.speed,display_active",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        gpus = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue

            # Split the CSV line and extract values
            values = [v.strip() for v in line.split(",")]

            # Validate we have enough values (13 expected)
            if len(values) < 13:
                continue

            # Parse memory values with validation
            try:
                total_mem = int(float(values[3])) if values[3] else 0
                used_mem = int(float(values[4])) if values[4] else 0
                free_mem = int(float(values[5])) if values[5] else 0
            except (ValueError, IndexError):
                continue

            # Calculate memory utilization percentage (rounded to 2 decimals)
            memory_util = (
                round((used_mem / total_mem * 100), 2)
                if total_mem > 0
                else 0.0
            )

            # Helper function to safely parse numeric values with unit suffixes
            def parse_numeric(
                value: str, suffixes: Optional[List[str]] = None
            ) -> int:
                """Parse numeric value, optionally removing unit suffixes."""
                if not value:
                    return 0
                try:
                    # Remove common suffixes if provided
                    cleaned = value
                    if suffixes:
                        for suffix in suffixes:
                            cleaned = cleaned.replace(suffix, "")
                    return int(float(cleaned))
                except (ValueError, AttributeError):
                    return 0

            # Parse power values (may have 'W' suffix)
            power_limit = parse_numeric(values[8], ["W", "w"])
            power_draw = parse_numeric(values[9], ["W", "w"])

            # Parse temperature (may have 'C' suffix)
            temperature = parse_numeric(values[10], ["C", "c"])

            # Parse fan speed (may have '%' suffix)
            fan_speed = parse_numeric(values[11], ["%"])

            # Parse display active (case-insensitive boolean)
            display_active_str = values[12].lower()
            display_active = display_active_str in [
                "enabled",
                "yes",
                "true",
                "1",
            ]

            gpu = GPUMetadata(
                index=int(values[0]),
                name=values[1],
                uuid=values[2],
                total_memory=total_mem,
                used_memory=used_mem,
                free_memory=free_mem,
                memory_utilization=memory_util,
                power_limit=power_limit,
                power_draw=power_draw,
                temperature=temperature,
                fan_speed=fan_speed,
                driver_version=values[7],
                display_active=display_active,
                compute_mode=values[6],
            )
            gpus.append(gpu)

        return gpus

    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        ValueError,
        IndexError,
    ):
        return []


def detect_gpu_count() -> int:
    """
    Detect the number of available GPUs on the system.

    Executes `nvidia-smi -L` via subprocess to list all GPUs and counts the
    non-empty lines in the output. Returns 0 if nvidia-smi is not available
    or fails to execute.

    Returns:
        int: Number of GPUs detected (0 if nvidia-smi fails or is unavailable)

    Raises:
        None: All exceptions are caught and handled internally
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
    Calculate the total VRAM across all available GPUs.

    Executes `nvidia-smi --query-gpu=memory.total` to query VRAM for each GPU,
    sums all values, and returns the total in MiB. Returns 0 if nvidia-smi
    is unavailable or parsing fails.

    Returns:
        int: Total VRAM across all GPUs in MiB (0 on failure)

    Raises:
        None: All exceptions are caught and handled internally
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
    Check if a specific GPU's memory usage is below a specified threshold.

    Args:
        gpu_index: Index of the GPU to check (0-based indexing)
        usage_threshold: Memory usage threshold in percentage (0.0-100.0)

    Returns:
        bool: True if GPU memory usage is below threshold, False otherwise.
              Returns False for invalid inputs or when nvidia-smi fails.

    Raises:
        None: All exceptions are caught and handled internally
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
    Get the free VRAM for each available GPU.

    Executes `nvidia-smi --query-gpu=memory.free` to query free memory for
    each GPU and returns a list of free VRAM values in MiB. Returns empty
    list if nvidia-smi is unavailable or parsing fails.

    Returns:
        List[int]: List of free VRAM values per GPU in MiB (empty list on failure)

    Raises:
        None: All exceptions are caught and handled internally
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
    Detect NVLink connectivity and bonding status between GPUs.

    Executes `nvidia-smi topo -m` to check GPU topology and searches for
    NVLink indicators (NV1-NV9 pattern) and bonded connections.

    Returns:
        Tuple[bool, Optional[str]]: A tuple containing:
            - bool: True if NVLink is detected, False otherwise
            - Optional[str]: "Bonded" if bonded connection found, None otherwise

    Raises:
        None: All exceptions are caught and handled internally
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
    Check if nvidia-smi is available and executable on the system.

    Executes `nvidia-smi --version` to verify availability. Returns True if
    nvidia-smi is found and executable, False otherwise.

    Returns:
        bool: True if nvidia-smi is available, False otherwise

    Raises:
        None: All exceptions are caught and handled internally
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
    Get the version of nvidia-smi installed on the system.

    Executes `nvidia-smi --version` and parses the version number using
    regex pattern matching. Returns empty string if version cannot be retrieved.

    Returns:
        str: The nvidia-smi version string (e.g., "535.104.05")
             Returns empty string if version cannot be retrieved

    Raises:
        None: All exceptions are caught and handled internally
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
