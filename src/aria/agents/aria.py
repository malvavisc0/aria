"""Chatter agent module.

This module provides the unified Aria agent — a single conversational agent
that handles all tasks using core + file tools + the ``ax`` dispatcher for
domain-specific capabilities (web search, finance, IMDb, etc.).
"""

from llama_index.core.agent import FunctionAgent
from llama_index.core.llms import LLM
from loguru import logger

from aria.agents.instructions import load_agent_instructions
from aria.tools.registry import AX, CORE_LITE, FILES_LITE, get_tools


class ChatterAgent(FunctionAgent):
    """
    The unified Aria agent.

    Handles natural dialogue, general knowledge, and file operations
    directly. Domain-specific tasks (web search, finance, entertainment,
    etc.) are delegated to CLI commands via the ``shell`` tool.
    """

    @staticmethod
    def get_system_prompt(extras: str | None = None) -> str:
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

    @classmethod
    def get_instructions(cls) -> str:
        """Return the full system prompt as the agent would see it at runtime.

        Composes all base sections + agent-specific markdown with the
        runtime extras (date, OS, restricted builtins, agent ID) that
        ``get_agent_workflow`` generates via ``get_instructions_extras``.

        Returns:
            The complete system prompt string.
        """
        from aria.llm import get_instructions_extras

        extras = get_instructions_extras(agent_name="aria")
        return cls.get_system_prompt(extras=extras)


def get_agent(
    llm: LLM,
    extras: str | None = None,
) -> ChatterAgent:
    """Factory function to create and return a ChatterAgent instance.

    Loads core + file tools + the unified ``ax`` dispatcher from the
    registry. Domain tools (web, finance, imdb, http, process, browser,
    development) are accessed through the ``ax`` tool directly.

    Args:
        llm: The language model to use for generating responses.
        extras: Optional additional context or instructions to customize the
            agent's behavior.

    Returns:
        A configured ChatterAgent instance ready for conversation.
    """

    tools = get_tools([CORE_LITE, FILES_LITE, AX])

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
