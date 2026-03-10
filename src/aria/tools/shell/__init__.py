"""Shell execution tools.

This module provides tools for executing shell commands safely across
Windows, Linux, and macOS platforms with proper security constraints,
timeout handling, and output capture.
"""

from aria.tools.shell.functions import (
    execute_command,
    execute_command_batch,
    execute_command_safe,
    get_platform_info,
)

__all__ = [
    "execute_command",
    "execute_command_batch",
    "execute_command_safe",
    "get_platform_info",
]
