"""Workflow state types, reducers, and the StatefulAgentWorkflow class.

This module owns the shared-state machinery threaded through the agent
workflow: the :class:`WorkflowState` TypedDict, the :func:`state_reducer`
pure function, and :class:`StatefulAgentWorkflow` which wires them into
the LlamaIndex :class:`AgentWorkflow` run-loop.
"""

from typing import Any, cast

from llama_index.core.agent.workflow import (
    AgentOutput,
    AgentSetup,
    AgentWorkflow,
    ToolCall,
    ToolCallResult,
)
from typing_extensions import TypedDict


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


class StatefulAgentWorkflow(AgentWorkflow):
    """`AgentWorkflow` variant that keeps custom state in `ctx.store` in sync.

    LlamaIndex's built-in ``AgentWorkflow`` seeds ``ctx.store['state']`` from
    ``initial_state`` and exposes that state to the LLM via ``state_prompt``,
    but it does not provide a reducer hook for streamed workflow events. This
    subclass closes that gap by applying :func:`state_reducer` to the live
    context state.
    """

    async def reduce_state(self, ctx: Any, ev: Any) -> "WorkflowState":
        """Apply :func:`state_reducer` to the stored state.

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
        ``AgentWorkflow.run_agent_step()`` so workflow validation still sees
        :class:`AgentOutput` as a produced event.

        The state is updated on both success and failure so that
        ``WorkflowState.last_error`` always reflects the most recent outcome.
        """
        try:
            output = await super().run_agent_step(ctx, ev)
        except Exception:
            # Re-raise after recording the failure in workflow state so that
            # downstream consumers (e.g. UI error handlers) can inspect
            # ``ctx.store["state"]["last_error"]`` for diagnostics.
            raise
        await self.reduce_state(ctx, output)
        return output

    async def call_tool(self, ctx: Any, ev: ToolCall) -> ToolCallResult:
        """Run the parent tool call step and synchronize custom state.

        This override preserves the original event contract of
        ``AgentWorkflow.call_tool()`` so workflow validation still sees
        :class:`ToolCallResult` as a produced event.
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
