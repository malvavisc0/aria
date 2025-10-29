from datetime import datetime
from os import environ

from agno.agent import Agent
from agno.db.redis import RedisDb
from agno.models.ollama import Ollama
from aria.ai.configs import (
    chatter_agent_description,
    chatter_agent_goal,
    chatter_agent_instructions,
    chatter_agent_name,
    chatter_agent_role,
    prompt_improver_agent_description,
    prompt_improver_agent_goal,
    prompt_improver_agent_instructions,
    prompt_improver_agent_name,
    prompt_improver_agent_role,
)
from aria.ai.kits import (
    calculator_tools,
    downloader_tools,
    reasoning_tools,
    searxng_tools,
    thinking_tools,
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
        "temperature": float(environ.get("OLLAMA_MODEL_TEMPERATURE", 0.65)),
        "mirostat": 2,
        "repeat_last_n": -1,
        "top_k": 20,
        "top_p": 0.9,
        "seed": 10,
        "keep_alive": "10m",
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
REDIS_HOST = environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(environ.get("REDIS_PORT", 6379))
REDIS_DB = int(environ.get("REDIS_DB", 10))


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
    num_history_runs = 0
    if enable_memory:
        num_history_runs = 3
        storage = RedisDb(
            db_prefix="chat", db_url=f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
        )

    return Agent(
        model=OLLAMA_MODEL,
        name=chatter_agent_name,
        description=f"{chatter_agent_description}\n\n{EXTRA_INFORMATION}",
        role=chatter_agent_role,
        instructions=f"{chatter_agent_instructions}\n\n{chatter_agent_goal}",
        user_id=user_id,
        session_id=session_id,
        enable_user_memories=enable_memory,
        read_chat_history=enable_memory,
        enable_session_summaries=enable_memory,
        num_history_runs=num_history_runs,
        db=storage,
        debug_mode=DEBUG_MODE,
        tools=[
            searxng_tools,
            thinking_tools,
            reasoning_tools,
            youtube_tools,
            weather_tools,
            yfinance_tools,
            calculator_tools,
            downloader_tools,
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
        name=prompt_improver_agent_name,
        description=f"{prompt_improver_agent_description}\n\n{EXTRA_INFORMATION}",
        role=prompt_improver_agent_role,
        instructions=f"{prompt_improver_agent_instructions}\n\n{prompt_improver_agent_goal}",
        add_datetime_to_context=True,
        debug_mode=DEBUG_MODE,
        tools=[thinking_tools],
        output_schema=ImprovedPromptResponse,
    )
