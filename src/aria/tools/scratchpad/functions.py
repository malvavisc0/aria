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
    intent: str,
    key: str,
    value: Optional[str] = None,
    operation: str = "get",
    agent_id: str = _DEFAULT_AGENT_ID,
) -> Dict[str, Any]:
    """Standalone key-value scratchpad for working memory.

    Use this to store and retrieve intermediate results, plans, error logs,
    or any data you need to reference later. Works independently of reasoning
    sessions — no need to call reasoning first.

    Operations:
    - "get" — retrieve a stored value by key
    - "set" — store a value (requires value parameter)
    - "delete" — remove a key
    - "list" — show all stored keys and values

    Args:
        intent: Why you're using the scratchpad (e.g., "Storing plan outline").
        key: The key to operate on (ignored for "list" operation).
        value: Value to store (required for "set" operation).
        operation: One of "get", "set", "delete", "list" (default: "get").
        agent_id: Agent identifier (auto-set, do not provide).

    Returns:
        Operation result with the stored/retrieved value.
    """
    operation = operation.lower().strip()
    now = utc_timestamp()

    if operation == "set":
        return _op_set(intent, agent_id, key, value, now)
    elif operation == "get":
        return _op_get(intent, agent_id, key, now)
    elif operation == "delete":
        return _op_delete(intent, agent_id, key, now)
    elif operation == "list":
        return _op_list(intent, agent_id, now)
    else:
        return _err(
            intent=intent,
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
    intent: str,
    agent_id: str,
    data: Dict[str, Any],
    timestamp: str,
) -> Dict[str, Any]:
    return {
        "status": "success",
        "tool": "scratchpad",
        "intent": intent,
        "agent_id": agent_id,
        "timestamp": timestamp,
        "data": data,
    }


def _err(
    *,
    intent: str,
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
        "intent": intent,
        "agent_id": agent_id,
        "timestamp": utc_timestamp(),
        "error": err,
    }


# ── operations ───────────────────────────────────────────────────────


def _op_set(
    intent: str,
    agent_id: str,
    key: str,
    value: Optional[str],
    now: str,
) -> Dict[str, Any]:
    if value is None:
        return _err(
            intent=intent,
            agent_id=agent_id,
            code="VALUE_REQUIRED",
            message="Value required for set operation",
            how_to_fix="Provide the 'value' parameter.",
        )

    db = get_database()
    db.set_item(agent_id, key, value, intent)

    return _ok(
        intent=intent,
        agent_id=agent_id,
        timestamp=now,
        data={
            "tool": "set",
            "key": key,
            "value": value,
            "intent": intent,
            "timestamp": now,
        },
    )


def _op_get(
    intent: str,
    agent_id: str,
    key: str,
    now: str,
) -> Dict[str, Any]:
    db = get_database()
    item = db.get_item(agent_id, key)

    if item is None:
        return _err(
            intent=intent,
            agent_id=agent_id,
            code="KEY_NOT_FOUND",
            message=f"Key '{key}' not found",
            how_to_fix=f"Use operation='set' to store a value for '{key}'.",
        )

    return _ok(
        intent=intent,
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
    intent: str,
    agent_id: str,
    key: str,
    now: str,
) -> Dict[str, Any]:
    db = get_database()

    if key == "all":
        count = db.clear_all(agent_id)
        return _ok(
            intent=intent,
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
            intent=intent,
            agent_id=agent_id,
            code="KEY_NOT_FOUND",
            message=f"Key '{key}' not found for delete operation",
        )

    return _ok(
        intent=intent,
        agent_id=agent_id,
        timestamp=now,
        data={
            "tool": "delete",
            "key": key,
            "timestamp": now,
        },
    )


def _op_list(
    intent: str,
    agent_id: str,
    now: str,
) -> Dict[str, Any]:
    db = get_database()
    items = db.list_items(agent_id)

    return _ok(
        intent=intent,
        agent_id=agent_id,
        timestamp=now,
        data={
            "tool": "list",
            "items": items,
            "timestamp": now,
        },
    )
