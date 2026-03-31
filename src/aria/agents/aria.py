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
from aria.tools.files import file_exists, read_file_chunk, read_full_file
from aria.tools.planner import (
    add_plan_step,
    create_execution_plan,
    get_execution_plan,
    remove_plan_step,
    reorder_plan_steps,
    replace_plan_step,
    update_plan_step,
)
from aria.tools.reasoning import (
    add_reasoning_step,
    add_reflection,
    end_reasoning,
    evaluate_reasoning,
    get_reasoning_summary,
    list_reasoning_sessions,
    reset_reasoning,
    start_reasoning,
    use_scratchpad,
)
from aria.tools.search import (
    duckduckgo_web_search,
    get_current_weather,
    get_youtube_video_transcription,
    grab_from_url,
)
from aria.tools.shell import (
    execute_command,
    execute_command_batch,
    get_platform_info,
)
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
        FunctionTool.from_defaults(fn=grab_from_url),
        FunctionTool.from_defaults(fn=read_full_file),
        FunctionTool.from_defaults(fn=read_file_chunk),
        FunctionTool.from_defaults(fn=file_exists),
        FunctionTool.from_defaults(fn=duckduckgo_web_search),
        FunctionTool.from_defaults(fn=get_platform_info),
        FunctionTool.from_defaults(fn=execute_command),
        FunctionTool.from_defaults(fn=execute_command_batch),
        FunctionTool.from_defaults(fn=start_reasoning),
        FunctionTool.from_defaults(fn=end_reasoning),
        FunctionTool.from_defaults(fn=add_reasoning_step),
        FunctionTool.from_defaults(fn=add_reflection),
        FunctionTool.from_defaults(fn=evaluate_reasoning),
        FunctionTool.from_defaults(fn=get_reasoning_summary),
        FunctionTool.from_defaults(fn=use_scratchpad),
        FunctionTool.from_defaults(fn=reset_reasoning),
        FunctionTool.from_defaults(fn=list_reasoning_sessions),
        FunctionTool.from_defaults(fn=add_plan_step),
        FunctionTool.from_defaults(fn=create_execution_plan),
        FunctionTool.from_defaults(fn=get_execution_plan),
        FunctionTool.from_defaults(fn=remove_plan_step),
        FunctionTool.from_defaults(fn=reorder_plan_steps),
        FunctionTool.from_defaults(fn=replace_plan_step),
        FunctionTool.from_defaults(fn=update_plan_step),
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
