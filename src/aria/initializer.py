"""First-run initialization for Aria CLI and GUI.

Creates required files and directories on first launch:
- .env file with generated CHAINLIT_AUTH_SECRET
- Data, storage, and chromadb directories
- SQLite database with tables
- Log file
"""

import secrets
from importlib.resources import as_file, files
from pathlib import Path
from shutil import copyfile

from rich.console import Console

from aria.helpers.network import get_network_ip

console = Console()


def _find_project_root() -> Path:
    """Walk up from this file to find the project root (contains pyproject.toml).

    Mirrors the same helper in ``aria.config.folders`` — kept separate to
    avoid importing that module before the ``.env`` file exists (its module-
    level code reads ``DATA_FOLDER`` from the environment).
    """
    current = Path(__file__).resolve().parent
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


_PROJECT_ROOT = _find_project_root()


def is_initialized() -> bool:
    """Check if the environment is already initialized.

    Returns True if .env exists with a non-empty CHAINLIT_AUTH_SECRET.
    """
    env_file = _PROJECT_ROOT / ".env"
    if not env_file.exists():
        return False

    content = env_file.read_text()
    for line in content.splitlines():
        if line.startswith("CHAINLIT_AUTH_SECRET"):
            if "=" in line:
                value = line.split("=", 1)[1].strip()
                return bool(value) and value not in (
                    "your-secret-here",
                    "changeme",
                )
    return False


def generate_secret() -> str:
    """Generate a secure random secret for CHAINLIT_AUTH_SECRET."""
    return secrets.token_urlsafe(32)


def setup_env_file() -> bool:
    """Create .env from .env.example with generated secret and network IP."""
    env_file = _PROJECT_ROOT / ".env"
    if env_file.exists():
        return False

    env_example_ref = files("aria").joinpath(".env.example")
    with as_file(env_example_ref) as env_example:
        copyfile(env_example, env_file)

    secret = generate_secret()
    content = env_file.read_text()
    content = content.replace(
        "CHAINLIT_AUTH_SECRET =", f"CHAINLIT_AUTH_SECRET = {secret}"
    )

    # Detect and set network IP for SERVER_HOST
    network_ip = get_network_ip()
    content = content.replace("SERVER_HOST = 0.0.0.0", f"SERVER_HOST = {network_ip}")

    env_file.write_text(content)

    console.print("   [green]✓[/green] Created .env configuration")
    console.print("   [green]✓[/green] Generated CHAINLIT_AUTH_SECRET")
    console.print(f"   [green]✓[/green] Detected network IP: {network_ip}")
    return True


def setup_directories() -> None:
    """Create required directories."""
    from dotenv import load_dotenv

    load_dotenv()

    from aria.config.database import ChromaDB
    from aria.config.folders import Data, Storage

    Data.path.mkdir(parents=True, exist_ok=True)
    Storage.path.mkdir(parents=True, exist_ok=True)
    ChromaDB.db_path.mkdir(parents=True, exist_ok=True)
    console.print("   [green]✓[/green] Created data directory")
    console.print("   [green]✓[/green] Created chromadb directory")


def setup_database() -> None:
    """Create SQLite database and all tables."""
    from sqlalchemy import create_engine

    from aria.config.database import SQLite
    from aria.db.models import Base

    engine = create_engine(SQLite.db_url)
    Base.metadata.create_all(engine)
    engine.dispose()
    console.print("   [green]✓[/green] Initialized database")


def setup_logs() -> None:
    """Create log file if it doesn't exist."""
    from aria.config.folders import Debug

    if not Debug.logs_path.exists():
        Debug.logs_path.parent.mkdir(parents=True, exist_ok=True)
        Debug.logs_path.touch()
    console.print("   [green]✓[/green] Created log file")


def run_initialization() -> None:
    """Run all initialization steps for first-time setup."""
    console.print("🔧 [bold]First-time setup...[/bold]")
    setup_env_file()
    setup_directories()
    setup_database()
    setup_logs()
    console.print()
