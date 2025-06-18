import os

from agno.agent import Agent
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.memory.v2.memory import Memory
from agno.models.ollama import Ollama
from agno.storage.sqlite import SqliteStorage

from aria.ai.configs import ARIA_AGENT_CONFIG, PROMPT_IMPROVER_AGENT_CONFIG
from aria.ai.kits import reasoning_tools, searxng_tools, weather_tools, youtube_tools


def get_ollama_core_agent(
    user_id: str, session_id: str, enable_memory: bool = False
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

    ollama = Ollama(
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

    debug_mode = os.environ.get("DEBUG_MODE", "false").lower() == "true"

    db_file = os.getenv("DB_FILE", "/opt/storage/sessions.db")
    storage = SqliteStorage(table_name="chat", db_file=db_file)
    memory = None
    if enable_memory:
        memory = Memory(db=SqliteMemoryDb(db_file=db_file))

    return Agent(
        model=ollama,
        name=ARIA_AGENT_CONFIG["name"],
        description=ARIA_AGENT_CONFIG["description"],
        role=ARIA_AGENT_CONFIG["role"],
        instructions=ARIA_AGENT_CONFIG["instructions"],
        goal=ARIA_AGENT_CONFIG["goal"],
        user_id=user_id,
        session_id=session_id,
        enable_session_summaries=enable_memory,
        search_previous_sessions_history=enable_memory,
        enable_agentic_memory=enable_memory,
        enable_user_memories=enable_memory,
        read_tool_call_history=enable_memory,
        add_history_to_messages=enable_memory,
        read_chat_history=enable_memory,
        add_datetime_to_instructions=True,
        memory=memory,
        storage=storage,
        debug_mode=debug_mode,
        show_tool_calls=debug_mode,
        tools=[searxng_tools, reasoning_tools, youtube_tools, weather_tools],
    )


def get_prompt_improver_agent() -> Agent:
    """
    Get an instance of the Prompt Improver agent.

    Initializes and returns an `Agent` configured to improve prompts without changing
    their original meaning. This agent uses the same Ollama model as the core agent
    but with different configuration parameters optimized for prompt improvement.

    Returns:
     Agent: An instance of the Prompt Improver agent configured with specified parameters.

    Raises:
     ValueError: If OLLAMA_URL or OLLAMA_MODEL_ID is not set in environment variables.
    """
    ollama_url = os.getenv("OLLAMA_URL")
    ollama_model_id = os.getenv("OLLAMA_MODEL_ID")
    if not ollama_url:
        raise ValueError("OLLAMA_URL is not set")
    if not ollama_model_id:
        raise ValueError("OLLAMA_MODEL_ID is not set")

    # Use a slightly higher temperature for more creative prompt improvements
    ollama_model_temperature = float(os.getenv("OLLAMA_MODEL_TEMPARATURE", 0.7))
    ollama_model_context_length = int(os.getenv("OLLAMA_MODEL_CONTEXT_LENGTH", 20480))

    ollama = Ollama(
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

    debug_mode = os.environ.get("DEBUG_MODE", "false").lower() == "true"

    return Agent(
        model=ollama,
        name=PROMPT_IMPROVER_AGENT_CONFIG["name"],
        description=PROMPT_IMPROVER_AGENT_CONFIG["description"],
        role=PROMPT_IMPROVER_AGENT_CONFIG["role"],
        instructions=PROMPT_IMPROVER_AGENT_CONFIG["instructions"],
        goal=PROMPT_IMPROVER_AGENT_CONFIG["goal"],
        add_datetime_to_instructions=True,
        debug_mode=debug_mode,
        show_tool_calls=debug_mode,
        tools=[reasoning_tools],
    )
