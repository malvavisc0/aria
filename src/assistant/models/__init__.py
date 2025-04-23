from os import environ
from typing import Optional

from agno.embedder.base import Embedder
from agno.embedder.fastembed import FastEmbedEmbedder
from agno.embedder.ollama import OllamaEmbedder
from agno.models.base import Model
from agno.models.ollama import Ollama
from agno.models.openrouter.openrouter import OpenRouter

OLLAMA_URL = environ.get("OLLAMA_URL", "")

CHATBOT_MODEL = environ.get("CHATBOT_MODEL", "")
TOOL_MODEL = environ.get("TOOL_MODEL", "")
VISION_MODEL = environ.get("VISION_MODEL", "")
EMBEDDING_MODEL = environ.get("EMBEDDING_MODEL", "")

OPENROUTER_API_KEY = environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = environ.get("OPENROUTER_MODEL", "")

assert OLLAMA_URL, "URL must be set in the environment"

assert CHATBOT_MODEL, "CHATBOT_MODEL must be set in the environment"
assert TOOL_MODEL, "TOOL_MODEL must be set in the environment"
assert VISION_MODEL, "VISION_MODEL must be set in the environment"
assert EMBEDDING_MODEL, "EMBEDDING_MODEL must be set in the environment"


def completion(
    model: Optional[str] = CHATBOT_MODEL, temperature: Optional[float] = 0.0
) -> Model:
    if OPENROUTER_API_KEY and OPENROUTER_MODEL:
        return OpenRouter(id=OPENROUTER_MODEL, name="Aria")
    return Ollama(
        id=model,
        host=OLLAMA_URL,
        timeout=600,
        options={
            "temperature": temperature,
            "num_ctx": 8192,
            "mirostat": 2,
            "repeat_last_n": -1,
            "top_k": 20,
            "seed": 10,
        },
    )


def embedder(model: Optional[str] = EMBEDDING_MODEL) -> Embedder:
    if not OLLAMA_URL:
        return FastEmbedEmbedder(dimensions=4096, id=model)
    return OllamaEmbedder(
        dimensions=4096,
        id=model,
        host=OLLAMA_URL,
        client_kwargs={"timeout": 600},
    )
