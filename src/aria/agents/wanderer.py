"""
Web Researcher Agent

This module defines a specialized agent for web research operations,
providing tools for web search, content downloading, and file operations
to gather and analyze information from the internet.
"""

import importlib
from typing import Dict, List, Optional

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
    def get_system_prompt(
        extras: Optional[str] = None,
        variables: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Return the system prompt for the Web Researcher Agent.

        Args:
            extras: Additional instructions to append to the system
                prompt. Defaults to empty string.
            variables: Optional template variables for
                ``{{KEY}}`` substitution.

        Returns:
            The complete system prompt with guidelines and
            best practices.
        """
        return load_agent_instructions(
            agent_name="wanderer",
            extras=extras,
            variables=variables,
            include_core=True,
        )


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
            "python",
        ],
        FILESYSTEM_TOOLS: [
            "read_file",
            "write_file",
            "file_info",
        ],
        WEB_SEARCH_TOOLS: [
            "web_search",
            "download",
            "get_youtube_video_transcription",
            "get_current_weather",
        ],
    }

    # Conditionally add browser tools if Lightpanda is installed
    from aria.config.api import Lightpanda

    browser_tools_module = None
    browser_available = Lightpanda.is_available()
    if browser_available:
        browser_tools_module = importlib.import_module(BROWSER_TOOLS)
        tools_selection[BROWSER_TOOLS] = [
            "open_url",
            "browser_click",
        ]
        logger.info("Browser tools enabled (Lightpanda available)")

    browser_note = (
        "Available and ready to use." if browser_available else "NOT available"
    )
    template_vars = {"BROWSER_TOOLS_NOTE": browser_note}

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
        logger.info("Browser tools enabled (Lightpanda available)")

    logger.info(f"Creating WebResearcherAgent with {len(tools)} tools")

    agent = WebResearcherAgent(
        name="Wanderer",
        description=(
            "Specialized in web research, information gathering, "
            "content downloading, and synthesis with file operations "
            "and basic data processing capabilities."
        ),
        tools=tools,
        llm=llm,
        system_prompt=WebResearcherAgent.get_system_prompt(
            extras=extras,
            variables=template_vars,
        ),
        verbose=True,
        streaming=True,
        can_handoff_to=can_handoff_to,
    )

    return agent
