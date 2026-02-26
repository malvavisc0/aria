"""Vision-Language (Document Intelligence) Agent

This module defines a specialized agent for document understanding tasks
powered by IBM Granite Docling. It handles OCR, layout analysis, table
extraction, and structured parsing of PDFs, scanned images, and forms.
"""

from typing import List, Optional

from llama_index.core.agent import FunctionAgent
from llama_index.core.llms import LLM
from llama_index.core.tools import FunctionTool

from aria.agents.utils import load_agent_instructions
from aria.tools.vision import make_analyze_document


class VLAgent(FunctionAgent):
    """Document intelligence agent backed by a vision-language model.

    Extends :class:`FunctionAgent` to provide structured extraction from
    documents: OCR, layout analysis, table parsing, and form field
    extraction. Uses IBM Granite Docling served via an OpenAI-compatible
    endpoint.
    """

    @staticmethod
    def get_system_prompt(extras: str = "") -> str:
        """Return the system prompt for the VL (Docling) agent.

        Args:
            extras: Additional context or instructions to append to the
                base instructions. Defaults to an empty string.

        Returns:
            The combined system prompt as a string.
        """
        return load_agent_instructions("vl_agent", extras)


def get_agent(
    llm: LLM,
    vl_llm: LLM,
    extras: Optional[str] = None,
    can_handoff_to: Optional[List[str]] = None,
) -> VLAgent:
    """Create a document intelligence agent backed by a VL model.

    Initialises a :class:`VLAgent` configured for document understanding:
    OCR, layout analysis, table extraction, and structured parsing of
    PDFs, scanned images, and forms.

    The ``parse_document_with_ocr`` tool is created as a closure that
    captures *vl_llm* so the tool can call the vision-language model
    directly without exposing the LLM instance as a tool parameter.  The
    agent's own reasoning loop uses *llm* (the general-purpose chat
    model), which is capable of following agent-loop instructions and
    deciding when to stop calling tools.

    Args:
        llm: General-purpose chat LLM used to drive the agent reasoning
            loop (tool selection, stopping, handoffs).
        vl_llm: Vision-language LLM used exclusively inside the
            ``parse_document_with_ocr`` tool closure for document
            extraction. Must be an :class:`OpenAILike` instance pointing
            at the VL server (default port 9091).
        extras: Optional additional context or instructions to append to
            the agent's system prompt.
        can_handoff_to: Optional list of agent names this agent may hand
            off to (e.g. ``["Notepad", "Developer"]``).

    Returns:
        A configured :class:`VLAgent` instance ready for document
        extraction tasks.
    """
    # Build the parse_file_with_ocr tool as a closure over the VL LLM only.
    # The agent's reasoning loop uses the general-purpose chat LLM (llm),
    # not the vision model, so it can correctly decide when to stop.
    analyze_fn = make_analyze_document(vl_llm)  # type: ignore[arg-type]
    tools = [
        FunctionTool.from_defaults(
            async_fn=analyze_fn,
            name="parse_file_with_ocr",
            description=(
                "Extract structured content (text, tables, layout) from a "
                "local PDF file using OCR and the vision-language model. "
                "Supported format: PDF only. "
                "You MUST call this tool for every uploaded PDF file path "
                "— do not attempt to read or describe the file yourself. "
                "Provide the absolute file path and an optional extraction "
                "prompt. Returns markdown."
            ),
        )
    ]

    agent = VLAgent(
        name="Docling",
        description=(
            "Specialized in PDF document understanding: OCR, layout "
            "analysis, table extraction, and structured parsing of PDF "
            "files using IBM Granite Docling. Handles PDF uploads only."
        ),
        tools=tools,
        llm=llm,
        system_prompt=VLAgent.get_system_prompt(extras or ""),
        streaming=False,
        verbose=True,
        can_handoff_to=can_handoff_to,
    )

    return agent
