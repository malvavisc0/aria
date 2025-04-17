from os import environ
from typing import Optional

from agno.embedder.base import Embedder
from agno.embedder.fastembed import FastEmbedEmbedder
from agno.models.base import Model
from agno.models.ollama.chat import Ollama
from agno.models.openrouter.openrouter import OpenRouter
from ollama import Client as OllamaClient

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
        client=OllamaClient(host=OLLAMA_URL),
        options={"temperature": temperature},
    )


def embedder(model: Optional[str] = EMBEDDING_MODEL) -> Embedder:
    return FastEmbedEmbedder(dimensions=4096, id=model)
