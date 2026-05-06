"""Configuration utilities for the Aria application.

Environment loading is lazy: the .env file is read on the first call to
``get_required_env()``, ``get_optional_env()``, or ``get_bool_env()`` —
**not** at import time.  This prevents import-time side effects and avoids
overriding monkeypatched env vars in tests.
"""

from os import getenv

_env_loaded = False


def _ensure_env() -> None:
    """Load the .env file on first use.  No-op on subsequent calls."""
    global _env_loaded
    if _env_loaded:
        return
    from dotenv import load_dotenv

    load_dotenv()
    _env_loaded = True


def get_bool_env(key: str, default: bool = False) -> bool:
    """Parse a boolean environment variable.

    Accepts common truthy strings: true, 1, yes, y, on (case-insensitive).
    """
    _ensure_env()
    value = getenv(key, None)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


DEBUG = get_bool_env("DEBUG", False)


def get_required_env(key: str) -> str:
    """Return the value of a required environment variable.

    Raises:
        ValueError: If the variable is not set.
    """
    _ensure_env()
    value = getenv(key, None)
    if value is None:
        raise ValueError(f"Required environment variable '{key}' is not set")
    return value


def get_optional_env(key: str, default: str = "") -> str:
    """Return the value of an optional environment variable."""
    _ensure_env()
    return getenv(key, default)
