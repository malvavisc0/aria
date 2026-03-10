from os import getenv

from dotenv import load_dotenv

load_dotenv()


def get_bool_env(key: str, default: bool = False) -> bool:
    """Parse a boolean environment variable.

    Accepts common truthy strings: true, 1, yes, y, on (case-insensitive).
    """

    value = getenv(key, None)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


DEBUG = get_bool_env("DEBUG", False)


def get_required_env(key: str) -> str:
    value = getenv(key, None)
    if value is None:
        raise ValueError(f"Required environment variable '{key}' is not set")
    return value


def get_optional_env(key: str, default: str = "") -> str:
    return getenv(key, default)
