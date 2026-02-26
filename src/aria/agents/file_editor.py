"""
File Editor Agent

This module provides a specialized agent for handling file operations
including reading, writing, and manipulating files. The agent uses the
FunctionAgent framework from llama_index and leverages tools from the
files module to perform actual file operations.

The agent follows strict security practices including:
- Automatic backup creation with .backup extension for all modifications
- Automatic cleanup of backup files after successful operations
- Rollback capability using backup files in case of operation failures
"""

import importlib
from typing import List, Optional

from llama_index.core.agent import FunctionAgent
from llama_index.core.llms import LLM
from llama_index.core.tools import FunctionTool

from aria.agents.utils import load_agent_instructions

FILESYSTEM_TOOLS = "aria.tools.files"


class FileEditorAgent(FunctionAgent):
    """
    A specialized agent for file editing operations.
    """

    @staticmethod
    def get_system_prompt(extras: str = "") -> str:
        """
        Return the system prompt for the File Editor Agent.

        Args:
            extras (str): Additional instructions to append to the system
                         prompt. Defaults to empty string.

        Returns:
            str: The complete system prompt with guidelines and best practices
        """
        return load_agent_instructions("file_editor", extras)


def get_agent(
    llm: LLM,
    extras: Optional[str] = None,
    can_handoff_to: Optional[List[str]] | None = None,
) -> FileEditorAgent:
    """
    Create a file editor agent with the given LLM.

    This function initializes and returns a FunctionAgent configured for
    secure file operations with comprehensive validation and safety features.

    Args:
        llm (LLM): The language model to be used by the agent
        extras (str, optional): Additional system prompt instructions.
                               Defaults to empty string.

    Returns:
        FileEditorAgent: A configured file editor agent ready for operations

    Security Features:
        - Path traversal protection and file type validation
        - Automatic backup creation for destructive operations
        - Atomic writes to prevent file corruption
        - Size limits and streaming for large files
    """
    functions = importlib.import_module(FILESYSTEM_TOOLS)

    tools = [
        FunctionTool.from_defaults(fn=getattr(functions, name))
        for name in functions.__all__
    ]

    agent = FileEditorAgent(
        name="Notepad",
        description=(
            "Specialized in secure file operations with streaming support "
            "for large files and automatic backup management."
        ),
        tools=tools,
        llm=llm,
        system_prompt=FileEditorAgent.get_system_prompt(extras or ""),
        streaming=True,
        verbose=True,
        can_handoff_to=can_handoff_to,
    )

    return agent
