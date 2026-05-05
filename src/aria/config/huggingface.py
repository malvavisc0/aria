"""HuggingFace configuration for the Aria application.

This module provides configuration for HuggingFace Hub access, including
authentication tokens.

Environment Variables:
    HF_TOKEN: Optional API token for accessing gated/private models.
        Leave empty for public models.

Example:
    ```python
    from aria.config.huggingface import HuggingFace

    # Get the token (may be None for public models)
    token = HuggingFace.token
    ```
"""

from os import getenv


class HuggingFace:
    """HuggingFace Hub configuration.

    Attributes:
        token: Optional HuggingFace API token. Required for gated or private
            models (e.g. Llama, Mistral). None if not set.
    """

    token: str | None = getenv("HF_TOKEN") or None
