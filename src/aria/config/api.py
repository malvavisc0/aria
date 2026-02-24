from pathlib import Path

from aria.config import get_optional_env, get_required_env
from aria.config.folders import Data


class LlamaCpp:
    bin_path = Data.path / Path(get_required_env("LLAMA_CPP_BIN_DIR"))
    version = get_required_env("LLAMA_CPP_VERSION")
    models_path = Data.path / Path(get_required_env("GGUF_MODELS_DIR"))

    # Context sizes for each model type
    chat_context_size = int(get_optional_env("CHAT_CONTEXT_SIZE", "65536"))
    vl_context_size = int(get_optional_env("VL_CONTEXT_SIZE", "8192"))
    embeddings_context_size = int(get_optional_env("EMBEDDINGS_CONTEXT_SIZE", "8192"))
