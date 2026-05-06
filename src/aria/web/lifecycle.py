"""Application lifecycle handlers for the Aria web UI.

This module provides startup and shutdown handlers that are invoked
by Chainlit when the application starts and stops. It manages:
- Database initialization (SQLite, ChromaDB)
- LLM and embeddings model setup
- vLLM server management
- Browser automation (Lightpanda)
- Logging configuration
"""

from __future__ import annotations

import asyncio
import logging
import os

from chromadb import PersistentClient as ChromaDBPersistentClient
from chromadb.config import Settings as ChromaDBSettings
from loguru import logger
from sqlalchemy import create_engine

from aria.config.api import Vllm as VllmConfig
from aria.config.database import ChromaDB as ChromaDBConfig
from aria.config.database import SQLite as SQLiteConfig
from aria.config.folders import Debug as DebugConfig
from aria.config.models import Chat as ChatConfig
from aria.config.models import Embeddings as EmbeddingsConfig
from aria.llm import get_agent_workflow, get_chat_llm, get_embeddings_model
from aria.server.vllm import VllmServerManager
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


def _init_langfuse() -> None:
    """Initialize Langfuse instrumentation if env vars are present."""
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


def _init_logging() -> None:
    """Configure loguru file sinks and stdlib logger filters."""
    global _log_sink_id, _tool_call_sink_id

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
    # Filter uses the bound "tool_call" extra field set by log_tool_call
    # decorator — precise match instead of fragile string search.
    _tool_call_sink_id = logger.add(
        DebugConfig.logs_path.parent / "tool-calls.log",
        rotation="10 MB",
        level="DEBUG",
        filter=lambda r: r["extra"].get("tool_call", False),
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {message}",
    )
    logging.getLogger("uvicorn.access").addFilter(_HealthCheckFilter())
    # Suppress WebSocket frame debug logs (TEXT/PING/PONG/keepalive spam)
    for _ws_logger_name in (
        "websockets",
        "uvicorn.protocol.websockets",
        "uvicorn.protocols.websockets",
    ):
        logging.getLogger(_ws_logger_name).setLevel(logging.WARNING)


def _init_storage_mount() -> None:
    """Mount the local storage directory as a static file server."""
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


def _init_database() -> None:
    """Create the SQLite engine and ensure all tables exist."""
    from aria.db.models import Base

    _state.db_engine = create_engine(SQLiteConfig.db_url)
    Base.metadata.create_all(_state.db_engine)


def _init_vllm_servers() -> None:
    """Start all configured vLLM inference servers."""
    _state.vllm_manager = VllmServerManager()
    _state.vllm_manager.start_all()
    logger.info("All vLLM servers ready")


def _init_chat_llm() -> None:
    """Initialize the chat LLM client (requires vLLM to be healthy)."""
    _state.llm = get_chat_llm(
        api_base=ChatConfig.api_url,
        model=ChatConfig.model,
        api_key=VllmConfig.api_key,
    )


def _load_embeddings_sync() -> None:
    """Load the embeddings model in-process (CPU-only, no vLLM dependency)."""
    _state.embeddings = get_embeddings_model(
        model_name=EmbeddingsConfig.model_path or EmbeddingsConfig.model,
    )


def _init_vector_db() -> None:
    """Initialize the ChromaDB persistent vector database."""
    _state.vector_db = ChromaDBPersistentClient(
        path=ChromaDBConfig.db_path,
        settings=ChromaDBSettings(
            is_persistent=True,
            persist_directory=ChromaDBConfig.db_path.absolute().as_posix(),
            anonymized_telemetry=False,
        ),
    )


def _init_agent_workflows() -> None:
    """Create the agent workflow and prompt enhancer."""
    from aria.agents import get_prompt_enhancer_agent

    _state.agents_workflow = get_agent_workflow(llm=_state.llm)
    _state.prompt_enhancer = get_prompt_enhancer_agent(llm=_state.llm)


async def _init_browser() -> None:
    """Start the Lightpanda browser if available."""
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
                    "Lightpanda browser failed to start — browser tools disabled"
                )
    else:
        logger.info("Lightpanda not installed — browser tools disabled")


async def _cleanup_on_failure() -> None:
    """Clean up partially initialized resources after startup failure.

    Mirrors the shutdown order in reverse so that resources are freed
    in the correct dependency order.
    """
    global _log_sink_id, _tool_call_sink_id

    if _state.browser_manager:
        try:
            await _state.browser_manager.stop()
        except Exception:
            pass
        _state.browser_manager = None

    if _state.vllm_manager:
        try:
            _state.vllm_manager.stop_all()
        except Exception:
            pass
        _state.vllm_manager = None

    if _state.db_engine:
        try:
            _state.db_engine.dispose()
        except Exception:
            pass
        _state.db_engine = None

    # Remove log sinks last so that cleanup logging above is captured.
    if _log_sink_id is not None:
        logger.remove(_log_sink_id)
        _log_sink_id = None
    if _tool_call_sink_id is not None:
        logger.remove(_tool_call_sink_id)
        _tool_call_sink_id = None


async def on_app_startup_handler() -> None:
    """Initialize the application on startup.

    Called by Chainlit when the application starts. Orchestrates a
    sequence of initialization steps.  Critical infrastructure
    (logging, storage, database) failures are fatal and trigger a
    full rollback.  Non-critical subsystems (LLM servers, vector
    database, browser) are best-effort: failures are logged but do
    **not** prevent the app from starting so that core features
    (e.g. authentication) remain available.
    """
    # ------------------------------------------------------------------
    # Phase 1 – Critical infrastructure (failure is fatal)
    # ------------------------------------------------------------------
    try:
        from chainlit.config import FILES_DIRECTORY

        FILES_DIRECTORY.mkdir(parents=True, exist_ok=True)

        _init_langfuse()
        _init_logging()
        logger.info("Starting Aria web UI...")

        _init_storage_mount()

        logger.info("Initializing database...")
        _init_database()
    except Exception as e:
        logger.exception(f"Failed to start Aria web UI (critical): {e}")
        await _cleanup_on_failure()
        raise

    # ------------------------------------------------------------------
    # Phase 2 – Non-critical subsystems (failure is tolerated)
    # Each subsystem is initialized independently so that a failure in
    # one does not prevent others from starting.
    # ------------------------------------------------------------------
    _vllm_ready = False
    _llm_ready = False

    # Start embeddings load concurrently with vLLM warmup (CPU-only,
    # no dependency on vLLM). This hides embeddings load latency behind
    # the vLLM health-check wait (~300s max).
    logger.info("Loading embeddings model (concurrent with vLLM)...")
    embed_task = asyncio.create_task(asyncio.to_thread(_load_embeddings_sync))

    try:
        logger.info("Starting vLLM inference servers...")
        await asyncio.to_thread(_init_vllm_servers)
        _vllm_ready = True
    except Exception as e:
        logger.warning(
            f"vLLM servers failed to start: {e}. LLM features disabled."
        )

    # Await embeddings result (likely already done by now)
    try:
        await embed_task
        logger.info("Embeddings model loaded")
    except Exception as e:
        logger.warning(f"Embeddings model failed to load: {e}.")

    if _vllm_ready:
        try:
            logger.info("Initializing chat LLM client...")
            _init_chat_llm()
            _llm_ready = True
        except Exception as e:
            logger.warning(f"Chat LLM client failed to initialize: {e}.")

    try:
        logger.info("Initializing vector database...")
        _init_vector_db()
    except Exception as e:
        logger.warning(f"Vector database failed to initialize: {e}.")

    if _llm_ready and _state.llm is not None:
        try:
            logger.info("Initializing agent workflows...")
            _init_agent_workflows()
        except Exception as e:
            logger.warning(f"Agent workflows failed to initialize: {e}.")

    try:
        await _init_browser()
    except Exception as e:
        logger.warning(f"Browser failed to start: {e}.")

    _state.startup_complete = True
    logger.info("Aria web UI startup complete")


async def on_app_shutdown_handler() -> None:
    """Clean up resources on application shutdown.

    Called by Chainlit when the application is shutting down.
    Performs cleanup of:
    - vLLM inference servers
    - Lightpanda browser
    - Database connections
    - Logging sinks
    """
    global _log_sink_id, _tool_call_sink_id
    logger.info("Shutting down Aria web UI...")

    if _state.vllm_manager:
        try:
            _state.vllm_manager.stop_all()
            logger.info("All vLLM servers stopped")
        except Exception as e:
            logger.error(f"Error stopping vLLM servers: {e}")

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

    _state.vllm_manager = None
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

    # Log sinks are removed LAST so that all cleanup logging above is
    # captured by the file sinks. This is intentional — removing sinks
    # earlier would silently drop diagnostic messages during shutdown.
    if _log_sink_id is not None:
        logger.remove(_log_sink_id)
        _log_sink_id = None

    if _tool_call_sink_id is not None:
        logger.remove(_tool_call_sink_id)
        _tool_call_sink_id = None
