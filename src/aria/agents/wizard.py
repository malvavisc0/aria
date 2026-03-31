"""
Market Analyst Agent

This module defines a specialized agent for market analysis and financial
research operations, providing tools for data retrieval, web search, and
file operations within a secure sandboxed environment.
"""

import importlib
from typing import Dict, List, Optional

from llama_index.core.agent import FunctionAgent
from llama_index.core.llms import LLM
from llama_index.core.tools import FunctionTool
from loguru import logger

from aria.agents.instructions import load_agent_instructions

FILESYSTEM_TOOLS = "aria.tools.files"
WEB_SEARCH_TOOLS = "aria.tools.search"
BROWSER_TOOLS = "aria.tools.browser"


class MarketAnalystAgent(FunctionAgent):
    """
    A specialized agent for market analysis and financial research operations.

    This agent extends FunctionAgent to provide financial analysis capabilities
    including data retrieval, web search, and file operations with security
    constraints for handling sensitive financial information.
    """

    @staticmethod
    def get_system_prompt(
        extras: Optional[str] = None,
        variables: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Return the system prompt for the Market Analyst Agent.

        Args:
            extras (str): Additional instructions to append to the system
                         prompt. Defaults to empty string.

        Returns:
            str: The complete system prompt with guidelines and best practices
        """
        return load_agent_instructions(
            agent_name="wizard", extras=extras, include_core=True
        )


def get_agent(
    llm: LLM,
    extras: Optional[str] = None,
    can_handoff_to: Optional[List[str]] | None = None,
) -> MarketAnalystAgent:
    """
    Create a market analyst agent with the given LLM.

    Args:
        llm (LLM): The language model to use for the agent
        extras (str, optional): Additional system prompt instructions

    Returns:
        MarketAnalystAgent: A configured market analysis agent instance

    The agent is initialized with tools for financial data retrieval, web
    search, and file operations with security features including restricted
    builtins,
    execution timeouts, and isolated namespaces to prevent malicious code
    execution.
    """
    tools_selection = {
        WEB_SEARCH_TOOLS: [
            "fetch_current_stock_price",
            "fetch_company_information",
            "fetch_ticker_news",
            "duckduckgo_web_search",
            "grab_from_url",
        ],
        FILESYSTEM_TOOLS: [
            "read_full_file",
            "read_file_chunk",
            "write_full_file",
            "file_exists",
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

    filesystem_tools = importlib.import_module(FILESYSTEM_TOOLS)
    web_search_tools = importlib.import_module(WEB_SEARCH_TOOLS)

    tools = [
        FunctionTool.from_defaults(fn=getattr(filesystem_tools, name))
        for name in tools_selection[FILESYSTEM_TOOLS]
    ] + [
        FunctionTool.from_defaults(fn=getattr(web_search_tools, name))
        for name in tools_selection[WEB_SEARCH_TOOLS]
    ]

    if browser_tools_module:
        tools += [
            FunctionTool.from_defaults(
                async_fn=getattr(browser_tools_module, name)
            )
            for name in tools_selection[BROWSER_TOOLS]
        ]
        logger.info("Browser tools enabled (Lightpanda available)")

    logger.info(f"Creating WebResearcherAgent with {len(tools)} tools")

    agent = MarketAnalystAgent(
        name="Wizard",
        description=(
            "Specialized in financial market analysis, data retrieval, "
            "and research with web search capabilities and secure file "
            "operations."
        ),
        tools=tools,
        llm=llm,
        system_prompt=MarketAnalystAgent.get_system_prompt(
            extras=extras,
            variables=template_vars,
        ),
        streaming=True,
        verbose=True,
        can_handoff_to=can_handoff_to,
    )

    return agent
