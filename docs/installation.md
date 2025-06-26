---
layout: default
title: Installation Guide
---

# Installation Guide

Aria is designed to be easy to set up and run using Docker. This guide will walk you through the installation process.

## Prerequisites

Before installing Aria, make sure you have the following prerequisites:

- [Docker](https://www.docker.com/get-started)
- [Docker Compose](https://docs.docker.com/compose/install/)
- An accessible [Ollama](https://ollama.com/) instance

## Installation Steps

The recommended way to install Aria is by using the official Docker image.

### 1. Create a `docker-compose.yml` file

Create a new file named `docker-compose.yml` with the following content:

```yaml
networks:
  mitty: null

volumes:
  redis: null

services:
  aria:
    image: 'ghcr.io/malvavisc0/aria:latest'
    container_name: aria
    hostname: aria
    restart: always
    env_file:
      - ./.env
    ports:
      - '8000:8000'
    environment:
      TZ: '${TZ}'
      SEARXNG_URL: '${SEARXNG_URL:-http://searxng:8080}'
      BYPARR_URL: '${BYPARR_URL:-http://byparr:8191/v1}'
      BYPARR_TIMEOUT: '${BYPARR_TIMEOUT:-120}'
      AGNO_TELEMETRY: '${AGNO_TELEMETRY:-false}'
      OLLAMA_URL: '${OLLAMA_URL}'
      OLLAMA_MODEL_ID: '${OLLAMA_MODEL_ID}'
      OLLAMA_MODEL_TEMPARATURE: '${OLLAMA_MODEL_TEMPARATURE:-0.65}'
      OLLAMA_MODEL_CONTEXT_LENGTH: '${OLLAMA_MODEL_CONTEXT_LENGTH:-1280}'
      DEBUG_MODE: '${DEBUG_MODE:-false}'
    volumes:
      - './data:/opt/storage'
    networks:
      - mitty
  redis:
    image: 'redis/redis-stack-server:latest'
    container_name: redis
    hostname: redis
    restart: always
    runtime: '${RUNTIME:-runc}'
    expose:
      - '${REDIS_PORT:-6379}'
    environment:
      TZ: '${TZ}'
    volumes:
      - 'redis:/data'
    networks:
      - mitty
  searxng:
    image: 'docker.io/searxng/searxng:latest'
    container_name: searxng
    hostname: searxng
    restart: always
    volumes:
      - './searxng:/etc/searxng'
    environment:
      TZ: '${TZ}'
      SEARXNG_BASE_URL: 'http://${SEARXNG_HOSTNAME:-searxng}:${SEARXNG_PORT:-8080}/'
      SEARXNG_SECRET: '${SEARXNG_SECRET}'
      UWSGI_WORKERS: '${SEARXNG_UWSGI_WORKERS:-4}'
      UWSGI_THREADS: '${SEARXNG_UWSGI_THREADS:-4}'
      SEARXNG_REDIS_URL: 'redis://redis:6379/10'
    expose:
      - '${SEARXNG_PORT:-8080}'
    cap_add:
      - CHOWN
      - SETGID
      - SETUID
    networks:
      - mitty
  byparr:
    image: 'ghcr.io/thephaseless/byparr:latest'
    container_name: byparr
    hostname: byparr
    restart: always
    runtime: '${RUNTIME:-runc}'
    environment:
      TZ: '${TZ}'
    expose:
      - '${BYPARR_PORT:-8191}'
    networks:
      - mitty
  dozzle:
    image: 'amir20/dozzle:latest'
    container_name: dozzle
    hostname: dozzle
    ports:
     - 8080:8080
    volumes:
      - '/var/run/docker.sock:/var/run/docker.sock:ro'
    environment:
      - DOZZLE_NO_ANALYTICS=1
      - DOZZLE_HOSTNAME=aria
      - DOZZLE_LEVEL=debug
    networks:
      - mitty
```

### 2. Configure your environment

Create a `.env` file and add your configuration. At a minimum, you need to set `OLLAMA_URL`.

```env
TZ=Europe/Berlin
OLLAMA_URL=http://your-ollama-instance:11434
OLLAMA_MODEL_ID=cogito:14b
SEARXNG_SECRET=your-super-secret-key
```

### 3. Run the application

```bash
docker-compose up -d
```

This command will download the necessary Docker images and start the Aria application in detached mode.

### 4. Access Aria

Open your web browser and navigate to `http://localhost:8000`.

## Troubleshooting

If you encounter any issues during installation:

1. Check that Docker and Docker Compose are properly installed
2. Ensure your Ollama instance is running and accessible
3. Verify that the ports (8000 and 8080) are not already in use
4. Check the logs with `docker-compose logs aria`

## Next Steps

Once you have Aria up and running, you can:

- [Configure Aria](/aria/configuration.html) to customize its behavior
- Learn how to [use Aria](/aria/usage.html) effectively
- Explore the [advanced features](/aria/advanced.html)
