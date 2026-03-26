"""Structured reasoning tools for AI agents."""

from functools import partial
from typing import List

from llama_index.core.tools import FunctionTool

from .functions import (
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

_REASONING_FUNCTIONS = {
    "start_reasoning": start_reasoning,
    "end_reasoning": end_reasoning,
    "add_reasoning_step": add_reasoning_step,
    "add_reflection": add_reflection,
    "evaluate_reasoning": evaluate_reasoning,
    "get_reasoning_summary": get_reasoning_summary,
    "use_scratchpad": use_scratchpad,
    "reset_reasoning": reset_reasoning,
    "list_reasoning_sessions": list_reasoning_sessions,
}


def make_reasoning_tools(agent_id: str) -> List[FunctionTool]:
    """Build reasoning FunctionTools with ``agent_id`` pre-filled.

    This lets every agent register reasoning tools without the LLM
    needing to know or supply the ``agent_id`` parameter.

    Args:
        agent_id: The agent name to bind (e.g. ``"Aria"``, ``"Guido"``).

    Returns:
        A list of :class:`FunctionTool` instances ready for registration.
    """
    return [
        FunctionTool.from_defaults(
            fn=partial(fn, agent_id=agent_id), name=name
        )
        for name, fn in _REASONING_FUNCTIONS.items()
    ]


__all__ = [
    "start_reasoning",
    "end_reasoning",
    "add_reasoning_step",
    "add_reflection",
    "use_scratchpad",
    "evaluate_reasoning",
    "get_reasoning_summary",
    "reset_reasoning",
    "list_reasoning_sessions",
    "make_reasoning_tools",
]

# ReasoningSession is available for direct import but not in __all__
# This prevents it from being loaded as an agent tool
