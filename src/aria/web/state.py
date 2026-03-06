"""Application state management for the Aria web UI.

This module provides the global application state that is initialized
at startup and used throughout the application. It includes:
- AppState: Pydantic model holding all application-wide state
- AppStateNotInitializedError: Exception raised when state accessed before init

The state is managed as a singleton instance (`_state`) that is populated
by the lifecycle handlers in `lifecycle.py`.
"""

from __future__ import annotations

from typing import Any

from chromadb.api import ClientAPI
from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai_like import OpenAILike
from pydantic import BaseModel
from sqlalchemy import Engine

from aria.agents.prompt_enhancer import PromptEnhancerAgent
from aria.server.llama import LlamaCppServerManager

ROOT_MESSAGE_TYPES = ["user_message", "assistant_message"]


class AppStateNotInitializedError(RuntimeError):
    """Raised when AppState attributes are accessed before initialization.

    This exception is raised when code attempts to use application state
    before the startup handler has completed initialization.
    """

    def __init__(
        self, message: str = "AppState is not fully initialized"
    ) -> None:
        super().__init__(message)


class AppState(BaseModel):
    """Application state initialized at startup.

    This Pydantic model holds all application-wide state including:
    - LLM and embeddings clients
    - Vector database connection
    - Agent workflow
    - LlamaCpp server manager
    - Browser manager
    - Database engine

    The state is populated by on_app_startup_handler() in lifecycle.py
    and cleaned up by on_app_shutdown_handler().
    """

    model_config = {"arbitrary_types_allowed": True}

    llm: OpenAILike | None = None
    embeddings: OpenAIEmbedding | None = None
    vector_db: ClientAPI | None = None
    agents_workflow: AgentWorkflow | None = None
    prompt_enhancer: PromptEnhancerAgent | None = None
    llama_manager: LlamaCppServerManager | None = None
    browser_manager: Any = None
    db_engine: Engine | None = None
    startup_complete: bool = False

    def is_initialized(self) -> bool:
        """Check if the application state is fully initialized.

        Returns:
            bool: True if all required components are initialized.
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
        """Validate that the application state is fully initialized."""
        if self.llm is None:
            raise AppStateNotInitializedError("llm not initialized")
        if self.embeddings is None:
            raise AppStateNotInitializedError("embeddings not initialized")
        if self.vector_db is None:
            raise AppStateNotInitializedError("vector_db not initialized")
        if self.agents_workflow is None:
            raise AppStateNotInitializedError(
                "agents_workflow not initialized"
            )
        if self.db_engine is None:
            raise AppStateNotInitializedError("db_engine not initialized")
        if not self.startup_complete:
            raise AppStateNotInitializedError("startup not complete")


_state = AppState()
