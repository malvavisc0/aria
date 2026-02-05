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
from pathlib import Path
from typing import Optional

from llama_index.core.agent import FunctionAgent
from llama_index.core.llms import LLM
from llama_index.core.tools import FunctionTool

from aria.agents.tool_schema import filter_tools_for_llamacpp
from aria.tools.documentation import tool_help

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
        instructions_dir = Path(__file__).parent / "instructions"
        core_path = instructions_dir / "core_rules.md"
        instructions_path = instructions_dir / "file_editor.md"

        core = ""
        with open(core_path, mode="r", encoding="utf-8") as file:
            core = file.read()

        instructions = ""
        with open(instructions_path, mode="r", encoding="utf-8") as file:
            instructions = file.read()

        return f"{core}\n\n{instructions}\n\n# Additional Notes\n{extras}"


def get_agent(llm: LLM, extras: Optional[str] = None) -> FileEditorAgent:
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

    # On-demand tool documentation.
    tools.append(FunctionTool.from_defaults(fn=tool_help))

    tools = filter_tools_for_llamacpp(tools, agent_name="Notepad")

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
    )

    return agent
