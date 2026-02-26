"""
Market Analyst Agent

This module defines a specialized agent for market analysis and financial
research operations, providing tools for data retrieval, web search, and
file operations within a secure sandboxed environment.
"""

import importlib
from typing import Optional

from llama_index.core.agent import FunctionAgent
from llama_index.core.llms import LLM
from llama_index.core.tools import FunctionTool

from aria.agents.tool_schema import filter_tools_for_llamacpp
from aria.agents.utils import load_agent_instructions

PYTHON_DEVELOPMENT_TOOLS = "aria.tools.development"
FILESYSTEM_TOOLS = "aria.tools.files"
WEB_SEARCH_TOOLS = "aria.tools.search"


class MarketAnalystAgent(FunctionAgent):
    """
    A specialized agent for market analysis and financial research operations.

    This agent extends FunctionAgent to provide financial analysis capabilities
    including data retrieval, web search, and file operations with security
    constraints for handling sensitive financial information.
    """

    @staticmethod
    def get_system_prompt(extras: str = "") -> str:
        """
        Return the system prompt for the Market Analyst Agent.

        Args:
            extras (str): Additional instructions to append to the system
                         prompt. Defaults to empty string.

        Returns:
            str: The complete system prompt with guidelines and best practices
        """
        return load_agent_instructions("market_analyist", extras)


def get_agent(llm: LLM, extras: Optional[str] = None) -> MarketAnalystAgent:
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
    development_tools = importlib.import_module(PYTHON_DEVELOPMENT_TOOLS)
    filesystem_tools = importlib.import_module(FILESYSTEM_TOOLS)
    web_search_tools = importlib.import_module(WEB_SEARCH_TOOLS)

    tools_selection = {
        PYTHON_DEVELOPMENT_TOOLS: [
            "execute_python_code",
        ],
        WEB_SEARCH_TOOLS: [
            "fetch_current_stock_price",
            "fetch_company_information",
            "fetch_ticker_news",
            "web_search",
            "get_file_from_url",
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

    tools = filter_tools_for_llamacpp(tools, agent_name="Wizard")

    agent = MarketAnalystAgent(
        name="Wizard",
        description=(
            "Specialized in financial market analysis, data retrieval, "
            "and research with web search capabilities and secure file "
            "operations."
        ),
        tools=tools,
        llm=llm,
        system_prompt=MarketAnalystAgent.get_system_prompt(extras or ""),
        streaming=True,
        verbose=True,
    )

    return agent
