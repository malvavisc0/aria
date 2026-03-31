"""Knowledge store tool for persistent key-value storage.

Phase 7: Provides a simple key-value store for the agent to remember
facts, preferences, and intermediate results across conversations.
"""

import uuid
from typing import List, Optional

from loguru import logger

from aria.tools import tool_response
from aria.tools.decorators import log_tool_call

from .database import get_database

_DEFAULT_AGENT_ID = "aria"


@log_tool_call
def knowledge(
    intent: str,
    action: str,
    key: Optional[str] = None,
    value: Optional[str] = None,
    tags: Optional[List[str]] = None,
    entry_id: Optional[str] = None,
    query: Optional[str] = None,
    max_results: int = 10,
    agent_id: str = _DEFAULT_AGENT_ID,
) -> str:
    """Persistent key-value knowledge store.

    Store and retrieve information across conversations. Useful for
    remembering user preferences, project context, and learned facts.

    Actions:
    - "store": Save a new entry (requires key and value)
    - "recall": Retrieve an entry by key (requires key)
    - "search": Search entries by query string (requires query)
    - "list": List all entries (optional tag filter)
    - "update": Update an existing entry (requires entry_id and value)
    - "delete": Remove an entry (requires entry_id)

    Args:
        intent: Why you're using the knowledge store.
        action: One of: store, recall, search, list, update, delete.
        key: Unique key for the entry (required for store/recall).
        value: Value to store (required for store/update).
        tags: Optional list of tags for categorization.
        entry_id: UUID of entry to update/delete.
        query: Search query for text search.
        max_results: Maximum results for search/list (default: 10).
        agent_id: Agent identifier (auto-set, do not provide).

    Returns:
        JSON response with action-specific data.
    """
    action = action.lower().strip()
    db = get_database()

    if action == "store":
        return _action_store(db, intent, agent_id, key, value, tags)
    elif action == "recall":
        return _action_recall(db, intent, agent_id, key)
    elif action == "search":
        return _action_search(db, intent, agent_id, query, max_results)
    elif action == "list":
        return _action_list(db, intent, agent_id, tags, max_results)
    elif action == "update":
        return _action_update(db, intent, agent_id, entry_id, value)
    elif action == "delete":
        return _action_delete(db, intent, agent_id, entry_id)
    else:
        return tool_response(
            tool="knowledge",
            intent=intent,
            data={
                "error": f"Unknown action '{action}'. "
                "Valid: store, recall, search, list, update, delete",
            },
        )


def _action_store(
    db,
    intent: str,
    agent_id: str,
    key: Optional[str],
    value: Optional[str],
    tags: Optional[List[str]],
) -> str:
    """Store a new knowledge entry."""
    if not key:
        return tool_response(
            tool="knowledge",
            intent=intent,
            data={"error": "Missing required 'key' parameter."},
        )
    if value is None:
        return tool_response(
            tool="knowledge",
            intent=intent,
            data={"error": "Missing required 'value' parameter."},
        )

    entry_id = uuid.uuid4().hex
    db.store(entry_id, agent_id, key, value, tags)

    logger.info(f"Stored knowledge: {key}")
    return tool_response(
        tool="knowledge",
        intent=intent,
        data={
            "action": "store",
            "entry_id": entry_id,
            "key": key,
            "message": "Knowledge entry stored successfully",
        },
    )


def _action_recall(
    db,
    intent: str,
    agent_id: str,
    key: Optional[str],
) -> str:
    """Recall a knowledge entry by key."""
    if not key:
        return tool_response(
            tool="knowledge",
            intent=intent,
            data={"error": "Missing required 'key' parameter."},
        )

    entry = db.recall(agent_id, key)
    if entry is None:
        return tool_response(
            tool="knowledge",
            intent=intent,
            data={"action": "recall", "found": False, "key": key},
        )

    return tool_response(
        tool="knowledge",
        intent=intent,
        data={"action": "recall", "found": True, **entry},
    )


def _action_search(
    db,
    intent: str,
    agent_id: str,
    query: Optional[str],
    max_results: int,
) -> str:
    """Search knowledge entries."""
    if not query:
        return tool_response(
            tool="knowledge",
            intent=intent,
            data={"error": "Missing required 'query' parameter."},
        )

    results = db.search(agent_id, query, max_results)
    return tool_response(
        tool="knowledge",
        intent=intent,
        data={
            "action": "search",
            "query": query,
            "results_count": len(results),
            "results": results,
        },
    )


def _action_list(
    db,
    intent: str,
    agent_id: str,
    tags: Optional[List[str]],
    max_results: int,
) -> str:
    """List all knowledge entries."""
    tag = tags[0] if tags else None
    entries = db.list_entries(agent_id, tag=tag, max_results=max_results)
    return tool_response(
        tool="knowledge",
        intent=intent,
        data={
            "action": "list",
            "count": len(entries),
            "entries": entries,
        },
    )


def _action_update(
    db,
    intent: str,
    agent_id: str,
    entry_id: Optional[str],
    value: Optional[str],
) -> str:
    """Update an existing knowledge entry."""
    if not entry_id:
        return tool_response(
            tool="knowledge",
            intent=intent,
            data={"error": "Missing required 'entry_id' parameter."},
        )
    if value is None:
        return tool_response(
            tool="knowledge",
            intent=intent,
            data={"error": "Missing required 'value' parameter."},
        )

    success = db.update(entry_id, agent_id, value)
    if not success:
        return tool_response(
            tool="knowledge",
            intent=intent,
            data={"error": f"Entry '{entry_id}' not found."},
        )

    return tool_response(
        tool="knowledge",
        intent=intent,
        data={
            "action": "update",
            "entry_id": entry_id,
            "message": "Knowledge entry updated successfully",
        },
    )


def _action_delete(
    db,
    intent: str,
    agent_id: str,
    entry_id: Optional[str],
) -> str:
    """Delete a knowledge entry."""
    if not entry_id:
        return tool_response(
            tool="knowledge",
            intent=intent,
            data={"error": "Missing required 'entry_id' parameter."},
        )

    success = db.delete(entry_id, agent_id)
    if not success:
        return tool_response(
            tool="knowledge",
            intent=intent,
            data={"error": f"Entry '{entry_id}' not found."},
        )

    return tool_response(
        tool="knowledge",
        intent=intent,
        data={
            "action": "delete",
            "entry_id": entry_id,
            "message": "Knowledge entry deleted successfully",
        },
    )
