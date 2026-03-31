"""Chatter agent module.

This module provides the unified Aria agent — a single conversational agent
that handles all tasks directly using the full tool registry.
"""

from typing import Optional

from llama_index.core.agent import FunctionAgent
from llama_index.core.llms import LLM
from llama_index.core.tools import FunctionTool
from loguru import logger

from aria.agents.instructions import load_agent_instructions
from aria.tools.registry import get_tools
from aria.tools.vision.functions import make_parse_pdf


class ChatterAgent(FunctionAgent):
    """
    The unified Aria agent.

    Handles natural dialogue, general knowledge, web research, code
    execution, financial analysis, entertainment queries, and more — all
    through a single set of tools loaded from the centralized registry.
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
    vl_api_base: str,
    vl_model: str,
    extras: Optional[str] = None,
) -> ChatterAgent:
    """Factory function to create and return a ChatterAgent instance.

    Loads all tools from the centralized registry and appends the
    ``parse_pdf`` tool (which requires VL server binding and cannot live
    in the registry).

    Args:
        llm: The language model to use for generating responses.
        vl_api_base: Base URL of the OpenAI-compatible VL server, e.g.
            ``"http://localhost:9091/v1"``.
        vl_model: Model name to pass in VL requests, e.g.
            ``"granite-docling-258M-Q8_0.gguf"``.
        extras: Optional additional context or instructions to customize the
            agent's behavior.

    Returns:
        A configured ChatterAgent instance ready for conversation.
    """

    parse_pdf_fn = make_parse_pdf(api_base=vl_api_base, model=vl_model)

    tools = get_tools(None)  # Load all categories from registry

    # parse_pdf needs VL server binding — can't be in the registry
    tools.append(
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
        )
    )

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
    )

    return agent
