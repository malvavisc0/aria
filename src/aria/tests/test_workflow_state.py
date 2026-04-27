"""Tests for WorkflowState, initial_workflow_state, and state_reducer.

These tests exercise the shared-state machinery in :mod:`aria.llm` in
isolation — no LLM, no network, no agents required.
"""

from types import SimpleNamespace

import pytest
from llama_index.core.agent.workflow import AgentOutput, ToolCallResult
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.llms.llm import ToolSelection
from llama_index.core.tools.types import ToolOutput

from aria.llm import (
    StatefulAgentWorkflow,
    ToolCallRecord,
    WorkflowState,
    get_agent_workflow,
    get_chat_llm,
    initial_workflow_state,
    state_reducer,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent_output(
    agent_name: str,
    tool_calls: list[ToolSelection] | None = None,
) -> AgentOutput:
    """Build a minimal :class:`AgentOutput` for testing."""
    return AgentOutput(
        response=ChatMessage(content=""),
        current_agent_name=agent_name,
        tool_calls=tool_calls or [],
    )


def _make_tool_call_result(
    tool_name: str,
    tool_kwargs: dict,
    content: str,
    is_error: bool = False,
) -> ToolCallResult:
    """Build a minimal :class:`ToolCallResult` for testing."""
    output = ToolOutput(
        content=content,
        tool_name=tool_name,
        raw_input=tool_kwargs,
        raw_output=content,
        is_error=is_error,
    )
    return ToolCallResult(
        tool_name=tool_name,
        tool_kwargs=tool_kwargs,
        tool_id="test-id",
        tool_output=output,
        return_direct=False,
    )


# ---------------------------------------------------------------------------
# initial_workflow_state
# ---------------------------------------------------------------------------


class TestInitialWorkflowState:
    """Tests for :func:`initial_workflow_state`."""

    def test_current_agent_is_root(self):
        state = initial_workflow_state("Aria")
        assert state["current_agent"] == "Aria"

    def test_tool_calls_empty(self):
        state = initial_workflow_state("Aria")
        assert state["tool_calls"] == []

    def test_last_error_is_none(self):
        state = initial_workflow_state("Aria")
        assert state["last_error"] is None

    def test_different_root_agents(self):
        for name in ["Aria", "Other"]:
            state = initial_workflow_state(name)
            assert state["current_agent"] == name

    def test_returns_independent_lists(self):
        """Each call must return fresh list objects, not shared references."""
        s1 = initial_workflow_state("Aria")
        s2 = initial_workflow_state("Aria")
        s1["tool_calls"].append(
            ToolCallRecord(
                agent="Aria",
                tool="x",
                args={},
                result="r",
                error=None,
            )
        )
        assert s2["tool_calls"] == []


# ---------------------------------------------------------------------------
# state_reducer — AgentOutput events
# ---------------------------------------------------------------------------


class TestStateReducerAgentOutput:
    """Tests for :func:`state_reducer` handling :class:`AgentOutput`."""

    def test_updates_current_agent(self):
        state = initial_workflow_state("Aria")
        ev = _make_agent_output("Aria")
        result = state_reducer(state, ev)
        assert result["current_agent"] == "Aria"

    def test_agent_output_does_not_modify_tool_calls(self):
        state = initial_workflow_state("Aria")
        ev = _make_agent_output("Aria")
        state_reducer(state, ev)
        assert state["tool_calls"] == []

    def test_agent_output_does_not_modify_last_error(self):
        state = initial_workflow_state("Aria")
        ev = _make_agent_output("Aria")
        state_reducer(state, ev)
        assert state["last_error"] is None

    def test_returns_same_state_object(self):
        state = initial_workflow_state("Aria")
        ev = _make_agent_output("Aria")
        result = state_reducer(state, ev)
        assert result is state


# ---------------------------------------------------------------------------
# state_reducer — ToolCallResult events
# ---------------------------------------------------------------------------


class TestStateReducerToolCallResult:
    """Tests for :func:`state_reducer` handling :class:`ToolCallResult`."""

    def test_appends_tool_call_record(self):
        state = initial_workflow_state("Aria")
        ev = _make_tool_call_result("web_search", {"query": "test"}, "results")
        state_reducer(state, ev)
        assert len(state["tool_calls"]) == 1

    def test_tool_call_record_fields_success(self):
        state = initial_workflow_state("Aria")
        ev = _make_tool_call_result("web_search", {"query": "test"}, "results")
        state_reducer(state, ev)
        record = state["tool_calls"][0]
        assert record["agent"] == "Aria"
        assert record["tool"] == "web_search"
        assert record["args"] == {"query": "test"}
        assert record["result"] == "results"
        assert record["error"] is None

    def test_tool_call_record_fields_error(self):
        state = initial_workflow_state("Aria")
        ev = _make_tool_call_result("bad_tool", {}, "boom", is_error=True)
        state_reducer(state, ev)
        record = state["tool_calls"][0]
        assert record["tool"] == "bad_tool"
        assert record["error"] == "boom"

    def test_last_error_none_on_success(self):
        state = initial_workflow_state("Aria")
        ev = _make_tool_call_result("web_search", {}, "ok")
        state_reducer(state, ev)
        assert state["last_error"] is None

    def test_last_error_set_on_failure(self):
        state = initial_workflow_state("Aria")
        ev = _make_tool_call_result("bad_tool", {}, "boom", is_error=True)
        state_reducer(state, ev)
        assert state["last_error"] == "boom"

    def test_last_error_cleared_after_success(self):
        """A successful tool call after a failure must clear ``last_error``."""
        state = initial_workflow_state("Aria")
        state_reducer(
            state,
            _make_tool_call_result("bad_tool", {}, "boom", is_error=True),
        )
        state_reducer(state, _make_tool_call_result("good_tool", {}, "ok"))
        assert state["last_error"] is None

    def test_multiple_tool_calls_accumulate(self):
        state = initial_workflow_state("Aria")
        state_reducer(state, _make_tool_call_result("tool_a", {}, "a"))
        state_reducer(state, _make_tool_call_result("tool_b", {}, "b"))
        assert len(state["tool_calls"]) == 2
        assert state["tool_calls"][0]["tool"] == "tool_a"
        assert state["tool_calls"][1]["tool"] == "tool_b"

    def test_agent_name_in_record_reflects_current_agent(self):
        """Record ``agent`` field must use the agent active at call time."""
        state = initial_workflow_state("Aria")
        state_reducer(state, _make_agent_output("Aria"))
        state_reducer(state, _make_tool_call_result("reasoning", {}, "deep thought"))
        assert state["tool_calls"][0]["agent"] == "Aria"

    def test_returns_same_state_object(self):
        state = initial_workflow_state("Aria")
        ev = _make_tool_call_result("tool", {}, "out")
        result = state_reducer(state, ev)
        assert result is state


# ---------------------------------------------------------------------------
# state_reducer — unknown / unhandled event types
# ---------------------------------------------------------------------------


class TestStateReducerUnknownEvents:
    """Tests for :func:`state_reducer` with unrecognised event types."""

    @pytest.mark.parametrize(
        "event",
        [
            None,
            42,
            "a string event",
            object(),
            {"type": "unknown"},
        ],
    )
    def test_unknown_event_leaves_state_unchanged(self, event):
        state = initial_workflow_state("Aria")
        original_agent = state["current_agent"]
        state_reducer(state, event)
        assert state["current_agent"] == original_agent
        assert state["tool_calls"] == []
        assert state["last_error"] is None


class _FakeStore:
    def __init__(self, initial: dict[str, object] | None = None):
        self._data = dict(initial or {})

    async def get(self, key: str, default: object = None) -> object:
        return self._data.get(key, default)

    async def set(self, key: str, value: object) -> None:
        self._data[key] = value


class TestStatefulAgentWorkflowReduceState:
    """Tests for live state synchronization in StatefulAgentWorkflow."""

    @staticmethod
    def _make_workflow() -> StatefulAgentWorkflow:
        workflow = StatefulAgentWorkflow.__new__(StatefulAgentWorkflow)
        workflow.root_agent = "Aria"
        return workflow

    @pytest.mark.asyncio
    async def test_reduce_state_initializes_missing_state(self):
        workflow = self._make_workflow()
        ctx = SimpleNamespace(store=_FakeStore())

        result = await workflow.reduce_state(ctx, _make_agent_output("Aria"))

        assert result["current_agent"] == "Aria"
        assert result["tool_calls"] == []
        assert result["last_error"] is None

        stored_state = await ctx.store.get("state")
        assert stored_state == result

    @pytest.mark.asyncio
    async def test_reduce_state_updates_existing_state(self):
        workflow = self._make_workflow()
        existing_state: WorkflowState = initial_workflow_state("Aria")
        ctx = SimpleNamespace(store=_FakeStore({"state": existing_state}))

        result = await workflow.reduce_state(
            ctx,
            _make_tool_call_result("web_search", {"query": "test"}, "results"),
        )

        assert result["tool_calls"][0]["tool"] == "web_search"
        assert result["tool_calls"][0]["agent"] == "Aria"
        assert result["last_error"] is None

        stored_state = await ctx.store.get("state")
        assert stored_state is result


class TestStatefulAgentWorkflowRegistration:
    """Regression tests for step discovery on workflow overrides."""

    def test_override_steps_keep_step_metadata(self):
        assert hasattr(StatefulAgentWorkflow.run_agent_step, "_step_config")
        assert hasattr(StatefulAgentWorkflow.call_tool, "_step_config")

    def test_get_agent_workflow_validation_succeeds(self):
        workflow = get_agent_workflow(get_chat_llm("http://127.0.0.1:1"))

        workflow._validate()
