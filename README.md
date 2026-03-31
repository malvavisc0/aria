<div align="center">

# 🧠 Aria

**Your local AI assistant with a unified tool-driven architecture**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

*Run a local AI assistant with a web UI, CLI, and desktop GUI*

[Features](#-features) • [Quick Start](#-quick-start) • [Agents](#-agent-system) • [Tools](#-tools) • [Installation](#-installation)

</div>

<div align="center">
<img src="screenshot.png" alt="Aria Screenshot" width="80%">
</div>

---

## ✨ Features

| 🎯 | **Unified Tool Architecture** - Consolidated tool registry with tiered domain loading |
|:--:|:--|
| 🖥️ | **Multiple Interfaces** - Web UI, CLI, and native GUI application |
| 🤖 | **Local LLM Support** - Run models locally with llama.cpp integration |
| 🔒 | **Privacy First** - Your data stays on your machine |
| 🌐 | **Web Research** - Search, weather, finance, and more |
| 💻 | **Code Execution** - Safe Python sandbox and shell commands |

---

## 🚀 Quick Start

```bash
# Clone and install
git clone <repository-url>
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

Aria is in the middle of a tool-first consolidation: the recent architecture work reduces duplicated specialist behavior and centers capability around one primary Aria agent plus a separate prompt-enhancement utility.

### Recent Changes

- Tooling was consolidated into **33 total tools** with a centralized registry and category-based loading.
- Core and file tools are treated as always available, while domain tools load on demand.
- Redundant tool variants were merged into unified interfaces such as [`python()`](docs/tools-inventory.md), `read_file`, `write_file`, `edit_file`, `web_search`, `download`, and `shell`.
- New persistent capability areas now include a **knowledge store** plus system tools for **HTTP requests** and **process management**.
- The specialist-agent model is being phased out in favor of a simpler unified workflow, while [`PromptEnhancerAgent`](src/aria/agents/prompt_enhancer.py:32) remains separate.

### Current Tool Categories

| Category | Tools | Capabilities |
|:---------|:------|:-------------|
| 🧠 **Core** | reasoning, scratchpad, plan, knowledge | Structured thinking, planning, memory |
| 📁 **Files** | read_file, write_file, edit_file, + 6 more | Full file management |
| 🌐 **Search** | web_search, download | Web research, content download |
| 🐍 **Development** | python | Code execution and validation |
| 📊 **Finance** | stock_price, company_info, ticker_news | Market data and analysis |
| 🎬 **Entertainment** | 7 IMDb tools, YouTube | Movie/TV data, transcripts |
| 🖥️ **System** | shell, http_request, process | Shell commands, HTTP, process management |
| 🌤️ **Utility** | weather, parse_pdf, browser | Weather, PDF parsing, web browsing |

### How It Works

```
User Request → Aria → Registry-selected tools → Response
```

Aria evaluates each request, keeps core capabilities available by default, and pulls in domain-specific tools only when the task requires them.

---

## 🛠️ Tools

The recent tool redesign merged previously overlapping functions into a smaller, clearer inventory. The registry now organizes tools into always-loaded and on-demand domains.

| Category | Tools |
|:---------|:------|
| 🧠 **Core** | reasoning, plan, knowledge, scratchpad, web_search, download, get_current_weather, shell |
| 📁 **Files** | read_file, write_file, edit_file, file_info, list_files, search_files, copy_file, delete_file, rename_file |
| 🌍 **Web** | open_url, browser_click |
| 🐍 **Development** | python |
| 📊 **Finance** | fetch_current_stock_price, fetch_company_information, fetch_ticker_news |
| 🎬 **Entertainment** | search_imdb_titles, get_movie_details, get_person_details, get_person_filmography, get_all_series_episodes, get_movie_reviews, get_movie_trivia, get_youtube_video_transcription |
| 🖥️ **System** | http_request, process |

For the full inventory, parameter reference, and category mapping, see [`docs/tools-inventory.md`](docs/tools-inventory.md).

### Architecture Direction

The current implementation direction documented in [`plans/agent-consolidation-review.md`](plans/agent-consolidation-review.md) is:

1. Delete redundant tools.
2. Merge overlapping tools into broader interfaces.
3. Add the knowledge store.
4. Add `http_request` and `process`.
5. Consolidate specialist agents into a unified Aria workflow.
6. Preserve specialist guidance as prompt sections instead of separate agents.

This reduces routing complexity, lowers prompt overhead, and makes future capabilities easier to add.

---

## 📦 Installation

### Prerequisites

- Python 3.12 or higher
- `uv` package manager (recommended)
- Git

### Install

```bash
# Clone the repository
git clone <repository-url>
cd aria

# Install dependencies
uv sync

# Or with GUI support
uv sync --extra gui
```

### First Run

On first launch, Aria automatically:
- Creates configuration files
- Sets up the database
- Generates auth secrets

```bash
aria check     # Verify installation
aria server run  # Start the web server
```

---

## 💻 Usage

### CLI Commands

```bash
# Server management
aria server run     # Run in foreground
aria server start   # Start in background
aria server stop    # Stop the server
aria server status  # Check status

# User management
aria users list     # List users
aria users add      # Add new user

# Model management
aria models list        # List downloaded models
aria models download    # Download a model

# System info
aria system info    # System information
aria system gpu     # GPU information

# Configuration
aria config show    # Show current config
```

### GUI Application

```bash
aria-gui    # Launch desktop application
```

The GUI provides:
- Server control (start/stop)
- User management
- Model downloads
- Log viewing

### Web UI

After starting the server, access the web interface at `http://localhost:8000`

---

## ⚙️ Configuration

Aria uses environment variables stored in `.env`:

```bash
# Core settings
DATA_FOLDER=./data
CHAINLIT_AUTH_SECRET=<auto-generated>

# Model paths
CHAT_MODEL=<path-to-chat-model>
VISION_MODEL=<path-to-vision-model>
EMBEDDING_MODEL=<path-to-embedding-model>
```

<details>
<summary>📁 Directory Structure</summary>

```
aria/
├── data/              # Database, models, binaries
│   ├── aria.db        # SQLite database
│   ├── models/        # GGUF model files
│   └── bin/           # llama.cpp binaries
├── storage/           # Uploaded files
├── chromadb/          # Vector database
└── .env               # Configuration
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
