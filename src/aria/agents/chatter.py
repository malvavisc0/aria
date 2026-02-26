"""Chatter agent module.

This module provides a conversational agent implementation for natural dialogue
and general knowledge questions. The ChatterAgent class creates a friendly AI
assistant that responds to user queries without using external tools, making it
suitable for casual conversation, support, and information sharing.
"""

from typing import Optional

from llama_index.core.agent import FunctionAgent
from llama_index.core.llms import LLM
from llama_index.core.tools import FunctionTool
from loguru import logger

from aria.agents.tool_schema import filter_tools_for_llamacpp
from aria.agents.utils import load_agent_instructions
from aria.tools.files.functions import read_full_file
from aria.tools.search import (
    get_current_weather,
    get_file_from_url,
    get_youtube_video_transcription,
)


class ChatterAgent(FunctionAgent):
    """
    A simple conversational agent that provides friendly and helpful responses
    without using any external tools. This agent is designed for natural
    dialogue, general knowledge questions, and supportive interaction.

    The agent loads its behavior instructions from the chatter.md file in the
    instructions directory and can be customized with additional context
    through the extras parameter.
    """

    @staticmethod
    def get_system_prompt(extras: str = "") -> str:
        """
        Constructs the system prompt for the agent by combining the base
        instructions from a Markdown file with optional extra context.

        Args:
            extras: Additional context or instructions to append to the base
                   instructions. Defaults to an empty string.

        Returns:
            The combined system prompt as a string.
        """
        return load_agent_instructions("chatter", extras)


def get_agent(llm: LLM, extras: Optional[str] = None) -> ChatterAgent:
    """Factory function to create and return a ChatterAgent instance.

    This function initializes a ChatterAgent with the provided LLM and optional
    extras, setting up a friendly conversational AI assistant for natural
    dialogue and general knowledge questions.

    Args:
        llm: The language model to use for generating responses.
        extras: Optional additional context or instructions to customize the
            agent's behavior.

    Returns:
        A configured ChatterAgent instance ready for conversation.
    """
    tools = [
        FunctionTool.from_defaults(fn=get_youtube_video_transcription),
        FunctionTool.from_defaults(fn=get_current_weather),
        FunctionTool.from_defaults(fn=get_file_from_url),
        FunctionTool.from_defaults(fn=read_full_file),
    ]
    tools = filter_tools_for_llamacpp(tools, agent_name="Aria")

    logger.debug(f"Creating ChatterAgent with {len(tools)} tools")
    logger.debug(f"LLM type: {type(llm)}")

    agent = ChatterAgent(
        name="Aria",
        description="A friendly conversational AI assistant for natural "
        "dialogue and general knowledge questions",
        tools=tools,
        llm=llm,
        system_prompt=ChatterAgent.get_system_prompt(extras or ""),
        streaming=True,
        verbose=True,
    )

    return agent
