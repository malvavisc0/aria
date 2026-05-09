# Model Memory Requirements

## Overview

When running LLM inference with vLLM, memory is primarily consumed by two components:

1. **Model weights** — Loaded into GPU VRAM for fast matrix operations
2. **KV cache** — Stored in GPU VRAM for attention computation during inference

Understanding these requirements is crucial for configuring context sizes and GPU memory utilization appropriately.

## Minimum Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| GPU VRAM | 8 GB    | 12+ GB      |
| System RAM | 16 GB  | 32+ GB      |

These requirements are validated during preflight checks. Systems below minimums will receive warnings but can still run.

## Memory Allocation

### GPU VRAM (Model Weights)

The model weights are loaded into GPU VRAM by vLLM. The required VRAM depends on the model size and quantization method:

| Model Type | Quantization | Typical VRAM |
|------------|-------------|-------------|
| 8B model   | GPTQ-INT4   | ~5 GB       |
| 8B model   | AWQ-INT4    | ~5 GB       |
| 8B model   | FP16        | ~16 GB      |
| 13B model  | GPTQ-INT4   | ~8 GB       |
| 13B model  | FP16        | ~26 GB      |

### GPU VRAM (KV Cache)

vLLM allocates a portion of GPU VRAM for the KV cache, which stores key-value pairs for all tokens in the context window. The `ARIA_VLLM_GPU_MEMORY_UTILIZATION` setting controls how much VRAM vLLM uses total (model weights + KV cache).

By default, Aria auto-calculates the optimal GPU memory utilization at launch based on detected VRAM, model size, and a 10% headroom:

| GPU VRAM | Auto-calculated Utilization | Headroom |
|----------|---------------------------|----------|
| 8 GB     | ~0.83                     | ~1.4 GB  |
| 12 GB    | ~0.86                     | ~1.7 GB  |
| 24 GB    | ~0.87                     | ~3.1 GB  |

## Default Context Sizes

Aria uses per-model context sizes configured via environment variables:

| Model    | Env Variable              | Default  |
|----------|---------------------------|----------|
| Chat     | `CHAT_CONTEXT_SIZE`       | 32768    |
| Embed    | `EMBEDDINGS_CONTEXT_SIZE` | 8192     |

### Rationale

**Chat model (32768 tokens):**
- Balances conversation length with VRAM usage
- 32K context with a GPTQ-INT4 8B model fits comfortably on 8 GB VRAM
- Can be increased to 49152+ on 12 GB+ GPUs

**Embeddings model (8192 tokens):**
- Loaded in-process via HuggingFace (not vLLM)
- 8K context allows embedding longer documents
- Runs on system RAM (~600 MB for a 311M model)

## vLLM Quantization

vLLM supports several quantization methods. Aria defaults to `gptq_marlin` for optimal performance on consumer GPUs:

| Quantization | Method | Quality | VRAM (8B) | Best For |
|-------------|--------|---------|-----------|----------|
| `gptq_marlin` | GPTQ INT4 | Excellent | ~5 GB | 8 GB VRAM (default) |
| `awq` | AWQ INT4 | Excellent | ~5 GB | Alternative to GPTQ |
| *(none)* | FP16 | Best | ~16 GB | 16+ GB VRAM |

Configure in `.env`:

```bash
ARIA_VLLM_QUANT = gptq_marlin    # Recommended for 8 GB GPUs
# ARIA_VLLM_QUANT = awq          # Alternative
# ARIA_VLLM_QUANT =              # Leave empty for FP16 (requires 16+ GB)
```

## KV Cache Data Type

vLLM supports FP8 KV cache, which halves the VRAM used by the KV cache at minimal quality cost. This is essential for 8 GB GPUs:

```bash
ARIA_VLLM_KV_CACHE_DTYPE = fp8   # Recommended for 8 GB GPUs
# ARIA_VLLM_KV_CACHE_DTYPE = auto  # Use model default (FP16)
```

## KV Cache RAM Offloading

When GPU VRAM is insufficient for the full KV cache (especially with large
context sizes or small GPUs), vLLM can offload KV cache blocks to system RAM.

### When to Use

- Your model weights fit in VRAM but the KV cache does not
- You need large context windows (>32K) on 8-12 GB GPUs
- You have abundant system RAM (32+ GB recommended)

### Configuration

```bash
ARIA_VLLM_KV_OFFLOAD_MODE = auto   # off | auto | ram
# ARIA_VLLM_KV_OFFLOADING_SIZE_GB = 8   # Override auto-calculated size (GiB)
# ARIA_VLLM_KV_OFFLOADING_BACKEND = native  # native | lmcache
```

| Mode | Behavior |
|------|----------|
| `off` | Default. GPU-only. Preflight warns if KV cache may not fit in VRAM. |
| `auto` | Aria calculates KV cache size from model architecture, and if VRAM is insufficient, automatically enables RAM offload. Preflight fails if RAM is also insufficient. |
| `ram` | Force RAM offload. Uses `ARIA_VLLM_KV_OFFLOADING_SIZE_GB` if set, otherwise auto-calculates. For testing or permanently constrained GPUs. |

### Expected Impact

- **Latency:** 10-30% slower for long contexts (CPU-GPU transfer overhead)
- **Throughput:** Minimal impact for short conversations
- **System RAM usage:** Equal to KV cache size + 2 GB headroom

### How It Works

1. Aria estimates KV cache size from model architecture (`config.json`)
2. In `auto` mode, if VRAM cannot hold model weights + KV cache, offload is enabled automatically
3. Preflight validates that system RAM is sufficient before starting
4. If RAM is also insufficient, preflight fails with a clear error

## Checking Memory Requirements

Use the CLI command to see current requirements:

```bash
aria models memory
```

This shows:
- Model sizes (GPU VRAM requirement)
- Available hardware resources
- Whether models fit in available memory

## Adjusting Context Sizes

Override defaults in your `.env` file:

```bash
# Larger context for long conversations (requires more VRAM)
CHAT_CONTEXT_SIZE=49152

# Smaller context to save VRAM
CHAT_CONTEXT_SIZE=16384
```

## Adjusting GPU Memory Utilization

Override the auto-calculated GPU memory utilization:

```bash
# Manual override (e.g., 85% of VRAM)
ARIA_VLLM_GPU_MEMORY_UTILIZATION=0.85

# Leave unset for auto-calculation
# ARIA_VLLM_GPU_MEMORY_UTILIZATION =
```

## Preflight Validation

The preflight checks validate memory requirements before starting the server:
- Validates minimum 8 GB GPU VRAM
- Validates minimum 16 GB system RAM
- Warns if models exceed available VRAM
- Auto-calculates optimal GPU memory utilization

These are non-blocking warnings — the server can still start, but performance may be impacted.

## Tensor Parallelism

For multi-GPU setups, vLLM supports tensor parallelism:

```bash
ARIA_VLLM_TP_SIZE = 1    # Single GPU (default)
# ARIA_VLLM_TP_SIZE = 2  # Split across 2 GPUs