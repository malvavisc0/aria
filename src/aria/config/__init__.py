from os import getenv

from dotenv import load_dotenv

load_dotenv()


def get_required_env(key: str) -> str:
    value = getenv(key, None)
    if value is None:
        raise ValueError(f"Required environment variable '{key}' is not set")
    return value


def get_optional_env(key: str, default: str = "") -> str:
    return getenv(key, default)
