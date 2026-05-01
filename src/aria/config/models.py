import random
import urllib.parse

from aria.config import get_optional_env, get_required_env


def _random_user_port() -> int:
    """Generate a random port in the user/dynamic range (49152–65535).

    Used as a last-resort fallback when the configured API URL has no
    explicit port (e.g. bare hostname without :PORT).
    """
    return random.randint(49152, 65535)


class Chat:
    api_url = get_required_env("CHAT_OPENAI_API")
    max_iteration = int(get_required_env("MAX_ITERATIONS"))
    repo_id = get_optional_env("CHAT_MODEL_REPO", "")
    filename = get_optional_env("CHAT_MODEL", "")
    quantization = get_optional_env("CHAT_MODEL_TYPE", "Q8_0")

    @classmethod
    def get_port(cls) -> int:
        return urllib.parse.urlparse(cls.api_url).port or _random_user_port()


class Embeddings:
    api_url = get_required_env("EMBEDDINGS_API_URL")
    model = get_required_env("EMBEDDINGS_MODEL")
    token_limit = int(get_required_env("TOKEN_LIMIT"))
    repo_id = get_optional_env("EMBEDDINGS_MODEL_REPO", "")
    filename = get_optional_env("EMBEDDINGS_MODEL", "")
    quantization = get_optional_env("EMBEDDINGS_MODEL_TYPE", "Q8_0")

    @classmethod
    def get_port(cls) -> int:
        return urllib.parse.urlparse(cls.api_url).port or _random_user_port()


class Rerank:
    api_url = get_optional_env("RERANK_API_URL", "http://0.0.0.0:7073")
    model = get_optional_env("RERANK_MODEL", "")
    repo_id = get_optional_env("RERANK_MODEL_REPO", "")
    filename = get_optional_env("RERANK_MODEL_FILE", "")
    quantization = get_optional_env("RERANK_MODEL_TYPE", "Q8_0")

    @classmethod
    def get_port(cls) -> int:
        return urllib.parse.urlparse(cls.api_url).port or _random_user_port()


class Vision:
    api_url = get_required_env("VL_OPENAI_API")
    model = get_required_env("VL_MODEL")
    repo_id = get_optional_env("VL_MODEL_REPO", "")
    filename = get_optional_env("VL_MODEL", "")
    mmproj_filename = get_optional_env("VL_MMPROJ_MODEL", "")
    quantization = get_optional_env("VISION_MODEL_TYPE", "Q8_0")

    @classmethod
    def get_port(cls) -> int:
        return urllib.parse.urlparse(cls.api_url).port or _random_user_port()
