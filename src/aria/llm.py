import platform
import uuid
from datetime import datetime
from typing import Any, cast

from chromadb.api import ClientAPI as ChromaClientAPI
from llama_index.core.agent.workflow import (
    AgentOutput,
    AgentSetup,
    AgentWorkflow,
    ToolCall,
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

from aria.agents import get_chatter_agent
from aria.config.models import Vision as VisionConfig


class StatefulAgentWorkflow(AgentWorkflow):
    """`AgentWorkflow` variant that keeps custom state in `ctx.store` in sync.

    LlamaIndex's built-in [`AgentWorkflow`](src/aria/llm.py:35) seeds
    ``ctx.store['state']`` from ``initial_state`` and exposes that state to
    the LLM via ``state_prompt``, but it does not provide a reducer hook for
    streamed workflow events. This subclass closes that gap by applying
    [`state_reducer()`](src/aria/llm.py:136) to the live context state.
    """

    async def reduce_state(self, ctx: Any, ev: Any) -> "WorkflowState":
        """Apply [`state_reducer()`](src/aria/llm.py:136) to the stored state.

        Args:
            ctx: Workflow context exposing ``ctx.store``.
            ev: Streamed workflow event to reduce into the state.

        Returns:
            The updated workflow state persisted back into ``ctx.store``.
        """
        state = await ctx.store.get("state", default=None)
        if state is None:
            state = dict(initial_workflow_state(root_agent=self.root_agent))

        reduced_state = state_reducer(cast(WorkflowState, state), ev)
        await ctx.store.set("state", reduced_state)
        return reduced_state

    async def run_agent_step(self, ctx: Any, ev: AgentSetup) -> AgentOutput:
        """Run the parent agent step and synchronize custom state.

        This override preserves the original event contract of
        [`AgentWorkflow.run_agent_step()`](src/aria/llm.py:62) so workflow
        validation still sees [`AgentOutput`](src/aria/llm.py:8) as a produced
        event.
        """
        output = await super().run_agent_step(ctx, ev)
        await self.reduce_state(ctx, output)
        return output

    async def call_tool(self, ctx: Any, ev: ToolCall) -> ToolCallResult:
        """Run the parent tool call step and synchronize custom state.

        This override preserves the original event contract of
        [`AgentWorkflow.call_tool()`](src/aria/llm.py:68) so workflow
        validation still sees [`ToolCallResult`](src/aria/llm.py:10) as a
        produced event.
        """
        result = await super().call_tool(ctx, ev)
        await self.reduce_state(ctx, result)
        return result


# Reuse base step metadata so overridden methods stay discoverable.
StatefulAgentWorkflow.run_agent_step._step_config = (  # type: ignore[attr-defined]
    AgentWorkflow.run_agent_step._step_config
)
StatefulAgentWorkflow.call_tool._step_config = (  # type: ignore[attr-defined]
    AgentWorkflow.call_tool._step_config
)


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
    """Minimal shared state threaded through the agent workflow.

    This dict is seeded into ``ctx.store`` by :func:`get_agent_workflow` via
    ``AgentWorkflow(initial_state=...)``. In this project, live updates are
    performed by :class:`StatefulAgentWorkflow`, which applies
    :func:`state_reducer` after every :class:`AgentOutput` and
    :class:`ToolCallResult` event so that the state reflects the latest
    activity within the current workflow context.

    Attributes:
        current_agent: Name of the agent that is currently active.
        tool_calls: Append-only log of every tool invocation during the run.
        last_error: Most recent tool error message, or ``None`` if the last
            tool call succeeded.
    """

    current_agent: str
    tool_calls: list[ToolCallRecord]
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
        #     current_agent="Aria", tool_calls=[], last_error=None
        # )
    """
    return WorkflowState(
        current_agent=root_agent,
        tool_calls=[],
        last_error=None,
    )


def state_reducer(state: WorkflowState, ev: Any) -> WorkflowState:
    """Update *state* in response to a workflow event.

    This function is designed to be called after relevant events emitted by the
    :class:`AgentWorkflow` run loop. In this project it is invoked by
    :class:`StatefulAgentWorkflow` after agent-output and tool-result steps. It
    handles two event types:

    * :class:`AgentOutput` — updates ``current_agent``.
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
            response=..., current_agent_name="Aria", tool_calls=[]
        )
        state = state_reducer(state, fake_output)
        assert state["current_agent"] == "Aria"
    """
    if isinstance(ev, AgentOutput):
        state["current_agent"] = ev.current_agent_name

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

    from aria.tools.development.constants import RESTRICTED_BUILTINS

    tz = timestamp.astimezone().tzinfo
    lines: list[str] = [
        f"- **Date**: {date_str}, {timestamp.strftime('%H:%M')} ({tz})",
        f"- **OS**: {host}",
        f"- **Restricted builtins**: {', '.join(sorted(RESTRICTED_BUILTINS))}",
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
    """Build the single-agent workflow used by the UI.

    Returns a :class:`StatefulAgentWorkflow` with the unified Aria agent
    as the sole agent. All tools are loaded from the centralized registry
    inside the agent factory — no specialist agents or handoffs.

    Args:
        llm: LLM instance used by the agent.

    Returns:
        A fully constructed :class:`AgentWorkflow`.
    """

    chatter = get_chatter_agent(
        llm=llm,
        vl_api_base=VisionConfig.api_url,
        vl_model=VisionConfig.model,
        extras=get_instructions_extras(agent_name="aria"),
    )

    workflow = StatefulAgentWorkflow(
        agents=[chatter],
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
    token_limit: int = 65536,
    llm: OpenAILike | None = None,
) -> Memory:
    """Create a Memory instance backed by a per-thread ChromaDB vector store.

    The memory system uses a hybrid approach with three tiers:

    1. **Recent History** (80% of token_limit): Raw message text kept in
       active buffer. When this exceeds ``token_flush_size``, older messages
       are moved to long-term storage.

    2. **Fact Extraction** (if LLM provided): Structured facts extracted
       from flushed messages. Token-efficient way to preserve key information.

    3. **Vector Memory** (20% of token_limit): Semantic search over
       flushed messages stored in ChromaDB. Retrieves relevant context
       based on similarity to current query.

    Args:
        vector_db: ChromaDB client used to get or create the thread collection.
        embed_model: Embedding model for encoding queries and documents.
        thread_id: Unique thread identifier; used as both the ChromaDB
            collection name (for vector store isolation) and the LlamaIndex
            ``Memory.session_id`` (so the ``VectorMemoryBlock`` metadata
            filter always matches embeddings from the same thread, across
            all sessions).
        token_limit: Total token budget shared between the short-term chat
            buffer and the vector-retrieved context. Must be less than
            ``CHAT_CONTEXT_SIZE`` to leave room for system prompts, tools,
            and model response generation. Default is 65536.
        llm: LLM instance for fact extraction in long-term memory.
            If provided, enables FactExtractionMemoryBlock.

    Returns:
        A configured :class:`Memory` instance.

    Note:
        The ``token_limit`` is validated during preflight checks to ensure
        it doesn't exceed 75% of ``CHAT_CONTEXT_SIZE``. This buffer accounts
        for system prompts (~2-4K tokens), tool definitions (~1-2K tokens),
        and response generation space.
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
        # Flush 8192 tokens at a time to long-term memory
        token_flush_size=8192,
    )

    return memory


def get_embeddings_model(
    api_base: str, model_name: str
) -> OpenAILikeEmbedding:
    return OpenAILikeEmbedding(
        api_base=api_base,
        model_name=model_name,
    )
