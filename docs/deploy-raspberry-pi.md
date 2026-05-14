# Deploy Aria on a Raspberry Pi with SearXNG

This guide walks through deploying Aria on a Raspberry Pi (ARM64) using Docker, with a local SearXNG instance for privacy-respecting web search and an optional Byparr proxy for bypassing search engine blocks.

## Table of Contents

- [Hardware Requirements](#hardware-requirements)
- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Directory Structure](#directory-structure)
- [Docker Compose](#docker-compose)
- [Docker Compose Environment](#docker-compose-environment)
- [SearXNG Configuration](#searxng-configuration)
- [Aria Environment](#aria-environment)
- [Deploy](#deploy)
- [Verify the Deployment](#verify-the-deployment)
- [Access Aria](#access-aria)
- [Running Without Docker](#running-without-docker)
- [Performance Tuning](#performance-tuning)
- [Upgrading](#upgrading)
- [Troubleshooting](#troubleshooting)

---

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **Board** | Raspberry Pi 4 (2 GB) | Raspberry Pi 4 (4 GB+) or Pi 5 |
| **Storage** | 16 GB microSD | 32 GB+ microSD or USB SSD |
| **Network** | Ethernet or Wi-Fi | Ethernet (for stability) |
| **OS** | 64-bit Raspberry Pi OS / Ubuntu / DietPi | Raspberry Pi OS Lite (64-bit) |

> **No GPU required.** The Pi ARM64 image connects to a remote LLM endpoint or runs in CPU-only mode. Local model inference on the Pi is not practical — you must point Aria at a remote vLLM, OpenAI-compatible, or OpenRouter API.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│                  Raspberry Pi (ARM64)                 │
│                                                      │
│  ┌──────────┐    ┌───────────┐    ┌───────────────┐  │
│  │  Aria    │───▶│  SearXNG  │    │   Byparr      │  │
│  │  :9876   │    │  :8080    │    │   :8191       │  │
│  └────┬─────┘    └───────────┘    └───────────────┘  │
│       │                                              │
└───────┼──────────────────────────────────────────────┘
        │
        ▼
  ┌───────────────┐
  │  Remote LLM   │   (GPU server, OpenRouter, etc.)
  │  Endpoint     │
  └───────────────┘
```

- **Aria** — the AI assistant (web UI on port 9876)
- **SearXNG** — self-hosted metasearch engine (port 8080, internal)
- **Byparr** — optional headless browser proxy to bypass CAPTCHA/rate-limit blocks

---

## Prerequisites

### 1. Install Docker and Docker Compose

On Raspberry Pi OS (64-bit) or Ubuntu:

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh

# Add your user to the docker group (avoids sudo for every command)
sudo usermod -aG docker $USER
newgrp docker

# Verify
docker --version
docker compose version
```

### 2. Create the directory structure

```bash
# Data directory (persistent storage for Aria and SearXNG)
mkdir -p /home/ubuntu/docker/data/aria/searxng

# Project directory (compose file and docker .env)
mkdir -p /home/ubuntu/docker/projects/aria
cd /home/ubuntu/docker/projects/aria
```

---

## Directory Structure

After deployment, the data directory will look like this:

```
/home/ubuntu/docker/data/aria/
├── .chainlit/          # Chainlit config (auto-created)
├── .files/             # Chainlit file storage (auto-created)
├── chainlit.md         # Chainlit welcome message (auto-created)
├── data/               # Aria runtime data (SQLite, ChromaDB, logs)
├── searxng/
│   └── settings.yml    # SearXNG configuration (you create this)
└── .env                # Aria configuration (you create this)
```

> **Note:** `.chainlit/`, `.files/`, `chainlit.md`, and `data/` are auto-created by Aria on first launch. You only need to create `searxng/settings.yml` and `.env`.

---

## Docker Compose

Create `docker-compose.yml` in the project directory (`/home/ubuntu/docker/projects/aria/`):

```yaml
services:
  searxng:
    image: searxng/searxng:latest
    container_name: searxng
    hostname: searxng
    volumes:
      - ${DATA_PATH}/aria/searxng/settings.yml:/etc/searxng/settings.yml
    environment:
      TZ: ${TZ:-Europe/Berlin}
    restart: unless-stopped

  byparr:
    image: ghcr.io/thephaseless/byparr:main
    container_name: byparr
    hostname: byparr
    environment:
      TZ: ${TZ:-Europe/Berlin}
    restart: unless-stopped

  aria:
    image: ghcr.io/malvavisc0/aria-ai-arm64:latest
    container_name: aria
    hostname: aria
    ports:
      - 9876:9876
    volumes:
      - ${DATA_PATH}/aria:/app
    environment:
      TZ: ${TZ:-Europe/Berlin}
    depends_on:
      - searxng
      - byparr
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:9876/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 300s   # 5 min grace for first-run model download
    restart: unless-stopped
```

> **Volume mapping:** `${DATA_PATH}/aria` is mounted as `/app` inside the container. Aria's `.env` file must live at `${DATA_PATH}/aria/.env` (which maps to `/app/.env`).

---

## Docker Compose Environment

Create a `.env` file in the **project directory** (`/home/ubuntu/docker/projects/aria/.env`). This file is used by Docker Compose for variable substitution:

```bash
TZ=Europe/Berlin
UID=1000
GID=1000
DATA_PATH=/home/ubuntu/docker/data
PROJECTS_PATH=/home/ubuntu/docker/projects
```

> **Tip:** Run `id` on the Pi to find your `UID` and `GID`.

---

## SearXNG Configuration

Create the SearXNG config file at `${DATA_PATH}/aria/searxng/settings.yml` (i.e., `/home/ubuntu/docker/data/aria/searxng/settings.yml`).

> **Important:** SearXNG refuses to start with the default `ultrasecretkey`. You must set a unique `secret_key` under `server:`. Generate one with:
>
> ```bash
> python3 -c "import secrets; print(secrets.token_hex(32))"
> ```

```yaml
use_default_settings: true

search:
  formats:
    - html
    - csv
    - json  # Required for agents to search

server:
  secret_key: "<your-generated-secret>"
  limiter: false      # Disable rate limiting on internal Docker network
  image_proxy: true
```

### Customizing SearXNG

You can edit `settings.yml` to:

- **Enable/disable search engines**: Add an `engines` section to cherry-pick which backends SearXNG queries
- **Set a default language**: Add `search.default_lang: en` under `search:`
- **Enable SafeSearch**: Change `safesearch` in Aria's tool calls (the config default is `0` = off)

Example with engine filtering:

```yaml
use_default_settings: true

search:
  formats:
    - html
    - json
  default_lang: en

server:
  secret_key: "<your-generated-secret>"
  limiter: false
  image_proxy: true

engines:
  - name: google
    disabled: false
  - name: duckduckgo
    disabled: false
  - name: wikipedia
    disabled: false
  - name: bing
    disabled: true
```

---

## Aria Environment

Create the Aria `.env` file at `${DATA_PATH}/aria/.env` (i.e., `/home/ubuntu/docker/data/aria/.env`). This file is read by Aria at runtime:

```bash
# ── Debug ───────────────────────────────────────────────────────────────────
DEBUG = false

# ── Aria home (must match the container volume mount) ───────────────────────
ARIA_HOME = /app

# ── Server ──────────────────────────────────────────────────────────────────
# Must bind to 0.0.0.0 inside the container (not a specific host IP)
SERVER_HOST = 0.0.0.0
SERVER_PORT = 9876

# ── Chainlit auth secret ────────────────────────────────────────────────────
# Generate with: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
CHAINLIT_AUTH_SECRET = <your-generated-secret>

# ── Agent loop safety ───────────────────────────────────────────────────────
MAX_ITERATIONS = 50
TOKEN_LIMIT_RATIO = 0.90

# ── LLM backend (remote — no GPU required) ──────────────────────────────────
CHAT_OPENAI_API = https://freellm.getalife.foundation/v1
CHAT_MODEL = auto
CHAT_CONTEXT_SIZE = 262144
ARIA_MAX_TOKENS = 8192
ARIA_VLLM_API_KEY = <your-api-key>
ARIA_VLLM_REMOTE = true

# ── Embeddings model (loaded in-process via HuggingFace) ────────────────────
# Use a lightweight model for Raspberry Pi to avoid OOM.
# all-MiniLM-L6-v2 (~90 MB) is fast and low-memory; for multilingual
# support use intfloat/multilingual-e5-small (~470 MB) instead.
EMBEDDINGS_MODEL = all-MiniLM-L6-v2
EMBED_MODEL_PATH = sentence-transformers/all-MiniLM-L6-v2
EMBEDDINGS_CONTEXT_SIZE = 512

# ── Database ────────────────────────────────────────────────────────────────
ARIA_DB_FILENAME = aria.db
CHROMADB_PERSISTENT_PATH = chromadb

# ── SearXNG & Byparr ───────────────────────────────────────────────────────
SEARXNG_URL = http://searxng:8080
BYPARR_API_URL = http://byparr:8191
```

### LLM Backend Options

The example above uses a free OpenAI-compatible endpoint. You can replace it with any of these:

**Option A — Free OpenAI-compatible API (as shown above):**

```bash
CHAT_OPENAI_API = https://freellm.getalife.foundation/v1
CHAT_MODEL = auto
ARIA_VLLM_API_KEY = <your-api-key>
ARIA_VLLM_REMOTE = true
```

**Option B — Remote vLLM server (self-hosted GPU machine):**

```bash
CHAT_OPENAI_API = http://YOUR-GPU-SERVER:9090/v1
CHAT_MODEL = <model-name>
ARIA_VLLM_API_KEY = sk-aria
ARIA_VLLM_REMOTE = true
```

**Option C — OpenRouter (cloud API):**

```bash
CHAT_OPENAI_API = https://openrouter.ai/api/v1
CHAT_MODEL = anthropic/claude-sonnet-4
CHAT_CONTEXT_SIZE = 131072
ARIA_VLLM_API_KEY = sk-or-YOUR-KEY
ARIA_VLLM_REMOTE = true
```

### Key Configuration Notes

| Variable | Description |
|----------|-------------|
| `ARIA_HOME = /app` | Must match the container volume mount path |
| `SERVER_HOST = 0.0.0.0` | Must bind to all interfaces inside Docker |
| `SEARXNG_URL = http://searxng:8080` | Uses Docker hostname `searxng` and SearXNG's internal port |
| `BYPARR_API_URL = http://byparr:8191` | Uses Docker hostname `byparr` |
| `ARIA_VLLM_REMOTE = true` | Required for remote LLM endpoints (no local GPU) |
| `TOKEN_LIMIT_RATIO = 0.90` | Fraction of context window for memory (0.90 = 90%) |
| `EMBEDDINGS_CONTEXT_SIZE = 4096` | Tokens moved to long-term vector memory per overflow cycle |

---

## Deploy

### Ensure files exist before starting

Docker cannot mount files that don't exist. Create them first:

```bash
# Create the SearXNG settings
mkdir -p /home/ubuntu/docker/data/aria/searxng
nano /home/ubuntu/docker/data/aria/searxng/settings.yml

# Create the Aria .env
nano /home/ubuntu/docker/data/aria/.env
```

### Pre-download the embedding model (recommended)

On the first launch Aria auto-downloads the embedding model from HuggingFace.
On a Raspberry Pi this can take several minutes and blocks the server from
starting.  Pre-downloading avoids startup timeouts and potential OOM issues:

```bash
cd /home/ubuntu/docker/projects/aria

docker compose run --rm aria aria models download --model embeddings
```

> **Tip:** The model is stored under `${DATA_PATH}/aria/models/` and persists
> across container restarts. You only need to run this once.

### Start all services

From the project directory:

```bash
cd /home/ubuntu/docker/projects/aria
docker compose up -d
```

This starts all three services: Aria, SearXNG, and Byparr. The `aria` service depends on `searxng` and `byparr`, so Docker Compose starts them automatically.

### What gets launched

| Container | Image | Port | Purpose |
|-----------|-------|------|---------|
| `aria` | `ghcr.io/malvavisc0/aria-ai-arm64:latest` | `9876` | Aria web UI |
| `searxng` | `searxng/searxng:latest` | `8080` (internal) | Metasearch engine |
| `byparr` | `ghcr.io/thephaseless/byparr:main` | `8191` (internal) | Browser proxy |

### Check status

```bash
# View running containers
docker compose ps

# Follow Aria logs
docker compose logs -f aria

# Follow SearXNG logs
docker compose logs -f searxng
```

---

## Verify the Deployment

### 1. Confirm Aria is healthy

```bash
curl -s http://localhost:9876/health
```

A `200 OK` response means the server is ready.

### 2. Run preflight checks (inside the container)

```bash
docker exec aria ax check preflight
```

---

## Access Aria

Open your browser and navigate to:

```
http://<pi-ip-address>:9876
```

### Create a user account

Aria requires authentication. On first launch, you need to create at least one user:

```bash
docker exec -it aria aria users add
```

You will be prompted to enter a username and password. Once created, use these credentials to log in at the web UI.

### Other user management commands

```bash
# List all users
docker exec aria aria users list

# Reset a user's password
docker exec -it aria aria users reset-password

# Update user details
docker exec -it aria aria users update

# Delete a user
docker exec -it aria aria users delete
```

---

## Running Without Docker

If you prefer to run Aria directly on the Pi (without Docker), you can install SearXNG separately and run Aria from uv.

### 1. Install SearXNG natively

Follow the [SearXNG installation docs](https://docs.searxng.org/dev/installation.html). The simplest method:

```bash
# Install dependencies
sudo apt-get install -y python3 git

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone SearXNG
git clone https://github.com/searxng/searxng.git ~/searxng
cd ~/searxng

# Create venv and install
uv venv
source .venv/bin/activate
uv pip install -e .

# Copy and edit the config
mkdir -p ~/.config/searxng
cp /path/to/settings.yml ~/.config/searxng/settings.yml

# Run SearXNG (binds to 0.0.0.0:8080)
python3 -m searx.webapp
```

### 2. Install Aria

```bash
uv tool install aria-ai
```

### 3. Configure `.env`

Point `SEARXNG_URL` at the local SearXNG instance:

```bash
SEARXNG_URL=http://localhost:8080
ARIA_VLLM_REMOTE=true
CHAT_OPENAI_API=http://YOUR-GPU-SERVER:9090/v1
ARIA_VLLM_API_KEY=sk-aria
```

### 4. Start Aria

```bash
aria server run
```

---

## Performance Tuning

### Raspberry Pi 4 (2–4 GB RAM)

- Use a lightweight LLM via the remote endpoint to minimize response latency
- Keep `MAX_ITERATIONS` at the default (50) or lower to prevent runaway tool loops
- Consider removing the `byparr` service from `docker-compose.yml` if search engines aren't blocking your requests (saves ~200 MB RAM)
- **Use a small embedding model.** The default `all-MiniLM-L6-v2` (~90 MB RAM) is chosen for Pi compatibility. Do **not** use `granite-embedding-311m` (~600 MB+ RAM) on boards with less than 4 GB

### Embedding model alternatives

| Model | Params | Download | RAM | Multilingual |
|-------|--------|----------|-----|--------------|
| `sentence-transformers/all-MiniLM-L6-v2` | 22 M | ~90 MB | ~100 MB | ❌ English |
| `intfloat/multilingual-e5-small` | 118 M | ~470 MB | ~500 MB | ✅ Yes |
| `BAAI/bge-small-en-v1.5` | 33 M | ~130 MB | ~150 MB | ❌ English |
| `ibm-granite/granite-embedding-311m-multilingual-r2` | 311 M | ~1.2 GB | ~600 MB | ✅ Yes |

To switch models, update both `EMBEDDINGS_MODEL` and `EMBED_MODEL_PATH` in
Aria's `.env`, then re-run the pre-download step.

### Raspberry Pi 5 (4–8 GB RAM)

- The Pi 5's faster CPU and I/O will noticeably improve SearXNG response times
- Use a USB SSD instead of a microSD card for better database and Docker performance

### Storage

Docker images consume ~1–2 GB total. Data (Aria's SQLite database, ChromaDB, logs) grows over time. Mount persistent volumes on fast storage:

```yaml
# In docker-compose.yml, the data volume is:
volumes:
  - ${DATA_PATH}/aria:/app
```

### Network

For best results, use a wired Ethernet connection. SearXNG makes outbound HTTP requests to multiple search engines — Wi-Fi latency compounds across backends.

### Reduce memory usage

If RAM is tight, limit Docker container memory:

```yaml
# Add to the aria service in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 1G
```

---

## Upgrading

### Docker Compose

```bash
cd /home/ubuntu/docker/projects/aria

# Pull latest images
docker compose pull

# Restart with new images
docker compose up -d

# Clean up old images
docker image prune -f
```

### Aria uv package (non-Docker)

```bash
uv tool upgrade aria-ai
```

### SearXNG (non-Docker)

```bash
cd ~/searxng
git pull
source .venv/bin/activate
uv pip install -e .
# Restart the service
```

---

## Troubleshooting

### SearXNG returns no results

1. Check SearXNG is running: `docker compose logs searxng`
2. Some engines block ARM64/datacenter IPs — edit `settings.yml` to disable problematic engines
3. If SearXNG shows CAPTCHA errors, ensure `BYPARR_API_URL=http://byparr:8191` is set in Aria's `.env`

### SearXNG fails to start with `ultrasecretkey` error

You must set a unique `secret_key` in `settings.yml`. See [SearXNG Configuration](#searxng-configuration).

### Aria can't reach SearXNG

The SearXNG URL must use the Docker hostname, not `localhost`:

```bash
# Correct (inside Docker network — matches hostname: searxng)
SEARXNG_URL = http://searxng:8080

# Wrong (would only work outside Docker)
SEARXNG_URL = http://localhost:8080
```

### Aria can't reach the remote LLM

1. Verify the endpoint from the Pi: `curl -H "Authorization: Bearer YOUR_KEY" http://YOUR-SERVER/v1/models`
2. Ensure `ARIA_VLLM_REMOTE = true` is set in Aria's `.env`
3. Check the Aria logs: `docker compose logs aria`

### Aria fails to bind on an address

If you see `could not bind on any address`, `SERVER_HOST` is set to a specific IP. Change it to:

```bash
SERVER_HOST = 0.0.0.0
```

Aria must bind to all interfaces inside the Docker container.

### Port 9876 is already in use

Change the port mapping in `docker-compose.yml`:

```yaml
ports:
  - 8080:9876
```

### Container restarts on boot

This is expected — all services use `restart: unless-stopped`. To prevent auto-restart:

```bash
docker compose stop
```

To disable permanently, remove `restart: unless-stopped` from the relevant service in `docker-compose.yml`.

### Out of memory

Monitor container memory usage:

```bash
docker stats --no-stream
```

If the Pi runs out of memory, consider:
- Switching to a smaller embedding model (see [Embedding model alternatives](#embedding-model-alternatives))
- Removing the Byparr service from `docker-compose.yml`
- Limiting Aria's memory allocation (see Performance Tuning)
- Using a Pi 5 with more RAM

### Embedding model download takes too long

The first startup auto-downloads the embedding model from HuggingFace. On slow
networks this can block for 10+ minutes, during which the `/health` endpoint is
unavailable. Pre-download the model before starting the stack:

```bash
docker compose run --rm aria aria models download --model embeddings
```