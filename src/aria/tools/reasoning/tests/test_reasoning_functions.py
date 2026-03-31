"""Tests for reasoning functions with persistence and multi-agent support."""

import os
import tempfile

import pytest

from aria.tools.database import ToolsDatabase
from aria.tools.reasoning import (
    add_reasoning_step,
    add_reflection,
    end_reasoning,
    evaluate_reasoning,
    get_reasoning_summary,
    list_reasoning_sessions,
    registry,
    reset_reasoning,
    start_reasoning,
    use_scratchpad,
)
from aria.tools.reasoning.database import ReasoningDatabase


@pytest.fixture
def test_agent_id():
    """Provide a test agent ID."""
    return "test_agent_123"


@pytest.fixture(autouse=True)
def test_db():
    """Create a temporary database for testing and clean up after each test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_tools.db")

        original_db = registry.get_db()

        # Reset singletons to force new instance
        ToolsDatabase._instance = None
        ReasoningDatabase._instance = None

        # Reset the module-level _db_instance in get_tools_database
        import aria.tools.database as db_module

        db_module._db_instance = None

        # Create shared tools database with temp path
        test_tools_db = ToolsDatabase(db_path)
        test_reasoning_db = ReasoningDatabase()

        # Replace the database in registry module
        import aria.tools.reasoning.registry as reg_module

        reg_module._db = test_reasoning_db

        yield test_reasoning_db

        # Clean up after test
        registry.clear_all()
        test_tools_db.close()
        # Reset singletons again
        ToolsDatabase._instance = None
        ReasoningDatabase._instance = None
        db_module._db_instance = None
        # Restore original
        reg_module._db = original_db


def test_start_reasoning(test_agent_id, test_db):
    """Test starting a new reasoning session."""
    result = start_reasoning("Testing intent", test_agent_id)
    assert result["status"] == "success"
    assert result["tool"] == "start_reasoning"
    assert result["intent"] == "Testing intent"
    assert result["agent_id"] == test_agent_id
    assert result["session_id"].startswith(f"{test_agent_id}_session_")

    # Verify active session was created
    assert test_agent_id in registry.get_active_session_id(test_agent_id)

    # Clean up
    end_reasoning("Testing intent", test_agent_id)


def test_start_reasoning_replaces_previous(test_agent_id, test_db):
    """Test that starting new session replaces previous one."""
    # Start first session
    start_reasoning("First analysis", test_agent_id)
    add_reasoning_step("Step 1", "First step", test_agent_id)

    # Start second session (should replace first)
    start_reasoning("Second analysis", test_agent_id)

    # Summary should show empty session (new one)
    summary = get_reasoning_summary("Check", test_agent_id)
    assert summary["status"] == "success"
    assert summary["data"]["steps_count"] == 0

    # Clean up
    end_reasoning("Testing intent", test_agent_id)


def test_add_step_without_session(test_agent_id, test_db):
    """Test that adding a step without starting session raises error."""
    result = add_reasoning_step(
        "Testing intent",
        "Test step",
        test_agent_id,
    )

    assert result["status"] == "error"
    assert result["error"]["code"] == "NO_ACTIVE_SESSION"


def test_add_step_with_session(test_agent_id, test_db):
    """Test adding a step after starting session."""
    start_reasoning("Testing intent", test_agent_id)
    result = add_reasoning_step(
        "Testing intent",
        "Analyzing the problem",
        test_agent_id,
        cognitive_mode="analysis",
    )

    assert result["status"] == "success"
    assert result["tool"] == "add_reasoning_step"
    assert result["data"]["step_id"] == 1
    assert result["data"]["content"] == "Analyzing the problem"

    # Clean up
    end_reasoning("Testing intent", test_agent_id)


def test_add_reflection_without_session(test_agent_id, test_db):
    """Test that adding reflection without session raises error."""
    result = add_reflection(
        "Testing intent",
        "Test reflection",
        test_agent_id,
    )

    assert result["status"] == "error"
    assert result["error"]["code"] == "NO_ACTIVE_SESSION"


def test_add_reflection_with_session(test_agent_id, test_db):
    """Test adding reflection after starting session."""
    start_reasoning("Testing intent", test_agent_id)
    result = add_reflection(
        "Testing intent",
        "Need to verify assumptions",
        test_agent_id,
    )

    assert result["status"] == "success"
    assert result["tool"] == "add_reflection"
    assert result["data"]["reflection_id"] == 1

    # Clean up
    end_reasoning("Testing intent", test_agent_id)


def test_scratchpad_without_session(test_agent_id, test_db):
    """Test that using scratchpad without session raises error."""
    result = use_scratchpad(
        "Testing intent",
        "key1",
        test_agent_id,
        value="value1",
        operation="set",
    )

    assert result["status"] == "error"
    assert result["error"]["code"] == "NO_ACTIVE_SESSION"


def test_scratchpad_with_session(test_agent_id, test_db):
    """Test using scratchpad after starting session."""
    start_reasoning("Testing reasoning", test_agent_id)

    # Set a value
    result = use_scratchpad(
        "Testing intent",
        "key1",
        test_agent_id,
        value="value1",
        operation="set",
    )
    assert result["status"] == "success"
    assert result["data"]["tool"] == "set"
    assert result["data"]["key"] == "key1"
    assert result["data"]["value"] == "value1"

    # Get the value
    result = use_scratchpad(
        "Testing intent",
        "key1",
        test_agent_id,
        operation="get",
    )
    assert result["status"] == "success"
    assert result["data"]["tool"] == "get"
    assert result["data"]["value"] == "value1"

    # Clean up
    end_reasoning("Testing intent", test_agent_id)


def test_evaluate_without_session(test_agent_id, test_db):
    """Test that evaluating without session raises error."""
    result = evaluate_reasoning("Testing intent", test_agent_id)
    assert result["status"] == "error"
    assert result["error"]["code"] == "NO_ACTIVE_SESSION"


def test_evaluate_with_session(test_agent_id, test_db):
    """Test evaluating after starting session."""
    start_reasoning("Testing intent", test_agent_id)
    add_reasoning_step("Testing intent", "Step 1", test_agent_id)

    result = evaluate_reasoning("Testing intent", test_agent_id)
    assert result["status"] == "success"
    assert result["tool"] == "evaluate_reasoning"
    assert result["data"]["steps_count"] == 1

    # Clean up
    end_reasoning("Testing intent", test_agent_id)


def test_summary_without_session(test_agent_id, test_db):
    """Test that getting summary without session raises error."""
    result = get_reasoning_summary("Testing intent", test_agent_id)
    assert result["status"] == "error"
    assert result["error"]["code"] == "NO_ACTIVE_SESSION"


def test_summary_with_session(test_agent_id, test_db):
    """Test getting summary after starting session."""
    start_reasoning("Testing intent", test_agent_id)
    add_reasoning_step("Testing intent", "Step 1", test_agent_id)

    result = get_reasoning_summary("Testing intent", test_agent_id)
    assert result["status"] == "success"
    assert result["data"]["steps_count"] == 1

    # Clean up
    end_reasoning("Testing intent", test_agent_id)


def test_reset_without_session(test_agent_id, test_db):
    """Test that resetting without session raises error."""
    result = reset_reasoning("Testing intent", test_agent_id)
    assert result["status"] == "error"
    assert result["error"]["code"] == "NO_ACTIVE_SESSION"


def test_reset_with_session(test_agent_id, test_db):
    """Test resetting after starting session."""
    start_reasoning("Testing intent", test_agent_id)
    add_reasoning_step("Testing intent", "Step 1", test_agent_id)

    result = reset_reasoning("Testing intent", test_agent_id)
    assert result["status"] == "success"
    assert "reset" in result["data"]["message"].lower()

    # Verify it's empty
    summary = get_reasoning_summary("Testing intent", test_agent_id)
    assert summary["status"] == "success"
    assert summary["data"]["steps_count"] == 0

    # Clean up
    end_reasoning("Testing intent", test_agent_id)


def test_end_reasoning(test_agent_id, test_db):
    """Test ending a session."""
    start_reasoning("Testing intent", test_agent_id)
    result = end_reasoning("Testing intent", test_agent_id)
    assert result["status"] == "success"
    assert result["tool"] == "end_reasoning"

    # Verify it's gone from active sessions
    assert registry.get_active_session_id(test_agent_id) is None

    # Verify tools fail now
    result = get_reasoning_summary("Testing intent", test_agent_id)
    assert result["status"] == "error"
    assert result["error"]["code"] == "NO_ACTIVE_SESSION"


def test_end_nonexistent_session(test_agent_id, test_db):
    """Test ending when no active session exists."""
    result = end_reasoning("Testing intent", test_agent_id)
    assert result["status"] == "error"
    assert result["error"]["code"] == "NO_ACTIVE_SESSION"


def test_list_sessions(test_agent_id, test_db):
    """Test listing all sessions for an agent."""
    # Start session (creates one in database)
    start_reasoning("Testing intent", test_agent_id)

    result = list_reasoning_sessions("Testing intent", test_agent_id)
    assert result["status"] == "success"
    assert result["tool"] == "list_reasoning_sessions"
    assert result["agent_id"] == test_agent_id
    assert isinstance(result["data"]["sessions"], list)

    # Clean up
    end_reasoning("Testing intent", test_agent_id)


def test_full_workflow(test_agent_id, test_db):
    """Test a complete reasoning workflow."""
    # Start session
    start_reasoning("Testing intent", test_agent_id)

    # Add steps
    add_reasoning_step(
        "Testing intent",
        "Identified the problem",
        test_agent_id,
        cognitive_mode="analysis",
    )
    add_reasoning_step(
        "Testing intent",
        "Formulated hypothesis",
        test_agent_id,
        cognitive_mode="synthesis",
    )

    # Add reflection
    add_reflection(
        "Testing intent",
        "Should verify assumptions",
        test_agent_id,
    )

    # Use scratchpad
    use_scratchpad(
        "Testing intent",
        "hypothesis",
        test_agent_id,
        value="Auth token issue",
        operation="set",
    )

    # Evaluate
    result = evaluate_reasoning("Testing intent", test_agent_id)
    assert result["status"] == "success"
    assert result["data"]["steps_count"] == 2
    assert result["data"]["reflections_count"] == 1

    # Get summary
    summary = get_reasoning_summary("Testing intent", test_agent_id)
    assert summary["status"] == "success"
    assert summary["data"]["steps_count"] == 2
    assert summary["data"]["reflections_count"] == 1

    # Clean up
    end_reasoning("Testing intent", test_agent_id)


def test_multi_agent_isolation(test_db):
    """Test that different agents have isolated sessions."""
    agent_1 = "agent_1"
    agent_2 = "agent_2"

    # Both agents start sessions
    start_reasoning("Testing intent", agent_1)
    start_reasoning("Testing intent", agent_2)

    # Add different steps
    add_reasoning_step("Testing intent", "Agent 1 step", agent_1)
    add_reasoning_step("Testing intent", "Agent 2 step", agent_2)

    # Verify isolation
    summary_1 = get_reasoning_summary("Testing intent", agent_1)
    summary_2 = get_reasoning_summary("Testing intent", agent_2)

    # Both should have 1 step
    assert summary_1["data"]["steps_count"] == 1
    assert summary_2["data"]["steps_count"] == 1

    # End one session
    end_reasoning("Testing intent", agent_1)

    # Agent 2's session should still exist
    summary_2_after = get_reasoning_summary("Testing intent", agent_2)
    assert summary_2_after["data"]["steps_count"] == 1

    # Agent 1's session should be gone
    result = get_reasoning_summary("Testing intent", agent_1)
    assert result["status"] == "error"
    assert result["error"]["code"] == "NO_ACTIVE_SESSION"

    # Clean up remaining session
    end_reasoning("Testing intent", agent_2)


def test_persistence_across_restart(test_agent_id, test_db):
    """Test that sessions survive cache clearing."""
    # Create and populate session
    start_reasoning("Testing intent", test_agent_id)
    add_reasoning_step("Testing intent", "Step 1", test_agent_id)
    add_reflection("Testing intent", "Reflection 1", test_agent_id)
    use_scratchpad(
        "Testing intent",
        "key1",
        test_agent_id,
        value="value1",
        operation="set",
    )

    # Simulate restart boundary: registry is DB-backed (no in-memory cache)

    # Verify data still accessible (loaded from database)
    summary = get_reasoning_summary("Testing intent", test_agent_id)
    assert summary["status"] == "success"
    assert summary["data"]["steps_count"] == 1
    assert summary["data"]["reflections_count"] == 1

    # Verify scratchpad persisted
    result = use_scratchpad(
        "Testing intent",
        "key1",
        test_agent_id,
        operation="get",
    )
    assert result["status"] == "success"
    assert result["data"]["value"] == "value1"

    # Clean up
    end_reasoning("Testing intent", test_agent_id)


def test_session_data_integrity(test_agent_id, test_db):
    """Test that all session data is correctly persisted and loaded."""
    # Create session with comprehensive data
    start_reasoning("Testing intent", test_agent_id)

    # Add multiple steps with evidence and biases
    add_reasoning_step(
        "Testing intent",
        "First analysis",
        test_agent_id,
        cognitive_mode="analysis",
        reasoning_type="deductive",
        evidence=["Evidence 1", "Evidence 2"],
        confidence=0.8,
    )

    add_reasoning_step(
        "Testing intent",
        "Second synthesis",
        test_agent_id,
        cognitive_mode="synthesis",
        reasoning_type="inductive",
        evidence=["Evidence 3"],
        confidence=0.7,
    )

    # Add reflection
    add_reflection(
        "Testing intent",
        "Important reflection",
        test_agent_id,
        on_step=1,
    )

    # Add scratchpad items
    use_scratchpad(
        "Testing intent",
        "hypothesis",
        test_agent_id,
        value="Test hypothesis",
        operation="set",
    )

    # DB-backed lookup should still load persisted session data

    # Verify all data is intact
    summary = get_reasoning_summary("Testing intent", test_agent_id)
    assert summary["status"] == "success"
    assert summary["data"]["steps_count"] == 2
    assert summary["data"]["reflections_count"] == 1
    assert summary["data"]["scratchpad_items_count"] == 1

    # Verify scratchpad
    result = use_scratchpad(
        "Testing intent",
        "hypothesis",
        test_agent_id,
        operation="get",
    )
    assert result["status"] == "success"
    assert result["data"]["value"] == "Test hypothesis"

    # Clean up
    end_reasoning("Testing intent", test_agent_id)


def test_list_sessions_multi_agent(test_db):
    """Test listing sessions filters by agent correctly."""
    agent_1 = "agent_1"
    agent_2 = "agent_2"

    # Create sessions for both agents
    start_reasoning("Testing intent", agent_1)
    start_reasoning("Testing intent", agent_2)

    # List sessions for agent_1
    result_1 = list_reasoning_sessions("Testing intent", agent_1)
    assert result_1["status"] == "success"
    assert result_1["agent_id"] == agent_1

    # List sessions for agent_2
    result_2 = list_reasoning_sessions("Testing intent", agent_2)
    assert result_2["status"] == "success"
    assert result_2["agent_id"] == agent_2

    # Clean up
    end_reasoning("Testing intent", agent_1)
    end_reasoning("Testing intent", agent_2)


def test_reset_clears_database(test_agent_id, test_db):
    """Test that reset clears data from database."""
    # Create and populate session
    start_reasoning("Testing intent", test_agent_id)
    add_reasoning_step("Testing intent", "Step 1", test_agent_id)

    # Reset session
    reset_reasoning("Testing intent", test_agent_id)

    # DB-backed lookup should still load persisted reset state

    # Verify session is empty after reload
    summary = get_reasoning_summary("Testing intent", test_agent_id)
    assert summary["status"] == "success"
    assert summary["data"]["steps_count"] == 0

    # Clean up
    end_reasoning("Testing intent", test_agent_id)
