---
layout: default
title: Configuration Options
---

# Configuration Options

Aria can be configured using environment variables in your `.env` file. This guide explains the available configuration options and their default values.

## Environment Variables

| Variable                      | Description                                       | Default                  |
| ----------------------------- | ------------------------------------------------- | ------------------------ |
| `TZ`                          | Timezone for the application                      | `Europe/Berlin`          |
| `OLLAMA_URL`                  | URL of your Ollama instance                       | `http://ollama:11434`    |
| `OLLAMA_MODEL_ID`             | The ID of the Ollama model to use                 | `cogito:14b`             |
| `OLLAMA_MODEL_TEMPARATURE`    | The temperature for the AI model                  | `0.65`                   |
| `OLLAMA_MODEL_CONTEXT_LENGTH` | The context length for the AI model               | `4096`                   |
| `DEBUG_MODE`                  | Enable or disable debug mode                      | `false`                  |
| `SEARXNG_SECRET`              | A secret key for SearXNG                          | `your-secret-key`        |
| `SEARXNG_URL`                 | URL of the SearXNG instance                       | `http://searxng:8080`    |
| `BYPARR_URL`                  | URL of the Byparr instance                        | `http://byparr:8191/v1`  |
| `BYPARR_TIMEOUT`              | Timeout for Byparr requests                       | `120`                    |
| `AGNO_TELEMETRY`              | Enable or disable Agno telemetry                  | `false`                  |
| `REDIS_PORT`                  | Port for Redis                                    | `6379`                   |
| `RUNTIME`                     | Runtime for Docker containers                     | `runc`                   |

## Configuration Examples

### Basic Configuration

A minimal configuration only requires the `OLLAMA_URL`:

```env
TZ=Europe/Berlin
OLLAMA_URL=http://your-ollama-instance:11434
OLLAMA_MODEL_ID=cogito:14b
SEARXNG_SECRET=your-super-secret-key
```

### Advanced Configuration

For more control over Aria's behavior, you can set additional variables:

```env
TZ=Europe/Berlin
OLLAMA_URL=http://your-ollama-instance:11434
OLLAMA_MODEL_ID=cogito:14b
OLLAMA_MODEL_TEMPARATURE=0.7
OLLAMA_MODEL_CONTEXT_LENGTH=8192
DEBUG_MODE=true
SEARXNG_SECRET=your-super-secret-key
SEARXNG_HOSTNAME=searxng
SEARXNG_PORT=8080
SEARXNG_UWSGI_WORKERS=8
SEARXNG_UWSGI_THREADS=8
BYPARR_PORT=8191
REDIS_PORT=6379
RUNTIME=runc
AGNO_TELEMETRY=false
```

## Model Configuration

Aria uses Ollama to run AI models. You can configure which model to use and its parameters:

- `OLLAMA_MODEL_ID`: The ID of the model to use (e.g., `cogito:14b`, `llama2:13b`, etc.)
- `OLLAMA_MODEL_TEMPARATURE`: Controls the randomness of the model's output (0.0 to 1.0)
- `OLLAMA_MODEL_CONTEXT_LENGTH`: The maximum context length for the model

## Service Configuration

Aria uses several services that can be configured:

### SearXNG

SearXNG is used for web search capabilities:

- `SEARXNG_SECRET`: A secret key for SearXNG
- `SEARXNG_HOSTNAME`: The hostname for SearXNG
- `SEARXNG_PORT`: The port for SearXNG
- `SEARXNG_UWSGI_WORKERS`: The number of uWSGI workers
- `SEARXNG_UWSGI_THREADS`: The number of uWSGI threads

### Redis

Redis is used for caching and session management:

- `REDIS_PORT`: The port for Redis

### Byparr

Byparr is used for additional functionality:

- `BYPARR_URL`: The URL of the Byparr instance
- `BYPARR_PORT`: The port for Byparr
- `BYPARR_TIMEOUT`: The timeout for Byparr requests

## Debug Mode

Setting `DEBUG_MODE=true` enables additional logging and debugging features, which can be helpful for troubleshooting issues.

## Next Steps

- Learn how to [use Aria](usage.html) effectively
- Explore the [advanced features](advanced.html)
- Return to the [installation guide](installation.html) if you need to make changes
