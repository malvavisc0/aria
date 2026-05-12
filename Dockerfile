# ─────────────────────────────────────────────────────────────────────────────
# Dockerfile — Aria + vLLM serving stack
#
# Build variants:
#   CUDA/CPU:  docker build --build-arg BASE_IMAGE=vllm/vllm-openai:latest -t aria .
#   ROCm:      docker build --build-arg BASE_IMAGE=vllm/vllm-openai-rocm:latest -t aria-rocm .
#
# Run:
#   docker run -p 9876:9876 \
#     -v ./data:/app/data \
#     --env-file .env \
#     ghcr.io/malvavisc0/aria:latest
# ─────────────────────────────────────────────────────────────────────────────

ARG BASE_IMAGE=vllm/vllm-openai:latest
FROM ${BASE_IMAGE}

LABEL org.opencontainers.image.source="https://github.com/malvavisc0/aria"
LABEL org.opencontainers.image.description="Aria — AI Assistant with web UI and local LLM support"
LABEL org.opencontainers.image.licenses="MIT"

# ── Install Aria ──────────────────────────────────────────────────────────────
RUN pip install --no-cache-dir aria-ai

# ── Runtime configuration ─────────────────────────────────────────────────────
ENV ARIA_HOME=/app/data

# ── Create data directory for persistent storage ──────────────────────────────
RUN mkdir -p /app/data
WORKDIR /app

# ── Expose Chainlit web UI port ───────────────────────────────────────────────
EXPOSE 9876

# ── Entrypoint ────────────────────────────────────────────────────────────────
ENTRYPOINT ["aria", "server", "run"]