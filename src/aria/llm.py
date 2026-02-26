import platform
import uuid
from datetime import datetime

from chromadb.api import ClientAPI as ChromaClientAPI
from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.core.memory import InsertMethod, Memory, VectorMemoryBlock
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.chroma import ChromaVectorStore

from aria.agents import (
    get_chatter_agent,
    get_file_editor_agent,
    get_market_analyst_agent,
    get_python_developer_agent,
    get_reasoning_agent,
    get_web_researcher_agent,
)


def generate_agent_id(agent_name: str) -> str:
    """Generate a unique, human-readable identifier for an agent.

    The generated ID is deterministic in shape but random in value:

    ``{agent_name}_{8-hex-chars}``

    Args:
        agent_name: Prefix identifying the agent.

    Returns:
        A unique agent ID string.
        Example: ``"aria_1a2b3c4d"``.
    """
    return f"{agent_name}_{uuid.uuid4().hex[:8]}"


def get_instructions_extras(agent_name: str, add_agent_id: bool = True) -> str:
    """
    Generates a formatted string containing additional information for
    instructions.

    This combines the current date and time with a unique agent ID (if
    requested) to provide context.
    It includes the following information in the output:
    - Current date (formatted as 'Month Day<suffix> Year',
      e.g. 'January 15th 2026')
    - Current time (formatted as 'HH:MM')
    - The system's timezone
    - Host operating system name and version
    - A unique ID generated for the agent (if add_agent_id is True)

    Args:
        agent_name (str): The name of the agent, used for generating a unique
            agent ID.
        add_agent_id (bool): Whether to include the unique agent ID in the
            output string. Defaults to True.

    Returns:
        str: A formatted string containing the current date, time, timezone,
            host information, and optionally agent ID.

            Example (no agent id)::

                "- **Current date**: January 15th 2026 "
                "- **Current time**: 14:30 "
                "- **Timezone**: America/New_York\n"
                "- **Host**: Linux 6.18"

            Example (with agent id)::

                "- **Current date**: January 15th 2026 "
                "- **Current time**: 14:30 "
                "- **Timezone**: America/New_York\n"
                "- **Host**: Linux 6.18\n"
                "- **Agent ID**: aria_1a2b3c4d"
    """

    def _ordinal_suffix(day: int) -> str:
        # 11th, 12th, 13th are special-cased.
        if 11 <= (day % 100) <= 13:
            return "th"
        return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

    timestamp = datetime.now()
    host = f"{platform.system()} {platform.release()}"

    day = timestamp.day
    date_str = (
        f"{timestamp.strftime('%B')} "
        f"{day}{_ordinal_suffix(day)} "
        f"{timestamp.year}"
    )

    lines: list[str] = [
        f"- **Current date**: {date_str}",
        f"- **Current time**: {timestamp.strftime('%H:%M')}",
        f"- **Timezone**: {timestamp.astimezone().tzinfo}",
        f"- **Host**: {host}",
    ]
    if add_agent_id:
        lines.append(f"- **Agent ID**: {generate_agent_id(agent_name)}")
    return "\n".join(lines)


def get_chat_llm(api_base: str) -> OpenAI:
    """Create the chat LLM client used by the application.

    Args:
        api_base: Base URL for the OpenAI-compatible API.

    Returns:
        An [`OpenAI`](src/aria2/utils.py:79) LLM instance configured to talk
        to ``api_base``.

    Notes:
        The application supplies a dummy API key here because some
        OpenAI-compatible servers require the header to be present even when
        authentication is handled elsewhere (e.g., via a reverse proxy).
    """
    llm = OpenAI(api_base=api_base, api_key="sk-dummy")
    return llm


def get_agent_workflow(llm: OpenAI) -> AgentWorkflow:
    """Build the multi-agent workflow used by the UI.

    This wires together the project's agent factory functions and returns a
    single [`AgentWorkflow`](src/aria2/utils.py:6) with Chatter as the root
    agent. Chatter routes requests to specialist agents through handoffs.

    Args:
        llm: LLM instance shared across all agents.

    Returns:
        A fully constructed [`AgentWorkflow`](src/aria2/utils.py:6).
    """
    # Create specialist agents
    file_editor = get_file_editor_agent(
        llm=llm, extras=get_instructions_extras(agent_name="notepad")
    )
    market_analyst = get_market_analyst_agent(
        llm=llm, extras=get_instructions_extras(agent_name="wizard")
    )
    python_developer = get_python_developer_agent(
        llm=llm, extras=get_instructions_extras(agent_name="guido")
    )
    deep_reasoning = get_reasoning_agent(
        llm=llm, extras=get_instructions_extras(agent_name="socrates")
    )
    web_researcher = get_web_researcher_agent(
        llm=llm, extras=get_instructions_extras(agent_name="wanderer")
    )

    # Create Chatter as root agent
    chatter = get_chatter_agent(
        llm=llm, extras=get_instructions_extras(agent_name="aria")
    )

    # Initialize Workflow (Chatter is the root agent)
    workflow = AgentWorkflow(
        agents=[
            chatter,
            file_editor,
            market_analyst,
            python_developer,
            deep_reasoning,
            web_researcher,
        ],
        root_agent=chatter.name,
    )
    return workflow


def get_default_memory(
    vector_db: ChromaClientAPI,
    embed_model: OpenAIEmbedding,
    thread_id: str,
    token_limit: int = 5120,
) -> Memory:
    """Create a Memory instance backed by a per-thread ChromaDB vector store.

    Args:
        vector_db: ChromaDB client used to get or create the thread collection.
        embed_model: Embedding model for encoding queries and documents.
        thread_id: Unique thread identifier; used as both the ChromaDB
            collection name (for vector store isolation) and the LlamaIndex
            ``Memory.session_id`` (so the ``VectorMemoryBlock`` metadata
            filter always matches embeddings from the same thread, across
            all sessions).
        token_limit: Total token budget shared between the short-term chat
            buffer and the vector-retrieved context.

    Returns:
        A configured :class:`Memory` instance.
    """
    memory = Memory.from_defaults(
        session_id=thread_id,
        # Insert retrieved memory as system prompts
        insert_method=InsertMethod.SYSTEM,
        memory_blocks=[
            VectorMemoryBlock(
                vector_store=ChromaVectorStore(
                    chroma_collection=vector_db.get_or_create_collection(
                        thread_id
                    )
                ),
                embed_model=embed_model,
                # Retrieve top 3 similar messages
                similarity_top_k=3,
            )
        ],
        # Total tokens for (Recent History + Vector Results)
        token_limit=token_limit,
        # 70% for Recent History, 30% for Vector Results
        chat_history_token_ratio=0.7,
        token_flush_size=1024,
    )

    return memory


def get_embeddings_model(api_base: str) -> OpenAIEmbedding:
    return OpenAIEmbedding(api_base=api_base, api_key="sk-dummy")
