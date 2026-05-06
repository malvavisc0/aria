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
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.memory import (
    FactExtractionMemoryBlock,
    InsertMethod,
    Memory,
    VectorMemoryBlock,
)
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai_like import OpenAILike
from llama_index.vector_stores.chroma import ChromaVectorStore
from typing_extensions import TypedDict

from aria.agents import get_chatter_agent


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
        f"{timestamp.strftime('%B')} {day}{_ordinal_suffix(day)} {timestamp.year}"
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


def get_chat_llm(
    api_base: str, model: str = "", api_key: str = "sk-aria"
) -> OpenAILike:
    """Create the chat LLM client used by the application.

    Args:
        api_base: Base URL for the OpenAI-compatible API.
        model: Model name to send in API requests (e.g. ``"Lucy-128k-gguf"``).
        api_key: API key sent in ``Authorization: Bearer`` header.
            Must match the ``--api-key`` used to start the vLLM server.

    Returns:
        An :class:`OpenAILike` LLM instance configured to talk to
        ``api_base``.
    """
    llm = OpenAILike(
        api_base=api_base,
        model=model,
        api_key=api_key,
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
    embed_model: BaseEmbedding,
    thread_id: str,
    token_limit: int = 32768,
    llm: OpenAILike | None = None,
) -> Memory:
    """Create a Memory instance backed by a per-thread ChromaDB vector store.

    Uses a hybrid approach: recent history buffer (80%) + vector retrieval
    (20%). Older messages are flushed to long-term storage when the buffer
    fills up.

    Args:
        vector_db: ChromaDB client for the thread collection.
        embed_model: Embedding model for semantic search.
        thread_id: Thread ID used as ChromaDB collection name and session ID.
        token_limit: Total token budget for history + vector context.
            Default 32768 — leaves room for system prompt and tool schemas.
        llm: If provided, enables fact extraction from flushed messages.

    Returns:
        A configured :class:`Memory` instance.
    """
    collection = vector_db.get_or_create_collection(thread_id)

    memory_blocks: list = []

    if llm is not None:
        memory_blocks.append(
            FactExtractionMemoryBlock(
                name="extracted_facts",
                llm=llm,
                max_facts=40,
                priority=1,
            )
        )

    memory_blocks.append(
        VectorMemoryBlock(
            name="vector_memory",
            vector_store=ChromaVectorStore(chroma_collection=collection),
            embed_model=embed_model,
            similarity_top_k=5,
            retrieval_context_window=2,
            priority=2,
        )
    )

    from aria.config.models import Embeddings as EmbeddingsConfig

    memory = Memory.from_defaults(
        session_id=thread_id,
        insert_method=InsertMethod.SYSTEM,
        memory_blocks=memory_blocks,
        token_limit=token_limit,
        chat_history_token_ratio=0.7,
        token_flush_size=EmbeddingsConfig.context_size,
    )

    return memory


def get_embeddings_model(
    model_name: str,
    device: str = "cpu",
) -> HuggingFaceEmbedding:
    """Create the embeddings model used by the application.

    Loads the model in-process via HuggingFace transformers — no separate
    embedding server required.  The native tokenizer handles truncation
    automatically, so long inputs (e.g. tool outputs) never crash the
    embedding call.

    Args:
        model_name: HuggingFace model ID or local path.
        device: Device to run on (``"cpu"`` or ``"cuda"``).

    Returns:
        A :class:`HuggingFaceEmbedding` instance.
    """
    return HuggingFaceEmbedding(
        model_name=model_name,
        device=device,
        trust_remote_code=True,
    )
