from datetime import datetime
from os import environ

from agno.agent import Agent
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.memory.v2.memory import Memory
from agno.models.ollama import Ollama
from agno.storage.sqlite import SqliteStorage

from aria.ai.configs import ARIA_AGENT_CONFIG, PROMPT_IMPROVER_AGENT_CONFIG
from aria.ai.kits import (
    calulator_tools,
    reasoning_tools,
    searxng_tools,
    weather_tools,
    yfinance_tools,
    youtube_tools,
)
from aria.ai.outputs import ImprovedPromptResponse

OLLAMA_MODEL = Ollama(
    id=environ.get("OLLAMA_MODEL_ID", "cogito:8bb"),
    host=environ.get("OLLAMA_URL"),
    timeout=300,
    options={
        "temperature": float(environ.get("OLLAMA_MODEL_TEMPARATURE", 0.65)),
        "mirostat": 2,
        "repeat_last_n": -1,
        "top_k": 20,
        "seed": 10,
        "num_ctx": int(environ.get("OLLAMA_MODEL_CONTEXT_LENGTH", 20480)),
    },
)
DEBUG_MODE = environ.get("DEBUG_MODE", "false").lower() == "true"
SESSIONS_DB_FILE = environ.get("DB_FILE", "/opt/storage/sessions.db")
EXTRA_INFORMATION = f"""
<additional_information>
**Current date and time is**: {datetime.now().isoformat()}
**Timezone is**: {environ.get("TZ","Europe/Berlin")}
</additional_information>
    """


def get_ollama_core_agent(
    user_id: str, session_id: str, enable_memory: bool = False
) -> Agent:
    """
    Get an instance of the Ollama agent.

    Initializes and returns an `Agent` configured with the provided parameters from
    environment variables.

    Parameters:
     user_id (str): The ID of the user.
     session_id (str): The session ID for the agent.
     enable_memory (bool, optional): Flag indicating whether to enable memory for the agent.

    Returns:
     Agent: An instance of the Ollama agent configured with specified parameters.
    """

    storage = None
    memory = None
    num_history_runs = 0
    if enable_memory:
        num_history_runs = 5
        storage = SqliteStorage(table_name="chat", db_file=SESSIONS_DB_FILE)
        memory_db = SqliteMemoryDb(table_name="memory", db_file=SESSIONS_DB_FILE)
        memory = Memory(model=OLLAMA_MODEL, db=memory_db)

    return Agent(
        model=OLLAMA_MODEL,
        name=ARIA_AGENT_CONFIG["name"],
        description=f"{ARIA_AGENT_CONFIG['description']}\n\n{EXTRA_INFORMATION}",
        role=ARIA_AGENT_CONFIG["role"],
        instructions=ARIA_AGENT_CONFIG["instructions"],
        goal=ARIA_AGENT_CONFIG["goal"],
        user_id=user_id,
        session_id=session_id,
        enable_agentic_memory=enable_memory,
        enable_user_memories=enable_memory,
        add_history_to_messages=enable_memory,
        read_chat_history=enable_memory,
        read_tool_call_history=enable_memory,
        enable_session_summaries=enable_memory,
        num_history_runs=num_history_runs,
        memory=memory,
        storage=storage,
        debug_mode=DEBUG_MODE,
        show_tool_calls=DEBUG_MODE,
        tools=[
            searxng_tools,
            reasoning_tools,
            youtube_tools,
            weather_tools,
            yfinance_tools,
            calulator_tools,
        ],
    )


def get_prompt_improver_agent() -> Agent:
    """
    Get an instance of the Prompt Improver agent.

    Initializes and returns an `Agent` configured to improve prompts without changing
    their original meaning. This agent uses the same Ollama model as the core agent
    but with different configuration parameters optimized for prompt improvement.

    Returns:
     Agent: An instance of the Prompt Improver agent configured with specified parameters.
    """

    return Agent(
        model=OLLAMA_MODEL,
        name=PROMPT_IMPROVER_AGENT_CONFIG["name"],
        description=f"{ARIA_AGENT_CONFIG['description']}\n\n{EXTRA_INFORMATION}",
        role=PROMPT_IMPROVER_AGENT_CONFIG["role"],
        instructions=PROMPT_IMPROVER_AGENT_CONFIG["instructions"],
        goal=PROMPT_IMPROVER_AGENT_CONFIG["goal"],
        add_datetime_to_instructions=True,
        debug_mode=DEBUG_MODE,
        show_tool_calls=DEBUG_MODE,
        tools=[reasoning_tools],
        response_model=ImprovedPromptResponse,
    )
