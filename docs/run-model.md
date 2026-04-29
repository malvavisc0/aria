# run-model — Hardware-Optimized llama-server Launcher

A powerful bash script that wraps `llama-server` (llama.cpp) with intelligent hardware detection, automatic resource estimation, and GPU optimization. Designed to run on **Linux (bash 4.0+)** and **macOS (with Homebrew bash 5.0+)**.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Arguments](#arguments)
  - [Options](#options)
  - [Environment Variables](#environment-variables)
- [Capabilities](#capabilities)
  - [Hardware Detection](#hardware-detection)
  - [Context Size Management](#context-size-management)
  - [Resource Estimation](#resource-estimation)
  - [Dual GPU Support](#dual-gpu-support)
  - [Multiple Modes](#multiple-modes)
- [Webapp / Programmatic Usage](#webapp--programmatic-usage)
  - [JSON Output](#json-output)
  - [Dry-Run Mode](#dry-run-mode)
  - [PID File](#pid-file)
- [Aria Integration](#aria-integration)
  - [Three-Server Architecture](#three-server-architecture)
  - [Python Integration Layer](#python-integration-layer)
  - [Environment Variable Translation](#environment-variable-translation)
- [Platform Support](#platform-support)
- [Examples](#examples)
- [Exit Codes](#exit-codes)
- [Signal Handling](#signal-handling)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Requirement | Linux | macOS |
|-------------|-------|-------|
| Shell | bash 4.0+ | bash 4.0+ (may need upgrade via `brew install bash`) |
| llama-server | In PATH or via `LLAMA_SERVER_PATH` | In PATH or via `LLAMA_SERVER_PATH` |
| Dependencies | `nvidia-smi` (GPU), `nproc`, `awk`, `od`, `strings` | `sysctl`, `system_profiler`, `vm_stat` |

> **macOS Note:** The default macOS bash is version 3.2. Install a newer version:
> ```bash
> brew install bash
> # Then run with: /opt/homebrew/bin/bash data/bin/run-model ... (Apple Silicon)
> # Or:              /usr/local/bin/bash data/bin/run-model ... (Intel)
> ```

---

## Quick Start

```bash
# Basic usage — launches llama-server with your model
./data/bin/run-model /path/to/model.gguf

# With custom context size and port
./data/bin/run-model /path/to/model.gguf 32768 --port 8081

# Debug mode — shows server output and full command
./data/bin/run-model /path/to/model.gguf --debug

# Use your full context size (bypass safety cap)
./data/bin/run-model /path/to/model.gguf 131072 --force-context
```

---

## Usage

```bash
./run-model <model_path> [context_size] [options]
```

### Arguments

| Argument | Description | Required |
|-----------|-------------|----------|
| `model_path` | Path to the GGUF model file | Yes |
| `context_size` | Context size in tokens (default: `8192`, must be power of 2 or `0` for auto) | No |

### Options

| Short | Long | Description |
|-------|------|-------------|
| `-p` | `--port PORT` | Port to run the server on (default: `8080`) |
| `-l` | `--n-gpu-layers N` | Number of model layers to offload to GPU (default: `999`, use `0` for CPU-only) |
| `-t` | `--temp TEMP` | Temperature for text generation (default: `0.65`) |
| — | `--top-p TOP_P` | Top-p sampling value (default: `0.95`) |
| `-m` | `--mmproj PATH` | Path to mmproj file for vision (multimodal) models |
| `-e` | `--embedding` | Run in embedding mode (deterministic, no sampling) |
| — | `--parallel N` | Number of parallel embedding requests (default: `4`, embedding mode only) |
| — | `--slots N` | Number of parallel slots for chat mode (default: `1`). Set >1 for concurrent requests |
| — | `--chat-template-file F` | Jinja2 chat template file for tool-calling models |
| — | `--force-context` | Bypass the safety cap on context size — use the exact value you specify |
| — | `--json` | Output structured JSON on stdout (for webapps and scripts) |
| — | `--dry-run` | Validate, compute, and show the command without launching the server |
| — | `--pid-file FILE` | Write the server PID to FILE after launch |
| `-d` | `--debug` | Enable debug output (shows server logs in terminal) |
| `-f` | `--log-file FILE` | Log server output to a file instead of terminal |
| `-h` | `--help` | Show help message and exit |

---

## Environment Variables

All options can be set via environment variables, enabling headless/automated usage:

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8080` | Server port |
| `N_GPU_LAYERS` | `999` | GPU offload layers (`0` = CPU-only) |
| `PLATFORM` | (auto-detect) | Force platform: `nvidia`, `metal`, or `cpu` |
| `DEBUG` | `0` | Enable debug mode (`1` or `0`) |
| `LOG_FILE` | (none) | Path to log file |
| `KV_CACHE_TYPE_K` | `q8_0` | KV cache quantization type for keys |
| `KV_CACHE_TYPE_V` | `q8_0` | KV cache quantization type for values |
| `TEMP` | `0.65` | Generation temperature |
| `TOP_P` | `0.95` | Top-p sampling |
| `FLASH_ATTN` | `1` | Enable flash attention (`1` or `0`) |
| `NO_MMAP` | `--no-mmap` | Disable memory mapping (set empty to enable mmap) |
| `MLOCK` | `--mlock` | Enable memory locking (set empty to disable) |
| `CONT_BATCHING` | `--cont-batching` | Enable continuous batching (set empty to disable) |
| `NO_KV_OFFLOAD` | `--no-kv-offload` | Keep KV cache in RAM instead of GPU (set empty to keep on GPU) |
| `LLAMA_SERVER_PATH` | `llama-server` | Path to llama-server binary |
| `MMPROJ_PATH` | (none) | Path to mmproj file for vision models |
| `EMBEDDING_MODE` | `0` | Embedding mode (`1` or `0`) |
| `EMBEDDING_PARALLEL` | `4` | Parallel embedding requests |
| `CHAT_PARALLEL` | `1` | Parallel slots for chat mode (concurrent requests) |
| `CHAT_TEMPLATE_FILE` | (none) | Path to Jinja2 chat template file |
| `STRICT_POWER_OF_2` | `1` | Enforce power-of-2 context sizes (`1` or `0`) |
| `FORCE_CONTEXT` | `0` | Bypass safety cap on context size (`1` or `0`) |
| `JSON_OUTPUT` | `0` | Output structured JSON on stdout (`1` or `0`) |
| `DRY_RUN` | `0` | Show command without launching (`1` or `0`) |
| `PID_FILE_PATH` | (none) | Write server PID to this file |

### Example with environment variables

```bash
PORT=8080 DEBUG=1 N_GPU_LAYERS=35 ./data/bin/run-model /path/to/model.gguf 16384
```

---

## Capabilities

### Hardware Detection

The script automatically detects your compute platform and optimizes accordingly:

1. **NVIDIA GPU** — Queries `nvidia-smi` for GPU count, VRAM, free memory, and NVLink topology
2. **Apple Metal** — Detects Apple Silicon via `sysctl` and `uname -m`, uses unified memory architecture
3. **CPU-only** — Falls back to CPU inference with automatic layer offloading disabled

#### Platform Override

Force a specific platform for testing:
```bash
PLATFORM=cpu ./data/bin/run-model /path/to/model.gguf    # Force CPU mode
PLATFORM=metal ./data/bin/run-model /path/to/model.gguf  # Force Metal mode
```

### Context Size Management

The script calculates a **safe maximum context size** based on available memory:

| Available Memory | Safe Max Context |
|-----------------|-----------------|
| ≤ 8 GB | 8,192 tokens |
| ≤ 12 GB | 16,384 tokens |
| ≤ 16 GB | 32,768 tokens |
| ≤ 24 GB | 65,536 tokens |
| ≤ 32 GB | 262,144 tokens |
| ≤ 48 GB | 524,288 tokens |
| ≤ 96 GB | 1,048,576 tokens |
| > 96 GB | 2,097,152 tokens |

If you request a context size exceeding the safe limit, the script will **by default**:
- Warn you about the overflow
- Show suggested alternatives with estimated KV cache sizes
- Automatically cap to the safe maximum

#### Bypassing the safety cap

If you know your hardware can handle it (e.g., you're using `--no-kv-offload=""` to keep KV cache on GPU, or using aggressive KV quantization), use `--force-context`:

```bash
# Honor the exact 131072 context size from your .env
./data/bin/run-model model.gguf 131072 --force-context

# Or via environment variable
FORCE_CONTEXT=1 ./data/bin/run-model model.gguf 131072
```

The safety calculation is purely VRAM-size-based and does **not** account for:
- Actual model file size (a 5 GB model has much more headroom than a 18 GB model)
- KV cache quantization type (q4_0 uses ¼ the cache of f16)
- Whether `--no-kv-offload` pushes KV cache to RAM
- Actual free VRAM at launch time

For this reason, `--force-context` is recommended when you've profiled your specific model + hardware combination.

> **Tip:** Context sizes should be powers of 2 for optimal performance. Set `STRICT_POWER_OF_2=0` to allow non-power-of-2 values.

### Resource Estimation

The script estimates and displays:

- **Model → VRAM:** Estimated VRAM usage (approximately equals model file size when fully offloaded)
- **KV Cache → RAM/VRAM:** Estimated KV cache memory based on context size, model size, and quantization type
- **System RAM:** Total and available system memory
- **VRAM pressure:** Warnings when the model exceeds free VRAM (triggers partial offloading)

#### KV Cache Estimation Formula

KV cache size is estimated using an empirical formula calibrated against real models:

```
kv_cache_MB = ctx_tokens × model_GB × kv_quant_multiplier × 0.01
```

Where `kv_quant_multiplier` depends on the cache type:

| KV Type | Multiplier |
|---------|-----------|
| f16 / fp16 | 1.0 |
| q8_0 | 0.5 |
| q5_0 / q5_1 / q5_k | 0.35 |
| q4_0 / q4_1 / q4_k | 0.25 |

### Dual GPU Support

For systems with **2 NVIDIA GPUs**, the script:

1. Detects NVLink connectivity via `nvidia-smi topo -m`
2. Queries free memory on each GPU
3. Calculates **proportional tensor split ratios** based on available VRAM
4. Configures row-split parallelism for NVLink or layer-split otherwise

Example output:
```
  ⚡  NVLink detected (NV01) — row-split tensor parallelism
     Tensor split: GPU0=0.6250  GPU1=0.3750
```

> For >2 GPUs, the script uses llama.cpp's default multi-GPU splitting.

### Multiple Modes

#### Chat Mode (default)

Text generation with sampling parameters. **By default, chat mode uses 1 parallel slot** (single concurrent request). Use `--slots N` for multi-user serving:

```bash
# Single user (default)
./data/bin/run-model model.gguf --temp 0.7 --top-p 0.9

# Multi-user: 4 concurrent requests
./data/bin/run-model model.gguf --slots 4 --temp 0.7
```

#### Embedding Mode
Deterministic embedding generation with parallel processing:
```bash
./data/bin/run-model embeddings.gguf --embedding --parallel 8 --port 7072
```

#### Vision Mode
For multimodal models with vision capabilities:
```bash
./data/bin/run-model llava-model.gguf --mmproj mmproj-model.q8_0.gguf
```

#### Tool-Calling Mode
For models using custom chat templates:
```bash
./data/bin/run-model tool-model.gguf --chat-template-file templates/llama-3.1-tools.jinja
```

---

## Webapp / Programmatic Usage

The script is designed to be callable from webapps and automation scripts. All diagnostic output goes to **stderr**, leaving stdout clean for structured data.

### JSON Output

Use `--json` to get a structured JSON object on **stdout** after launch:

```bash
./data/bin/run-model model.gguf 131072 --force-context --json 2>/dev/null
```

Output:
```json
{
  "pid": 12345,
  "port": 8080,
  "model": "/path/to/model.gguf",
  "platform": "nvidia",
  "context_size": 131072,
  "context_requested": 131072,
  "context_capped": false,
  "force_context": true,
  "max_safe_context": 65536,
  "vram_mb": 24576,
  "ram_total_mb": 65536,
  "ram_available_mb": 48000,
  "gpu_count": 1,
  "gpu_layers": 999,
  "flash_attn": true,
  "embedding_mode": false,
  "chat_parallel": 1,
  "kv_cache_type_k": "q8_0",
  "kv_cache_type_v": "q8_0",
  "command": "llama-server --model /path/to/model.gguf ..."
}
```

### Dry-Run Mode

Validate configuration and see the computed command without actually launching:

```bash
./data/bin/run-model model.gguf 32768 --dry-run
# Shows full command, resource estimates, then exits

# Combine with --json for programmatic validation
./data/bin/run-model model.gguf 32768 --dry-run --json 2>/dev/null
# JSON output has "pid": null in dry-run mode
```

### PID File

Write the server PID to a file for external process management:

```bash
./data/bin/run-model model.gguf --pid-file /var/run/aria/llama.pid
# External script can: kill $(cat /var/run/aria/llama.pid)
```

---

## Aria Integration

### Three-Server Architecture

Aria uses `run-model` to launch three llama-server instances:

| Server | Role | Default Port | Context Source |
|--------|------|-------------|---------------|
| **Chat** | Main LLM inference | `CHAT_OPENAI_API` port | `CHAT_CONTEXT_SIZE` |
| **Vision/Language** | VL model for images/PDFs | `VL_OPENAI_API` port | `VL_CONTEXT_SIZE` |
| **Embeddings** | Vector embeddings | `EMBEDDINGS_API_URL` port | `EMBEDDINGS_CONTEXT_SIZE` |

### Python Integration Layer

The `LlamaCppServerManager` class in `src/aria/server/llama.py` orchestrates all three servers:

```python
from aria.server.llama import LlamaCppServerManager

manager = LlamaCppServerManager()
manager.start_all()   # starts all three, waits for /health
# ... run Chainlit ...
manager.stop_all()    # graceful shutdown
```

The Python layer:
1. Reads context sizes from `.env` via `LlamaCppConfig` (`CHAT_CONTEXT_SIZE`, `VL_CONTEXT_SIZE`, `EMBEDDINGS_CONTEXT_SIZE`)
2. Resolves model file paths from the configured models directory
3. Builds the `run-model` command with appropriate flags
4. Sets `LLAMA_SERVER_PATH` to the bundled llama-server binary
5. Sets `LD_LIBRARY_PATH` / `DYLD_LIBRARY_PATH` for shared libraries
6. Polls `/health` on each server until ready (120s timeout)
7. Persists PIDs to `data/llama_servers.json`

### Environment Variable Translation

Some Aria `.env` variables are translated before reaching `run-model`:

| `.env` Variable | Python Translation | `run-model` Receives |
|----------------|-------------------|---------------------|
| `KV_CACHE_OFFLOAD=true` | `NO_KV_OFFLOAD="--no-kv-offload"` | KV cache in RAM |
| `KV_CACHE_OFFLOAD=false` | `NO_KV_OFFLOAD=""` | KV cache on GPU |
| `CHAT_TEMPLATE_FILE=path` | Passed as `--chat-template-file` to chat server only | Only chat server gets it |

> **Important:** `CHAT_TEMPLATE_FILE` is stripped from the environment by the Python layer to prevent it from leaking to VL or embedding servers. If you run `run-model` standalone with `CHAT_TEMPLATE_FILE` set in your environment, it will be applied to all modes.

---

## Platform Support

| Platform | GPU Detection | Features |
|----------|--------------|----------|
| **Linux + NVIDIA** | `nvidia-smi` | Full: multi-GPU, NVLink, VRAM monitoring, tensor splitting |
| **macOS (Apple Silicon)** | `sysctl` + `system_profiler` | Full: Metal acceleration, unified memory, 99 default GPU layers |
| **Linux CPU-only** | — | Full: auto thread detection, RAM-based context sizing |
| **macOS (Intel)** | — | Falls back to CPU-only mode |

---

## Examples

### Basic Usage

```bash
# Launch with defaults (8192 context, port 8080, all GPU layers)
./data/bin/run-model ~/models/llama-3.1-8b.q4_k_m.gguf

# Specify context size
./data/bin/run-model ~/models/llama-3.1-8b.q4_k_m.gguf 32768

# Debug mode with custom port
./data/bin/run-model ~/models/llama-3.1-8b.q4_k_m.gguf --debug --port 3000
```

### Honoring Your .env Context Size

```bash
# Your .env says CHAT_CONTEXT_SIZE=131072, but the safety cap
# would reduce it to 65536 on a 24GB GPU. Use --force-context:
./data/bin/run-model model.gguf 131072 --force-context

# Or from the Python layer, set FORCE_CONTEXT=1 in the environment
```

### GPU Optimization

```bash
# Force all layers to GPU (default)
./data/bin/run-model model.gguf -l 999

# Partial offload (e.g., for large models that don't fit)
./data/bin/run-model model.gguf -l 40

# CPU-only mode
./data/bin/run-model model.gguf -l 0
```

### Multi-User Chat

```bash
# 4 parallel slots for concurrent requests (webapp scenario)
./data/bin/run-model model.gguf --slots 4 --port 8080

# Or via environment variable
CHAT_PARALLEL=4 ./data/bin/run-model model.gguf
```

### Multi-GPU Setup

```bash
# Automatic tensor splitting (2 GPUs with NVLink)
./data/bin/run-model large-model.gguf

# Custom llama-server path
LLAMA_SERVER_PATH=/opt/llama.cpp/build/bin/llama-server \
  ./data/bin/run-model model.gguf
```

### Embedding Mode

```bash
# Run in embedding mode with 8 parallel requests
./data/bin/run-model all-minilm.gguf --embedding --parallel 8 --port 7072
```

### Production / Logging

```bash
# Log to file instead of terminal
./data/bin/run-model model.gguf -f /var/log/aria/llama-server.log

# Continuous batching with metrics (default in chat mode)
./data/bin/run-model model.gguf --port 8080 --temp 0.5
```

### Webapp Automation

```bash
# Validate configuration without launching (dry-run + JSON)
./data/bin/run-model model.gguf 131072 --force-context --dry-run --json 2>/dev/null

# Launch with JSON output and PID file for process management
./data/bin/run-model model.gguf 131072 --force-context \
  --json --pid-file /var/run/llama.pid \
  -f /var/log/llama.log 2>/dev/null
```

### macOS Homebrew bash

```bash
# Install newer bash
brew install bash

# Run with Homebrew bash
/opt/homebrew/bin/bash data/bin/run-model ~/models/model.gguf

# Or add to your PATH in ~/.zshrc
echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.zshrc
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success (server ran and exited, or dry-run completed) |
| `1` | Validation error (invalid model, port, context, missing binary, etc.) |
| `130` | Received SIGINT (Ctrl+C) |
| `143` | Received SIGTERM |

---

## Signal Handling

The script handles graceful shutdown on signals:

| Signal | Trigger | Behavior |
|--------|---------|----------|
| `SIGINT` | Ctrl+C | Calls `exit 130`, which triggers cleanup |
| `SIGTERM` | `kill <PID>` | Calls `exit 143`, which triggers cleanup |
| `EXIT` | Any exit | Sends SIGTERM to llama-server, waits 2 seconds, then SIGKILL if still running |

---

## Troubleshooting

### "llama-server not found"

Ensure llama-server is in your PATH or specify its location:

```bash
LLAMA_SERVER_PATH=/path/to/llama-server ./data/bin/run-model model.gguf
```

### "Context size exceeds safe limit"

The script caps the context to prevent OOM. Options:
- Accept the capped value (shown in output)
- Use `--force-context` to bypass the cap (when you know your hardware can handle it)
- Reduce the requested context size
- Free up memory before running

### "Model exceeds free VRAM"

The model will be partially offloaded to RAM (slower inference). Options:
- Use a smaller quantization (Q4_K_M instead of Q8_0)
- Reduce `--n-gpu-layers` to control offloading
- Reduce context size to free VRAM for KV cache

### "Port already in use"

Choose a different port:

```bash
./data/bin/run-model model.gguf --port 8081
```

### macOS bash version too old

```bash
brew install bash
# Run with the Homebrew version:
/opt/homebrew/bin/bash data/bin/run-model model.gguf
```

### GGUF validation fails

The file may not be a valid GGUF model:
- Verify the file is complete (re-download if necessary)
- Check that it's actually a GGUF file (not a safetensors or PyTorch checkpoint)

### 'failed to mlock' warnings

Increase locked memory limit:

```bash
ulimit -l unlimited
```

Or add to `/etc/security/limits.conf`:
```
* hard memlock unlimited
* soft memlock unlimited
```

### Chat mode only handles one request at a time

By default, chat mode uses `--parallel 1` (single slot). To serve multiple concurrent users:

```bash
./data/bin/run-model model.gguf --slots 4
```

---

## File Locations

| Item | Path |
|------|------|
| Script | `data/bin/run-model` |
| Documentation | `docs/run-model.md` |
| Default log location | `/var/log/aria/` (when using `--log-file`) |
| Server API | `http://0.0.0.0:<PORT>/v1/chat/completions` |
| PID state (Python) | `data/llama_servers.json` |
