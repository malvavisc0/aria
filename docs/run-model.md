# `run-model` — GPU-Optimized llama-server Launcher

**Location:** [`data/bin/run-model`](../data/bin/run-model)  
**Type:** Bash script (`#!/bin/bash`, `set -euo pipefail`)  
**Purpose:** Launch one or more `llama-server` processes with automatic GPU detection, KV cache tuning, flash attention, and dual-GPU configuration.

---

## Overview

`run-model` is the central launcher for all `llama-server` instances in Aria. It wraps `llama-server` (from [llama.cpp](https://github.com/ggml-org/llama.cpp)) with:

- **GGUF file validation** — magic number check, size check
- **NVIDIA GPU detection** — VRAM inventory, multi-GPU topology
- **Context size management** — power-of-2 enforcement, safe-context capping
- **Resource estimation** — KV cache size, VRAM headroom, RAM pressure warnings
- **Dual-GPU support** — NVLink detection, proportional tensor splitting
- **Two operating modes** — chat (default) and embedding
- **Signal handling** — graceful `SIGTERM`/`SIGINT` with `SIGKILL` fallback
- **Structured terminal output** — colored, boxed sections with key-value pairs

The script is invoked by the Python layer ([`src/aria/server/llama.py`](../src/aria/server/llama.py)) via `subprocess.Popen`, but can also be run directly from the command line.

---

## Usage

```bash
./run-model <model_path> [context_size] [options]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `model_path` | **Yes** | Path to the GGUF model file |
| `context_size` | No | Context window size in tokens (default: `8192`) |

### Options

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--port PORT` | `-p` | Port to run the server on | `8080` |
| `--n-gpu-layers N` | `-l` | Number of transformer layers to offload to GPU | `999` (all) |
| `--temp TEMP` | `-t` | Sampling temperature | `0.65` |
| `--top-p TOP_P` | | Top-p (nucleus) sampling value | `0.95` |
| `--mmproj PATH` | `-m` | Path to multimodal projector file (vision models) | — |
| `--embedding` | `-e` | Run in embedding mode (deterministic, no sampling) | off |
| `--parallel N` | | Parallel embedding requests (embedding mode only) | `4` |
| `--debug` | `-d` | Enable verbose server output to stdout | off |
| `--log-file FILE` | `-f` | Write server output to FILE | — |
| `--help` | `-h` | Show usage information | — |

### Examples

```bash
# Basic usage — default 8192 context
./run-model /data/models/llama-3.1-8b-q8_0.gguf

# Explicit context size
./run-model /data/models/llama-3.1-8b-q8_0.gguf 32768

# Custom port and debug output
./run-model /data/models/llama-3.1-8b-q8_0.gguf 32768 --port 8081 --debug

# Vision model with mmproj
./run-model /data/models/llava-1.6-q5_k_m.gguf 8192 --mmproj /data/models/llava-mmproj.gguf

# Embedding server
./run-model /data/models/nomic-embed-text-q8_0.gguf 4096 --embedding --port 7072

# Override via environment variables
PORT=8080 DEBUG=1 FLASH_ATTN=0 ./run-model /data/models/model.gguf 16384
```

---

## Environment Variables

All options can be set via environment variables. CLI flags take precedence over env vars.

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8080` | Server port |
| `N_GPU_LAYERS` | `999` | GPU layers to offload (999 = all) |
| `DEBUG` | `0` | Enable debug output (`1`/`0`) |
| `STRICT_POWER_OF_2` | `1` | Enforce power-of-2 context sizes (`1`/`0`) |
| `LOG_FILE` | _(empty)_ | Path to log file |
| `KV_CACHE_TYPE_K` | `q8_0` | KV cache quantization for keys |
| `KV_CACHE_TYPE_V` | `q8_0` | KV cache quantization for values |
| `TEMP` | `0.65` | Sampling temperature |
| `TOP_P` | `0.95` | Top-p sampling value |
| `FLASH_ATTN` | `1` | Enable flash attention (`1`/`0`) |
| `NO_MMAP` | `--no-mmap` | Disable memory mapping (set to `""` to enable mmap) |
| `MLOCK` | `--mlock` | Lock model in RAM (set to `""` to disable) |
| `CONT_BATCHING` | `--cont-batching` | Enable continuous batching (set to `""` to disable) |
| `NO_KV_OFFLOAD` | `--no-kv-offload` | Keep KV cache in RAM, not VRAM (set to `""` to offload to VRAM) |
| `LLAMA_SERVER_PATH` | `llama-server` | Path to the `llama-server` binary |
| `MMPROJ_PATH` | _(empty)_ | Path to mmproj file (vision models) |
| `EMBEDDING_MODE` | `0` | Run in embedding mode (`1`/`0`) |
| `EMBEDDING_PARALLEL` | `4` | Parallel embedding requests |

> **Note on flag-style variables:** `NO_MMAP`, `MLOCK`, `CONT_BATCHING`, and `NO_KV_OFFLOAD` hold the actual CLI flag string. To disable a feature, set the variable to an empty string (e.g. `NO_MMAP=""`). Setting to `0` or `false` will NOT disable them — the string `"0"` would be passed as a flag to `llama-server`.

---

## Execution Flow

```
main()
  ├── parse_args()          Parse CLI arguments
  ├── print_banner()        Display ASCII art header
  ├── validate_inputs()
  │     ├── validate_gguf_file()    Check file exists, size > 1MB, GGUF magic number
  │     ├── validate_context_size() Check non-negative integer, power-of-2 warning
  │     └── validate_port()         Check range 1–65535, check if port in use
  ├── detect_gpu()          Query nvidia-smi for GPU count and VRAM
  ├── calculate_max_safe_ctx()  Compute safe context cap from total VRAM
  ├── detect_system_ram()   Read total and available system RAM
  ├── extract_model_metadata()  Read GGUF header for architecture/quantization
  ├── get_performance_tips()    Print topology-aware recommendations
  ├── build_command()
  │     ├── Cap context to MAX_SAFE_CTX if needed
  │     ├── configure_dual_gpu()   NVLink detection, tensor split ratios
  │     ├── estimate_kv_cache_mb() Estimate KV cache RAM usage
  │     └── Assemble CMD_ARRAY
  └── launch_server()
        ├── init_logging()    Write startup info to LOG_FILE
        ├── Launch llama-server in background
        ├── Print "Server is running!" banner
        └── wait $SERVER_PID  (blocks until server exits)
```

---

## Startup Sequence Detail

### 1. GGUF Validation

Before any GPU queries, the script validates the model file:

1. **File existence** — `[[ -f "$model_path" ]]`
2. **Minimum size** — file must be > 1 MB (rejects symlinks to nothing, empty files)
3. **Magic number** — first 4 bytes must be `47 47 55 46` (`GGUF` in ASCII)

```bash
magic=$(head -c 4 "$model_path" | od -An -tx1 | tr -d ' \n')
# Expected: "47475546"
```

### 2. GPU Detection

Calls `nvidia-smi` to enumerate GPUs and measure VRAM:

```bash
GPU_COUNT=$(nvidia-smi -L | grep -c "GPU")
TOTAL_VRAM_MB=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | awk '{sum += $1} END {print sum}')
```

If `nvidia-smi` is not found or returns no GPUs, the script exits with an error. This script **requires NVIDIA GPU + drivers**.

### 3. Safe Context Calculation

`calculate_max_safe_ctx()` maps total VRAM to a conservative maximum context size:

| Total VRAM | Max Safe Context |
|-----------|-----------------|
| ≤ 8 GB | 8,192 |
| ≤ 12 GB | 16,384 |
| ≤ 16 GB | 32,768 |
| ≤ 24 GB | 65,536 |
| ≤ 32 GB | 262,144 |
| ≤ 48 GB | 524,288 |
| ≤ 96 GB | 1,048,576 |
| > 96 GB | 2,097,152 |

If the requested context exceeds `MAX_SAFE_CTX`, it is **capped** and alternatives are displayed with estimated KV cache sizes.

### 4. KV Cache Estimation

`estimate_kv_cache_mb()` uses an empirical formula to estimate KV cache RAM:

```
kv_cache_MB ≈ ctx_tokens × model_GB × kv_mult × 0.01
```

Where `kv_mult` depends on quantization:

| KV Type | Multiplier |
|---------|-----------|
| `f16` / `fp16` | 1.0 |
| `q8_0` (default) | 0.5 |
| `q5_0` / `q5_1` / `q5_k` | 0.35 |
| `q4_0` / `q4_1` / `q4_k` | 0.25 |

**Calibration examples:**
- 8B Q8_0 (~8 GB file), 128K ctx → ~4 GB KV cache
- 24B Q8_0 (~25 GB file), 262K ctx → ~32 GB KV cache
- 70B Q8_0 (~70 GB file), 32K ctx → ~10 GB KV cache

### 5. Dual-GPU Configuration

When exactly 2 GPUs are detected, `configure_dual_gpu()` checks for NVLink:

```bash
nvidia-smi topo -m | grep -q "NV"
```

**With NVLink:** Uses `--split-mode row` (tensor parallelism) with proportional `--tensor-split` based on free VRAM on each GPU:

```bash
ratio0 = free_vram_gpu0 / (free_vram_gpu0 + free_vram_gpu1)
ratio1 = free_vram_gpu1 / (free_vram_gpu0 + free_vram_gpu1)
```

**Without NVLink:** Uses `--split-mode layer` (layer parallelism, no tensor split).

**For 1 GPU or >2 GPUs:** No split mode is set; `llama-server` handles distribution automatically.

---

## Operating Modes

### Chat Mode (default)

Standard inference mode with sampling. Adds these flags to `llama-server`:

```
--temp <TEMP>
--top-p <TOP_P>
--cont-batching          (continuous batching for throughput)
--cache-type-k <K_TYPE>
--cache-type-v <V_TYPE>
--metrics                (Prometheus metrics endpoint)
--host 0.0.0.0
--port <PORT>
--no-kv-offload          (KV cache stays in RAM, not VRAM)
[--mmproj <PATH>]        (only if MMPROJ_PATH is set)
```

### Embedding Mode (`--embedding` / `EMBEDDING_MODE=1`)

Deterministic mode for generating text embeddings. Sampling parameters (`--temp`, `--top-p`) are omitted. Adds:

```
--embedding
--parallel <N>           (concurrent embedding requests)
--cache-type-k <K_TYPE>
--cache-type-v <V_TYPE>
--host 0.0.0.0
--port <PORT>
```

Note: `--no-kv-offload`, `--cont-batching`, and `--metrics` are **not** added in embedding mode.

---

## Common Flags Passed in Both Modes

```
<llama-server-binary>
--model <MODEL_PATH>
--n-gpu-layers <N>
--ctx-size <N_CTX>
[--split-mode row|layer]     (dual GPU only)
[--tensor-split R0,R1]       (NVLink dual GPU only)
[--flash-attn]               (when FLASH_ATTN=1)
[--no-mmap]                  (when NO_MMAP is set)
[--mlock]                    (when MLOCK is set)
--threads <cpu_count>        (logical CPU count, cross-platform)
```

---

## Signal Handling

The script registers three signal handlers:

| Signal | Handler |
|--------|---------|
| `EXIT` | `cleanup()` — sends `SIGTERM` to server, waits 2s, then `SIGKILL` if needed |
| `SIGINT` (Ctrl+C) | Logs "Received SIGINT", exits with code 130 (triggering `EXIT` trap) |
| `SIGTERM` | Logs "Received SIGTERM", exits with code 143 (triggering `EXIT` trap) |

The `cleanup()` function is idempotent — it checks `kill -0 $SERVER_PID` before sending signals, so it is safe to call even if the server has already exited.

---

## Python Integration

The script is invoked by [`src/aria/server/llama.py`](../src/aria/server/llama.py) via `LlamaCppServerManager`:

```python
RUN_MODEL_SCRIPT = DataConfig.path / "bin" / "run-model"

cmd = [
    str(self.RUN_MODEL_SCRIPT),
    str(model_path),
    str(context_size),
    "--port", str(port),
    # optionally: "--embedding", "--parallel", "4"
    # optionally: "--mmproj", str(mmproj_path)
]

env = os.environ.copy()
env["LLAMA_SERVER_PATH"] = str(LlamaCppConfig.bin_path / "llama-server")

proc = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
```

The manager then polls `http://<host>:<port>/health` every 0.5 seconds for up to 120 seconds to confirm the server is ready. If `run-model` exits within the first 2 seconds (indicating a validation failure), the manager reads stderr and raises a `RuntimeError` with the actual error message.

### Ports used by default

| Role | Port |
|------|------|
| Chat server | 7070 |
| Vision/Language server | 7071 |
| Embeddings server | 7072 |

---

## Context Size Guidelines

Context size should ideally be a power of 2 for optimal memory alignment. The script enforces this by default (`STRICT_POWER_OF_2=1`). To allow non-power-of-2 values:

```bash
STRICT_POWER_OF_2=0 ./run-model /path/to/model.gguf 12000
```

Common context sizes and their use cases:

| Context | Use Case |
|---------|----------|
| `4096` | Minimal, fast, low VRAM |
| `8192` | Default, good for most tasks |
| `16384` | Extended conversations |
| `32768` | Long documents, code analysis |
| `65536` | Very long context (requires ≥24 GB VRAM) |
| `131072` | 128K context (requires ≥32 GB VRAM) |

---

## KV Cache Quantization

The KV cache quantization type controls the memory/quality tradeoff for the attention cache:

| Type | Memory | Quality | Recommended For |
|------|--------|---------|-----------------|
| `f16` | 2× baseline | Best | High-VRAM systems, quality-critical |
| `q8_0` | 1× baseline (default) | Excellent | General use |
| `q5_k` | 0.7× baseline | Very good | Memory-constrained |
| `q4_k` | 0.5× baseline | Good | Low VRAM |

Set via environment variables:
```bash
KV_CACHE_TYPE_K=q4_k KV_CACHE_TYPE_V=q4_k ./run-model /path/to/model.gguf 65536
```

---

## Troubleshooting

### `nvidia-smi not found`
Install NVIDIA drivers. The script requires NVIDIA GPU + drivers. It does not support AMD, Intel, or Apple Silicon GPUs.

### `Port N is already in use`
Another process is listening on the port. Either stop it or use a different port:
```bash
./run-model /path/to/model.gguf --port 8081
```

### `Invalid GGUF file (missing GGUF magic number)`
The file is not a valid GGUF model. Check that the download completed successfully. GGUF files start with the bytes `47 47 55 46`.

### `llama-server not found at: ...`
The `LLAMA_SERVER_PATH` environment variable points to a non-existent or non-executable binary. Run `aria llamacpp install` to install the binaries, or set `LLAMA_SERVER_PATH` to the correct path.

### `failed to mlock` warnings in server output
The OS limits how much memory can be locked. Increase the limit:
```bash
ulimit -l unlimited
./run-model /path/to/model.gguf
```

### Context capped unexpectedly
The requested context exceeds the safe limit for your VRAM. The script will display alternatives. To override the cap (at your own risk):
```bash
# The cap is based on TOTAL_VRAM_MB; you cannot disable it directly,
# but you can reduce N_GPU_LAYERS to free VRAM for the KV cache:
N_GPU_LAYERS=32 ./run-model /path/to/model.gguf 131072
```

### Server exits immediately (when launched via Python)
Check the `RuntimeError` message from `LlamaCppServerManager` — it will include the stderr output from `run-model`, which contains the specific validation error (e.g. model file not found, port in use).

---

## Architecture Notes

- The script uses `set -euo pipefail` — any unhandled error causes immediate exit, which triggers the `EXIT` trap and graceful server shutdown.
- All user-facing output goes to **stderr** (`>&2`). Stdout is reserved for the server process itself (or redirected to `/dev/null` / a log file).
- The `CMD_ARRAY` pattern (bash array) is used for command construction to avoid word-splitting issues with paths containing spaces.
- Color output is automatically disabled when stderr is not a TTY (`[[ -t 2 ]]`), making the script safe for log capture.
- The `clear` call at startup is guarded with `[[ -t 1 ]]` to avoid clearing the terminal when launched non-interactively.
