"""
Deep Reasoning Agent

This module provides a specialized agent designed for complex problem solving,
logical analysis, and deep conceptual reasoning. The agent combines web search
capabilities with structured reasoning tools to tackle intricate questions that
require both information gathering and sophisticated analytical thinking.

The DeepReasoningAgent follows the same patterns as other agents in
the codebase:
- Uses FunctionAgent framework from llama_index
- Integrates tools from aria.tools.search and aria.tools.reasoning modules
- Implements proper system prompts with clear instructions and best practices
- Follows security and logging conventions used throughout the codebase
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

PYTHON_DEVELOPMENT_TOOLS = "aria.tools.development"
REASONING_TOOLS = "aria.tools.reasoning"
WEB_SEARCH_TOOLS = "aria.tools.search"
FILESYSTEM_TOOLS = "aria.tools.files"


class DeepReasoningAgent(FunctionAgent):
    """
    A specialized agent for deep reasoning and complex problem solving.

    This agent extends FunctionAgent to provide sophisticated reasoning
    capabilities including structured analysis, web search integration,
    and reasoning session
    management. It's designed for tackling complex problems that require both
    information gathering and logical analysis.
    """

    @staticmethod
    def get_system_prompt(extras: str = "") -> str:
        """
        Return the system prompt for the Deep Reasoning Agent.

        Args:
            extras (str): Additional instructions to append to the system
                         prompt. Defaults to empty string.

        Returns:
            str: The complete system prompt with guidelines and best practices
        """
        instructions_dir = Path(__file__).parent / "instructions"
        core_path = instructions_dir / "core_rules.md"
        instructions_path = instructions_dir / "deep_reasoning.md"

        core = ""
        with open(core_path, mode="r", encoding="utf-8") as file:
            core = file.read()

        instructions = ""
        with open(instructions_path, mode="r", encoding="utf-8") as file:
            instructions = file.read()

        return f"{core}\n\n{instructions}\n\n# Additional Notes\n{extras}"


def get_agent(llm: LLM, extras: Optional[str] = None) -> DeepReasoningAgent:
    """
    Create a deep reasoning agent with the given LLM.

    This function initializes and returns a FunctionAgent configured for
    deep reasoning operations with comprehensive tool integration and
    structured reasoning capabilities.

    Args:
        llm (LLM): The language model to be used by the agent
        extras (str, optional): Additional system prompt instructions.
                               Defaults to empty string.

    Returns:
        DeepReasoningAgent: A configured deep reasoning agent ready for complex
            analysis.

    Security Features:
        - Integrates with existing tool security patterns
        - Follows established logging and debugging conventions
        - Uses standard agent configuration patterns
    """
    development_tools = importlib.import_module(PYTHON_DEVELOPMENT_TOOLS)
    reasoning_tools = importlib.import_module(REASONING_TOOLS)
    filesystem_tools = importlib.import_module(FILESYSTEM_TOOLS)
    web_search_tools = importlib.import_module(WEB_SEARCH_TOOLS)

    tools_selection = {
        PYTHON_DEVELOPMENT_TOOLS: [
            "execute_python_code",
        ],
        WEB_SEARCH_TOOLS: [
            "web_search",
            "get_file_from_url",
            "get_current_weather",
        ],
        FILESYSTEM_TOOLS: [
            "read_full_file",
            "read_file_chunk",
            "write_full_file",
            "file_exists",
        ],
    }

    tools = (
        [
            FunctionTool.from_defaults(fn=getattr(development_tools, name))
            for name in tools_selection[PYTHON_DEVELOPMENT_TOOLS]
        ]
        + [
            FunctionTool.from_defaults(fn=getattr(reasoning_tools, name))
            for name in reasoning_tools.__all__
        ]
        + [
            FunctionTool.from_defaults(fn=getattr(web_search_tools, name))
            for name in tools_selection[WEB_SEARCH_TOOLS]
        ]
        + [
            FunctionTool.from_defaults(fn=getattr(filesystem_tools, name))
            for name in tools_selection[FILESYSTEM_TOOLS]
        ]
    )

    # On-demand tool documentation.
    tools.append(FunctionTool.from_defaults(fn=tool_help))

    tools = filter_tools_for_llamacpp(tools, agent_name="Socrates")

    logger.debug(f"Creating DeepReasoningAgent with {len(tools)} tools")
    logger.debug(f"Tool names: {[tool.metadata.name for tool in tools]}")
    logger.debug(f"LLM type: {type(llm)}")

    agent = DeepReasoningAgent(
        name="Socrates",
        description=(
            "Specialized in deep reasoning, complex problem solving, "
            "and structured analytical thinking with web search capabilities."
        ),
        tools=tools,
        llm=llm,
        system_prompt=DeepReasoningAgent.get_system_prompt(extras or ""),
        streaming=True,
        verbose=True,
    )

    return agent
