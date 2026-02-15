"""
Web UI module for the ARIA application using Chainlit framework.

This module provides the web interface for the ARIA application, handling:
- User authentication and session management
- Chat session lifecycle (start, resume, message handling)
- Integration with LLM agents and workflows
- Data persistence and storage
- UI command handling

The module uses Chainlit for the web interface and integrates with:
- SQL database for user authentication and chat history
- Local storage for uploaded files and images
- LLM agents for conversation handling and prompt enhancement
"""

import json

import chainlit as cl
from chainlit.types import ThreadDict
from chromadb import PersistentClient as ChromaDBPersistentClient
from chromadb.config import Settings as ChromaDBSettings
from llama_index.core.agent.workflow import AgentStream, ToolCall
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.memory import Memory
from loguru import logger
from sqlalchemy import create_engine

from aria.agents import get_prompt_enhancer_agent
from aria.agents.prompt_enhancer import PromptEnhancementResult
from aria.config.database import ChromaDB as ChromaDBConfig
from aria.config.database import SQLite as SQLiteConfig
from aria.config.folders import Debug as DebugConfig
from aria.config.folders import Storage as StorageConfig
from aria.config.models import Chat as ChatConfig
from aria.config.models import Embeddings as EmbeddingsConfig
from aria.db.layer import SQLiteSQLAlchemyDataLayer
from aria.db.local_storage_client import LocalStorageClient
from aria.db.models import Base
from aria.helpers.ui import maybe_remove_step, send_tool_step
from aria.llm import (
    get_agent_workflow,
    get_chat_llm,
    get_default_memory,
    get_embeddings_model,
)

# Constants
ROOT_MESSAGE_TYPES = ["user_message", "assistant_message"]
LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}"

# Initialize logging
log_path = DebugConfig.logs_path
logger.add(
    log_path,
    rotation="10 MB",
    level="DEBUG",
    format=LOG_FORMAT,
)

# Initialize LLM and embeddings
llm = get_chat_llm(api_base=ChatConfig.api_url)
embeddings = get_embeddings_model(api_base=EmbeddingsConfig.api_url)

vector_db = ChromaDBPersistentClient(
    path=ChromaDBConfig.db_path,
    settings=ChromaDBSettings(
        is_persistent=True,
        persist_directory=ChromaDBConfig.db_path.absolute().as_posix(),
        anonymized_telemetry=False,
    ),
)


# Initialize workflow and agents
agents_workflow = get_agent_workflow(llm=llm)
prompt_enhancer = get_prompt_enhancer_agent(llm=llm)


def _create_memory(thread_id: str) -> Memory:
    """
    Create and return a new memory instance for a chat thread.

    Args:
        thread_id: The unique identifier for the chat thread

    Returns:
        Configured Memory instance for the thread
    """
    return get_default_memory(
        vector_db=vector_db,
        thread_id=thread_id,
        embed_model=embeddings,
        token_limit=EmbeddingsConfig.token_limit,
    )


async def _handle_message(message: cl.Message) -> str:
    """
    Handle messages.

    Args:
        message: The incoming user message

    Returns:
        The processed prompt (either original or enhanced)
    """
    prompt = message.content
    if message.command == "Enhance":
        response = await prompt_enhancer.run(user_msg=message.content)
        results: PromptEnhancementResult = response.structured_response
        prompt = results.enhanced

    return prompt


async def _restore_chat_history(thread: ThreadDict) -> Memory:
    """
    Restore chat history from thread data into memory.

    Args:
        thread: The thread dictionary containing chat steps and metadata

    Returns:
        Memory instance populated with chat history
    """
    thread_id = thread.get("id")
    thread_name = thread.get("name")
    logger.debug(f"Restoring chat history for thread {thread_id} ({thread_name})")

    chat_steps = thread.get("steps", [])
    logger.debug(f"Thread contains {len(chat_steps)} total steps")

    # Filter for root-level messages only
    root_messages = [m for m in chat_steps if m.get("parentId") is None]
    logger.debug(f"Found {len(root_messages)} root-level messages")

    memory = _create_memory(thread_id)

    # Restore conversation history
    steps_restored = 0
    for message_step in root_messages:
        content = message_step.get("output", "")
        message_type = message_step.get("type")

        if not content or message_type not in ROOT_MESSAGE_TYPES:
            continue

        role = (
            MessageRole.USER
            if message_type == "user_message"
            else MessageRole.ASSISTANT
        )

        await memory.aput(ChatMessage(role=role, content=content))
        steps_restored += 1

    logger.info(f"Restored {steps_restored} messages for thread {thread_id}")
    return memory


@cl.data_layer
def get_data_layer() -> SQLiteSQLAlchemyDataLayer:
    """
    Initialize and return the data layer for Chainlit.

    Returns:
        Configured data layer instance with database and storage providers
    """
    engine = create_engine(SQLiteConfig.db_url)
    Base.metadata.create_all(engine)

    storage_client = LocalStorageClient(storage_path=StorageConfig.path)

    return SQLiteSQLAlchemyDataLayer(
        conninfo=SQLiteConfig.conn_info,
        storage_provider=storage_client,
        show_logger=True,
    )


@cl.password_auth_callback
async def auth_callback(username: str, password: str) -> cl.User | None:
    """
    Handle user authentication against the database.

    Args:
        username: The username provided by the user
        password: The password provided by the user

    Returns:
        User object if authentication succeeds, None otherwise
    """
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from aria.db.auth import verify_password
    from aria.db.models import User

    engine = create_engine(SQLiteConfig.db_url)

    try:
        with Session(engine) as session:
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


@cl.on_chat_start
async def on_chat_start() -> None:
    """Initialize new chat session with available commands."""
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


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict) -> None:
    """Restore previous chat session from thread data."""
    memory = await _restore_chat_history(thread)
    cl.user_session.set("memory", memory)


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """
    Process incoming user messages through the agent workflow.

    Handles command messages, memory management, and streaming responses.
    """
    output = cl.Message(content="")
    try:
        prompt = await _handle_message(message)

        # Get or create memory
        memory: Memory | None = cl.user_session.get("memory")
        if memory is None:
            memory = _create_memory(message.thread_id)
            cl.user_session.set("memory", memory)
            logger.debug(f"Created new Memory for thread {message.thread_id}")

        # Process with agent workflow
        handler = agents_workflow.run(
            user_msg=prompt,
            memory=memory,
            max_iterations=ChatConfig.max_iteration,
        )

        current_step: cl.Step | None = None

        # Stream events as they arrive
        async for event in handler.stream_events():
            if isinstance(event, ToolCall):
                current_step = await send_tool_step(event)
            elif isinstance(event, AgentStream):
                current_step = await maybe_remove_step(current_step)
                await output.stream_token(event.delta)

        # Finalize and send the message
        await output.send()
        await handler

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        output.content = "An error occurred. Please try again."
        await output.send()
        raise
