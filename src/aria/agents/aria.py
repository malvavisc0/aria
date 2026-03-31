"""Chatter agent module.

This module provides a conversational agent implementation for natural dialogue
and general knowledge questions. The ChatterAgent class creates a friendly AI
assistant that responds to user queries, making it suitable for casual
conversation, support, and information sharing.
"""

from typing import List, Optional

from llama_index.core.agent import FunctionAgent
from llama_index.core.llms import LLM
from llama_index.core.tools import FunctionTool
from loguru import logger

from aria.agents.instructions import load_agent_instructions
from aria.config.api import Lightpanda
from aria.tools.browser import browser_click, open_url
from aria.tools.files import edit_file, file_info, read_file, write_file
from aria.tools.planner import plan
from aria.tools.reasoning import reasoning
from aria.tools.scratchpad import scratchpad
from aria.tools.search import (
    download,
    get_current_weather,
    get_youtube_video_transcription,
    web_search,
)
from aria.tools.shell import shell
from aria.tools.vision.functions import make_parse_pdf


class ChatterAgent(FunctionAgent):
    """
    A conversational agent that provides friendly and helpful responses.
    Handles natural dialogue, general knowledge questions, and supportive
    interaction. Can call tools directly — including ``parse_pdf`` for
    uploaded PDF files — without handing off to a specialist agent.

    The agent loads its behavior instructions from the chatter.md file in the
    instructions directory and can be customized with additional context
    through the extras parameter.
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
        return load_agent_instructions(
            agent_name="aria", extras=extras, include_core=True
        )


def get_agent(
    llm: LLM,
    vl_api_base: str,
    vl_model: str,
    extras: Optional[str] = None,
    can_handoff_to: Optional[List[str]] = None,
) -> ChatterAgent:
    """Factory function to create and return a ChatterAgent instance.

    This function initializes a ChatterAgent with the provided LLM and optional
    extras, setting up a friendly conversational AI assistant for natural
    dialogue and general knowledge questions. The agent also receives a
    ``parse_pdf`` tool bound to the VL server so it can process uploaded PDF
    files directly without a handoff.

    Args:
        llm: The language model to use for generating responses.
        vl_api_base: Base URL of the OpenAI-compatible VL server, e.g.
            ``"http://localhost:9091/v1"``.
        vl_model: Model name to pass in VL requests, e.g.
            ``"granite-docling-258M-Q8_0.gguf"``.
        extras: Optional additional context or instructions to customize the
            agent's behavior.
        can_handoff_to: Optional list of agent names this agent may hand off
            to.

    Returns:
        A configured ChatterAgent instance ready for conversation.
    """

    parse_pdf_fn = make_parse_pdf(api_base=vl_api_base, model=vl_model)

    tools = [
        FunctionTool.from_defaults(fn=get_youtube_video_transcription),
        FunctionTool.from_defaults(fn=get_current_weather),
        FunctionTool.from_defaults(fn=download),
        FunctionTool.from_defaults(fn=read_file),
        FunctionTool.from_defaults(fn=file_info),
        FunctionTool.from_defaults(fn=write_file),
        FunctionTool.from_defaults(fn=edit_file),
        FunctionTool.from_defaults(fn=web_search),
        FunctionTool.from_defaults(fn=shell),
        FunctionTool.from_defaults(fn=reasoning),
        FunctionTool.from_defaults(fn=scratchpad),
        FunctionTool.from_defaults(fn=plan),
        FunctionTool.from_defaults(
            async_fn=parse_pdf_fn,
            name="parse_pdf",
            description=(
                "Extract structured content (text, tables, layout) from a "
                "local PDF file using the vision-language model. Call this "
                "tool whenever the prompt contains an [Uploaded files] block "
                "with a .pdf path. Provide the absolute file path and an "
                "optional extraction prompt. Returns markdown with "
                "--- Page N --- separators."
            ),
        ),
    ]

    if Lightpanda.is_available():
        tools += [
            FunctionTool.from_defaults(async_fn=open_url),
            FunctionTool.from_defaults(async_fn=browser_click),
        ]
        logger.info("Browser tools enabled (Lightpanda available)")

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
        verbose=True,
        can_handoff_to=can_handoff_to,
    )

    return agent
