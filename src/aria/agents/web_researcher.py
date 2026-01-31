"""
Web Researcher Agent

This module defines a specialized agent for web research operations,
providing tools for web search, content downloading, and file operations
to gather and analyze information from the internet.
"""

import importlib
from pathlib import Path
from typing import Optional

from llama_index.core.agent import FunctionAgent
from llama_index.core.llms import LLM
from llama_index.core.tools import FunctionTool
from loguru import logger

from aria.agents.tool_schema import filter_tools_for_llamacpp
from aria.tools.documentation import tool_help

PYTHON_DEVELOPMENT_TOOLS = "aria2.tools.development"
FILESYSTEM_TOOLS = "aria2.tools.files"
WEB_SEARCH_TOOLS = "aria2.tools.search"


class WebResearcherAgent(FunctionAgent):
    """
    A specialized agent for web research operations.

    This agent extends FunctionAgent to provide web research capabilities
    including web search, content downloading, file operations, and basic
    Python execution for data processing.
    """

    @staticmethod
    def get_system_prompt(extras: str = "") -> str:
        """
        Return the system prompt for the Web Researcher Agent.

        Args:
            extras (str): Additional instructions to append to the system
                prompt. Defaults to empty string.

        Returns:
            str: The complete system prompt with guidelines and best practices
        """
        instructions_dir = Path(__file__).parent / "instructions"
        core_path = instructions_dir / "core_rules.md"
        instructions_path = instructions_dir / "web_researcher.md"

        core = ""
        with open(core_path, mode="r", encoding="utf-8") as file:
            core = file.read()

        instructions = ""
        with open(instructions_path, mode="r", encoding="utf-8") as file:
            instructions = file.read()

        return f"{core}\n\n{instructions}\n\n# Additional Notes\n{extras}"


def get_agent(llm: LLM, extras: Optional[str] = None) -> WebResearcherAgent:
    """
    Create a web researcher agent with the given LLM.

    Args:
        llm (LLM): The language model to use for the agent
        extras (str, optional): Additional system prompt instructions

    Returns:
        WebResearcherAgent: A configured web research agent instance

    The agent is initialized with tools for web search, content downloading,
    file operations, and basic Python execution for data processing.
    """
    development_tools = importlib.import_module(PYTHON_DEVELOPMENT_TOOLS)
    filesystem_tools = importlib.import_module(FILESYSTEM_TOOLS)
    web_search_tools = importlib.import_module(WEB_SEARCH_TOOLS)

    tools_selection = {
        PYTHON_DEVELOPMENT_TOOLS: [
            "execute_python_code",
        ],
        FILESYSTEM_TOOLS: [
            "create_directory",
            "read_file_chunk",
            "read_full_file",
            "insert_lines_at",
            "get_file_info",
            "write_full_file",
            "replace_lines_range",
            "search_in_files",
            "file_exists",
        ],
        WEB_SEARCH_TOOLS: [
            "web_search",
            "get_file_from_url",
            "get_youtube_video_transcription",
            "get_current_weather",
        ],
    }
    tools = (
        [
            FunctionTool.from_defaults(fn=getattr(filesystem_tools, name))
            for name in tools_selection[FILESYSTEM_TOOLS]
        ]
        + [
            FunctionTool.from_defaults(fn=getattr(development_tools, name))
            for name in tools_selection[PYTHON_DEVELOPMENT_TOOLS]
        ]
        + [
            FunctionTool.from_defaults(fn=getattr(web_search_tools, name))
            for name in tools_selection[WEB_SEARCH_TOOLS]
        ]
    )

    # On-demand tool documentation.
    tools.append(FunctionTool.from_defaults(fn=tool_help))

    tools = filter_tools_for_llamacpp(tools, agent_name="Researcher")

    logger.info(f"Creating WebResearcherAgent with {len(tools)} tools")
    logger.info(f"Tool names: {[tool.metadata.name for tool in tools]}")
    logger.info(f"LLM type: {type(llm)}")
    logger.info(f"LLM model: {getattr(llm, 'model', 'unknown')}")

    agent = WebResearcherAgent(
        name="Wanderer",
        description=(
            "Specialized in web research, information gathering, "
            "content downloading, and synthesis with file operations "
            "and basic data processing capabilities."
        ),
        tools=tools,
        llm=llm,
        system_prompt=WebResearcherAgent.get_system_prompt(extras or ""),
        verbose=True,
        streaming=True,
    )

    return agent
