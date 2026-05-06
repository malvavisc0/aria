"""Model configuration for the Aria application.

Each model class exposes a ``model_path`` that can be either a HuggingFace
Hub repository ID (e.g. ``"TheBloke/Lucy-128k-GPTQ"``) or an absolute
local filesystem path to a downloaded snapshot directory.

Class attributes are evaluated lazily on first access so that importing
this module does NOT require environment variables to be set.  This makes
the module testable without env fixtures and avoids import-order landmines.

Environment Variables:
    CHAT_MODEL_PATH: HuggingFace repo ID or local path for the chat model.
    EMBED_MODEL_PATH: HuggingFace repo ID or local path for the embeddings model.
"""

import random
import urllib.parse
from pathlib import Path
from typing import Any

from aria.config import get_optional_env, get_required_env
from aria.config.api import Vllm as VllmConfig
from aria.config.folders import Data

_SENTINEL = object()


class _Lazy:
    """Descriptor that defers evaluation until first attribute access.

    This enables class-level attributes to be declared declaratively
    while avoiding import-time side effects (e.g. env-var lookups that
    raise ``ValueError`` when the variable is unset).
    """

    def __init__(self, factory: Any) -> None:
        self._factory = factory
        self._value: Any = _SENTINEL

    def __set_name__(self, owner: type, name: str) -> None:
        self._attr = name

    def __get__(self, obj: Any, objtype: type | None = None) -> Any:
        if self._value is _SENTINEL:
            self._value = self._factory()
        return self._value


def _resolve_model_path(path: str) -> str:
    """Resolve a model path against DATA_FOLDER/models/.

    All models must reside under DATA_FOLDER/models/. For HuggingFace
    repo IDs (e.g. ``Stffens/bge-small-rrf-v4``), only the model name
    (last segment) is used as the local directory name.

    - Empty string → return as-is (not configured)
    - Absolute path → use as-is
    - Otherwise → resolve against DATA_FOLDER/models/ using last segment
    """
    if not path:
        return path
    if Path(path).is_absolute():
        return path
    # For HF repo IDs like "org/model-name", use only "model-name"
    model_name = path.rsplit("/", maxsplit=1)[-1].lower()
    return str(Data.path / "models" / model_name)


_random_port: int | None = None


def _random_user_port() -> int:
    """Generate a random port in the user/dynamic range (49152–65535).

    Used as a last-resort fallback when the configured API URL has no
    explicit port (e.g. bare hostname without :PORT). The port is cached
    so that repeated calls return the same value, preventing the vLLM
    command and health check from using different ports.
    """
    global _random_port
    if _random_port is None:
        _random_port = random.randint(49152, 65535)
    return _random_port


class Chat:
    """Chat model configuration (lazy — evaluated on first access)."""

    api_url = _Lazy(lambda: get_required_env("CHAT_OPENAI_API"))
    model = _Lazy(lambda: get_required_env("CHAT_MODEL"))
    max_iteration = _Lazy(lambda: int(get_required_env("MAX_ITERATIONS")))
    model_path = _Lazy(
        lambda: _resolve_model_path(get_optional_env("CHAT_MODEL_PATH", ""))
    )

    @classmethod
    def get_port(cls) -> int:
        return urllib.parse.urlparse(cls.api_url).port or _random_user_port()


class Embeddings:
    """Embeddings model configuration (lazy — evaluated on first access)."""

    model = _Lazy(lambda: get_required_env("EMBEDDINGS_MODEL"))
    context_size = _Lazy(
        lambda: int(get_optional_env("EMBEDDINGS_CONTEXT_SIZE", "8192"))
    )
    token_limit_ratio = _Lazy(
        lambda: float(get_optional_env("TOKEN_LIMIT_RATIO", "0.85"))
    )
    token_limit = _Lazy(
        lambda: int(VllmConfig.chat_context_size * Embeddings.token_limit_ratio)
    )
    model_path = _Lazy(
        lambda: _resolve_model_path(get_optional_env("EMBED_MODEL_PATH", ""))
    )
