"""Unified ax dispatcher tool.

Single-tool interface that routes `ax(family, command, args)` calls
directly to the underlying Python functions — no shell subprocess needed.
"""

from .dispatcher import ax

__all__ = ["ax"]
