"""Chainlit webhook handlers for the Aria web UI.

This module provides callback handlers for Chainlit events including:
- Authentication (login/logout)
- Chat session lifecycle (start, resume)
- Data layer initialization

These handlers are invoked by Chainlit at various points in the app lifecycle.
"""

from __future__ import annotations

import json

import chainlit as cl
from chainlit.types import ThreadDict
from loguru import logger
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from aria.config.database import SQLite as SQLiteConfig
from aria.config.folders import Storage as StorageConfig
from aria.db.auth import verify_password
from aria.db.layer import SQLiteSQLAlchemyDataLayer
from aria.db.local_storage_client import LocalStorageClient
from aria.db.models import Base, User
from aria.web.session import restore_chat_history, wait_for_initialization
from aria.web.state import _state


def get_data_layer_handler() -> SQLiteSQLAlchemyDataLayer:
    """Create and return a SQLite data layer instance.

    Initializes the database engine with SQLite configuration,
    creates all necessary tables, and returns a configured
    SQLiteSQLAlchemyDataLayer with local storage client.

    Returns:
        SQLiteSQLAlchemyDataLayer: Configured data layer instance.
    """
    engine = create_engine(SQLiteConfig.db_url)
    Base.metadata.create_all(engine)

    storage_client = LocalStorageClient(storage_path=StorageConfig.path)
    return SQLiteSQLAlchemyDataLayer(
        conninfo=SQLiteConfig.conn_info,
        storage_provider=storage_client,
        show_logger=True,
    )


async def auth_callback_handler(
    username: str, password: str
) -> cl.User | None:
    """Authenticate a user with username and password.

    Called by Chainlit during login to verify user credentials
    against the database. Returns a Chainlit User object with
    metadata if authentication succeeds, None otherwise.

    Args:
        username: The user's identifier (login name).
        password: The user's password to verify.

    Returns:
        cl.User | None: Authenticated user object with metadata,
            or None if authentication fails.
    """
    try:
        with Session(_state.db_engine) as session:
            user = session.execute(
                select(User).where(User.identifier == username)
            ).scalar_one_or_none()

            if not user:
                logger.debug(f"User not found: {username}")
                return None

            user_password = str(user.password)
            if user_password and verify_password(password, user_password):
                metadata = json.loads(str(user.metadata_))
                logger.debug(f"User authenticated: {username}")
                return cl.User(
                    identifier=str(user.identifier),
                    metadata=metadata,
                )

            logger.debug(f"Invalid password for user: {username}")
            return None

    except Exception as e:
        logger.error(f"Authentication error for user {username}: {e}")
        return None


async def on_chat_start_handler() -> None:
    """Handle the start of a new chat session.

    Called by Chainlit when a new chat session begins. Sets up
    custom commands available in the chat interface.
    """
    logger.debug("Starting new chat session")
    await cl.context.emitter.set_commands(
        [
            {
                "id": "Enhance",
                "icon": "wand-sparkles",
                "description": "Enhance Prompt",
                "button": None,
                "persistent": True,
            }
        ]
    )


async def on_chat_resume_handler(thread: ThreadDict) -> None:
    """Resume an existing chat session with conversation history.

    Called by Chainlit when resuming a previous chat session.
    Restores the chat memory from the thread history so the
    conversation can continue from where it left off.

    Args:
        thread: Thread dictionary containing conversation history
            and metadata from the previous session.
    """
    try:
        if not _state.is_initialized():
            logger.info(
                "AppState not yet initialized, waiting for startup to "
                "complete..."
            )
            if not await wait_for_initialization():
                logger.warning(
                    "AppState initialization timed out after 30s. "
                    "Continuing with empty memory."
                )
                return

        memory = await restore_chat_history(thread)
        cl.user_session.set("memory", memory)
    except Exception as e:
        logger.exception(f"Failed to restore chat history: {e}")
