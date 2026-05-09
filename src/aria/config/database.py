from pathlib import Path

from aria.config import get_required_env
from aria.config.folders import DB

# Ensure the database directory exists (defensive — handles first-run and tests)
DB.path.mkdir(parents=True, exist_ok=True)

_ARIA_DB_FILE_PATH = DB.path / Path(get_required_env("ARIA_DB_FILENAME"))


class SQLite:
    file_path = _ARIA_DB_FILE_PATH
    db_url = f"sqlite:///{_ARIA_DB_FILE_PATH}"
    conn_info = f"sqlite+aiosqlite:///{_ARIA_DB_FILE_PATH}"


class ChromaDB:
    db_path = DB.path / Path(get_required_env("CHROMADB_PERSISTENT_PATH"))
