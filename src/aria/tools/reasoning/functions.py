"""
Functional interface for reasoning tools.

This module provides standalone functions that wrap ReasoningSession methods
for use with LLM agent frameworks that expect function tools.

Each agent has ONE active reasoning session at a time, automatically managed
by the framework. This eliminates the need for agents to track session_id
parameters, solving the memory management problem inherent in LLM agents.
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from .database import get_database
from .session import ReasoningSession

# Session registry - maps "agent_id:session_id" to ReasoningSession instances
_session_registry: Dict[str, ReasoningSession] = {}

# Active sessions - maps agent_id to their current active session_id
_active_sessions: Dict[str, str] = {}

# Get database instance
_db = get_database()


def _make_cache_key(agent_id: str, session_id: str) -> str:
    """Create cache key from agent_id and session_id."""
    return f"{agent_id}:{session_id}"


def _get_active_session_id(agent_id: str) -> str:
    """Get the active session ID for an agent.

    Args:
        agent_id: Agent identifier

    Returns:
        str: The active session ID for this agent

    Raises:
        ValueError: If no active session exists for this agent
    """
    session_id = _active_sessions.get(agent_id)
    if session_id is None:
        raise ValueError(
            f"No active reasoning session for agent '{agent_id}'.\n"
            f"Start reasoning first:\n"
            f"  start_reasoning('Describe your reasoning goal', '{agent_id}')"
        )
    return session_id


def _get_active_session_id_safe(agent_id: str) -> Optional[str]:
    """Get the active session ID for an agent, or None if absent.

    Prefer this helper in tool functions to avoid exceptions escaping.
    """
    return _active_sessions.get(agent_id)


def _timestamp() -> str:
    return datetime.now().isoformat()


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
        "timestamp": timestamp or _timestamp(),
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
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    err = {"code": code, "message": message}
    if how_to_fix:
        err["how_to_fix"] = how_to_fix
    return {
        "status": "error",
        "tool": tool,
        "intent": intent,
        "agent_id": agent_id,
        **({"session_id": session_id} if session_id is not None else {}),
        "timestamp": timestamp or _timestamp(),
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
    cache_key = _make_cache_key(agent_id, session_id)

    # Check cache first
    if cache_key not in _session_registry:
        # Try to load from database
        session_data = _db.load_session(session_id, agent_id)

        if session_data:
            # Reconstruct session from database
            session = ReasoningSession.from_dict(session_data)
            session.set_database(_db)
            _session_registry[cache_key] = session
            logger.debug(
                f"Loaded session {session_id} for agent {agent_id} " f"from database"
            )
        else:
            # Session doesn't exist
            available = list(_session_registry.keys()) or ["(none)"]
            logger.error(
                f"Session '{session_id}' for agent '{agent_id}' "
                f"does not exist. Available sessions: {available}"
            )
            raise ValueError(
                f"Session '{session_id}' for agent '{agent_id}' "
                f"does not exist. Available sessions: {available}"
            )

    return _session_registry[cache_key]


def start_reasoning(intent: str, agent_id: str) -> Dict[str, Any]:
    """
    Start a new reasoning session with automatic management.

    Creates a new session and sets it as the active session for this agent.
    Any previous active session for this agent is automatically replaced.

    Args:
        reason (str): Why you're starting this reasoning session
        agent_id (str): Agent identifier for multi-agent isolation

    Returns:
        str: Confirmation message
    """
    # Auto-generate unique session ID
    session_id = f"{agent_id}_session_{int(time.time() * 1000)}"

    # If agent already has active session, clean it up first
    if agent_id in _active_sessions:
        old_session_id = _active_sessions[agent_id]
        logger.info(
            f"Replacing active session {old_session_id} with {session_id} "
            f"for agent '{agent_id}'"
        )
        # Clean up old session
        old_cache_key = _make_cache_key(agent_id, old_session_id)
        if old_cache_key in _session_registry:
            del _session_registry[old_cache_key]
        _db.delete_session(old_session_id, agent_id)

    # Create new session
    session = ReasoningSession(session_id=session_id, agent_id=agent_id)
    session.set_database(_db)
    session.persist_metadata()

    # Register session
    cache_key = _make_cache_key(agent_id, session_id)
    _session_registry[cache_key] = session
    _active_sessions[agent_id] = session_id

    logger.success(f"Started reasoning session for agent '{agent_id}'")
    now = _timestamp()
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
    agent_id: str,
    cognitive_mode: str = "analysis",
    reasoning_type: str = "deductive",
    evidence: Optional[List[str]] = None,
    confidence: float = 0.65,
) -> Dict[str, Any]:
    """
    Add a structured reasoning step to the active session.

    Args:
        reason (str): Why you're adding this step
        content: The reasoning content or thought
        agent_id: Agent identifier for multi-agent isolation
        cognitive_mode: Type of thinking
            - "analysis", "synthesis", "evaluation",
            "planning", "creative", or "reflection"
        reasoning_type: Logic type
            - "deductive", "inductive", "abductive",
            "causal", "probabilistic", or "analogical"
        evidence: Optional list of evidence supporting this reasoning
        confidence: Your confidence level (0.0 to 1.0)

    Returns:
        Formatted confirmation with step details and any detected biases
    """
    session_id = _get_active_session_id_safe(agent_id)
    if session_id is None:
        return _err(
            tool="add_reasoning_step",
            intent=intent,
            agent_id=agent_id,
            session_id=None,
            code="NO_ACTIVE_SESSION",
            message=f"No active reasoning session for agent '{agent_id}'.",
            how_to_fix="Call start_reasoning(intent, agent_id) first.",
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
    agent_id: str,
    on_step: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Add a meta-cognitive reflection to the active session.

    Args:
        reason (str): Why you're adding this reflection
        reflection: Your reflection on the reasoning process
        agent_id: Agent identifier for multi-agent isolation
        on_step: Optional step number this reflection refers to

    Returns:
        Confirmation message
    """
    session_id = _get_active_session_id_safe(agent_id)
    if session_id is None:
        return _err(
            tool="add_reflection",
            intent=intent,
            agent_id=agent_id,
            session_id=None,
            code="NO_ACTIVE_SESSION",
            message=f"No active reasoning session for agent '{agent_id}'.",
            how_to_fix="Call start_reasoning(intent, agent_id) first.",
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
    agent_id: str,
    value: Optional[str] = None,
    operation: str = "get",
) -> Dict[str, Any]:
    """
    Use a scratchpad for temporary working memory in the active session.

    Args:
        reason (str): Why you're using the scratchpad
        key: The key to operate on (or "all" for clear operation)
        agent_id: Agent identifier for multi-agent isolation
        value: Value to set (required for "set" operation)
        operation: Operation type - "get", "set", "list", or "clear"

    Returns:
        Result of the operation
    """
    session_id = _get_active_session_id_safe(agent_id)
    if session_id is None:
        return _err(
            tool="use_scratchpad",
            intent=intent,
            agent_id=agent_id,
            session_id=None,
            code="NO_ACTIVE_SESSION",
            message=f"No active reasoning session for agent '{agent_id}'.",
            how_to_fix="Call start_reasoning(intent, agent_id) first.",
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


def evaluate_reasoning(intent: str, agent_id: str) -> Dict[str, Any]:
    """
    Evaluate the quality of your reasoning process in the active session.

    Args:
        reason (str): Why you're evaluating your reasoning
        agent_id (str): Agent identifier for multi-agent isolation

    Returns:
        str: Formatted evaluation report with quality score and suggestions
    """
    session_id = _get_active_session_id_safe(agent_id)
    if session_id is None:
        return _err(
            tool="evaluate_reasoning",
            intent=intent,
            agent_id=agent_id,
            session_id=None,
            code="NO_ACTIVE_SESSION",
            message=f"No active reasoning session for agent '{agent_id}'.",
            how_to_fix="Call start_reasoning(intent, agent_id) first.",
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


def get_reasoning_summary(intent: str, agent_id: str) -> Dict[str, Any]:
    """
    Get a summary of your active reasoning session.

    Args:
        reason (str): Why you're getting the summary
        agent_id (str): Agent identifier for multi-agent isolation

    Returns:
        str: Brief overview of steps, reflections, and scratchpad items
    """
    session_id = _get_active_session_id_safe(agent_id)
    if session_id is None:
        return _err(
            tool="get_reasoning_summary",
            intent=intent,
            agent_id=agent_id,
            session_id=None,
            code="NO_ACTIVE_SESSION",
            message=f"No active reasoning session for agent '{agent_id}'.",
            how_to_fix="Call start_reasoning(intent, agent_id) first.",
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


def reset_reasoning(intent: str, agent_id: str) -> Dict[str, Any]:
    """
    Reset the active reasoning session and start fresh.

    Args:
        reason (str): Why you're resetting the session
        agent_id (str): Agent identifier for multi-agent isolation

    Returns:
        str: Confirmation message
    """
    session_id = _get_active_session_id_safe(agent_id)
    if session_id is None:
        return _err(
            tool="reset_reasoning",
            intent=intent,
            agent_id=agent_id,
            session_id=None,
            code="NO_ACTIVE_SESSION",
            message=f"No active reasoning session for agent '{agent_id}'.",
            how_to_fix="Call start_reasoning(intent, agent_id) first.",
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


def end_reasoning(intent: str, agent_id: str) -> Dict[str, Any]:
    """
    End the active reasoning session for this agent.

    Cleans up the session and removes it from active sessions.

    Args:
        reason (str): Why you're ending this reasoning session
        agent_id (str): Agent identifier for multi-agent isolation

    Returns:
        str: Confirmation message
    """
    session_id = _active_sessions.get(agent_id)
    if session_id is None:
        return _err(
            tool="end_reasoning",
            intent=intent,
            agent_id=agent_id,
            session_id=None,
            code="NO_ACTIVE_SESSION",
            message=f"No active reasoning session for agent '{agent_id}'.",
        )

    now = _timestamp()
    try:
        # If we can still resolve the session, emit an audit event.
        session = _get_session(session_id, agent_id)
        session.persist_tool_event(
            tool_name="end_reasoning",
            intent=intent,
            timestamp=now,
            payload=None,
        )
    except Exception:
        # Ending should still succeed even if session can't be loaded.
        logger.debug(f"Could not persist end_reasoning tool event for {session_id}")

    # Remove from active sessions
    del _active_sessions[agent_id]

    # Clean up session
    cache_key = _make_cache_key(agent_id, session_id)
    if cache_key in _session_registry:
        del _session_registry[cache_key]

    _db.delete_session(session_id, agent_id)

    logger.info(f"Ended reasoning session for agent '{agent_id}'")
    return _ok(
        tool="end_reasoning",
        intent=intent,
        agent_id=agent_id,
        session_id=session_id,
        timestamp=now,
        data={"message": "Reasoning session ended successfully"},
    )


def list_reasoning_sessions(intent: str, agent_id: str) -> Dict[str, Any]:
    """
    List all active reasoning sessions for an agent.

    Args:
        reason (str): Objective and reasoning
        agent_id (str): Agent identifier to filter sessions

    Returns:
        str: List of session IDs and their summaries
    """
    try:
        sessions = _db.list_sessions(agent_id)
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
