# Model Memory Requirements

## Overview

When running LLM inference with llama.cpp, memory is primarily consumed by two components:

1. **Model weights** - Loaded into GPU VRAM for fast matrix operations
2. **KV cache** - Stored in GPU VRAM by default (can be moved to system RAM for low-VRAM GPUs)

Understanding these requirements is crucial for configuring context sizes appropriately.

## Minimum Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| GPU VRAM | 8 GB    | 12+ GB      |
| System RAM | 8 GB  | 16+ GB      |

These requirements are validated during preflight checks. Systems below minimums will receive warnings but can still run.

## Memory Allocation

### GPU VRAM (Model Weights)

The model weights are loaded into GPU VRAM when using `--n-gpu-layers 999`. The required VRAM is approximately equal to the model file size:

| Model Type | Typical Size | VRAM Required |
|------------|--------------|---------------|
| 4B Q8_0    | ~4.4 GB      | 4.4 GB        |
| 7B Q8_0    | ~7.5 GB      | 7.5 GB        |
| 13B Q8_0   | ~14 GB       | 14 GB         |
| 70B Q8_0   | ~70 GB       | 70 GB         |

### GPU VRAM (KV Cache)

The KV cache stores the key-value pairs for all tokens in the context window. By default, this is stored in **GPU VRAM** alongside the model weights for maximum inference speed. If VRAM is limited, you can move it to system RAM with `NO_KV_OFFLOAD="--no-kv-offload"` (see [KV Cache Placement](#kv-cache-placement) below).

**KV cache formula:**
```
kv_cache_mb ≈ context_size × model_size_gb × kv_mult × 0.01
```

Where `kv_mult` depends on KV cache quantization:
- `q8_0`: 0.5 (default, good balance)
- `q4_0`: 0.25 (smaller, slight quality loss)
- `f16`: 1.0 (full precision, largest)

## Default Context Sizes

Aria uses per-model context sizes configured via environment variables:

| Model    | Env Variable              | Default | KV Cache* |
|----------|---------------------------|---------|-----------|
| Chat     | `CHAT_CONTEXT_SIZE`       | 65536   | ~1.4 GB   |
| VL       | `VL_CONTEXT_SIZE`         | 8192    | ~6 MB     |
| Embed    | `EMBEDDINGS_CONTEXT_SIZE` | 8192    | ~24 MB    |

*Based on typical model sizes: Chat 4.4 GB, VL 0.2 GB, Embed 0.6 GB

### Rationale

**Chat model (65536 tokens):**
- Large context enables long conversations and document analysis
- 64K context with a 4B model uses ~1.4 GB VRAM for KV cache
- Combined with model weights (~4.4 GB), total VRAM ≈ 5.8 GB — fits comfortably on 8+ GB GPUs

**VL model (8192 tokens):**
- Vision models typically process single images
- 8K context is sufficient for image + conversation
- Minimal VRAM impact (~6 MB)

**Embeddings model (8192 tokens):**
- 8K context allows embedding longer documents
- Minimal VRAM impact (~24 MB)

## KV Cache Placement

By default, the KV cache is stored in **GPU VRAM** alongside the model weights. This maximizes inference speed by avoiding CPU↔GPU data transfers during attention computation.

If your GPU has limited VRAM (e.g., 8 GB), you can force the KV cache to system RAM by setting:

```bash
NO_KV_OFFLOAD="--no-kv-offload"
```

**Trade-offs of `--no-kv-offload` (KV cache on CPU):**

1. **Frees VRAM** - Useful when model weights barely fit in VRAM
2. **Slower inference** - Every attention step requires CPU↔GPU transfers, causing high CPU usage and many graph splits
3. **CPU-bound** - The CPU will run at 100% managing data transfers instead of the GPU doing all the work

For most setups with 12+ GB VRAM, keeping the KV cache on GPU (the default) is strongly recommended.

## Checking Memory Requirements

Use the CLI command to see current requirements:

```bash
aria models memory
```

This shows:
- Model sizes (GPU VRAM requirement)
- KV cache sizes (RAM requirement)
- Available hardware resources
- Whether models fit in available memory

## Adjusting Context Sizes

Override defaults in your `.env` file:

```bash
# Larger context for long conversations
CHAT_CONTEXT_SIZE=131072

# Smaller context to save RAM
CHAT_CONTEXT_SIZE=32768
```

## Preflight Validation

The preflight checks validate memory requirements before starting the server:
- Validates minimum 8 GB GPU VRAM
- Validates minimum 16 GB system RAM
- Warns if models exceed available VRAM
- Warns if KV cache exceeds 50% of available RAM

These are non-blocking warnings - the server can still start, but performance may be impacted.

## Quantization

The default quantization is **Q8_0**, which provides the best quality for GGUF models. For systems with limited VRAM, you can use smaller quantizations:

| Quantization | 4B Model | Quality | Use Case |
|--------------|----------|---------|----------|
| Q8_0         | ~4.4 GB  | Best    | Default, fits 8 GB VRAM |
| Q5_K_M       | ~3.0 GB  | Good    | Tight VRAM, better quality |
| Q4_K_M       | ~2.5 GB  | OK      | Very limited VRAM |

Override in your `.env` file:

```bash
CHAT_MODEL_TYPE=Q4_K_M
VL_MODEL_TYPE=Q4_K_M
EMBEDDINGS_MODEL_TYPE=Q4_K_M
```
