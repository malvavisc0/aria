"""Shell Executor Agent.

This module provides a specialized agent for executing shell commands
safely across Windows, Linux, and macOS platforms with proper security
constraints, timeout handling, and output capture.
"""

import platform
from typing import List, Optional

from llama_index.core.agent import FunctionAgent
from llama_index.core.llms import LLM
from llama_index.core.tools import FunctionTool

from aria.agents.instructions import load_agent_instructions
from aria.tools.shell import (
    execute_command,
    execute_command_batch,
    execute_command_safe,
    get_platform_info,
)


class ShellExecutorAgent(FunctionAgent):
    """A specialized agent for shell command execution.

    This agent extends FunctionAgent to provide safe shell command execution
    capabilities across multiple platforms. It includes proper security
    constraints, timeout handling, and output capture.

    The agent follows strict security practices including:
    - Command whitelisting to prevent shell injection
    - Platform-specific command handling
    - Timeout limits for long-running commands
    - Output size limits to prevent token overflow
    """

    @staticmethod
    def get_system_prompt(extras: str = "") -> str:
        """Return the system prompt for the Shell Executor Agent.

        Args:
            extras: Additional instructions to append to the system
                   prompt. Defaults to empty string.

        Returns:
            The complete system prompt with guidelines and best practices.
        """
        return load_agent_instructions("stallman", extras)


def get_agent(
    llm: LLM,
    extras: Optional[str] = None,
    can_handoff_to: Optional[List[str]] | None = None,
) -> ShellExecutorAgent:
    """Create a shell executor agent with the given LLM.

    Args:
        llm: The language model to be used by the agent
        extras: Additional system prompt instructions.
               Defaults to empty string.

    Returns:
        A configured ShellExecutorAgent instance ready for operations.

    Security Features:
        - Command whitelisting to prevent shell injection
        - Platform-specific command handling
        - Timeout limits for long-running commands
        - Output size limits to prevent token overflow
    """
    shell_hint = (
        "PowerShell/cmd"
        if platform.system() == "Windows"
        else "/bin/bash (likely)"
    )
    platform_context = (
        f"- **Current platform**: "
        f"{platform.system()} {platform.release()}\n"
        f"- **Architecture**: {platform.machine()}\n"
        f"- **Shell**: {shell_hint}"
    )
    full_extras = (
        f"{platform_context}\n{extras}" if extras else platform_context
    )

    tools = [
        FunctionTool.from_defaults(fn=get_platform_info),
        FunctionTool.from_defaults(fn=execute_command),
        FunctionTool.from_defaults(fn=execute_command_safe),
        FunctionTool.from_defaults(fn=execute_command_batch),
    ]

    agent = ShellExecutorAgent(
        name="Stallman",
        description=(
            "Specialized in safe shell command execution across "
            "Windows, Linux, and macOS platforms with proper security "
            "constraints and timeout handling."
        ),
        tools=tools,
        llm=llm,
        system_prompt=ShellExecutorAgent.get_system_prompt(full_extras),
        streaming=True,
        verbose=True,
        can_handoff_to=can_handoff_to,
    )

    return agent
