from os import getenv
from pathlib import Path

from chromadb import PersistentClient as ChromaDBPersistentClient
from chromadb.config import Settings as ChromaDBSettings

from aria.llm import get_chat_llm


def _get_required_env(key: str) -> str:
    value = getenv(key, None)
    if value is None:
        raise ValueError(f"Required environment variable '{key}' is not set")
    return value


DATA_FOLDER = Path.cwd() / Path(_get_required_env("DATA_FOLDER"))
DATA_FOLDER.mkdir(exist_ok=True)

DEBUG_LOGS_PATH = DATA_FOLDER / Path("debug.logs")

LOCAL_STORAGE_PATH = DATA_FOLDER / Path(
    _get_required_env("LOCAL_STORAGE_PATH")
)

# Chat LLM
CHAT_OPENAI_API = _get_required_env("CHAT_OPENAI_API")
MAX_ITERATIONS = int(_get_required_env("MAX_ITERATIONS"))
LLM = get_chat_llm(api_base=CHAT_OPENAI_API)

# Chat History
CHAT_HISTORY_DB_PATH = DATA_FOLDER / Path(
    _get_required_env("CHAT_HISTORY_DB_FILE_NAME")
)
CHAT_HISTORY_DB_URL = f"sqlite:///{CHAT_HISTORY_DB_PATH}"
SQLITE_CONN_INFO = f"sqlite+aiosqlite:///{CHAT_HISTORY_DB_PATH}"

# Embeddings
EMBEDDINGS_API_URL = _get_required_env("EMBEDDINGS_API_URL")
EMBEDDINGS_MODEL = _get_required_env("EMBEDDINGS_MODEL")

# Embeddings Database
CHROMADB_PERSISTENT_PATH = (
    Path.cwd()
    / DATA_FOLDER
    / Path(_get_required_env("CHROMADB_PERSISTENT_PATH"))
)

VECTOR_DB = ChromaDBPersistentClient(
    path=CHROMADB_PERSISTENT_PATH,
    settings=ChromaDBSettings(
        is_persistent=True,
        persist_directory=CHROMADB_PERSISTENT_PATH.absolute().as_posix(),
        anonymized_telemetry=False,
    ),
)
