# Aria: Your Personal AI Assistant

Aria is a powerful, self-hosted AI assistant designed for reasoning, task completion, and seamless interaction. It provides a feature-rich chat interface with multi-session support, real-time streaming responses, and advanced AI capabilities.

## ✨ Features

- **Multi-Session Chat**: Manage multiple conversations with persistent history.
- **Real-Time Streaming**: Get instant responses from the AI as they are generated.
- **Markdown & Mermaid Support**: Render rich text and diagrams directly in the chat.
- **AI-Powered Tools**:
  - **Web Search**: Access real-time information from the web.
  - **Reasoning Engine**: Perform complex reasoning and analysis.
  - **YouTube Analysis**: Extract insights from YouTube videos.
  - **Weather & Finance Data**: Get up-to-date information on weather and financial markets.
- **Prompt Improvement**: Automatically enhance your prompts for better AI responses.
- **Dockerized Deployment**: Easy to set up and run with Docker.

## 🏗️ Architecture

Aria is built with a modern, modular architecture:

- **Backend**: A robust FastAPI server that handles all business logic, including:
  - Session and message management
  - Integration with Ollama for AI model access
  - A suite of AI tools for enhanced capabilities
- **Frontend**: A responsive web UI built with HTML, CSS, and JavaScript, providing a seamless user experience.
- **AI Core**: Powered by Ollama, allowing you to use a variety of open-source language models.
- **Services**:
  - **Redis**: For caching and session management.
  - **SearXNG**: For private and secure web search.
  - **Byparr**: For additional backend functionality.

## 🚀 Getting Started

### Prerequisites

- [Docker](https://www.docker.com/get-started)
- [Docker Compose](https://docs.docker.com/compose/install/)
- An accessible [Ollama](https://ollama.com/) instance

### Installation

The recommended way to install Aria is by using the official Docker image.

1. **Create a `docker-compose.yml` file**:
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

2. **Configure your environment**:
   - Create a `.env` file and add your configuration. At a minimum, you need to set `OLLAMA_URL`.
     ```env
     TZ=Europe/Berlin
     OLLAMA_URL=http://your-ollama-instance:11434
     OLLAMA_MODEL_ID=cogito:14b
     SEARXNG_SECRET=your-super-secret-key
     ```

3. **Run the application**:
   ```bash
   docker-compose up -d
   ```

4. **Access Aria**:
   - Open your web browser and navigate to `http://localhost:8000`.

## ⚙️ Configuration

You can configure Aria using the following environment variables in your `.env` file:

| Variable                      | Description                                       | Default                  |
| ----------------------------- | ------------------------------------------------- | ------------------------ |
| `TZ`                          | Timezone for the application                      | `Europe/Berlin`          |
| `OLLAMA_URL`                  | URL of your Ollama instance                       | `http://ollama:11434`    |
| `OLLAMA_MODEL_ID`             | The ID of the Ollama model to use                 | `cogito:14b`             |
| `OLLAMA_MODEL_TEMPARATURE`    | The temperature for the AI model                  | `0.65`                   |
| `OLLAMA_MODEL_CONTEXT_LENGTH` | The context length for the AI model               | `4096`                   |
| `DEBUG_MODE`                  | Enable or disable debug mode                      | `false`                  |
| `SEARXNG_SECRET`              | A secret key for SearXNG                          | `your-secret-key`        |

## 🧑‍💻 Development

To run Aria in development mode, you can use the following command:

```bash
python -m aria.cli run --reload
```

This will start the FastAPI server with hot-reloading enabled.

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
