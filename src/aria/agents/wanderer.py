"""
Web Researcher Agent

This module defines a specialized agent for web research operations,
providing tools for web search, content downloading, and file operations
to gather and analyze information from the internet.
"""

import importlib
from typing import List, Optional

from llama_index.core.agent import FunctionAgent
from llama_index.core.llms import LLM
from llama_index.core.tools import FunctionTool
from loguru import logger

from aria.agents.instructions import load_agent_instructions

PYTHON_DEVELOPMENT_TOOLS = "aria.tools.development"
FILESYSTEM_TOOLS = "aria.tools.files"
WEB_SEARCH_TOOLS = "aria.tools.search"
BROWSER_TOOLS = "aria.tools.browser"


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
        return load_agent_instructions("wanderer", extras)


def get_agent(
    llm: LLM,
    extras: Optional[str] = None,
    can_handoff_to: Optional[List[str]] | None = None,
) -> WebResearcherAgent:
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
            "read_full_file",
            "write_full_file",
            "file_exists",
        ],
        WEB_SEARCH_TOOLS: [
            "web_search",
            "get_file_from_url",
            "get_youtube_video_transcription",
            "get_current_weather",
        ],
    }

    # Conditionally add browser tools if Lightpanda is installed
    from aria.config.api import Lightpanda

    browser_tools_module = None
    if Lightpanda.is_available():
        browser_tools_module = importlib.import_module(BROWSER_TOOLS)
        tools_selection[BROWSER_TOOLS] = [
            "open_url",
            "browser_click",
            "browser_screenshot",
        ]
        logger.info("Browser tools enabled (Lightpanda available)")
    else:
        logger.info(
            "Lightpanda not installed — browser tools disabled. "
            "Run 'aria lightpanda download' to enable."
        )

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

    # Add browser tools if available (async — registered via async_fn)
    if browser_tools_module:
        tools += [
            FunctionTool.from_defaults(
                async_fn=getattr(browser_tools_module, name)
            )
            for name in tools_selection[BROWSER_TOOLS]
        ]

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
        can_handoff_to=can_handoff_to,
    )

    return agent
