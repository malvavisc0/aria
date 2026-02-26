"""Shell Executor Agent.

This module provides a specialized agent for executing shell commands
safely across Windows, Linux, and macOS platforms with proper security
constraints, timeout handling, and output capture.
"""

from pathlib import Path
from typing import Optional

from llama_index.core.agent import FunctionAgent
from llama_index.core.llms import LLM
from llama_index.core.tools import FunctionTool

from aria.agents.tool_schema import filter_tools_for_llamacpp
from aria.tools.documentation import tool_help
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
        instructions_dir = Path(__file__).parent / "instructions"
        core_path = instructions_dir / "core_rules.md"
        instructions_path = instructions_dir / "shell_executor.md"

        core = ""
        with open(core_path, mode="r", encoding="utf-8") as file:
            core = file.read()

        instructions = ""
        with open(instructions_path, mode="r", encoding="utf-8") as file:
            instructions = file.read()

        return f"{core}\n\n{instructions}\n\n# Additional Notes\n{extras}"


def get_agent(llm: LLM, extras: Optional[str] = None) -> ShellExecutorAgent:
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
    tools = [
        FunctionTool.from_defaults(fn=get_platform_info),
        FunctionTool.from_defaults(fn=execute_command),
        FunctionTool.from_defaults(fn=execute_command_safe),
        FunctionTool.from_defaults(fn=execute_command_batch),
    ]

    # On-demand tool documentation.
    tools.append(FunctionTool.from_defaults(fn=tool_help))

    tools = filter_tools_for_llamacpp(tools, agent_name="Shell")

    agent = ShellExecutorAgent(
        name="Shell",
        description=(
            "Specialized in safe shell command execution across "
            "Windows, Linux, and macOS platforms with proper security "
            "constraints and timeout handling."
        ),
        tools=tools,
        llm=llm,
        system_prompt=ShellExecutorAgent.get_system_prompt(extras or ""),
        streaming=True,
        verbose=True,
    )

    return agent
