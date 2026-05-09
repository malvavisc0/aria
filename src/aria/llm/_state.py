"""Workflow state types, reducers, and the StatefulAgentWorkflow class.

This module owns the shared-state machinery threaded through the agent
workflow: the :class:`WorkflowState` TypedDict, the :func:`state_reducer`
pure function, and :class:`StatefulAgentWorkflow` which wires them into
the LlamaIndex :class:`AgentWorkflow` run-loop.
"""

import copy
from typing import Any, cast

from llama_index.core.agent.workflow import (
    AgentOutput,
    AgentSetup,
    AgentWorkflow,
    ToolCall,
    ToolCallResult,
)
from llama_index.core.tools.types import ToolOutput
from loguru import logger
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

    A pristine copy of the initial state is kept in ``_state_template`` so
    that every new workflow run receives a fresh, un-mutated state —
    preventing cross-conversation leakage of accumulated tool-call records.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Store a deep copy that is never mutated, so each run can start
        # from a clean slate regardless of how many tool calls happened
        # in previous conversations.
        self._state_template: dict = copy.deepcopy(self.initial_state)

    async def _init_context(self, ctx: Any, ev: Any) -> None:
        """Initialise context with a *fresh* copy of the initial state.

        The parent ``_init_context`` sets ``ctx.store["state"]`` to
        ``self.initial_state`` — a single dict instance that is shared
        across all runs.  Because :func:`state_reducer` mutates that
        dict in-place (appending to ``tool_calls``), the state silently
        accumulates records from every previous conversation.

        Overriding here to deep-copy from the pristine ``_state_template``
        ensures each run starts with an empty ``tool_calls`` list.
        """
        await super()._init_context(ctx, ev)
        await ctx.store.set("state", copy.deepcopy(self._state_template))

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
        If the LLM produces an empty terminal response after a tool failure,
        a single retry is attempted before injecting a synthesized error report.
        """
        # DIAGNOSTIC: log what's being sent
        msg_count = len(ev.input)
        approx_tokens = sum(len(str(m.content or "")) // 4 for m in ev.input)
        logger.info(
            f"run_agent_step: {msg_count} messages, ~{approx_tokens} tokens "
            f"(roles: {[m.role.value for m in ev.input[:5]]}...)"
        )
        # END DIAGNOSTIC

        try:
            output = await super().run_agent_step(ctx, ev)
        except Exception:
            # Re-raise after recording the failure in workflow state so that
            # downstream consumers (e.g. UI error handlers) can inspect
            # ``ctx.store["state"]["last_error"]`` for diagnostics.
            raise
        await self.reduce_state(ctx, output)

        # Guard against empty terminal responses after a tool failure.
        # Some local models occasionally produce no text after receiving a
        # tool error result — retry once, then synthesize a fallback reply.
        if not output.tool_calls and not (output.response.content or "").strip():
            state = await ctx.store.get("state", default=None)
            last_err = (state or {}).get("last_error")
            if last_err:
                # Retry the agent step once to give the model another chance.
                try:
                    output = await super().run_agent_step(ctx, ev)
                    await self.reduce_state(ctx, output)
                except Exception:
                    pass

                # If still empty after retry, inject synthesized response.
                if (
                    not output.tool_calls
                    and not (output.response.content or "").strip()
                ):
                    output.response.content = (
                        f"The tool call encountered an error:\n\n"
                        f"```\n{last_err}\n```\n\n"
                        "I'll try a different approach if you'd like — "
                        "just let me know how to proceed."
                    )
        return output

    async def call_tool(self, ctx: Any, ev: ToolCall) -> ToolCallResult:
        """Run the parent tool call step and synchronize custom state.

        If the parent ``call_tool`` raises unexpectedly (e.g. a failure in
        tool lookup, event streaming, or an uncaught tool exception), the
        error is caught and wrapped in an error :class:`ToolCallResult` so
        the agent can surface it to the user instead of crashing the
        workflow.
        """
        try:
            result = await super().call_tool(ctx, ev)
        except Exception as exc:
            # Build an error result so the workflow survives and the agent
            # can report the failure to the user.
            result = ToolCallResult(
                tool_name=ev.tool_name,
                tool_kwargs=ev.tool_kwargs,
                tool_id=ev.tool_id,
                tool_output=ToolOutput(
                    content=f"Tool execution failed: {exc}",
                    tool_name=ev.tool_name,
                    raw_input=ev.tool_kwargs,
                    raw_output=str(exc),
                    is_error=True,
                    exception=exc,
                ),
                return_direct=False,
            )
        await self.reduce_state(ctx, result)
        return result


# Reuse base step metadata so overridden methods stay discoverable.
StatefulAgentWorkflow.run_agent_step._step_config = (  # type: ignore[attr-defined]
    AgentWorkflow.run_agent_step._step_config
)
StatefulAgentWorkflow.call_tool._step_config = (  # type: ignore[attr-defined]
    AgentWorkflow.call_tool._step_config
)
