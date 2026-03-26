"""Structured reasoning tools for AI agents."""

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
]

# ReasoningSession is available for direct import but not in __all__
# This prevents it from being loaded as an agent tool
