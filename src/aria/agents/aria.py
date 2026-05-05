"""Chatter agent module.

This module provides the unified Aria agent — a single conversational agent
that handles all tasks using core + file tools. Domain-specific capabilities
(web search, finance, IMDb, etc.) are accessed via CLI commands through
the ``shell`` tool.
"""

from typing import Optional

from llama_index.core.agent import FunctionAgent
from llama_index.core.llms import LLM
from loguru import logger

from aria.agents.instructions import load_agent_instructions
from aria.tools.registry import CORE_LITE, FILES_LITE, get_tools


class ChatterAgent(FunctionAgent):
    """
    The unified Aria agent.

    Handles natural dialogue, general knowledge, and file operations
    directly. Domain-specific tasks (web search, finance, entertainment,
    etc.) are delegated to CLI commands via the ``shell`` tool.
    """

    @staticmethod
    def get_system_prompt(extras: Optional[str] = None) -> str:
        """
        Constructs the system prompt for the agent by combining the base
        instructions from a Markdown file with optional extra context.

        Args:
            extras: Additional context or instructions to append to the base
                   instructions. Defaults to an empty string.

        Returns:
            The combined system prompt as a string.
        """
        return load_agent_instructions(agent_name="aria", extras=extras)


def get_agent(
    llm: LLM,
    extras: Optional[str] = None,
) -> ChatterAgent:
    """Factory function to create and return a ChatterAgent instance.

    Loads only core + file tools from the registry. Domain tools
    (web, finance, imdb, http, process, browser, development)
    are accessed via CLI commands through the ``shell`` tool.

    Args:
        llm: The language model to use for generating responses.
        extras: Optional additional context or instructions to customize the
            agent's behavior.

    Returns:
        A configured ChatterAgent instance ready for conversation.
    """

    tools = get_tools([CORE_LITE, FILES_LITE])  # Lean tool set for Aria

    logger.debug(f"Creating ChatterAgent with {len(tools)} tools")

    agent = ChatterAgent(
        name="Aria",
        description=(
            "A friendly conversational AI assistant for natural dialogue, "
            "general knowledge, and complex reasoning with structured analysis"
        ),
        tools=tools,
        llm=llm,
        system_prompt=ChatterAgent.get_system_prompt(extras=extras),
        streaming=True,
        verbose=False,
    )

    return agent
