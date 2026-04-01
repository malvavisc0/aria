"""Application lifecycle handlers for the Aria web UI.

This module provides startup and shutdown handlers that are invoked
by Chainlit when the application starts and stops. It manages:
- Database initialization (SQLite, ChromaDB)
- LLM and embeddings model setup
- LlamaCpp server management
- Browser automation (Lightpanda)
- Logging configuration
"""

from __future__ import annotations

import logging
import os

from chromadb import PersistentClient as ChromaDBPersistentClient
from chromadb.config import Settings as ChromaDBSettings
from loguru import logger
from sqlalchemy import create_engine

from aria.config.database import ChromaDB as ChromaDBConfig
from aria.config.database import SQLite as SQLiteConfig
from aria.config.folders import Debug as DebugConfig
from aria.config.models import Chat as ChatConfig
from aria.config.models import Embeddings as EmbeddingsConfig
from aria.llm import get_agent_workflow, get_chat_llm, get_embeddings_model
from aria.server.llama import LlamaCppServerManager
from aria.web.state import _state

LOG_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss} - {level} - {name}.{function} : {message}"
)

_HEALTH_ENDPOINTS = ("/health",)

_log_sink_id: int | None = None
_tool_call_sink_id: int | None = None


class _HealthCheckFilter(logging.Filter):
    """Logging filter to suppress health check endpoint requests.

    Filters out noisy health check requests from uvicorn access logs
    to reduce log verbosity while still capturing other access logs.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return not any(ep in msg for ep in _HEALTH_ENDPOINTS)


async def on_app_startup_handler() -> None:
    """Initialize the application on startup.

    Called by Chainlit when the application starts. Performs:
    - Creates files directory for uploads
    - Initializes Langfuse and LlamaIndex instrumentation
    - Configures logging with file rotation
    - Creates SQLite database and tables
    - Starts LlamaCpp inference servers
    - Initializes LLM and embeddings clients
    - Sets up ChromaDB vector database
    - Creates agent workflows
    - Starts Lightpanda browser if available

    Raises:
        Exception: If any critical initialization step fails,
            cleanup is attempted before re-raising.
    """
    global _log_sink_id, _tool_call_sink_id
    try:
        from chainlit.config import FILES_DIRECTORY

        FILES_DIRECTORY.mkdir(parents=True, exist_ok=True)

        _langfuse_keys = (
            "LANGFUSE_SECRET_KEY",
            "LANGFUSE_PUBLIC_KEY",
            "LANGFUSE_BASE_URL",
        )
        if all(os.getenv(k) for k in _langfuse_keys):
            from langfuse import get_client
            from openinference.instrumentation.llama_index import (
                LlamaIndexInstrumentor,
            )

            get_client()
            LlamaIndexInstrumentor().instrument()
            logger.info("Langfuse instrumentation initialized")
        else:
            _missing = [k for k in _langfuse_keys if not os.getenv(k)]
            logger.warning(
                f"Langfuse instrumentation disabled — "
                f"missing env vars: {', '.join(_missing)}"
            )

        logger.remove()

        log_path = DebugConfig.logs_path
        # Always store INFO+ to avoid DEBUG log spam (WebSocket frames, etc.)
        _log_sink_id = logger.add(
            log_path,
            rotation="10 MB",
            level="INFO",  # Never store DEBUG to keep logs clean
            format=LOG_FORMAT,
        )

        # Dedicated sink for tool-call debug logs (keeps main log clean).
        _tool_call_sink_id = logger.add(
            DebugConfig.logs_path.parent / "tool-calls.log",
            rotation="10 MB",
            level="DEBUG",
            filter=lambda r: "Calling" in r["message"],
            format=LOG_FORMAT,
        )
        logging.getLogger("uvicorn.access").addFilter(_HealthCheckFilter())
        # Suppress WebSocket frame debug logs (TEXT/PING/PONG/keepalive spam)
        for _ws_logger_name in (
            "websockets",
            "uvicorn.protocol.websockets",
            "uvicorn.protocols.websockets",
        ):
            logging.getLogger(_ws_logger_name).setLevel(logging.WARNING)
        logger.info("Starting Aria web UI...")

        # Mount local storage directory so the browser can fetch
        # element files (images, documents, etc.) via HTTP.
        from chainlit.server import app
        from starlette.staticfiles import StaticFiles

        from aria.config.folders import Storage as StorageConfig

        storage_dir = StorageConfig.path
        storage_dir.mkdir(parents=True, exist_ok=True)
        app.mount(
            "/storage",
            StaticFiles(directory=str(storage_dir)),
            name="local-storage",
        )
        logger.info(f"Mounted /storage → {storage_dir}")

        logger.info("Initializing database...")
        from aria.db.models import Base

        _state.db_engine = create_engine(SQLiteConfig.db_url)
        Base.metadata.create_all(_state.db_engine)

        logger.info("Starting LlamaCpp inference servers...")
        _state.llama_manager = LlamaCppServerManager()
        _state.llama_manager.start_all()
        logger.info("All LlamaCpp servers ready")

        logger.info("Initializing LLM and embeddings clients...")
        _state.llm = get_chat_llm(api_base=ChatConfig.api_url)
        _state.embeddings = get_embeddings_model(
            api_base=EmbeddingsConfig.api_url,
            model_name=EmbeddingsConfig.model,
        )

        logger.info("Initializing vector database...")
        _state.vector_db = ChromaDBPersistentClient(
            path=ChromaDBConfig.db_path,
            settings=ChromaDBSettings(
                is_persistent=True,
                persist_directory=ChromaDBConfig.db_path.absolute().as_posix(),
                anonymized_telemetry=False,
            ),
        )

        logger.info("Initializing agent workflows...")
        from aria.agents import get_prompt_enhancer_agent

        _state.agents_workflow = get_agent_workflow(llm=_state.llm)
        _state.prompt_enhancer = get_prompt_enhancer_agent(llm=_state.llm)

        from aria.config.api import Lightpanda

        if Lightpanda.is_available():
            from aria.tools.browser.manager import (
                LightpandaManager,
                set_browser_manager,
            )

            binary = Lightpanda.get_binary_path()
            if binary:
                browser_mgr = LightpandaManager(binary, port=Lightpanda.port)
                if await browser_mgr.start():
                    _state.browser_manager = browser_mgr
                    set_browser_manager(browser_mgr)
                    logger.info("Lightpanda browser started successfully")
                else:
                    logger.warning(
                        "Lightpanda browser failed to start — "
                        "browser tools disabled"
                    )
        else:
            logger.info("Lightpanda not installed — browser tools disabled")

        _state.startup_complete = True
        logger.info("Aria web UI startup complete")

    except Exception as e:
        logger.exception(f"Failed to start Aria web UI: {e}")
        if _state.llama_manager:
            try:
                _state.llama_manager.stop_all()
            except Exception as cleanup_error:
                logger.error(f"Error during cleanup: {cleanup_error}")
        raise


async def on_app_shutdown_handler() -> None:
    """Clean up resources on application shutdown.

    Called by Chainlit when the application is shutting down.
    Performs cleanup of:
    - LlamaCpp inference servers
    - Lightpanda browser
    - Database connections
    - Logging sinks
    """
    global _log_sink_id, _tool_call_sink_id
    logger.info("Shutting down Aria web UI...")

    if _state.llama_manager:
        try:
            _state.llama_manager.stop_all()
            logger.info("All LlamaCpp servers stopped")
        except Exception as e:
            logger.error(f"Error stopping LlamaCpp servers: {e}")

    if _state.browser_manager:
        try:
            await _state.browser_manager.stop()
            logger.info("Lightpanda browser stopped")
        except Exception as e:
            logger.error(f"Error stopping Lightpanda browser: {e}")
        finally:
            from aria.tools.browser.manager import set_browser_manager

            set_browser_manager(None)
            _state.browser_manager = None

    _state.llama_manager = None
    _state.llm = None
    _state.embeddings = None
    _state.vector_db = None
    _state.agents_workflow = None
    _state.prompt_enhancer = None
    _state.startup_complete = False

    if _state.db_engine:
        _state.db_engine.dispose()
        _state.db_engine = None

    logger.info("Aria web UI shutdown complete")

    if _log_sink_id is not None:
        logger.remove(_log_sink_id)
        _log_sink_id = None

    if _tool_call_sink_id is not None:
        logger.remove(_tool_call_sink_id)
        _tool_call_sink_id = None
