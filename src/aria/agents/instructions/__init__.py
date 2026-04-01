"""Utility functions for agents instructions.

This module provides shared utility functions used across multiple agents
to reduce code duplication and ensure consistent behavior.
"""

from pathlib import Path
from typing import Dict, Optional


def load_agent_instructions(
    agent_name: str,
    extras: Optional[str] = None,
    variables: Optional[Dict[str, str]] = None,
) -> str:
    """Load agent instructions from a markdown file.

    This function loads the system prompt for an agent from its
    instruction file, optionally appending extra context and performing
    template variable substitution.

    Args:
        agent_name: The name of the agent, used to find the instruction file
            (e.g., "aria", "prompt_enhancer").
        extras: Additional instructions to append to the prompt.
            Defaults to empty string.
        variables: Optional mapping used for ``{{KEY}}`` template
            substitution in loaded instruction content.
            Defaults to None.

    Returns:
        The system prompt as a string.

    Example:
        >>> prompt = load_agent_instructions("aria", "Focus on brevity")
        >>> prompt = load_agent_instructions("prompt_enhancer")
    """
    instructions_dir = Path(__file__).parent
    parts = []

    instructions_path = instructions_dir / f"{agent_name}.md"
    if instructions_path.exists():
        with open(instructions_path, mode="r", encoding="utf-8") as file:
            parts.append(file.read())

    if extras:
        parts.append(f"# Environment\n{extras}")

    content = "\n\n".join(parts)

    if variables:
        for key, value in variables.items():
            content = content.replace(f"{{{{{key}}}}}", value)

    return content
