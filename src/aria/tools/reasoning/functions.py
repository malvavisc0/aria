"""
Functional interface for reasoning tools.

This module provides standalone functions that wrap ReasoningSession methods
for use with LLM agent frameworks that expect function tools.

Each agent has ONE active reasoning session at a time, automatically managed
by the framework. This eliminates the need for agents to track session_id
parameters, solving the memory management problem inherent in LLM agents.
"""

import uuid
from typing import Any, Dict, List, Optional

from loguru import logger

from aria.tools import utc_timestamp

from . import registry
from .session import ReasoningSession

_DEFAULT_AGENT_ID = "aria"


def _ok(
    *,
    tool: str,
    intent: str,
    agent_id: str,
    session_id: Optional[str],
    data: Dict[str, Any],
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "status": "success",
        "tool": tool,
        "intent": intent,
        "agent_id": agent_id,
        **({"session_id": session_id} if session_id is not None else {}),
        "timestamp": timestamp or utc_timestamp(),
        "data": data,
    }


def _err(
    *,
    tool: str,
    intent: str,
    agent_id: str,
    session_id: Optional[str],
    code: str,
    message: str,
    how_to_fix: Optional[str] = None,
    recoverable: bool = False,
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    err = {"code": code, "message": message, "recoverable": recoverable}
    if how_to_fix:
        err["how_to_fix"] = how_to_fix
    return {
        "status": "error",
        "tool": tool,
        "intent": intent,
        "agent_id": agent_id,
        **({"session_id": session_id} if session_id is not None else {}),
        "timestamp": timestamp or utc_timestamp(),
        "error": err,
    }


def _get_session(session_id: str, agent_id: str) -> ReasoningSession:
    """Get session from cache or load from database.

    Args:
        session_id: Session identifier
        agent_id: Agent identifier for multi-agent isolation

    Returns:
        ReasoningSession instance for the given ID

    Raises:
        ValueError: If the session does not exist
    """
    return registry.get_session(session_id, agent_id)


def start_reasoning(
    intent: str, agent_id: str = _DEFAULT_AGENT_ID
) -> Dict[str, Any]:
    """
    Begin structured reasoning for a complex task.

    Use this BEFORE tackling tasks that need multiple steps, have tradeoffs,
    or require tracking partial findings. This is always the first reasoning
    tool to call. Follow with add_reasoning_step calls to build your analysis.

    Args:
        intent: What you're reasoning about (e.g. "Analyzing deployment
            options for the user's project")
        agent_id: Agent identifier (auto-set, do not provide)

    Returns:
        Session confirmation with session_id. Call add_reasoning_step next.
    """
    # Auto-generate unique session ID using UUID for collision resistance
    session_id = f"{agent_id}_session_{uuid.uuid4().hex[:12]}"

    # If agent already has active session, we'll mark it inactive AFTER
    # successfully creating the new session to avoid losing active session
    # on creation failure (atomic replacement).
    old_session_id = registry.get_active_session_id(agent_id)

    # Create new session
    session = ReasoningSession(session_id=session_id, agent_id=agent_id)
    session.set_database(registry.get_db())
    session.persist_metadata()

    # Now safe to mark old session as inactive (after new one succeeds)
    if old_session_id is not None:
        logger.info(
            f"Replacing active session {old_session_id} with {session_id} "
            f"for agent '{agent_id}'"
        )
        registry.get_db().delete_session(old_session_id, agent_id)

    logger.success(f"Started reasoning session for agent '{agent_id}'")
    now = utc_timestamp()
    # Audit event
    session.persist_tool_event(
        tool_name="start_reasoning",
        intent=intent,
        timestamp=now,
        payload=None,
    )
    return _ok(
        tool="start_reasoning",
        intent=intent,
        agent_id=agent_id,
        session_id=session_id,
        timestamp=now,
        data={"message": "Reasoning session started successfully"},
    )


def add_reasoning_step(
    intent: str,
    content: str,
    agent_id: str = _DEFAULT_AGENT_ID,
    cognitive_mode: str = "analysis",
    reasoning_type: str = "deductive",
    evidence: Optional[List[str]] = None,
    confidence: float = 0.65,
) -> Dict[str, Any]:
    """
    Record one reasoning step in the active session.

    Use this to build your analysis step by step. Each call adds one thought
    to the reasoning chain. Pick the cognitive_mode that matches what you're
    doing:

    - "planning" — outlining steps, constraints, or contingencies
    - "analysis" — examining evidence, data, or tool results
    - "evaluation" — assessing quality, failures, or comparing options
    - "synthesis" — combining findings into a conclusion
    - "creative" — generating alternatives or reframing the problem
    - "reflection" — checking for bias, gaps, or assumptions

    Requires an active session (call start_reasoning first).

    Args:
        intent: Why you're adding this step (e.g. "Recording observation
            about file structure")
        content: The reasoning content — your actual thought or analysis
        agent_id: Agent identifier (auto-set, do not provide)
        cognitive_mode: What kind of thinking this is (default: "analysis")
        reasoning_type: Logical approach — deductive, inductive, abductive,
            causal, probabilistic, analogical (default: "deductive")
        evidence: Optional list of evidence supporting this step
        confidence: How confident you are, 0.0-1.0 (default: 0.65)

    Returns:
        Step details with bias detection results. Add more steps or call
        add_reflection to check your reasoning.
    """
    session_id = registry.get_active_session_id(agent_id)
    if session_id is None:
        return _err(
            tool="add_reasoning_step",
            intent=intent,
            agent_id=agent_id,
            session_id=None,
            code="NO_ACTIVE_SESSION",
            message=f"No active reasoning session for agent '{agent_id}'.",
            how_to_fix="Call start_reasoning first.",
            recoverable=True,
        )

    try:
        session = _get_session(session_id, agent_id)
        step = session.add_step(
            intent=intent,
            content=content,
            cognitive_mode=cognitive_mode,
            reasoning_type=reasoning_type,
            evidence=evidence,
            confidence=confidence,
        )
        return _ok(
            tool="add_reasoning_step",
            intent=intent,
            agent_id=agent_id,
            session_id=session_id,
            timestamp=step.get("timestamp"),
            data=step,
        )
    except Exception as exc:
        logger.exception("add_reasoning_step failed")
        return _err(
            tool="add_reasoning_step",
            intent=intent,
            agent_id=agent_id,
            session_id=session_id,
            code="INTERNAL_ERROR",
            message=str(exc),
        )


def add_reflection(
    intent: str,
    reflection: str,
    agent_id: str = _DEFAULT_AGENT_ID,
    on_step: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Pause and reflect on your reasoning process.

    Use this to check your own thinking — look for gaps, biases, or
    assumptions you may have missed. Call this after a few reasoning steps
    to ensure quality, or when you're unsure about a conclusion.

    Requires an active session (call start_reasoning first).

    Args:
        intent: Why you're reflecting (e.g. "Checking for confirmation bias
            in my analysis")
        reflection: Your meta-cognitive observation about the reasoning
        agent_id: Agent identifier (auto-set, do not provide)
        on_step: Optional step number this reflection refers to

    Returns:
        Reflection confirmation. Continue with more steps or call
        evaluate_reasoning to score your analysis.
    """
    session_id = registry.get_active_session_id(agent_id)
    if session_id is None:
        return _err(
            tool="add_reflection",
            intent=intent,
            agent_id=agent_id,
            session_id=None,
            code="NO_ACTIVE_SESSION",
            message=f"No active reasoning session for agent '{agent_id}'.",
            how_to_fix="Call start_reasoning first.",
        )

    try:
        session = _get_session(session_id, agent_id)
        refl = session.add_reflection(
            intent=intent,
            reflection=reflection,
            on_step=on_step,
        )
        return _ok(
            tool="add_reflection",
            intent=intent,
            agent_id=agent_id,
            session_id=session_id,
            timestamp=refl.get("timestamp"),
            data=refl,
        )
    except Exception as exc:
        logger.exception("add_reflection failed")
        return _err(
            tool="add_reflection",
            intent=intent,
            agent_id=agent_id,
            session_id=session_id,
            code="INTERNAL_ERROR",
            message=str(exc),
        )


def use_scratchpad(
    intent: str,
    key: str,
    agent_id: str = _DEFAULT_AGENT_ID,
    value: Optional[str] = None,
    operation: str = "get",
) -> Dict[str, Any]:
    """
    Working memory for storing and retrieving intermediate results.

    Use this to save partial findings, plans, error logs, or any data you
    need to reference later in the reasoning process. Think of it as your
    notepad.

    Operations:
    - "set" — store a value (requires value parameter)
    - "get" — retrieve a stored value by key
    - "list" — show all stored keys and values
    - "clear" — remove a key (or "all" to clear everything)

    Requires an active session (call start_reasoning first).

    Args:
        intent: Why you're using the scratchpad (e.g. "Storing plan outline")
        key: The key to operate on (or "all" for clear)
        agent_id: Agent identifier (auto-set, do not provide)
        value: Value to store (required for "set" operation)
        operation: One of "get", "set", "list", "clear" (default: "get")

    Returns:
        Operation result with the stored/retrieved value.
    """
    session_id = registry.get_active_session_id(agent_id)
    if session_id is None:
        return _err(
            tool="use_scratchpad",
            intent=intent,
            agent_id=agent_id,
            session_id=None,
            code="NO_ACTIVE_SESSION",
            message=f"No active reasoning session for agent '{agent_id}'.",
            how_to_fix="Call start_reasoning first.",
        )

    try:
        session = _get_session(session_id, agent_id)
        result = session.scratchpad_operation(
            intent=intent,
            key=key,
            value=value,
            operation=operation,
        )
        if result.get("status") == "error":
            # Already structured error from session layer
            return _err(
                tool="use_scratchpad",
                intent=intent,
                agent_id=agent_id,
                session_id=session_id,
                code=result["error"]["code"],
                message=result["error"]["message"],
                how_to_fix=result["error"].get("how_to_fix"),
            )
        return _ok(
            tool="use_scratchpad",
            intent=intent,
            agent_id=agent_id,
            session_id=session_id,
            timestamp=result.get("timestamp"),
            data=result,
        )
    except Exception as exc:
        logger.exception("use_scratchpad failed")
        return _err(
            tool="use_scratchpad",
            intent=intent,
            agent_id=agent_id,
            session_id=session_id,
            code="INTERNAL_ERROR",
            message=str(exc),
        )


def evaluate_reasoning(
    intent: str, agent_id: str = _DEFAULT_AGENT_ID
) -> Dict[str, Any]:
    """
    Score the quality of your reasoning before concluding.

    Use this before ending a session to check if your analysis is thorough
    enough. Returns a quality score and specific recommendations for
    improvement (e.g. "Add at least one reflection", "Low confidence").

    Requires an active session (call start_reasoning first).

    Args:
        intent: Why you're evaluating (e.g. "Quality check before giving
            my final answer")
        agent_id: Agent identifier (auto-set, do not provide)

    Returns:
        Quality score, step/reflection counts, and recommendations.
        If score is low, add more steps or reflections before concluding.
    """
    session_id = registry.get_active_session_id(agent_id)
    if session_id is None:
        return _err(
            tool="evaluate_reasoning",
            intent=intent,
            agent_id=agent_id,
            session_id=None,
            code="NO_ACTIVE_SESSION",
            message=f"No active reasoning session for agent '{agent_id}'.",
            how_to_fix="Call start_reasoning first.",
        )

    try:
        session = _get_session(session_id, agent_id)
        evaluation = session.evaluate(intent=intent)
        return _ok(
            tool="evaluate_reasoning",
            intent=intent,
            agent_id=agent_id,
            session_id=session_id,
            timestamp=evaluation.get("timestamp"),
            data=evaluation,
        )
    except Exception as exc:
        logger.exception("evaluate_reasoning failed")
        return _err(
            tool="evaluate_reasoning",
            intent=intent,
            agent_id=agent_id,
            session_id=session_id,
            code="INTERNAL_ERROR",
            message=str(exc),
        )


def get_reasoning_summary(
    intent: str, agent_id: str = _DEFAULT_AGENT_ID
) -> Dict[str, Any]:
    """
    Review your progress in the current reasoning session.

    Use this to check how many steps you've taken, your average confidence,
    and what's in the scratchpad. Helpful mid-analysis to decide if you
    need more steps or can wrap up.

    Requires an active session (call start_reasoning first).

    Args:
        intent: Why you're checking progress (e.g. "Reviewing what I've
            covered so far")
        agent_id: Agent identifier (auto-set, do not provide)

    Returns:
        Session overview with step count, reflection count, scratchpad
        item count, and average confidence.
    """
    session_id = registry.get_active_session_id(agent_id)
    if session_id is None:
        return _err(
            tool="get_reasoning_summary",
            intent=intent,
            agent_id=agent_id,
            session_id=None,
            code="NO_ACTIVE_SESSION",
            message=f"No active reasoning session for agent '{agent_id}'.",
            how_to_fix="Call start_reasoning first.",
        )

    try:
        session = _get_session(session_id, agent_id)
        summary = session.summary(intent=intent)
        return _ok(
            tool="get_reasoning_summary",
            intent=intent,
            agent_id=agent_id,
            session_id=session_id,
            timestamp=summary.get("timestamp"),
            data=summary,
        )
    except Exception as exc:
        logger.exception("get_reasoning_summary failed")
        return _err(
            tool="get_reasoning_summary",
            intent=intent,
            agent_id=agent_id,
            session_id=session_id,
            code="INTERNAL_ERROR",
            message=str(exc),
        )


def reset_reasoning(
    intent: str, agent_id: str = _DEFAULT_AGENT_ID
) -> Dict[str, Any]:
    """
    Wipe the current reasoning session and start fresh.

    Use this when your current approach isn't working and you want to
    try a completely different strategy. Clears all steps, reflections,
    and scratchpad data but keeps the session active.

    After resetting, call add_reasoning_step to begin your new approach.

    Requires an active session (call start_reasoning first).

    Args:
        intent: Why you're resetting (e.g. "Previous approach failed,
            trying alternative strategy")
        agent_id: Agent identifier (auto-set, do not provide)

    Returns:
        Reset confirmation. Call add_reasoning_step to start over.
    """
    session_id = registry.get_active_session_id(agent_id)
    if session_id is None:
        return _err(
            tool="reset_reasoning",
            intent=intent,
            agent_id=agent_id,
            session_id=None,
            code="NO_ACTIVE_SESSION",
            message=f"No active reasoning session for agent '{agent_id}'.",
            how_to_fix="Call start_reasoning first.",
        )

    try:
        session = _get_session(session_id, agent_id)
        reset = session.reset(intent=intent)
        return _ok(
            tool="reset_reasoning",
            intent=intent,
            agent_id=agent_id,
            session_id=session_id,
            timestamp=reset.get("timestamp"),
            data=reset,
        )
    except Exception as exc:
        logger.exception("reset_reasoning failed")
        return _err(
            tool="reset_reasoning",
            intent=intent,
            agent_id=agent_id,
            session_id=session_id,
            code="INTERNAL_ERROR",
            message=str(exc),
        )


def end_reasoning(
    intent: str, agent_id: str = _DEFAULT_AGENT_ID
) -> Dict[str, Any]:
    """
    Finish the reasoning session and clean up.

    Call this when you've reached a conclusion and are ready to respond
    to the user. Consider calling evaluate_reasoning first to verify
    your analysis quality.

    Args:
        intent: Why you're ending (e.g. "Analysis complete, ready to
            respond")
        agent_id: Agent identifier (auto-set, do not provide)

    Returns:
        Session ended confirmation. Now deliver your answer to the user.
    """
    session_id = registry.get_active_session_id(agent_id)
    if session_id is None:
        return _err(
            tool="end_reasoning",
            intent=intent,
            agent_id=agent_id,
            session_id=None,
            code="NO_ACTIVE_SESSION",
            message=f"No active reasoning session for agent '{agent_id}'.",
        )

    now = utc_timestamp()
    try:
        # If we can still resolve the session, emit an audit event.
        session = registry.get_session(session_id, agent_id)
        session.persist_tool_event(
            tool_name="end_reasoning",
            intent=intent,
            timestamp=now,
            payload=None,
        )
    except Exception:
        # Ending should still succeed even if session can't be loaded.
        logger.debug(
            f"Could not persist end_reasoning tool event for {session_id}"
        )

    # Mark inactive in persistence store
    registry.get_db().delete_session(session_id, agent_id)

    logger.info(f"Ended reasoning session for agent '{agent_id}'")
    return _ok(
        tool="end_reasoning",
        intent=intent,
        agent_id=agent_id,
        session_id=session_id,
        timestamp=now,
        data={"message": "Reasoning session ended successfully"},
    )


def list_reasoning_sessions(
    intent: str, agent_id: str = _DEFAULT_AGENT_ID
) -> Dict[str, Any]:
    """
    List all active reasoning sessions.

    Use this to check if you have any open sessions before starting a
    new one. Rarely needed — start_reasoning automatically replaces
    any previous session.

    Args:
        intent: Why you're listing sessions (e.g. "Checking for open
            sessions")
        agent_id: Agent identifier (auto-set, do not provide)

    Returns:
        List of active session IDs and their metadata.
    """
    try:
        sessions = registry.get_db().list_sessions(agent_id)
        return _ok(
            tool="list_reasoning_sessions",
            intent=intent,
            agent_id=agent_id,
            session_id=None,
            data={"sessions": sessions},
        )
    except Exception as exc:
        logger.exception("list_reasoning_sessions failed")
        return _err(
            tool="list_reasoning_sessions",
            intent=intent,
            agent_id=agent_id,
            session_id=None,
            code="INTERNAL_ERROR",
            message=str(exc),
        )


__all__ = [
    "start_reasoning",
    "end_reasoning",
    "add_reasoning_step",
    "add_reflection",
    "use_scratchpad",
    "evaluate_reasoning",
    "get_reasoning_summary",
    "reset_reasoning",
    "list_reasoning_sessions",
]
