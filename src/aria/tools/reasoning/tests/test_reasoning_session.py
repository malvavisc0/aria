"""Tests for ReasoningSession class."""

from aria.tools.reasoning.session import ReasoningSession


def test_session_creation():
    """Test that a session can be created."""
    session = ReasoningSession()
    assert session.id is not None
    assert len(session.steps) == 0
    assert len(session.reflections) == 0
    assert len(session.scratchpad) == 0


def test_add_step():
    """Test adding reasoning steps."""
    session = ReasoningSession()

    result = session.add_step(
        intent="Record a hypothesis",
        content="Testing hypothesis",
        cognitive_mode="analysis",
        reasoning_type="deductive",
        confidence=0.8,
    )

    assert result["step_id"] == 1
    assert result["content"] == "Testing hypothesis"
    assert result["intent"] == "Record a hypothesis"
    assert len(session.steps) == 1
    assert session.steps[0]["content"] == "Testing hypothesis"
    assert session.steps[0]["confidence"] == 0.8


def test_add_reflection():
    """Test adding reflections."""
    session = ReasoningSession()

    result = session.add_reflection(
        intent="Check for bias",
        reflection="Need to verify assumptions",
    )

    assert result["reflection_id"] == 1
    assert result["intent"] == "Check for bias"
    assert len(session.reflections) == 1
    assert session.reflections[0]["content"] == "Need to verify assumptions"


def test_scratchpad_operations():
    """Test scratchpad operations."""
    session = ReasoningSession()

    # Set a value
    result = session.scratchpad_operation(
        intent="Store intermediate",
        key="key1",
        operation="set",
        value="value1",
    )
    assert result["operation"] == "set"
    assert result["key"] == "key1"
    assert result["value"] == "value1"

    # Get the value
    result = session.scratchpad_operation(
        intent="Retrieve variable",
        key="key1",
        operation="get",
    )
    assert result["operation"] == "get"
    assert result["value"] == "value1"

    # List all
    result = session.scratchpad_operation(
        intent="Inspect scratchpad",
        key="",
        operation="list",
    )
    assert result["operation"] == "list"
    assert any(item["key"] == "key1" for item in result["items"])

    # Clear one
    result = session.scratchpad_operation(
        intent="Remove intermediate",
        key="key1",
        operation="clear",
    )
    assert result["operation"] == "clear"
    assert result["key"] == "key1"

    # Verify empty
    result = session.scratchpad_operation(
        intent="Check scratchpad empty",
        key="",
        operation="list",
    )
    assert result["items"] == []


def test_evaluate():
    """Test evaluation of reasoning quality."""
    session = ReasoningSession()

    session.add_step(intent="Add step", content="Step 1", confidence=0.7)
    session.add_step(intent="Add step", content="Step 2", confidence=0.8)
    session.add_reflection(intent="Reflect", reflection="Reflection 1")

    result = session.evaluate(intent="Assess reasoning")

    assert result["steps_count"] == 2
    assert result["reflections_count"] == 1


def test_summary():
    """Test session summary."""
    session = ReasoningSession()

    session.add_step(intent="Add step", content="Step 1")
    session.add_reflection(intent="Reflect", reflection="Reflection 1")
    session.scratchpad_operation(
        intent="Store intermediate",
        key="key1",
        operation="set",
        value="value1",
    )

    result = session.summary(intent="Summarize")

    assert result["steps_count"] == 1
    assert result["reflections_count"] == 1
    assert result["scratchpad_items_count"] == 1


def test_reset():
    """Test resetting a session."""
    session = ReasoningSession()

    session.add_step(intent="Add step", content="Step 1")
    session.add_reflection(intent="Reflect", reflection="Reflection 1")
    session.scratchpad_operation(
        intent="Store intermediate",
        key="key1",
        operation="set",
        value="value1",
    )

    result = session.reset(intent="Restart")

    assert "reset" in result["message"].lower()
    assert len(session.steps) == 0
    assert len(session.reflections) == 0
    assert len(session.scratchpad) == 0


def test_bias_detection():
    """Test bias detection in reasoning steps."""
    session = ReasoningSession()

    session.add_step(
        intent="Add biased step",
        content="This definitely proves my point",
        evidence=["Obviously this is correct"],
        confidence=0.9,
    )

    # Should detect overconfidence and confirmation bias
    assert len(session.steps[0]["biases_detected"]) > 0


def test_multiple_sessions_independent():
    """Test that multiple sessions are independent (no global state)."""
    session1 = ReasoningSession()
    session2 = ReasoningSession()

    session1.add_step(intent="Add", content="Session 1 step")
    session2.add_step(intent="Add", content="Session 2 step")

    assert len(session1.steps) == 1
    assert len(session2.steps) == 1
    assert session1.steps[0]["content"] == "Session 1 step"
    assert session2.steps[0]["content"] == "Session 2 step"
    assert session1.id != session2.id


def test_add_step_with_invalid_cognitive_mode():
    """Test add_step with invalid cognitive mode defaults to 'analysis'."""
    session = ReasoningSession()

    session.add_step(
        intent="Invalid mode",
        content="Testing with invalid mode",
        cognitive_mode="invalid_mode",
        reasoning_type="deductive",
        confidence=0.8,
    )

    assert len(session.steps) == 1
    assert session.steps[0]["cognitive_mode"] == "analysis"


def test_add_step_with_invalid_reasoning_type():
    """Test add_step with invalid reasoning type defaults to 'deductive'."""
    session = ReasoningSession()

    session.add_step(
        intent="Invalid type",
        content="Testing with invalid type",
        cognitive_mode="analysis",
        reasoning_type="invalid_type",
        confidence=0.8,
    )

    assert len(session.steps) == 1
    assert session.steps[0]["reasoning_type"] == "deductive"


def test_scratchpad_set_without_value():
    """Test scratchpad set operation without providing a value."""
    session = ReasoningSession()

    result = session.scratchpad_operation(
        intent="Set without value",
        key="key1",
        operation="set",
    )

    assert result["status"] == "error"
    assert result["error"]["code"] == "VALUE_REQUIRED"


def test_scratchpad_get_nonexistent_key():
    """Test scratchpad get operation for non-existent key."""
    session = ReasoningSession()

    result = session.scratchpad_operation(
        intent="Get missing key",
        key="nonexistent",
        operation="get",
    )

    assert result["status"] == "error"
    assert result["error"]["code"] == "KEY_NOT_FOUND"


def test_scratchpad_clear_all():
    """Test scratchpad clear all operation."""
    session = ReasoningSession()

    # Add some items
    session.scratchpad_operation(
        intent="Add",
        key="key1",
        operation="set",
        value="value1",
    )
    session.scratchpad_operation(
        intent="Add",
        key="key2",
        operation="set",
        value="value2",
    )

    # Clear all
    result = session.scratchpad_operation(
        intent="Clear all",
        key="all",
        operation="clear",
    )

    assert result["operation"] == "clear"
    assert result["key"] == "all"
    assert len(session.scratchpad) == 0


def test_scratchpad_unsupported_operation():
    """Test scratchpad with unsupported operation."""
    session = ReasoningSession()

    result = session.scratchpad_operation(
        intent="Bad op",
        key="key1",
        operation="invalid",
    )

    assert result["status"] == "error"
    assert result["error"]["code"] == "UNSUPPORTED_OPERATION"


def test_evaluate_with_low_confidence():
    """Test evaluate with low average confidence."""
    session = ReasoningSession()

    # Add steps with low confidence
    session.add_step(intent="Add", content="Step 1", confidence=0.5)
    session.add_step(intent="Add", content="Step 2", confidence=0.55)

    result = session.evaluate(intent="Assess")

    assert any("Low confidence" in r for r in result["recommendations"])
