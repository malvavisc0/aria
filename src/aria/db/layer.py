"""SQLite compatibility shim for Chainlit SQLAlchemy data layer.

Chainlit's built-in [`SQLAlchemyDataLayer`](.venv/lib/python3.12/site-packages/chainlit/data/sql_alchemy.py:1)
expects Postgres-style `TEXT[]` for the `tags` columns. With SQLite, Chainlit
currently passes Python `list[str]` directly into a SQL parameter, which fails
with:

    sqlite3.ProgrammingError: Error binding parameter ... type 'list' is not supported

This subclass fixes SQLite compatibility by serializing `tags` as JSON strings
on write and deserializing them back to `list[str]` on read.

It also normalizes `metadata`, `generation`, and `props` fields to/from JSON
strings in the same spirit as Chainlit's own SQLite handling.

Naming Convention
-----------------
Database column names use camelCase (e.g., createdAt, userId) to match
Chainlit's PostgreSQL schema. Python attributes use snake_case where
possible, with suffixes for reserved names (e.g., metadata_ for the
'metadata' column which conflicts with SQLAlchemy's DeclarativeBase).

Workarounds
-----------
1. Message Promotion: Assistant messages are promoted to root level
   (parentId=NULL) on read because Chainlit only displays root messages
   in thread history. See _promote_assistant_messages().

2. User ID from Context: get_all_user_threads() attempts to infer
   user_id from Chainlit's context when not provided, supporting
   multi-user scenarios.
"""

from __future__ import annotations

import json
import logging
import uuid as _uuid
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, cast

from chainlit import PersistedUser
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from chainlit.step import StepDict
from chainlit.types import PaginatedResponse, Pagination, ThreadFilter
from chainlit.user import User

logger = logging.getLogger(__name__)

# Constants
ASSISTANT_MESSAGE_TYPE = "assistant_message"


def _json_dumps_or_none(value: Any) -> Optional[str]:
    """Serialize value to JSON string, returning None for None input."""
    if value is None:
        return None
    return json.dumps(value)


def _json_loads_or(value: Any, default: Any) -> Any:
    """Deserialize JSON string or return default.

    Args:
        value: Value to deserialize (JSON string, already-parsed object, or None)
        default: Default value to return if deserialization fails

    Returns:
        Deserialized object or default value
    """
    if value is None:
        return default
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            # Log warning for debugging data corruption issues
            logger.warning(
                f"Failed to parse JSON value (returning default): "
                f"{value[:100] if len(value) > 100 else value}... Error: {e}"
            )
            return default
    return value


def _parse_iso_timestamp(value: Any) -> Optional[datetime]:
    """Parse an ISO 8601 timestamp string into a timezone-aware datetime."""
    if not isinstance(value, str) or not value.strip():
        return None

    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        logger.warning(f"Failed to parse timestamp value: {value}")
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)

    return parsed


def _to_local_timestamp_string(value: Any) -> Any:
    """Convert ISO timestamps to local-time ISO strings for Chainlit sidebar bucketing.

    Chainlit's frontend groups threads by constructing `new Date(createdAt)` and then
    zeroing local hours before computing day buckets. When timestamps end with `Z`, the
    bucket is based on the user's local timezone. Some SQLite-returned timestamps near
    midnight UTC are therefore grouped into an unexpected day from the user's point of
    view. Returning an explicit local offset keeps the represented wall-clock day aligned
    with the local grouping logic without mutating persisted database values.
    """
    parsed = _parse_iso_timestamp(value)
    if parsed is None:
        return value

    return parsed.astimezone().isoformat(timespec="microseconds")


class SQLiteSQLAlchemyDataLayer(SQLAlchemyDataLayer):
    """Chainlit SQLAlchemy data layer patched for SQLite."""

    def _deserialize_step(self, step: StepDict) -> StepDict:
        """Deserialize JSON fields in a step dict.

        Args:
            step: Step dictionary with potentially JSON-string fields

        Returns:
            Step dictionary with deserialized fields (modified in-place)
        """
        step["tags"] = _json_loads_or(step.get("tags"), default=[])
        step["metadata"] = _json_loads_or(step.get("metadata"), default={})
        step["generation"] = _json_loads_or(step.get("generation"), default={})
        return step

    def _deserialize_element(self, element: Dict[str, Any]) -> Dict[str, Any]:
        """Deserialize JSON fields in an element dict.

        Args:
            element: Element dictionary with potentially JSON-string fields

        Returns:
            Element dictionary with deserialized fields (modified in-place)
        """
        element["props"] = _json_loads_or(element.get("props"), default={})
        return element

    def _deserialize_thread(self, thread: Dict[str, Any]) -> Dict[str, Any]:
        """Deserialize JSON fields in a thread dict.

        Args:
            thread: Thread dictionary with potentially JSON-string fields

        Returns:
            Thread dictionary with deserialized fields (modified in-place)
        """
        thread["tags"] = _json_loads_or(thread.get("tags"), default=[])
        thread["metadata"] = _json_loads_or(thread.get("metadata"), default={})
        thread["createdAt"] = _to_local_timestamp_string(thread.get("createdAt"))

        for step in thread.get("steps") or []:
            self._deserialize_step(cast(StepDict, step))
        for element in thread.get("elements") or []:
            self._deserialize_element(element)

        return thread

    def _promote_assistant_messages(self, steps: list) -> None:
        """Workaround: Promote assistant messages to root level for display.

        Chainlit only displays root-level messages (parentId=NULL) in thread
        history. Messages created inside workflow context get parentId set
        automatically, but we want them visible in thread history.

        This modifies steps in-place.

        Args:
            steps: List of step dictionaries to process
        """
        for step in steps:
            if step.get("type") == ASSISTANT_MESSAGE_TYPE and step.get("parentId"):
                logger.debug(
                    f"Promoting assistant message {step.get('id')} to root level "
                    f"(was child of {step.get('parentId')})"
                )
                step["parentId"] = None

    async def create_user(self, user: User) -> Optional[PersistedUser]:
        """Override create_user to include display_name in the INSERT.

        Chainlit's base implementation omits display_name from the INSERT
        statement, which violates the NOT NULL constraint on users.display_name.
        We fall back to the identifier when display_name is not provided.

        Uses INSERT OR IGNORE to handle race conditions where concurrent
        requests might attempt to create the same user.

        Args:
            user: Chainlit User object with identifier and optional display_name

        Returns:
            PersistedUser if successful, None otherwise
        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"SQLiteSQLAlchemyDataLayer: create_user, "
                f"user_identifier={user.identifier}"
            )

        display_name = getattr(user, "display_name", None) or user.identifier
        metadata_str = json.dumps(user.metadata) if user.metadata else "{}"

        # Check if user exists
        existing_user = await self.get_user(user.identifier)

        if not existing_user:
            user_id = str(_uuid.uuid4())
            created_at = await self.get_current_timestamp()

            # Use INSERT OR IGNORE to handle race condition
            # If another request inserted the same user, this will be ignored
            query = (
                'INSERT OR IGNORE INTO users ("id", "identifier", "display_name", '
                '"createdAt", "metadata") '
                "VALUES (:id, :identifier, :display_name, :createdAt, :metadata)"
            )
            await self.execute_sql(
                query=query,
                parameters={
                    "id": user_id,
                    "identifier": user.identifier,
                    "display_name": display_name,
                    "createdAt": created_at,
                    "metadata": metadata_str,
                },
            )

        # Always update metadata (idempotent operation)
        update_query = (
            'UPDATE users SET "metadata" = :metadata, '
            '"display_name" = :display_name '
            'WHERE "identifier" = :identifier'
        )
        await self.execute_sql(
            query=update_query,
            parameters={
                "metadata": metadata_str,
                "display_name": display_name,
                "identifier": user.identifier,
            },
        )

        return await self.get_user(user.identifier)

    async def update_thread(
        self,
        thread_id: str,
        name: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ):
        """Update thread with SQLite-compatible tags serialization.

        Args:
            thread_id: Thread ID to update
            name: Optional new name
            user_id: Optional user ID
            metadata: Optional metadata dict
            tags: Optional list of tags (will be JSON-serialized for SQLite)
        """
        # Chainlit passes `tags` as Python list; sqlite cannot bind it.
        tags_json = _json_dumps_or_none(tags)
        # Pass tags as Any to bypass type check - we intentionally pass a JSON string
        # for SQLite compatibility, even though the base class expects List[str]
        return await super().update_thread(
            thread_id=thread_id,
            name=name,
            user_id=user_id,
            metadata=metadata,
            tags=cast(Any, tags_json),
        )

    async def create_step(self, step_dict: StepDict):
        """Create/update a step, ensuring SQLite-safe serialization.

        Args:
            step_dict: Step dictionary with potentially list-type tags
        """
        # Chainlit does not json.dumps(tags) for steps, but for SQLite we store
        # tags as TEXT containing a JSON array.
        patched: Dict[str, Any] = dict(step_dict)
        if isinstance(patched.get("tags"), list):
            patched["tags"] = _json_dumps_or_none(patched["tags"])

        return await super().create_step(cast(StepDict, patched))

    async def get_all_user_threads(
        self, user_id: Optional[str] = None, thread_id: Optional[str] = None
    ):
        """Get all threads for a user with proper JSON deserialization.

        Args:
            user_id: Optional user ID (if None, attempts to infer from context)
            thread_id: Optional specific thread ID

        Returns:
            List of thread dictionaries with deserialized JSON fields
        """
        # Fix for multi-user support: If user_id is not provided, try to get it
        # from the current Chainlit session context. This ensures each user
        # only sees their own threads.
        if user_id is None and thread_id is None:
            try:
                # Try to get the current user from Chainlit's context
                # This works when called from within a Chainlit session (e.g., websocket)
                from chainlit.context import context

                if hasattr(context, "session") and hasattr(context.session, "user"):
                    current_user = context.session.user
                    if current_user and hasattr(current_user, "identifier"):
                        # Look up the user_id from the database using the identifier
                        user_query = """
                            SELECT id FROM users WHERE identifier = :identifier LIMIT 1
                        """
                        result = await self.execute_sql(
                            query=user_query,
                            parameters={"identifier": current_user.identifier},
                        )
                        if isinstance(result, list) and len(result) > 0:
                            user_id = result[0].get("id")
                            logger.debug(
                                f"Retrieved user_id '{user_id}' from session context "
                                f"for user '{current_user.identifier}'"
                            )
            except Exception as e:
                logger.debug(
                    f"Could not get user_id from session context: {e}. "
                    "This is expected when called from API endpoints."
                )

        threads = await super().get_all_user_threads(
            user_id=user_id, thread_id=thread_id
        )
        if threads is None:
            return None

        logger.debug(f"get_all_user_threads returning {len(threads)} thread(s)")

        # Deserialize JSON-string columns into the shapes Chainlit's types expect.
        for t in threads:
            logger.debug(f"Thread {t.get('id')}: {len(t.get('steps', []))} steps")
            self._deserialize_thread(cast(Dict[str, Any], t))

            # Promote assistant messages to root level for thread display
            steps = t.get("steps") or []
            self._promote_assistant_messages(steps)

        return threads

    async def get_step(self, step_id: str):
        """Get a step by ID, ensuring JSON fields are deserialized.

        Args:
            step_id: The step ID to retrieve

        Returns:
            StepDict with deserialized JSON fields, or None if not found
        """
        step = await super().get_step(step_id)
        if step is None:
            return None

        return self._deserialize_step(step)

    async def list_threads(
        self, pagination: Pagination, filters: ThreadFilter
    ) -> PaginatedResponse:
        """List threads with pagination, ensuring JSON fields are deserialized.

        Args:
            pagination: Pagination parameters
            filters: Thread filter parameters

        Returns:
            PaginatedResponse with deserialized thread data
        """
        response = await super().list_threads(pagination, filters)

        # Deserialize JSON fields in all returned threads
        for thread in response.data:
            self._deserialize_thread(thread)

            # Promote assistant messages to root level for thread display
            steps = thread.get("steps") or []
            self._promote_assistant_messages(steps)

        return response
