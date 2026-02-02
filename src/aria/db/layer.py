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
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, cast

import chainlit as cl
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from chainlit.step import StepDict
from chainlit.types import PaginatedResponse, Pagination, ThreadFilter

logger = logging.getLogger(__name__)


def _json_dumps_or_none(value: Any) -> Optional[str]:
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


class SQLiteSQLAlchemyDataLayer(SQLAlchemyDataLayer):
    """Chainlit SQLAlchemy data layer patched for SQLite."""

    async def update_thread(
        self,
        thread_id: str,
        name: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
    ):
        # Chainlit passes `tags` as Python list; sqlite cannot bind it.
        tags_json = _json_dumps_or_none(tags) if tags is not None else None
        return await super().update_thread(
            thread_id=thread_id,
            name=name,
            user_id=user_id,
            metadata=metadata,
            # Store as JSON string (TEXT column).
            tags=tags_json,  [arg-type]
        )

    async def create_step(self, step_dict: StepDict):
        """Create/update a step, ensuring SQLite-safe serialization."""

        # Chainlit does not json.dumps(tags) for steps, but for SQLite we store
        # tags as TEXT containing a JSON array.
        patched: Dict[str, Any] = dict(step_dict)
        if isinstance(patched.get("tags"), list):
            patched["tags"] = _json_dumps_or_none(patched["tags"])

        return await super().create_step(cast(StepDict, patched))

    async def get_all_user_threads(
        self, user_id: Optional[str] = None, thread_id: Optional[str] = None
    ):
        # Fix for multi-user support: If user_id is not provided, try to get it
        # from the current Chainlit session context. This ensures each user
        # only sees their own threads.
        if user_id is None and thread_id is None:
            try:
                # Try to get the current user from Chainlit's context
                # This works when called from within a Chainlit session (e.g., websocket)
                from chainlit.context import context

                if hasattr(context, "session") and hasattr(
                    context.session, "user"
                ):
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

        logger.debug(
            f"get_all_user_threads returning {len(threads)} thread(s)"
        )

        # Deserialize JSON-string columns into the shapes Chainlit's types expect.
        for t in threads:
            logger.debug(
                f"Thread {t.get('id')}: {len(t.get('steps', []))} steps"
            )
            t["tags"] = _json_loads_or(t.get("tags"), default=[])
            t["metadata"] = _json_loads_or(t.get("metadata"), default={})

            for s in t.get("steps") or []:
                # `metadata`/`generation` are already normalized by Chainlit for SQLite
                # in some codepaths, but we keep this defensive.
                s["tags"] = _json_loads_or(s.get("tags"), default=[])
                s["metadata"] = _json_loads_or(s.get("metadata"), default={})
                s["generation"] = _json_loads_or(
                    s.get("generation"), default={}
                )

                # FIX: Promote assistant messages to root level for thread display
                # Chainlit only displays root-level messages (parentId=NULL) in thread history.
                # Messages created inside workflow context get parentId set automatically,
                # but we want them to appear in thread history, so we clear parentId on read.
                if s.get("type") == "assistant_message" and s.get("parentId"):
                    logger.debug(
                        f"Promoting assistant message {s.get('id')} to root level "
                        f"(was child of {s.get('parentId')})"
                    )
                    s["parentId"] = None

            for e in t.get("elements") or []:
                e["props"] = _json_loads_or(e.get("props"), default={})

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

        # Deserialize JSON fields
        step["tags"] = _json_loads_or(step.get("tags"), default=[])
        step["metadata"] = _json_loads_or(step.get("metadata"), default={})
        step["generation"] = _json_loads_or(step.get("generation"), default={})

        return step

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
            thread["tags"] = _json_loads_or(thread.get("tags"), default=[])
            thread["metadata"] = _json_loads_or(
                thread.get("metadata"), default={}
            )

            # Deserialize nested steps
            for step in thread.get("steps") or []:
                step["tags"] = _json_loads_or(step.get("tags"), default=[])
                step["metadata"] = _json_loads_or(
                    step.get("metadata"), default={}
                )
                step["generation"] = _json_loads_or(
                    step.get("generation"), default={}
                )

                # FIX: Promote assistant messages to root level for thread display
                if step.get("type") == "assistant_message" and step.get(
                    "parentId"
                ):
                    logger.debug(
                        f"Promoting assistant message {step.get('id')} to root level "
                        f"(was child of {step.get('parentId')})"
                    )
                    step["parentId"] = None

            # Deserialize nested elements
            for element in thread.get("elements") or []:
                element["props"] = _json_loads_or(
                    element.get("props"), default={}
                )

        return response
