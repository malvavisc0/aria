"""HuggingFace configuration for the Aria application.

This module provides configuration for HuggingFace Hub access, including
authentication tokens and model storage paths.

Environment Variables:
    HUGGINGFACE_TOKEN: Optional API token for accessing gated/private models.
        Leave empty for public models.
    GGUF_MODELS_DIR: Directory name (relative to DATA_FOLDER) where downloaded
        .gguf model files are stored. Defaults to "models".

Example:
    ```python
    from aria.config.huggingface import HuggingFace

    # Get the token (may be None for public models)
    token = HuggingFace.token

    # Get the models directory path
    models_dir = HuggingFace.models_dir
    ```
"""

from os import getenv
from pathlib import Path

from dotenv import load_dotenv

from aria.config.folders import Data

load_dotenv()

_DEFAULT_MODELS_DIR = "models"


class HuggingFace:
    """HuggingFace Hub configuration.

    Attributes:
        token: Optional HuggingFace API token. Required for gated or private
            models (e.g. Llama, Mistral). None if not set.
        models_dir: Path to the directory where downloaded .gguf model files
            are stored. Resolved relative to the DATA_FOLDER. Defaults to
            ``DATA_FOLDER/models`` when ``GGUF_MODELS_DIR`` is not set.
    """

    token: str | None = getenv("HUGGINGFACE_TOKEN") or None
    models_dir: Path = Data.path / Path(getenv("GGUF_MODELS_DIR", _DEFAULT_MODELS_DIR))
