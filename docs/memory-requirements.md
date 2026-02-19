# Model Memory Requirements

## Overview

When running LLM inference with llama.cpp, memory is divided into two distinct pools:

1. **GPU VRAM** - Stores the model weights for fast inference
2. **System RAM** - Stores the KV cache for context

Understanding this separation is crucial for configuring context sizes appropriately.

## Minimum Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| GPU VRAM | 8 GB    | 12+ GB      |
| System RAM | 16 GB  | 32+ GB      |

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

### System RAM (KV Cache)

The KV cache stores the key-value pairs for all tokens in the context window. This is stored in **system RAM**, not GPU VRAM, when using the default `--no-kv-offload` setting in the run-model script.

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
- 64K context with a 4B model uses ~1.4 GB RAM
- This is ~2% of a 64 GB system, very reasonable

**VL model (8192 tokens):**
- Vision models typically process single images
- 8K context is sufficient for image + conversation
- Minimal RAM impact (~6 MB)

**Embeddings model (8192 tokens):**
- 8K context allows embedding longer documents
- Still minimal RAM impact (~24 MB)

## Why RAM for KV Cache?

The run-model script uses `--no-kv-offload` by default, which keeps the KV cache in system RAM rather than VRAM. This is intentional:

1. **VRAM is precious** - Model weights need it for fast inference
2. **RAM is abundant** - Most systems have 32-128 GB RAM vs 8-24 GB VRAM
3. **KV cache access is less frequent** - Only needed during generation, not matrix operations

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
