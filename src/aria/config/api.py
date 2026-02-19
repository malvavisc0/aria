from pathlib import Path

from aria.config import get_optional_env, get_required_env
from aria.config.folders import Data


class LlamaCpp:
    bin_path = Data.path / Path(get_required_env("LLAMA_CPP_BIN_DIR"))
    version = get_required_env("LLAMA_CPP_VERSION")
    models_path = Data.path / Path(get_required_env("GGUF_MODELS_DIR"))
    context_size = int(get_optional_env("LLAMA_CONTEXT_SIZE", "8192"))
