from pathlib import Path

from aria.config import get_required_env


class Data:
    path = Path.cwd() / Path(get_required_env("DATA_FOLDER"))


class Debug:
    logs_path = Data.path / Path("debug.logs")


class Storage:
    path = Data.path / Path(get_required_env("LOCAL_STORAGE_PATH"))
