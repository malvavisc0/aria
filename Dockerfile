# ─────────────────────────────────────────────────────────────────────────────
# Dockerfile — Aria + vLLM serving stack
#
# Build variants:
#   CUDA/CPU:  docker build --build-arg BASE_IMAGE=vllm/vllm-openai:latest -t aria .
#   ROCm:      docker build --build-arg BASE_IMAGE=vllm/vllm-openai-rocm:latest -t aria-rocm .
#
# Run:
#   docker run -p 8000:8000 -v ./data:/app/data ghcr.io/malvavisc0/aria:latest
# ─────────────────────────────────────────────────────────────────────────────

ARG BASE_IMAGE=vllm/vllm-openai:latest
FROM ${BASE_IMAGE}

LABEL org.opencontainers.image.source="https://github.com/malvavisc0/aria"
LABEL org.opencontainers.image.description="Aria — AI Assistant with web UI and local LLM support"
LABEL org.opencontainers.image.licenses="MIT"

# ── Install Aria ──────────────────────────────────────────────────────────────
RUN pip install --no-cache-dir aria

# ── Create data directory for persistent storage ──────────────────────────────
RUN mkdir -p /app/data
WORKDIR /app

# ── Expose Chainlit web UI port ───────────────────────────────────────────────
EXPOSE 8000

# ── Entrypoint ────────────────────────────────────────────────────────────────
ENTRYPOINT ["aria", "server", "run"]