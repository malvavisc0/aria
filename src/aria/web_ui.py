"""
Aria2 Chainlit web UI.

This module wires Chainlit event handlers into a LlamaIndex AgentWorkflow
that coordinates specialist agents through handoffs.

Conversation state is stored per-Chainlit-session using a token-limited
`ChatMemoryBuffer`. The workflow manages specialist agents and handoffs.

The workflow manages agent handoffs and maintains conversation context across
specialist interactions.
"""

import os

import chainlit as cl
from chainlit.types import ThreadDict
from llama_index.core.agent.workflow import AgentStream, ToolCall
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from loguru import logger
from sqlalchemy import create_engine

from aria.db.layer import SQLiteSQLAlchemyDataLayer
from aria.db.local_storage_client import LocalStorageClient
from aria.db.models import Base
from aria.llm import get_agent_workflow, get_chat_llm, get_default_memory
from aria.ui import maybe_remove_step, send_tool_step


def _get_required_env(key: str) -> str:
    """Get required environment variable or raise an error."""
    value = os.getenv(key)
    if value is None:
        raise ValueError(f"Required environment variable '{key}' is not set")
    return value


MAIN_LLAMACPP_API_URL = _get_required_env("MAIN_LLAMACPP_API_URL")
MEMORY_LLAMACPP_API_URL = _get_required_env("MEMORY_LLAMACPP_API_URL")
CHAT_MEMORY_TOKEN_LIMIT = int(_get_required_env("CHAT_MEMORY_TOKEN_LIMIT"))
MAX_FACTS = int(_get_required_env("MAX_FACTS"))
MAX_ITERATIONS = int(_get_required_env("MAX_ITERATIONS"))

log_path = os.path.expanduser(".files/debug.log")
logger.add(
    log_path,
    rotation="10 MB",
    level="DEBUG",
    format=(
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
        "{name}:{function}:{line} - {message}"
    ),
)

shared_llm = get_chat_llm(api_base=MAIN_LLAMACPP_API_URL)
workflow = get_agent_workflow(llm=shared_llm)
memory = get_default_memory(
    llm=shared_llm, tokens=CHAT_MEMORY_TOKEN_LIMIT, max_facts=MAX_FACTS
)


@cl.data_layer
def get_data_layer():
    # SQLite file (async URL required by Chainlit's SQLAlchemyDataLayer).
    # Stored in `data/` directory for persistence across server restarts.
    # The `.files/` directory is for temporary data only.
    os.makedirs("data", exist_ok=True)

    # Chainlit does not auto-create its tables; create them from our SQLAlchemy
    # models (idempotent).
    sync_url = "sqlite:///./data/chainlit.db"
    engine = create_engine(sync_url)

    # Create tables (idempotent - won't drop existing tables)
    Base.metadata.create_all(engine)

    # Use local storage for elements (images, files, etc.)
    storage_client = LocalStorageClient(storage_path=".files/storage")

    return SQLiteSQLAlchemyDataLayer(
        conninfo="sqlite+aiosqlite:///./data/chainlit.db",
        storage_provider=storage_client,
        show_logger=True,  # Enable to debug data layer issues
    )


@cl.password_auth_callback
async def auth_callback(username: str, password: str):
    """Authenticate user against database using password field."""
    import json

    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from aria.db.auth import verify_password
    from aria.db.models import User

    # Create database session (sync since this is a sync callback)
    sync_url = "sqlite:///./data/chainlit.db"
    engine = create_engine(sync_url)

    try:
        with Session(engine) as session:
            # Find user by identifier (username)
            user = session.execute(
                select(User).where(User.identifier == username)
            ).scalar_one_or_none()

            if not user:
                logger.debug(f"User not found: {username}")
                return None

            # Verify password using new password field
            # Type ignore needed because SQLAlchemy's type system doesn't fully capture runtime values
            if user.password and verify_password(password, str(user.password)):  # type: ignore
                metadata = json.loads(str(user.metadata_))  # type: ignore
                logger.debug(f"User authenticated: {username}")
                return cl.User(
                    identifier=str(user.identifier),  # type: ignore
                    metadata=metadata,
                )

            logger.debug(f"Invalid password for user: {username}")
            return None

    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return None


@cl.on_chat_start
async def start():
    """
    Chainlit chat-start handler.

    Initializes a new chat session.
    """
    logger.debug("Starting new chat session")


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    """
    Chainlit chat-resume handler.

    Called when a user resumes a previous conversation thread.
    This restores the conversation history to the LLM memory.

    Args:
        thread: The thread data containing steps (messages) and metadata
    """
    logger.debug(f"Resuming thread: {thread.get('id')} - {thread.get('name')}")

    steps = thread.get("steps", [])
    logger.debug(f"Thread has {len(steps)} total steps")

    # Filter for root-level messages only (parentId == None)
    # This matches the official Chainlit pattern from the cookbook
    root_messages = [m for m in steps if m.get("parentId") is None]
    logger.debug(f"Thread has {len(root_messages)} root-level messages")

    # Restore the conversation history by replaying messages into memory
    # Chainlit automatically displays the messages in the UI from the database
    for step in root_messages:
        step_type = step.get("type")
        content = step.get("output", "")

        if not content:
            continue

        # Add user messages to memory
        if step_type == "user_message":
            memory.put(ChatMessage(role=MessageRole.USER, content=content))
            logger.debug(f"Restored user message: {content[:50]}...")

        # Add assistant messages to memory
        elif step_type == "assistant_message":
            memory.put(
                ChatMessage(role=MessageRole.ASSISTANT, content=content)
            )
            logger.debug(f"Restored assistant message: {content[:50]}...")

    logger.debug(
        f"Restored {len([s for s in root_messages if s.get('output')])} messages for thread {thread.get('id')}"
    )


@cl.on_message
async def main(message: cl.Message):
    """
    Chainlit message handler.

    Args:
        message (cl.Message): The inbound user message.
    """
    # Create assistant message at root level (no parent_id)
    # By creating it outside any step context, it will be a root-level message
    msg = cl.Message(content="", parent_id=None)

    handler = workflow.run(
        user_msg=message.content, memory=memory, max_iterations=MAX_ITERATIONS
    )

    step: cl.Step | None = None
    # Stream events as they arrive
    async for event in handler.stream_events():
        if isinstance(event, ToolCall):
            logger.debug(
                {
                    "tool_id": event.tool_id,
                    "tool_name": event.tool_name,
                    "tool_kwargs": event.tool_kwargs,
                }
            )

            step = await send_tool_step(event)
        elif isinstance(event, AgentStream):
            step = await maybe_remove_step(step)
            await msg.stream_token(event.delta)

    # Send the final message - this persists it to the database for thread resumption
    await msg.send()

    # Finalize the run
    _ = await handler
