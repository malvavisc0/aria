"""Python Developer Agent

This module defines a specialized agent for Python development operations,
providing tools for code validation, execution, and file operations within
a secure sandboxed environment.
"""

import importlib
from typing import Optional

from llama_index.core.agent import FunctionAgent
from llama_index.core.llms import LLM
from llama_index.core.tools import FunctionTool
from loguru import logger

from aria.agents.tool_schema import filter_tools_for_llamacpp
from aria.agents.utils import load_agent_instructions
from aria.tools.documentation import tool_help

PYTHON_DEVELOPMENT_TOOLS = "aria.tools.development"
FILESYSTEM_TOOLS = "aria.tools.files"
WEB_SEARCH_TOOLS = "aria.tools.search"


class PythonDeveloperAgent(FunctionAgent):
    """
    A specialized agent for python development operations.

    This agent extends FunctionAgent to provide Python-specific development
    capabilities including code execution, syntax checking, and file operations
    with security constraints.
    """

    @staticmethod
    def get_system_prompt(extras: str = "") -> str:
        """
        Return the system prompt for the Python Developer Agent.

        Args:
            extras (str): Additional instructions to append to the system
                         prompt. Defaults to empty string.

        Returns:
            str: The complete system prompt with guidelines and best practices
        """
        return load_agent_instructions("python_developer", extras)


def get_agent(llm: LLM, extras: Optional[str] = None) -> PythonDeveloperAgent:
    """
    Create a python developer agent with the given LLM.

    Args:
        llm (LLM): The language model to use for the agent
        extras (str, optional): Additional system prompt instructions

    Returns:
        PythonDeveloperAgent: A configured Python development agent instance

    The agent is initialized with tools from the development module and
    configured with security features including restricted builtins,
    execution timeouts, and isolated namespaces to prevent malicious code
    execution.
    """
    development_tools = importlib.import_module(PYTHON_DEVELOPMENT_TOOLS)
    filesystem_tools = importlib.import_module(FILESYSTEM_TOOLS)
    web_search_tools = importlib.import_module(WEB_SEARCH_TOOLS)

    tools_selection = {
        PYTHON_DEVELOPMENT_TOOLS: [
            "check_python_syntax",
            "check_python_file_syntax",
            "execute_python_code",
            "execute_python_file",
        ],
        FILESYSTEM_TOOLS: [
            "create_directory",
            "get_directory_tree",
            "move_file",
            "read_file_chunk",
            "read_full_file",
            "insert_lines_at",
            "get_file_info",
            "write_full_file",
            "replace_lines_range",
            "search_files_by_name",
            "search_in_files",
            "list_files",
            "delete_lines_range",
            "file_exists",
            "copy_file",
            "get_file_permissions",
            "append_to_file",
        ],
        WEB_SEARCH_TOOLS: [
            "web_search",
            "get_file_from_url",
            "get_youtube_video_transcription",
        ],
    }

    tools = (
        [
            FunctionTool.from_defaults(fn=getattr(development_tools, name))
            for name in tools_selection[PYTHON_DEVELOPMENT_TOOLS]
        ]
        + [
            FunctionTool.from_defaults(fn=getattr(filesystem_tools, name))
            for name in tools_selection[FILESYSTEM_TOOLS]
        ]
        + [
            FunctionTool.from_defaults(fn=getattr(web_search_tools, name))
            for name in tools_selection[WEB_SEARCH_TOOLS]
        ]
    )

    # On-demand tool documentation.
    tools.append(FunctionTool.from_defaults(fn=tool_help))

    tools = filter_tools_for_llamacpp(tools, agent_name="Developer")

    logger.debug(f"Creating PythonDeveloperAgent with {len(tools)} tools")
    logger.debug(f"Tool names: {[tool.metadata.name for tool in tools]}")
    logger.debug(f"LLM type: {type(llm)}")

    agent = PythonDeveloperAgent(
        name="Developer",
        description=(
            "Specialized in Python development with sandboxed code execution, "
            "syntax validation, file operations, and web search capabilities."
        ),
        tools=tools,
        llm=llm,
        system_prompt=PythonDeveloperAgent.get_system_prompt(extras or ""),
        streaming=True,
        verbose=True,
    )

    return agent
