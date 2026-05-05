"""Model configuration for the Aria application.

Each model class exposes a ``model_path`` that can be either a HuggingFace
Hub repository ID (e.g. ``"TheBloke/Lucy-128k-GPTQ"``) or an absolute
local filesystem path to a downloaded snapshot directory.

Environment Variables:
    CHAT_MODEL_PATH: HuggingFace repo ID or local path for the chat model.
    EMBED_MODEL_PATH: HuggingFace repo ID or local path for the embeddings model.
"""

import random
import urllib.parse
from pathlib import Path

from aria.config import get_optional_env, get_required_env
from aria.config.api import Vllm as VllmConfig
from aria.config.folders import Data


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


def _random_user_port() -> int:
    """Generate a random port in the user/dynamic range (49152–65535).

    Used as a last-resort fallback when the configured API URL has no
    explicit port (e.g. bare hostname without :PORT).
    """
    return random.randint(49152, 65535)


class Chat:
    api_url = get_required_env("CHAT_OPENAI_API")
    model = get_required_env("CHAT_MODEL")
    max_iteration = int(get_required_env("MAX_ITERATIONS"))
    model_path = _resolve_model_path(get_optional_env("CHAT_MODEL_PATH", ""))

    @classmethod
    def get_port(cls) -> int:
        return urllib.parse.urlparse(cls.api_url).port or _random_user_port()


class Embeddings:
    model = get_required_env("EMBEDDINGS_MODEL")
    context_size = int(get_optional_env("EMBEDDINGS_CONTEXT_SIZE", "8192"))
    token_limit_ratio = float(get_optional_env("TOKEN_LIMIT_RATIO", "0.85"))
    token_limit = int(VllmConfig.chat_context_size * token_limit_ratio)
    model_path = _resolve_model_path(get_optional_env("EMBED_MODEL_PATH", ""))
