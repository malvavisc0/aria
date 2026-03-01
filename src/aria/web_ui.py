"""
Web UI module for the ARIA application using Chainlit framework.

This module provides the web interface for the ARIA application, handling:
- User authentication and session management
- Chat session lifecycle (start, resume, message handling)
- Integration with LLM agents and workflows
- Data persistence and storage
- UI command handling
- LlamaCpp server lifecycle management

The module uses Chainlit for the web interface and integrates with:
- SQL database for user authentication and chat history
- Local storage for uploaded files and images
- LLM agents for conversation handling and prompt enhancement
- LlamaCpp servers for inference (managed via lifecycle hooks)

AppState Lifecycle:
    The [`AppState`](_state) instance starts with all attributes set to None.
    During [`on_app_startup()`](on_app_startup), all services are initialized
    in sequence. If any step fails, the app should not accept connections.
    Use [`AppState.validate()`](AppState.validate) before accessing state
    attributes to ensure the app is properly initialized.

Attributes:
    _state: Global AppState instance holding all shared services.
"""

from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import chainlit as cl
from chainlit.types import ThreadDict
from chromadb import PersistentClient as ChromaDBPersistentClient
from chromadb.api import ClientAPI
from chromadb.config import Settings as ChromaDBSettings
from llama_index.core.agent.workflow import (
    AgentOutput,
    AgentStream,
    AgentWorkflow,
    ToolCall,
)
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.memory import Memory
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai_like import OpenAILike
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import Engine, create_engine

from aria.agents.prompt_enhancer import PromptEnhancerAgent
from aria.config import DEBUG
from aria.config.database import ChromaDB as ChromaDBConfig
from aria.config.database import SQLite as SQLiteConfig
from aria.config.folders import Debug as DebugConfig
from aria.config.folders import Storage as StorageConfig
from aria.config.folders import Uploads as UploadsConfig
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
from aria.server.llama import LlamaCppServerManager

if TYPE_CHECKING:
    from aria.agents.prompt_enhancer import PromptEnhancementResult

# Constants
ROOT_MESSAGE_TYPES = ["user_message", "assistant_message"]

# Hardcoded MIME-to-extension map for uploaded file renaming.
# mimetypes.guess_extension() is unreliable on Linux (reads /etc/mime.types,
# can return None or platform-specific values like ".jpe").  This map covers
# exactly the formats supported by parse_pdf.
# Only PDF is accepted — image uploads are disabled in config.toml.
_MIME_TO_EXT: dict[str, str] = {
    "application/pdf": ".pdf",
}

LOG_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
    "{name}:{function}:{line} - {message}"
)

# Loguru sink ID — kept at module level for cleanup in on_app_shutdown().
# Note: We use logger.remove() at startup to clear all handlers, so this
# tracks only the current sink for proper shutdown cleanup.
_log_sink_id: int | None = None


class AppStateNotInitializedError(RuntimeError):
    """Raised when AppState attributes are accessed before initialization."""

    def __init__(self, message: str = "AppState is not fully initialized") -> None:
        super().__init__(message)


class AppState(BaseModel):
    """Application state initialized at startup.

    This class holds all shared services and resources for the web UI.
    All attributes default to None and are initialized during app startup.

    Attributes:
        llm: OpenAI-compatible LLM client for chat completions.
        embeddings: Embedding model for vector memory operations.
        vector_db: ChromaDB client for persistent vector storage.
        agents_workflow: Multi-agent workflow for conversation handling.
        prompt_enhancer: Agent for enhancing user prompts.
        llama_manager: Manager for LlamaCpp inference servers.
        db_engine: SQLAlchemy engine for database operations.
        startup_complete: True once on_app_startup() completes successfully.

    Warning:
        All attributes are None by default. Always call ``validate()``
        before accessing attributes, or use ``is_initialized()``
        to check the state.

    Example:
        ```python
        # Safe attribute access
        _state.validate()
        handler = _state.agents_workflow.run(...)

        # Conditional access
        if _state.is_initialized():
            memory = _create_memory(thread_id)
        ```
    """

    model_config = {"arbitrary_types_allowed": True}

    llm: OpenAILike | None = None
    embeddings: OpenAIEmbedding | None = None
    vector_db: ClientAPI | None = None
    agents_workflow: AgentWorkflow | None = None
    prompt_enhancer: PromptEnhancerAgent | None = None
    llama_manager: LlamaCppServerManager | None = None
    db_engine: Engine | None = None
    startup_complete: bool = False

    def is_initialized(self) -> bool:
        """Check if all required attributes are initialized.

        Required attributes are those needed for core functionality:
        - llm: Required for all LLM operations
        - embeddings: Required for vector memory
        - vector_db: Required for persistent memory storage
        - agents_workflow: Required for conversation handling
        - db_engine: Required for database operations

        Optional attributes (not checked):
        - prompt_enhancer: Only needed for prompt enhancement command
        - llama_manager: May be None if no local servers configured

        Returns:
            True if all required attributes are initialized, False otherwise.
        """
        return all(
            [
                self.llm is not None,
                self.embeddings is not None,
                self.vector_db is not None,
                self.agents_workflow is not None,
                self.db_engine is not None,
                self.startup_complete,
            ]
        )

    def validate_initialized(self) -> None:
        """Validate that the state is fully initialized.

        Raises:
            AppStateNotInitializedError: If any required attribute is None.
        """
        missing: list[str] = []
        if self.llm is None:
            missing.append("llm")
        if self.embeddings is None:
            missing.append("embeddings")
        if self.vector_db is None:
            missing.append("vector_db")
        if self.agents_workflow is None:
            missing.append("agents_workflow")
        if self.db_engine is None:
            missing.append("db_engine")

        if missing:
            raise AppStateNotInitializedError(
                f"AppState is not fully initialized. Missing: {', '.join(missing)}. "
                "Ensure on_app_startup() completed successfully."
            )

        if not self.startup_complete:
            raise AppStateNotInitializedError(
                "AppState startup not marked complete. "
                "Ensure on_app_startup() completed successfully."
            )


# Global state instance
_state = AppState()


def _create_memory(thread_id: str) -> Memory:
    """Create a new Memory instance for a chat thread.

    Creates a vector-backed memory instance using the shared embedding model
    and vector database from the application state.

    Args:
        thread_id: Unique identifier for the chat thread. Used as both the
            ChromaDB collection name (for vector store isolation per thread)
            and the LlamaIndex ``Memory.session_id`` (so the
            ``VectorMemoryBlock`` metadata filter always matches embeddings
            from the same thread, across all sessions).

    Returns:
        A Memory instance configured with vector storage.

    Raises:
        AppStateNotInitializedError: If state is not initialized.
        ValueError: If thread_id is None or empty.

    Note:
        This function validates the AppState before creating memory.
        Each thread gets its own ChromaDB collection for isolation.
    """
    _state.validate_initialized()

    if not thread_id:
        raise ValueError("thread_id cannot be None or empty")

    # Type assertions: validate() ensures these are not None
    assert _state.vector_db is not None
    assert _state.embeddings is not None

    return get_default_memory(
        vector_db=_state.vector_db,
        thread_id=thread_id,
        embed_model=_state.embeddings,
        token_limit=EmbeddingsConfig.token_limit,
    )


async def _wait_for_initialization(
    timeout: float = 30.0, poll_interval: float = 0.1
) -> bool:
    """Wait for AppState to be fully initialized.

    Polls _state.is_initialized() at regular intervals until the state
    is ready or the timeout expires. This handles the race condition
    where on_chat_resume fires before on_app_startup completes.

    Args:
        timeout: Maximum time to wait in seconds (default: 30s).
        poll_interval: Time between checks in seconds (default: 0.1s).

    Returns:
        True if initialized within timeout, False if timed out.
    """
    start_time = asyncio.get_event_loop().time()
    while not _state.is_initialized():
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed >= timeout:
            return False
        await asyncio.sleep(poll_interval)
    return True


def _extract_file_paths(message: cl.Message) -> list[str]:
    """Return absolute file paths for any uploaded elements in *message*.

    Chainlit stores uploaded files as :class:`~chainlit.element.Element`
    objects on ``message.elements``.  Each element exposes a ``path``
    attribute pointing to the file on disk.  Only elements that have a
    non-empty ``path`` are included.

    Chainlit saves uploaded files without a file extension (the filename
    is a bare UUID).  When the element has a ``mime`` attribute, this
    function copies the file into ``_UPLOADS_DIR`` (``BASE_DIR/uploads``)
    with the correct extension added.  The original file is left in
    ``.files/`` so Chainlit can still serve it to the browser.  The copy
    in ``BASE_DIR/uploads`` is what is passed to agents: it lives in a
    stable, tool-accessible location that persists across Chainlit
    restarts and is within the workspace all agents are allowed to read.

    Args:
        message: The incoming Chainlit message.

    Returns:
        List of absolute file path strings, one per uploaded file.
        Empty list if no files were uploaded.
    """
    paths: list[str] = []
    for element in message.elements or []:
        path = getattr(element, "path", None)
        if not path:
            continue

        path_str = str(path)

        # Determine the correct extension from the MIME type.
        mime = getattr(element, "mime", None)
        ext = _MIME_TO_EXT.get(mime or "", "")

        # Build the destination filename: use the element name when
        # available (preserves the original filename the user uploaded),
        # otherwise fall back to the bare UUID stem + extension.
        src = Path(path_str)
        element_name = getattr(element, "name", None)
        if element_name:
            dest_name = element_name
            # Ensure the destination has the correct extension.
            if ext and not dest_name.lower().endswith(ext):
                dest_name = Path(dest_name).stem + ext
        else:
            dest_name = src.stem + ext

        dest = UploadsConfig.path / dest_name

        try:
            shutil.copy2(path_str, dest)
            path_str = str(dest)
            logger.debug(f"Copied uploaded file to safe path: {dest}")
        except OSError as e:
            logger.warning(
                f"Could not copy uploaded file {path_str}"
                f" to {dest}: {e} — using original path"
            )

        paths.append(path_str)
        logger.debug(f"Uploaded file path: {path_str}")
    return paths


async def _handle_message(message: cl.Message) -> str:
    """Process an incoming message and return the prompt to use.

    Handles special commands like "Enhance" that modify the user's input
    before it's processed by the agent workflow.  If the message contains
    uploaded file elements, their absolute paths are appended to the
    prompt so the parse_pdf tool can locate and process them.

    Args:
        message: The incoming Chainlit message with content, optional
            command, and optional file elements.

    Returns:
        The prompt to use for agent processing. This may be the original
        message content, an enhanced version (Enhance command), and/or
        augmented with uploaded file paths.

    Note:
        If prompt enhancement fails or is unavailable, the original
        message content is returned unchanged. Errors are logged but
        do not interrupt the flow.
    """
    prompt = message.content

    if message.command == "Enhance":
        if not _state.prompt_enhancer:
            logger.warning("Prompt enhancer not available, returning original prompt")
            return prompt

        try:
            response = await _state.prompt_enhancer.run(user_msg=message.content)
            results: PromptEnhancementResult = response.structured_response
            prompt = results.enhanced
            logger.debug("Prompt enhancement completed successfully")
        except Exception as e:
            logger.error(f"Prompt enhancement failed: {e}")
            # Return original prompt on failure

    # Append uploaded file paths so the parse_pdf tool can process them.
    file_paths = _extract_file_paths(message)
    if file_paths:
        paths_block = "\n".join(f"- {p}" for p in file_paths)
        prompt = f"{prompt}\n\n" "[Uploaded files]:\n" f"{paths_block}"
        logger.debug(f"Appended {len(file_paths)} file path(s) to prompt")

    return prompt


async def _restore_chat_history(thread: ThreadDict) -> Memory:
    """Restore chat history from thread data into memory.

    Reconstructs the conversation history from a Chainlit thread dictionary
    and creates a Memory instance with the historical messages.

    Args:
        thread: Chainlit thread dictionary containing:
            - id: Thread identifier (required)
            - name: Thread display name (optional)
            - steps: List of message steps in the thread

    Returns:
        A Memory instance populated with the conversation history.

    Raises:
        AppStateNotInitializedError: If state is not initialized.
        ValueError: If thread_id is missing from the thread.

    Note:
        Only root-level messages (those with no parentId) are restored.
        This filters out tool calls and other nested interactions.

        :func:`_create_memory` uses ``thread_id`` as both the ChromaDB
        collection name and the LlamaIndex ``Memory.session_id``, so the
        ``VectorMemoryBlock`` metadata filter always matches embeddings from
        the same thread across all sessions.

        ``memory.aset()`` is used instead of ``memory.aput()`` to populate
        the short-term sql buffer directly, without triggering the waterfall
        to ChromaDB.  The vector store already holds the embeddings from
        previous sessions; re-embedding on every resume would create
        duplicate entries.
    """
    thread_id = thread.get("id")
    if not thread_id:
        raise ValueError("Thread dictionary must contain a valid 'id' field")

    thread_name = thread.get("name", "Unnamed")
    logger.debug(f"Restoring chat history for thread {thread_id} ({thread_name})")

    chat_steps = thread.get("steps", [])
    logger.debug(f"Thread contains {len(chat_steps)} total steps")

    # Filter for root-level messages only (excludes tool calls etc.)
    root_messages = [m for m in chat_steps if m.get("parentId") is None]
    logger.debug(f"Found {len(root_messages)} root-level messages")

    memory = _create_memory(thread_id)

    # Build the chat history list from root-level steps
    chat_history: list[ChatMessage] = []
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
        chat_history.append(ChatMessage(role=role, content=content))

    # Populate the short-term sql buffer directly — no ChromaDB writes.
    # The vector store already holds embeddings from previous sessions;
    # re-embedding here would create duplicates on every resume.
    await memory.aset(chat_history)

    logger.info(f"Restored {len(chat_history)} messages for thread {thread_id}")
    return memory


@cl.on_app_startup
async def on_app_startup() -> None:
    """Initialize all services when the Chainlit app starts.

    Startup sequence:
        1. Initialize logging with file rotation
        2. Create database engine and tables
        3. Start LlamaCpp inference servers (blocking)
        4. Initialize LLM and embeddings clients
        5. Initialize vector database
        6. Initialize agent workflows

    Raises:
        Exception: If any startup step fails, the exception is logged and
            re-raised to prevent the app from starting in a broken state.

    Note:
        This function is called once when the Chainlit app starts.
        All services are stored in the global _state instance.
        The startup_complete flag is only set if all steps succeed.
    """
    global _log_sink_id
    try:
        # Ensure Chainlit's file upload directory exists. Chainlit creates it
        # at import time but deletes it on shutdown (shutil.rmtree). Without
        # this, session.files_dir.mkdir(exist_ok=True) raises FileNotFoundError
        # because the parent .files/ directory no longer exists.
        from chainlit.config import FILES_DIRECTORY

        FILES_DIRECTORY.mkdir(parents=True, exist_ok=True)

        # Initialize logging — remove all existing handlers first to prevent
        # duplicates from hot-reload or the default stderr handler.
        # This ensures a clean slate before adding our file handler.
        logger.remove()

        log_path = DebugConfig.logs_path
        _log_sink_id = logger.add(
            log_path,
            rotation="10 MB",
            level="DEBUG" if DEBUG else "INFO",
            format=LOG_FORMAT,
        )
        logger.info("Starting Aria web UI...")

        # Initialize database engine (shared across requests)
        logger.info("Initializing database...")
        _state.db_engine = create_engine(SQLiteConfig.db_url)
        Base.metadata.create_all(_state.db_engine)

        # Start LlamaCpp servers (blocking - waits for health checks)
        logger.info("Starting LlamaCpp inference servers...")
        _state.llama_manager = LlamaCppServerManager()
        _state.llama_manager.start_all()
        logger.info("All LlamaCpp servers ready")

        # Initialize LLM and embeddings
        logger.info("Initializing LLM and embeddings clients...")
        _state.llm = get_chat_llm(api_base=ChatConfig.api_url)
        _state.embeddings = get_embeddings_model(
            api_base=EmbeddingsConfig.api_url,
            model_name=EmbeddingsConfig.model,
        )

        # Initialize vector database
        logger.info("Initializing vector database...")
        _state.vector_db = ChromaDBPersistentClient(
            path=ChromaDBConfig.db_path,
            settings=ChromaDBSettings(
                is_persistent=True,
                persist_directory=ChromaDBConfig.db_path.absolute().as_posix(),
                anonymized_telemetry=False,
            ),
        )

        # Initialize workflows and agents
        logger.info("Initializing agent workflows...")
        from aria.agents import get_prompt_enhancer_agent

        _state.agents_workflow = get_agent_workflow(llm=_state.llm)
        _state.prompt_enhancer = get_prompt_enhancer_agent(llm=_state.llm)

        # Mark startup complete
        _state.startup_complete = True
        logger.info("Aria web UI startup complete")

    except Exception as e:
        logger.exception(f"Failed to start Aria web UI: {e}")
        # Clean up any partially initialized resources
        if _state.llama_manager:
            try:
                _state.llama_manager.stop_all()
            except Exception as cleanup_error:
                logger.error(f"Error during cleanup: {cleanup_error}")
        raise


@cl.on_app_shutdown
async def on_app_shutdown() -> None:
    """Clean up all services when the Chainlit app shuts down.

    Stops all LlamaCpp servers and resets the global state.
    This function is called once when the Chainlit app stops.
    """
    global _log_sink_id
    logger.info("Shutting down Aria web UI...")

    if _state.llama_manager:
        try:
            _state.llama_manager.stop_all()
            logger.info("All LlamaCpp servers stopped")
        except Exception as e:
            logger.error(f"Error stopping LlamaCpp servers: {e}")

    # Reset state
    _state.llama_manager = None
    _state.llm = None
    _state.embeddings = None
    _state.vector_db = None
    _state.agents_workflow = None
    _state.prompt_enhancer = None
    _state.startup_complete = False

    # Dispose database engine
    if _state.db_engine:
        _state.db_engine.dispose()
        _state.db_engine = None

    logger.info("Aria web UI shutdown complete")

    # Remove the log handler to prevent accumulation across restarts
    if _log_sink_id is not None:
        logger.remove(_log_sink_id)
        _log_sink_id = None


@cl.data_layer
def get_data_layer() -> SQLiteSQLAlchemyDataLayer:
    """Initialize and return the data layer for Chainlit.

    Creates the database tables if they don't exist and returns
    a data layer instance for Chainlit to use for persistence.

    Returns:
        A SQLiteSQLAlchemyDataLayer instance configured with:
        - SQLite database connection
        - Local file storage provider

    Note:
        This function is called by Chainlit during app initialization.
        The database engine is created here for Chainlit's internal use,
        but the shared engine in AppState should be used for other operations.
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
    """Handle user authentication against the database.

    Validates user credentials against the SQLite database and returns
    a Chainlit User instance if authentication succeeds.

    Args:
        username: The username provided in the login form.
        password: The password provided in the login form.

    Returns:
        A Chainlit User instance if authentication succeeds, None otherwise.

    Note:
        Authentication failures are logged at DEBUG level to avoid
        cluttering logs with failed login attempts. Errors during
        authentication are logged at ERROR level.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from aria.db.auth import verify_password
    from aria.db.models import User

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


@cl.on_chat_start
async def on_chat_start() -> None:
    """Initialize new chat session with available commands.

    Sets up the available slash commands for the chat interface.
    Currently only the "Enhance" command is available.

    Also ensures Chainlit's file-upload directory exists.  Chainlit
    deletes ``.files/`` on shutdown (``shutil.rmtree``) but its
    ``upload_file`` endpoint calls ``session.files_dir.mkdir(exist_ok=True)``
    without ``parents=True``, so if the parent ``.files/`` was removed
    the next upload raises ``FileNotFoundError``.  Re-creating it here
    (at the start of every session) prevents that race.
    """
    from chainlit.config import FILES_DIRECTORY

    FILES_DIRECTORY.mkdir(parents=True, exist_ok=True)

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
    """Restore previous chat session from thread data.

    Waits for AppState initialization if needed (handles the race
    condition where this fires before on_app_startup completes),
    then reconstructs conversation memory from the thread history.

    Args:
        thread: Chainlit thread dictionary containing the conversation
            history and metadata.

    Note:
        If initialization times out or restoration fails, the chat
        continues with empty memory — the user can still send new
        messages but won't have prior context in the agent's memory.
    """
    try:
        # Gate: wait for on_app_startup() to finish if it hasn't yet.
        # This handles the race where Chainlit fires on_chat_resume
        # before on_app_startup completes.
        if not _state.is_initialized():
            logger.info(
                "AppState not yet initialized, waiting for startup to complete..."
            )
            if not await _wait_for_initialization():
                logger.warning(
                    "AppState initialization timed out after 30s. "
                    "Continuing with empty memory."
                )
                return

        memory = await _restore_chat_history(thread)
        cl.user_session.set("memory", memory)
    except Exception as e:
        logger.exception(f"Failed to restore chat history: {e}")
        # Continue with empty memory - user can still chat


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """Handle incoming chat messages.

    Processes the user's message through the agent workflow and streams
    the response back to the client.

    Args:
        message: The incoming Chainlit message from the user.

    Note:
        This function:
        1. Validates the app state is initialized
        2. Processes any commands (like Enhance)
        3. Gets or creates conversation memory
        4. Streams the agent response to the client
        5. Handles errors gracefully with user notification

        Errors are caught, logged, and a user-friendly message is shown.
        The exception is not re-raised to prevent duplicate error messages.
    """
    output = cl.Message(content="")

    try:
        # Validate state before processing
        _state.validate_initialized()

        prompt = await _handle_message(message)

        # Get or create memory
        memory: Memory | None = cl.user_session.get("memory")
        if memory is None:
            memory = _create_memory(message.thread_id)
            cl.user_session.set("memory", memory)
            logger.debug(f"Created new Memory for thread {message.thread_id}")

        # Type assertion: validate() ensures agents_workflow is not None
        assert _state.agents_workflow is not None

        # Process with agent workflow
        handler = _state.agents_workflow.run(
            user_msg=prompt,
            memory=memory,
            max_iterations=ChatConfig.max_iteration,
        )

        current_step: cl.Step | None = None
        # Tracks whether AgentStream tokens were received for the current
        # agent turn. Used to avoid double-printing: streaming agents emit
        # both AgentStream deltas AND a final AgentOutput, so we only fall
        # back to AgentOutput.response.content when no stream tokens arrived.
        streamed_tokens: bool = False

        # Stream events as they arrive
        async for event in handler.stream_events():
            if isinstance(event, ToolCall):
                await maybe_remove_step(current_step)
                current_step = await send_tool_step(event)
                streamed_tokens = False
            elif isinstance(event, AgentStream):
                await maybe_remove_step(current_step)
                current_step = None
                await output.stream_token(event.delta)
                streamed_tokens = True
            elif isinstance(event, AgentOutput):
                # Non-streaming agents emit AgentOutput without preceding
                # AgentStream deltas.
                # Only write the response here when no stream tokens were
                # already received, to avoid duplicating streamed output.
                if not event.tool_calls and not streamed_tokens:
                    await maybe_remove_step(current_step)
                    current_step = None
                    content = (event.response.content or "").strip()
                    if content:
                        await output.stream_token(content)
                streamed_tokens = False

        # Finalize and send the message
        await output.send()
        await handler

    except AppStateNotInitializedError as e:
        logger.error(f"App state not initialized: {e}")
        output.content = (
            "The application is not fully initialized. "
            "Please wait a moment and try again."
        )
        await output.send()

    except Exception as e:
        error_msg = str(e)
        logger.exception(f"Error processing message: {e}")

        # Check for context size exceeded error
        if (
            "exceed_context_size_error" in error_msg
            or "exceeds the available context size" in error_msg
        ):
            output.content = (
                "The conversation has grown too large for the embeddings model to process. "
                "Consider starting a new chat thread to continue."
            )
        else:
            output.content = "An error occurred. Please try again."
        await output.send()
