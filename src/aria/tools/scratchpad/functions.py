"""Standalone scratchpad tool — decoupled from reasoning sessions.

Provides a persistent key-value working memory that survives across
reasoning sessions and conversations.
"""

from typing import Any, Dict, Optional

from aria.tools import utc_timestamp
from aria.tools.decorators import log_tool_call

from .database import get_database

_DEFAULT_AGENT_ID = "aria"


@log_tool_call
def scratchpad(
    reason: str,
    key: str,
    value: Optional[str] = None,
    operation: str = "get",
    agent_id: str = _DEFAULT_AGENT_ID,
) -> Dict[str, Any]:
    """Ephemeral key-value scratchpad for working memory.

    When to use:
        - Use this to store intermediate results, calculations, or
          notes within a task (e.g., "analysis_v1": "Option A: 8/10").
        - Use this to pass data between reasoning steps or across
          tool calls within the same task.
        - Use this to save partial progress that you'll reference
          later in the conversation.
        - Do NOT use this for long-term facts that must survive
          across conversations — use `knowledge` instead.
        - Do NOT use this for structured execution plans — use `plan`.

    Why:
        Scratchpad is lightweight working memory that persists across
        reasoning sessions but is designed for ephemeral data. It's
        independent of reasoning sessions — no need to call reasoning
        first.

    Operations:
        - "get": Retrieve a stored value by key.
        - "set": Store a value (requires value parameter).
        - "delete": Remove a key (use key="all" to clear everything).
        - "list": Show all stored keys and values.

    Args:
        reason: Why you're using the scratchpad (for logging/auditing).
        key: The key to operate on (ignored for "list" operation).
        value: Value to store (required for "set" operation).
        operation: One of "get", "set", "delete", "list"
            (default: "get").
        agent_id: Agent identifier (auto-set, do not provide).

    Returns:
        Operation result with the stored/retrieved value.

    Important:
        - Data is persisted to SQLite and survives server restarts,
          but is designed for ephemeral use within a task.
        - Use key="all" with operation="delete" to clear all entries.
    """
    operation = operation.lower().strip()
    now = utc_timestamp()

    if operation == "set":
        return _op_set(reason, agent_id, key, value, now)
    elif operation == "get":
        return _op_get(reason, agent_id, key, now)
    elif operation == "delete":
        return _op_delete(reason, agent_id, key, now)
    elif operation == "list":
        return _op_list(reason, agent_id, now)
    else:
        return _err(
            reason=reason,
            agent_id=agent_id,
            code="UNSUPPORTED_OPERATION",
            message=(
                f"Unknown operation '{operation}'. "
                "Supported: get, set, delete, list"
            ),
            how_to_fix="Use one of: get, set, delete, list",
        )


# ── helpers ──────────────────────────────────────────────────────────


def _ok(
    *,
    reason: str,
    agent_id: str,
    data: Dict[str, Any],
    timestamp: str,
) -> Dict[str, Any]:
    return {
        "status": "success",
        "tool": "scratchpad",
        "reason": reason,
        "agent_id": agent_id,
        "timestamp": timestamp,
        "data": data,
    }


def _err(
    *,
    reason: str,
    agent_id: str,
    code: str,
    message: str,
    how_to_fix: Optional[str] = None,
) -> Dict[str, Any]:
    err: Dict[str, Any] = {
        "code": code,
        "message": message,
        "recoverable": True,
    }
    if how_to_fix:
        err["how_to_fix"] = how_to_fix
    return {
        "status": "error",
        "tool": "scratchpad",
        "reason": reason,
        "agent_id": agent_id,
        "timestamp": utc_timestamp(),
        "error": err,
    }


# ── operations ───────────────────────────────────────────────────────


def _op_set(
    reason: str,
    agent_id: str,
    key: str,
    value: Optional[str],
    now: str,
) -> Dict[str, Any]:
    if value is None:
        return _err(
            reason=reason,
            agent_id=agent_id,
            code="VALUE_REQUIRED",
            message="Value required for set operation",
            how_to_fix="Provide the 'value' parameter.",
        )

    db = get_database()
    db.set_item(agent_id, key, value, reason)

    return _ok(
        reason=reason,
        agent_id=agent_id,
        timestamp=now,
        data={
            "tool": "set",
            "key": key,
            "value": value,
            "reason": reason,
            "timestamp": now,
        },
    )


def _op_get(
    reason: str,
    agent_id: str,
    key: str,
    now: str,
) -> Dict[str, Any]:
    db = get_database()
    item = db.get_item(agent_id, key)

    if item is None:
        return _err(
            reason=reason,
            agent_id=agent_id,
            code="KEY_NOT_FOUND",
            message=f"Key '{key}' not found",
            how_to_fix=f"Use operation='set' to store a value for '{key}'.",
        )

    return _ok(
        reason=reason,
        agent_id=agent_id,
        timestamp=now,
        data={
            "tool": "get",
            "key": key,
            "value": item["value"],
            "timestamp": now,
        },
    )


def _op_delete(
    reason: str,
    agent_id: str,
    key: str,
    now: str,
) -> Dict[str, Any]:
    db = get_database()

    if key == "all":
        count = db.clear_all(agent_id)
        return _ok(
            reason=reason,
            agent_id=agent_id,
            timestamp=now,
            data={
                "tool": "delete",
                "key": "all",
                "deleted_count": count,
                "timestamp": now,
            },
        )

    success = db.delete_item(agent_id, key)
    if not success:
        return _err(
            reason=reason,
            agent_id=agent_id,
            code="KEY_NOT_FOUND",
            message=f"Key '{key}' not found for delete operation",
        )

    return _ok(
        reason=reason,
        agent_id=agent_id,
        timestamp=now,
        data={
            "tool": "delete",
            "key": key,
            "timestamp": now,
        },
    )


def _op_list(
    reason: str,
    agent_id: str,
    now: str,
) -> Dict[str, Any]:
    db = get_database()
    items = db.list_items(agent_id)

    return _ok(
        reason=reason,
        agent_id=agent_id,
        timestamp=now,
        data={
            "tool": "list",
            "items": items,
            "timestamp": now,
        },
    )
