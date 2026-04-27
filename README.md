<div align="center">

# 🧠 Aria

**Your local AI assistant with a unified tool-driven architecture**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

*Run a local AI assistant with a web UI, CLI, and desktop GUI*

[Features](#-features) • [Quick Start](#-quick-start) • [CLI](#-cli-commands) • [GUI](#-gui-application) • [Tools](#-tools) • [Installation](#-installation)

</div>

<div align="center">
<img src="screenshot.png" alt="Aria Screenshot" width="80%">
</div>

---

## ✨ Features

| 🎯 | **Unified Tool Architecture** — Centralized registry with category-based domain loading |
|:--:|:--|
| 🖥️ | **Multiple Interfaces** — Web UI, CLI, and native PySide6 desktop GUI |
| 🤖 | **Local LLM Support** — Run models locally with llama.cpp (auto-compile with CUDA) |
| 🌐 | **Browser Automation** — Lightpanda headless browser with CDP/Playwright support |
| 🔒 | **Privacy First** — Your data stays on your machine |
| 🌐 | **Web Research** — Search, weather, finance, and more |
| 💻 | **Code Execution** — Safe Python sandbox and shell commands |
| 📊 | **Knowledge & Planning** — Persistent knowledge store, structured reasoning, task planning |

---

## 🚀 Quick Start

```bash
# Clone and install
git clone git@github.com:malvavisc0/aria.git
cd aria
uv sync

# Start the server
aria server run

# Open http://localhost:8000 in your browser
```

<details>
<summary>📦 Install with GUI support</summary>

```bash
uv sync --extra gui
aria-gui  # Launch desktop application
```

</details>

---

## 🤖 Agent System

Aria uses a **tool-first architecture** centered around one primary agent with a centralized tool registry. Tools are organized into always-loaded core capabilities and on-demand domain tools that load when needed.

### How It Works

```
User Request → Aria → Registry-selected tools → Response
```

Aria evaluates each request, keeps core capabilities available by default, and pulls in domain-specific tools only when the task requires them.

---

## 🛠️ Tools

Tools are organized into **14 categories** managed by a centralized registry. Core and file tools are always available; domain tools load on demand.

| Category | Tools | Capabilities |
|:---------|:------|:-------------|
| 🧠 **Core** | reasoning, scratchpad, plan, knowledge | Structured thinking, planning, persistent memory |
| 📁 **Files** | read_file, write_file, edit_file, file_info, list_files, search_files, copy_file, delete_file, rename_file | Full file management |
| 🌐 **Search** | web_search, download | Web research, content download |
| 🐍 **Development** | python | Code execution and validation |
| 🌍 **Browser** | open_url, browser_click | Headless browser automation (Lightpanda) |
| 📊 **Finance** | fetch_current_stock_price, fetch_company_information, fetch_ticker_news | Market data and analysis |
| 🎬 **Entertainment** | 7 IMDb tools, get_youtube_video_transcription | Movie/TV data, transcripts |
| 🖥️ **System** | shell, http_request, process | Shell commands, HTTP requests, process management |
| 🌤️ **Utility** | get_current_weather, parse_pdf | Weather, PDF parsing |
| 🔍 **IMDb** | search_imdb_titles, get_movie_details, get_person_details, get_person_filmography, get_all_series_episodes, get_movie_reviews, get_movie_trivia | Movie and TV database |
| 📚 **Knowledge** | add_to_knowledge, search_knowledge, list_knowledge | Persistent knowledge store |
| 📋 **Planner** | create_plan, update_plan, list_plans | Task planning and tracking |
| 🔗 **HTTP** | http_request | Direct HTTP requests |
| ⚙️ **Process** | process | Process management |

For the full inventory with parameter reference, see [`docs/tools-inventory.md`](docs/tools-inventory.md).

---

## 📦 Installation

### Prerequisites

- **GPU with 8 GB+ VRAM** (minimum; 12 GB+ recommended)
- **16 GB+ system RAM**
- Python 3.12 or higher
- `uv` package manager (recommended)
- Git

> See [`docs/memory-requirements.md`](docs/memory-requirements.md) for detailed VRAM/RAM breakdown per model.

### Install

```bash
# Clone the repository
git clone git@github.com:malvavisc0/aria.git
cd aria

# Install dependencies
uv sync

# Or with GUI support
uv sync --extra gui
```

### First Run

On first launch, Aria automatically:
- Creates `.env` configuration with generated auth secrets
- Sets up the SQLite database
- Creates required directories

```bash
aria check       # Verify installation
aria server run  # Start the web server
```

---

## 💻 CLI Commands

```bash
# Server management
aria server run       # Run in foreground
aria server start     # Start in background
aria server stop      # Stop the server
aria server status    # Check status

# Binary management
aria llamacpp download    # Download llama.cpp binaries (auto-compile with CUDA if nvcc available)
aria llamacpp status      # Check llama.cpp installation
aria lightpanda download  # Download Lightpanda headless browser
aria lightpanda status    # Check Lightpanda installation

# Model management
aria models download      # Download a GGUF model
aria models list          # List downloaded models
aria models memory        # Show model memory requirements

# User management
aria users list           # List users
aria users add            # Add new user
aria users reset-password # Reset user password
aria users update         # Update user details
aria users delete         # Delete a user

# System info
aria system info          # Full system overview
aria system gpu           # GPU information
aria system vram          # VRAM details
aria system context       # Calculate max context size

# Configuration
aria config show          # Show current config
aria config paths         # Show configured paths
aria config database      # Show database info
aria config api           # Show API endpoints

# Health check
aria check                # Verify installation and connectivity
```

---

## 🖥️ GUI Application

```bash
aria-gui    # Launch desktop application (requires: uv sync --extra gui)
```

The native PySide6 desktop GUI provides:

| Tab | Features |
|:----|:---------|
| **Overview** | System status, database info, API endpoints, debug log viewer |
| **Setup** | Download/manage llama.cpp binaries, GGUF models (chat/vision/embeddings), and Lightpanda browser — with real-time output and cancel support |
| **Users** | Create, edit, delete users with password strength validation |
| **Settings** | Configure model paths, API URLs, and service parameters |
| **Logs** | View application logs with search, level filtering, and auto-refresh |

Additional features:
- **System tray** — minimizes to tray on close; force-quit via menu or Ctrl+Q
- **First-run wizard** — guided setup on first launch
- **Responsive layout** — adapts to window size
- **Preflight checks** — validates configuration on tab switch

---

## 🌐 Web UI

After starting the server, access the web interface at `http://localhost:8000`

The web UI is powered by [Chainlit](https://github.com/Chainlit/chainlit) and provides a chat interface to interact with Aria.

---

## ⚙️ Configuration

Aria uses environment variables stored in `.env`:

```bash
# Core settings
DATA_FOLDER=./data
CHAINLIT_AUTH_SECRET=<auto-generated>

# Model configuration
CHAT_MODEL=<path-to-chat-model>
VISION_MODEL=<path-to-vision-model>
EMBEDDING_MODEL=<path-to-embedding-model>
```

<details>
<summary>📁 Directory Structure</summary>

```
aria/
├── data/                  # Data root
│   ├── aria.db            # SQLite database
│   ├── models/            # GGUF model files
│   └── bin/
│       ├── llamacpp/      # llama.cpp binaries and shared libraries
│       └── lightpanda/    # Lightpanda headless browser binary
├── storage/               # Uploaded files
├── chromadb/              # Vector database
└── .env                   # Configuration
```

</details>

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

### Development Setup

```bash
# Install dev dependencies
uv sync --group dev

# Run tests
uv run pytest

# Format code
uv run black src/
uv run isort src/
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Made with ❤️ by malvavisc0**

[Report Bug](https://github.com/malvavisc0/aria/issues) · [Request Feature](https://github.com/malvavisc0/aria/issues)

</div>