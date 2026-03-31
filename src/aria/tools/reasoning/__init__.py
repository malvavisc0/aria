"""Structured reasoning tools for AI agents.

The ``reasoning()`` function is the public tool that agents call.
``ReasoningSession`` is the internal implementation class — importable
for direct use in tests or custom integrations, but not exported as
a tool.
"""

from .functions import reasoning

__all__ = [
    "reasoning",
]
