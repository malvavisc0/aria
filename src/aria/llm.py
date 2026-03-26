import platform
import uuid
from datetime import datetime
from typing import Any

from chromadb.api import ClientAPI as ChromaClientAPI
from llama_index.core.agent.workflow import (
    AgentOutput,
    AgentWorkflow,
    ToolCallResult,
)
from llama_index.core.memory import (
    FactExtractionMemoryBlock,
    InsertMethod,
    Memory,
    VectorMemoryBlock,
)
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from llama_index.llms.openai_like import OpenAILike
from llama_index.vector_stores.chroma import ChromaVectorStore
from typing_extensions import TypedDict

from aria.agents import (
    get_chatter_agent,
    get_imdb_exper_agent,
    get_market_analyst_agent,
    get_python_developer_agent,
    get_web_researcher_agent,
)
from aria.config.models import Vision as VisionConfig


class ToolCallRecord(TypedDict):
    """A single tool invocation captured in the workflow state.

    Attributes:
        agent: Name of the agent that invoked the tool.
        tool: Name of the tool that was called.
        args: Keyword arguments passed to the tool.
        result: String representation of the tool's output.
        error: Error message if the tool raised an exception, else ``None``.
    """

    agent: str
    tool: str
    args: dict
    result: str
    error: str | None


class WorkflowState(TypedDict):
    """Minimal shared state threaded through the multi-agent workflow.

    This dict is seeded into ``ctx.store`` by :func:`get_agent_workflow` via
    ``AgentWorkflow(initial_state=...)``.  The :func:`state_reducer` function
    updates it after every :class:`AgentOutput` and :class:`ToolCallResult`
    event so that the state always reflects the latest activity.

    Attributes:
        current_agent: Name of the agent that is currently active.
        tool_calls: Append-only log of every tool invocation during the run.
        handoffs: Ordered list of agent names visited (breadcrumb trail).
        last_error: Most recent tool error message, or ``None`` if the last
            tool call succeeded.
    """

    current_agent: str
    tool_calls: list[ToolCallRecord]
    handoffs: list[str]
    last_error: str | None


def initial_workflow_state(root_agent: str) -> WorkflowState:
    """Return a fresh :class:`WorkflowState` for a new workflow run.

    Args:
        root_agent: Name of the root agent (used to seed ``current_agent``).

    Returns:
        A :class:`WorkflowState` with empty collections and no error.

    Example::

        state = initial_workflow_state("Aria")
        # WorkflowState(
        #     current_agent="Aria", tool_calls=[], handoffs=[], last_error=None
        # )
    """
    return WorkflowState(
        current_agent=root_agent,
        tool_calls=[],
        handoffs=[],
        last_error=None,
    )


def state_reducer(state: WorkflowState, ev: Any) -> WorkflowState:
    """Update *state* in response to a workflow event.

    This function is designed to be called after every event emitted by the
    :class:`AgentWorkflow` run loop.  It handles two event types:

    * :class:`AgentOutput` — updates ``current_agent`` and appends to
      ``handoffs`` when a ``handoff`` tool call is detected.
    * :class:`ToolCallResult` — appends a :class:`ToolCallRecord` to
      ``tool_calls`` and updates ``last_error``.

    All other event types are ignored and the state is returned unchanged.

    Args:
        state: The current workflow state dict (mutated in-place and returned).
        ev: Any event object emitted by the workflow.

    Returns:
        The updated :class:`WorkflowState`.

    Example::

        from llama_index.core.agent.workflow import AgentOutput

        state = initial_workflow_state("Aria")
        fake_output = AgentOutput(
            response=..., current_agent_name="Wanderer", tool_calls=[]
        )
        state = state_reducer(state, fake_output)
        assert state["current_agent"] == "Wanderer"
    """
    if isinstance(ev, AgentOutput):
        state["current_agent"] = ev.current_agent_name
        for tc in ev.tool_calls:
            if tc.tool_name == "handoff":
                to_agent: str = tc.tool_kwargs.get("to_agent", "")
                if to_agent:
                    state["handoffs"].append(to_agent)

    elif isinstance(ev, ToolCallResult):
        output = ev.tool_output
        is_error: bool = getattr(output, "is_error", False)
        raw_output: str = str(getattr(output, "content", output))

        record = ToolCallRecord(
            agent=state["current_agent"],
            tool=ev.tool_name,
            args=ev.tool_kwargs,
            result=raw_output,
            error=raw_output if is_error else None,
        )
        state["tool_calls"].append(record)
        state["last_error"] = record["error"]

    return state


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

    shell_hint = (
        "PowerShell/cmd"
        if platform.system() == "Windows"
        else "/bin/bash (likely)"
    )

    lines: list[str] = [
        f"- **Current date**: {date_str}",
        f"- **Current time**: {timestamp.strftime('%H:%M')}",
        f"- **Timezone**: {timestamp.astimezone().tzinfo}",
        f"- **OS**: {host}",
        f"- **Architecture**: {platform.machine()}",
        f"- **Shell**: {shell_hint}",
    ]
    if add_agent_id:
        lines.append(f"- **Agent ID**: {generate_agent_id(agent_name)}")
    return "\n".join(lines)


def get_chat_llm(api_base: str) -> OpenAILike:
    """Create the chat LLM client used by the application.

    Args:
        api_base: Base URL for the OpenAI-compatible API.

    Returns:
        An :class:`OpenAILike` LLM instance configured to talk to
        ``api_base``.

    Notes:
        The application supplies a dummy API key here because some
        OpenAI-compatible servers require the header to be present even when
        authentication is handled elsewhere (e.g., via a reverse proxy).
    """
    llm = OpenAILike(
        api_base=api_base,
        api_key="sk-dummy",
        is_chat_model=True,
        is_function_calling_model=True,
    )
    return llm


def get_agent_workflow(llm: OpenAILike) -> AgentWorkflow:
    """Build the multi-agent workflow used by the UI.

    This wires together the project's agent factory functions and returns a
    single :class:`AgentWorkflow` with Chatter as the root agent. Chatter
    routes requests to specialist agents through handoffs. PDF parsing is
    handled directly by Chatter via the ``parse_pdf`` tool — no VL agent
    handoff is needed.

    Args:
        llm: LLM instance shared across all chat/reasoning agents.

    Returns:
        A fully constructed :class:`AgentWorkflow`.
    """

    # Specialist agents
    imdb_expert = get_imdb_exper_agent(
        llm=llm,
        extras=get_instructions_extras(agent_name="Spielberg"),
        can_handoff_to=["Wanderer"],
    )
    market_analyst = get_market_analyst_agent(
        llm=llm,
        extras=get_instructions_extras(agent_name="Wizard"),
        can_handoff_to=["Wanderer", "Guido"],
    )
    python_developer = get_python_developer_agent(
        llm=llm,
        extras=get_instructions_extras(agent_name="Guido"),
        can_handoff_to=["Wanderer"],
    )
    web_researcher = get_web_researcher_agent(
        llm=llm,
        extras=get_instructions_extras(agent_name="Wanderer"),
        can_handoff_to=["Wizard", "Guido", "Spielberg"],
    )
    # Create Chatter as root agent
    chatter = get_chatter_agent(
        llm=llm,
        vl_api_base=VisionConfig.api_url,
        vl_model=VisionConfig.model,
        extras=get_instructions_extras(agent_name="aria"),
        can_handoff_to=[
            "Guido",
            "Wanderer",
            "Wizard",
            "Spielberg",
        ],
    )

    # Initialize Workflow (Chatter is the root agent)
    workflow = AgentWorkflow(
        agents=[
            chatter,
            market_analyst,
            python_developer,
            web_researcher,
            imdb_expert,
        ],
        root_agent=chatter.name,
        # Cast to plain dict: AgentWorkflow expects Dict, WorkflowState is
        # a TypedDict (structurally compatible at runtime).
        initial_state=dict(initial_workflow_state(root_agent=chatter.name)),
    )
    return workflow


def get_default_memory(
    vector_db: ChromaClientAPI,
    embed_model: OpenAIEmbedding,
    thread_id: str,
    token_limit: int = 24576,
    llm: OpenAILike | None = None,
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
            buffer and the vector-retrieved context. Default is 24576 to
            utilize the embedding model's 32K context window effectively.
        llm: LLM instance for fact extraction in long-term memory.
            If provided, enables FactExtractionMemoryBlock.

    Returns:
        A configured :class:`Memory` instance.
    """
    collection = vector_db.get_or_create_collection(thread_id)

    # Build memory blocks list
    memory_blocks: list = []

    # Add fact extraction block if LLM is provided
    if llm is not None:
        memory_blocks.append(
            FactExtractionMemoryBlock(
                name="extracted_facts",
                llm=llm,
                # Extract up to 50 facts from flushed messages
                max_facts=50,
                # Priority 1: can be disabled if token budget is exceeded
                priority=1,
            )
        )

    # Add vector memory block for semantic search
    memory_blocks.append(
        VectorMemoryBlock(
            name="vector_memory",
            vector_store=ChromaVectorStore(chroma_collection=collection),
            embed_model=embed_model,
            # Retrieve top 5 similar messages (increased from 3)
            similarity_top_k=5,
            # Include more context from previous messages
            retrieval_context_window=10,
            # Priority 2: lower priority than fact extraction
            priority=2,
        )
    )

    memory = Memory.from_defaults(
        session_id=thread_id,
        # Insert retrieved memory as system prompts
        insert_method=InsertMethod.SYSTEM,
        memory_blocks=memory_blocks,
        # Total tokens for (Recent History + Vector Results)
        token_limit=token_limit,
        # 80% for Recent History, 20% for Vector Results
        # This keeps more recent context in working memory
        chat_history_token_ratio=0.8,
        # Flush 8196 tokens at a time to long-term memory
        token_flush_size=8196,
    )

    return memory


def get_embeddings_model(
    api_base: str, model_name: str
) -> OpenAILikeEmbedding:
    return OpenAILikeEmbedding(
        api_base=api_base,
        model_name=model_name,
    )
