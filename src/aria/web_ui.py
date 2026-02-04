import chainlit as cl
from chainlit.types import ThreadDict
from llama_index.core.agent.workflow import AgentStream, ToolCall
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from loguru import logger
from sqlalchemy import create_engine

from aria.config import (
    CHAT_HISTORY_DB_URL,
    DEBUG_LOGS_PATH,
    EMBEDDINGS_API_URL,
    EMBEDDINGS_MODEL,
    LLM,
    LOCAL_STORAGE_PATH,
    MAX_ITERATIONS,
    SQLITE_CONN_INFO,
    VECTOR_DB,
)
from aria.db.layer import SQLiteSQLAlchemyDataLayer
from aria.db.local_storage_client import LocalStorageClient
from aria.db.models import Base
from aria.llm import (
    get_agent_workflow,
    get_default_memory,
    get_embeddings_model,
)
from aria.ui import maybe_remove_step, send_tool_step

log_path = DEBUG_LOGS_PATH
logger.add(
    log_path,
    rotation="10 MB",
    level="DEBUG",
    format=(
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
        "{name}:{function}:{line} - {message}"
    ),
)


@cl.data_layer
def get_data_layer():
    engine = create_engine(CHAT_HISTORY_DB_URL)

    # Create tables (idempotent - won't drop existing tables)
    Base.metadata.create_all(engine)

    # Use local storage for elements (images, files, etc.)
    storage_client = LocalStorageClient(storage_path=LOCAL_STORAGE_PATH)

    return SQLiteSQLAlchemyDataLayer(
        conninfo=SQLITE_CONN_INFO,
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
    engine = create_engine(CHAT_HISTORY_DB_URL)

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
        logger.error(f"Authentication error: {e}")
        return None


@cl.on_chat_start
async def on_chat_start():
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
    thread_id = thread.get("id")
    thread_name = thread.get("name")
    logger.debug(f"Resuming thread: {thread_id} - {thread_name}")

    steps = thread.get("steps", [])
    logger.debug(f"Thread has {len(steps)} total steps")

    # Filter for root-level messages only (parentId == None)
    # This matches the official Chainlit pattern from the cookbook
    root_messages = [m for m in steps if m.get("parentId") is None]
    logger.debug(f"Thread has {len(root_messages)} root-level messages")

    memory = get_default_memory(
        vector_db=VECTOR_DB,
        thread_id=thread_id,
        embed_model=get_embeddings_model(
            api_base=EMBEDDINGS_API_URL, model=EMBEDDINGS_MODEL
        ),
    )

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
async def on_message(message: cl.Message):
    """
    Chainlit message handler.

    Args:
        message (cl.Message): The inbound user message.
    """
    # Create assistant message at root level (no parent_id)
    # By creating it outside any step context, it will be a root-level message
    msg = cl.Message(content="", parent_id=None)

    memory = get_default_memory(
        vector_db=VECTOR_DB,
        thread_id=message.thread_id,
        embed_model=get_embeddings_model(
            api_base=EMBEDDINGS_API_URL, model=EMBEDDINGS_MODEL
        ),
    )

    workflow = get_agent_workflow(llm=LLM)

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
