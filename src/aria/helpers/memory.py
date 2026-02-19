"""Memory estimation utilities for model requirements.

Provides functions to estimate GPU VRAM and system RAM requirements
for running GGUF models with llama.cpp.
"""

import platform
import subprocess
from pathlib import Path
from typing import Tuple

from loguru import logger


def get_model_file_size(model_path: Path) -> int:
    """Get model file size in MB.

    Args:
        model_path: Path to the GGUF model file.

    Returns:
        File size in MB, or 0 if file doesn't exist.
    """
    if not model_path.exists():
        return 0
    return model_path.stat().st_size // (1024 * 1024)


def detect_system_ram() -> Tuple[int, int]:
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
            with open("/proc/meminfo", "r") as f:
                meminfo = f.read()

            total_mb = 0
            available_mb = 0
            for line in meminfo.split("\n"):
                if line.startswith("MemTotal:"):
                    total_mb = int(line.split()[1]) // 1024
                elif line.startswith("MemAvailable:"):
                    available_mb = int(line.split()[1]) // 1024

            return total_mb, available_mb

    except (subprocess.CalledProcessError, FileNotFoundError, ValueError, OSError) as e:
        logger.warning(f"Failed to detect system RAM: {e}")
        return 0, 0


def estimate_kv_cache_mb(
    ctx_size: int, model_size_mb: int, kv_type: str = "q8_0"
) -> int:
    """Estimate KV cache size in MB for given context.

    Uses a heuristic based on model file size:
      - Model file size roughly correlates with parameter count
      - KV cache per token ≈ 2 × n_layers × n_kv_heads × head_dim × bytes_per_element
      - With q8_0 KV cache: ~1 byte per element (vs 2 bytes for f16)
      - Empirical formula: kv_cache_MB ≈ ctx_size × model_GB × kv_mult × 0.01

    Calibrated against known models:
      - 8B Q8_0 (~8GB file), 128K ctx → ~4 GB KV cache with q8_0
      - 24B Q8_0 (~25GB file), 262K ctx → ~32 GB KV cache with q8_0
      - 70B Q8_0 (~70GB file), 32K ctx → ~10 GB KV cache with q8_0

    Args:
        ctx_size: Context window size in tokens.
        model_size_mb: Model file size in MB.
        kv_type: KV cache quantization type (f16, q8_0, q5_0, q4_0).

    Returns:
        Estimated KV cache size in MB.
    """
    # KV quant multiplier: q8_0 ≈ 0.5x of f16, q4_0 ≈ 0.25x
    kv_mult = {
        "f16": 1.0,
        "fp16": 1.0,
        "q8_0": 0.5,
        "q5_0": 0.35,
        "q5_1": 0.35,
        "q5_k": 0.35,
        "q4_0": 0.25,
        "q4_1": 0.25,
        "q4_k": 0.25,
    }.get(kv_type.lower(), 0.5)

    # Model size in GB
    model_gb = model_size_mb / 1024

    # Empirical formula: kv_cache_MB ≈ ctx_tokens × model_GB × kv_mult × 0.01
    kv_cache_mb = int(ctx_size * model_gb * kv_mult * 0.01)

    return kv_cache_mb


def get_total_model_size_mb() -> int:
    """Get total size of all downloaded models in MB.

    Returns:
        Total size of chat, vl, and embeddings models in MB.
        Returns 0 if no models are downloaded.
    """
    import os

    from aria.config.api import LlamaCpp as LlamaCppConfig
    from aria.config.models import Chat, Embeddings, Vision
    from aria.scripts.gguf import get_model_path

    models_dir = LlamaCppConfig.models_path
    if not models_dir.exists():
        return 0

    model_configs = [
        Chat.filename,
        Vision.filename,
        Embeddings.filename,
    ]

    total_size = 0
    for filename in model_configs:
        if not filename:
            continue
        model_path = get_model_path(filename, models_dir)
        if model_path:
            total_size += get_model_file_size(model_path)

    return total_size


def get_total_kv_cache_mb() -> int:
    """Get total KV cache size for all models with their context sizes.

    Returns:
        Total estimated KV cache size in MB for all configured models.
    """
    from aria.config.api import LlamaCpp as LlamaCppConfig
    from aria.config.models import Chat, Embeddings, Vision
    from aria.scripts.gguf import get_model_path

    models_dir = LlamaCppConfig.models_path
    if not models_dir.exists():
        return 0

    model_configs = [
        (Chat.filename, LlamaCppConfig.chat_context_size),
        (Vision.filename, LlamaCppConfig.vl_context_size),
        (Embeddings.filename, LlamaCppConfig.embeddings_context_size),
    ]

    total_kv = 0
    for filename, ctx_size in model_configs:
        if not filename:
            continue
        model_path = get_model_path(filename, models_dir)
        if model_path:
            model_size_mb = get_model_file_size(model_path)
            total_kv += estimate_kv_cache_mb(ctx_size, model_size_mb)

    return total_kv
