from aria.config import get_required_env


class Chat:
    api_url = get_required_env("CHAT_OPENAI_API")
    max_iteration = int(get_required_env("MAX_ITERATIONS"))


class Embeddings:
    api_url = get_required_env("EMBEDDINGS_API_URL")
    model = get_required_env("EMBEDDINGS_MODEL")
    token_limit = int(get_required_env("TOKEN_LIMIT"))
