import os

from agno.agent import Agent
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.memory.v2.memory import Memory
from agno.models.ollama import Ollama
from agno.storage.sqlite import SqliteStorage


def get_ollama_agent(
    user_id: str, session_id: str, markdown: bool = False, enable_memory: bool = False
) -> Agent:
    """
    Get an instance of the Ollama agent.

    Initializes and returns an `Agent` configured with the provided parameters from
    environment variables. It ensures that necessary environment settings
    (OLLAMA_URL and OLLAMA_MODEL_ID) are present before attempting to create the model.

    Parameters:
     user_id (str): The ID of the user.
     session_id (str): The session ID for the agent.
     markdown (bool, optional): Flag indicating whether to use Markdown formatting.
     enable_memory (bool, optional): Flag indicating whether to enable memory for the agent.

    Returns:
     Agent: An instance of the Ollama agent configured with specified parameters.

    Raises:
     ValueError: If OLLAMA_URL or OLLAMA_MODEL_ID is not set in environment variables.
    """
    ollama_url = os.getenv("OLLAMA_URL")
    ollama_model_id = os.getenv("OLLAMA_MODEL_ID")
    if not ollama_url:
        raise ValueError("OLLAMA_URL is not set")
    if not ollama_model_id:
        raise ValueError("OLLAMA_MODEL_ID is not set")

    ollama_model_temperature = float(os.getenv("OLLAMA_MODEL_TEMPARATURE", 0.65))
    ollama_model_context_length = int(os.getenv("OLLAMA_MODEL_CONTEXT_LENGTH", 20480))

    ollama_model = Ollama(
        id=ollama_model_id,
        host=ollama_url,
        timeout=300,
        options={
            "temperature": ollama_model_temperature,
            "mirostat": 2,
            "repeat_last_n": -1,
            "top_k": 20,
            "seed": 10,
            "num_ctx": ollama_model_context_length,
        },
    )

    storage = SqliteStorage(table_name="session", db_file="/opt/storage/storage.db")

    memory = None
    if enable_memory:
        memory = Memory(db=SqliteMemoryDb(db_file="/opt/storage/memories.db"))

    return Agent(
        model=ollama_model,
        user_id=user_id,
        session_id=session_id,
        name="Core",
        markdown=markdown,
        memory=memory,
        storage=storage,
        enable_user_memories=enable_memory,
    )
