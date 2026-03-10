from pathlib import Path

from aria.config import get_required_env
from aria.config.folders import Data

_ARIA_DB_FILE_PATH = Data.path / Path(get_required_env("ARIA_DB_FILENAME"))


class SQLite:
    file_path = _ARIA_DB_FILE_PATH
    db_url = f"sqlite:///{_ARIA_DB_FILE_PATH}"
    conn_info = f"sqlite+aiosqlite:///{_ARIA_DB_FILE_PATH}"


class ChromaDB:
    db_path = Data.path / Path(get_required_env("CHROMADB_PERSISTENT_PATH"))
