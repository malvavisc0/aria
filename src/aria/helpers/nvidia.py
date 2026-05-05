import re
import subprocess
from typing import List, Optional, Tuple

from loguru import logger
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


def detect_gpus_with_details(log_errors: bool = False) -> List[GPUMetadata]:
    """
    Detect all installed NVIDIA GPUs with detailed information.

    Executes nvidia-smi query to gather comprehensive GPU information
    including memory, power, temperature, fan speed, and more.

    Args:
        log_errors: If True, log warnings when nvidia-smi fails.

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
    ) as e:
        if log_errors:
            logger.warning(f"Failed to detect GPUs: {e}")
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


def get_cuda_version() -> str:
    """Get the CUDA version from nvidia-smi.

    Parses the CUDA version from ``nvidia-smi --version`` output.

    Returns:
        CUDA version string (e.g. ``"13.2"``, ``"12.4"``), or ``""``
        if unavailable.

    Example:
        ```python
        cuda = get_cuda_version()
        # "13.2"
        ```
    """
    try:
        result = subprocess.run(
            ["nvidia-smi", "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        match = re.search(r"CUDA Version\s*:\s*(\d+\.\d+)", result.stdout)
        return match.group(1) if match else ""
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


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


def calculate_max_safe_context(
    free_vram_mb: int, model_size_mb: int = 0, is_embedding_model: bool = False
) -> int:
    """
    Calculate the maximum safe context size (in tokens) for a language model or embedding
    model based on available VRAM, accounting for the model's memory requirements and
    applying a safety margin.

    The function uses tiered thresholds that provide appropriate context sizes for different
    VRAM capacities, with more conservative values for embedding models. It validates inputs
    to prevent errors and ensures at least a minimum context size is always available when
    possible. The function distinguishes between regular language models and embedding models
    through a boolean flag, providing optimized context sizes for each type of model.

    Process:
    1. Validates input parameters (type and value checks)
    2. Subtracts model size from free VRAM to get available memory
    3. Applies a 10% safety margin to available memory
    4. Checks if safe memory meets minimum tier threshold
    5. Selects appropriate tier based on safe memory
    6. Returns context size (enforcing minimum of 1024 tokens)

    Args:
        free_vram_mb: Currently free VRAM in megabytes (from get_free_vram_per_gpu)
        model_size_mb: Size of the model being loaded in megabytes (including embeddings)
        is_embedding_model: Whether this is an embedding model (default: False)

    Returns:
        Maximum safe context size in tokens (0 if VRAM is insufficient)

    Examples:
        >>> # LLM with 16GB free VRAM, no model loaded
        >>> calculate_max_safe_context(16384, 0, False)
        32768

        >>> # Embedding model with 8GB free VRAM
        >>> calculate_max_safe_context(8192, 0, True)
        1024

        >>> # LLM with 10GB free, 2GB model
        >>> calculate_max_safe_context(10240, 2048, False)
        16384
    """
    # Constants
    SAFETY_MARGIN = 0.10  # 10% safety margin for other operations
    MIN_CONTEXT = 1024  # Minimum context size in tokens

    # Embedding-specific thresholds (more conservative, more granular)
    # Format: (memory_threshold_gb, context_tokens)
    EMBEDDING_TIERS = [
        (2, 256),  # 2GB → 256 tokens
        (3, 384),  # 3GB → 384 tokens
        (4, 512),  # 4GB → 512 tokens
        (6, 768),  # 6GB → 768 tokens
        (8, 1024),  # 8GB → 1024 tokens
        (12, 1536),  # 12GB → 1536 tokens
        (16, 2048),  # 16GB → 2048 tokens
        (24, 3072),  # 24GB → 3072 tokens
        (32, 4096),  # 32GB+ → 4096 tokens (max for embeddings)
    ]

    # Regular LLM tiers (more granular)
    # Format: (memory_threshold_gb, context_tokens)
    LLM_TIERS = [
        (4, 2048),  # 4GB → 2,048 tokens
        (6, 4096),  # 6GB → 4,096 tokens
        (8, 8192),  # 8GB → 8,192 tokens
        (10, 12288),  # 10GB → 12,288 tokens
        (12, 16384),  # 12GB → 16,384 tokens
        (14, 24576),  # 14GB → 24,576 tokens
        (16, 32768),  # 16GB → 32,768 tokens
        (20, 49152),  # 20GB → 49,152 tokens
        (24, 65536),  # 24GB → 65,536 tokens
        (28, 131072),  # 28GB → 131,072 tokens
        (32, 262144),  # 32GB → 262,144 tokens
        (40, 393216),  # 40GB → 393,216 tokens
        (48, 524288),  # 48GB → 524,288 tokens
        (64, 786432),  # 64GB → 786,432 tokens
        (96, 1048576),  # 96GB → 1,048,576 tokens
        (128, 1572864),  # 128GB → 1,572,864 tokens
        (192, 2097152),  # 192GB+ → 2,097,152 tokens (max for LLMs)
    ]

    # Select appropriate tier list based on model type
    tiers = EMBEDDING_TIERS if is_embedding_model else LLM_TIERS

    # Absolute minimum memory threshold (below this, return 0)
    # This is lower than the first tier to allow the tier selection to work
    ABSOLUTE_MIN_GB = 1.5

    # Comprehensive input validation
    if not isinstance(free_vram_mb, int) or not isinstance(model_size_mb, int):
        return 0
    if free_vram_mb <= 0 or model_size_mb < 0:
        return 0
    if model_size_mb > 0 and free_vram_mb < model_size_mb:
        return 0

    # Calculate memory available after loading model
    available_after_model = free_vram_mb - model_size_mb

    # Apply safety margin
    safe_memory_mb = available_after_model * (1 - SAFETY_MARGIN)
    safe_memory_gb = safe_memory_mb / 1024

    # Check if we have enough for absolute minimum threshold
    if safe_memory_gb < ABSOLUTE_MIN_GB:
        return 0

    # Find the appropriate tier based on safe memory
    # Select the first tier where safe_memory_gb <= threshold
    context_size = MIN_CONTEXT
    for threshold_gb, tokens in tiers:
        if safe_memory_gb <= threshold_gb:
            context_size = tokens
            break
    else:
        # If no tier matched (memory exceeds all thresholds), use maximum tier
        context_size = tiers[-1][1]

    # Ensure we return at least the minimum context
    return max(MIN_CONTEXT, context_size)


def calculate_gpu_memory_utilization(
    total_vram_mb: int,
    model_path: str = "",
    context_size: int = 65536,
    kv_cache_dtype: str = "auto",
    safety_factor: float = 1.20,
    headroom_mb: int = 1024,
    vllm_overhead_mb: int = 512,
) -> float:
    """Calculate the optimal ``gpu_memory_utilization`` fraction for vLLM.

    Instead of using a percentage of total VRAM (which wastes memory on large
    GPUs), this function estimates the **actual memory needs** based on model
    weight size, KV cache requirements for the target context length, and
    fixed overhead.

    The formula is::

        kv_cache    = model_weights × (context_size / 32768) × kv_dtype_factor
        needed      = (model_weights + kv_cache + overhead + headroom) × safety
        utilization = needed / total_vram

    Where ``kv_dtype_factor`` is 0.5 for fp8 KV cache, 1.0 otherwise.

    This means a small model on a large GPU gets a low utilization (e.g. 0.45
    on a 33 GiB GPU with an 8B INT4 model at 128k context), instead of always
    reserving ~90 %.

    Args:
        total_vram_mb: Total GPU VRAM in MiB (from ``get_total_vram_mb()``).
        model_path: Local path to the model directory.  Used to estimate
            model weight size from disk.
        context_size: Target maximum sequence length (from
            ``CHAT_CONTEXT_SIZE``).  Directly scales KV cache estimate.
        kv_cache_dtype: KV cache data type (``"auto"``, ``"fp8"``, etc.).
            ``"fp8"`` halves the KV cache memory footprint.
        safety_factor: Multiplier for the total memory estimate to account
            for activation memory, fragmentation, and batch processing.
            Default ``1.20`` (20 % safety margin).
        headroom_mb: Fixed VRAM reserved for the OS, display, and thermal
            headroom.  Default 1024 MiB (1 GiB).
        vllm_overhead_mb: Fixed overhead for vLLM CUDA kernels, buffers,
            and scratch memory.  Default 512 MiB.

    Returns:
        Float in [0.50, 0.95] suitable for ``--gpu-memory-utilization``.
        Returns ``0.85`` as a safe fallback when inputs are insufficient.

    Example::

        >>> # 8 GB GPU, 8B INT4 model (~4 GiB), 128k context, fp8 KV
        >>> calculate_gpu_memory_utilization(8192, "/path/to/8b-int4", 131072, "fp8")
        0.90

        >>> # 33 GB GPU, same model
        >>> calculate_gpu_memory_utilization(34120, "/path/to/8b-int4", 131072, "fp8")
        0.50

        >>> # 33 GB GPU, 32k context
        >>> calculate_gpu_memory_utilization(34120, "/path/to/8b-int4", 32768, "fp8")
        0.50
    """
    from pathlib import Path

    from aria.helpers.memory import get_model_file_size

    MIN_UTILIZATION = 0.50
    MAX_UTILIZATION = 0.95
    FALLBACK = 0.85
    DEFAULT_MODEL_SIZE_MB = 4096  # Assume ~4 GiB if model path is unknown

    # Guard: if VRAM detection failed, return a safe fallback
    if total_vram_mb <= 0:
        logger.warning(
            "Cannot auto-calculate gpu_memory_utilization: "
            "VRAM detection returned 0. Using fallback={}.",
            FALLBACK,
        )
        return FALLBACK

    # --- Step 1: Estimate model weight size ---
    model_size_mb = 0
    if model_path:
        model_size_mb = get_model_file_size(Path(model_path))

    if model_size_mb <= 0:
        logger.info(
            "Model path '{path}' not found on disk; using default "
            "weight estimate of {default} MiB.",
            path=model_path or "(empty)",
            default=DEFAULT_MODEL_SIZE_MB,
        )
        model_size_mb = DEFAULT_MODEL_SIZE_MB

    # --- Step 2: Estimate KV cache size ---
    # Heuristic: KV cache scales linearly with context size and model size.
    #   fp8 KV:  half the footprint of auto/fp16
    #   Reference: 32k context baseline (factor = 1.0 at 32k)
    kv_dtype_factor = 0.5 if kv_cache_dtype == "fp8" else 1.0
    context_factor = context_size / 32768
    kv_cache_mb = int(model_size_mb * context_factor * kv_dtype_factor)

    # --- Step 3: Compute total memory needed ---
    raw_needed_mb = (
        model_size_mb + kv_cache_mb + vllm_overhead_mb + headroom_mb
    )
    needed_mb = int(raw_needed_mb * safety_factor)

    # --- Step 4: Calculate utilization ---
    utilization = needed_mb / total_vram_mb

    # Clamp to safe bounds
    utilization = max(
        MIN_UTILIZATION, min(MAX_UTILIZATION, round(utilization, 2))
    )

    # --- Step 5: Log the reasoning ---
    logger.info(
        "Auto-calculated gpu_memory_utilization={util:.2f}\n"
        "  VRAM total:        {vram:>8,} MiB\n"
        "  Model weights:     {model:>8,} MiB\n"
        "  KV cache estimate: {kv:>8,} MiB  "
        "(ctx={ctx:,}, dtype={kv_dtype}, factor={kv_factor})\n"
        "  vLLM overhead:     {over:>8,} MiB\n"
        "  Headroom:          {head:>8,} MiB\n"
        "  Raw needed:        {raw:>8,} MiB\n"
        "  With safety (×{sf}): {needed:>8,} MiB\n"
        "  → vLLM will use    {used:>8,} MiB ({pct:.0f}% of VRAM)",
        util=utilization,
        vram=total_vram_mb,
        model=model_size_mb,
        kv=kv_cache_mb,
        ctx=context_size,
        kv_dtype=kv_cache_dtype,
        kv_factor=kv_dtype_factor,
        over=vllm_overhead_mb,
        head=headroom_mb,
        raw=raw_needed_mb,
        sf=safety_factor,
        needed=needed_mb,
        used=int(total_vram_mb * utilization),
        pct=utilization * 100,
    )

    return utilization
