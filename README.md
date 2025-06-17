# Aria Backend

## Installation

1. Install [uv](https://github.com/astral-sh/uv) (required for running the server):

   ```sh
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Install the package (from the project root):

   ```sh
   pip install .
   ```

## Usage

To start the backend server:

```sh
aria run
```

This will launch the FastAPI server using uv and uvicorn.

- By default, the server runs on http://0.0.0.0:8000
- You can customize host, port, reload, and log-level via CLI options:

  ```sh
  aria run --host 127.0.0.1 --port 8080 --reload False --log-level debug
  ```

## Project Structure

- `aria/` - Python package with all backend code
- `aria/cli.py` - CLI entry point for the `aria` command
- `aria/main.py` - FastAPI app definition
- `pyproject.toml` - Packaging and dependencies

## Requirements

- Python 3.8+
- [uv](https://github.com/astral-sh/uv)
- See `pyproject.toml` for Python dependencies
