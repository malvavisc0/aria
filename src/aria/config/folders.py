from pathlib import Path

from aria.config import get_required_env


def _find_project_root() -> Path:
    """Walk up from this file to find the project root (contains pyproject.toml)."""
    current = Path(__file__).resolve().parent
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


_PROJECT_ROOT = _find_project_root()


class Data:
    path = (_PROJECT_ROOT / Path(get_required_env("DATA_FOLDER"))).resolve()


class Debug:
    logs_path = Data.path / Path("debug.logs")


class Storage:
    path = Data.path / Path(get_required_env("LOCAL_STORAGE_PATH"))


class Uploads:
    path = Data.path / Path("uploads/")
