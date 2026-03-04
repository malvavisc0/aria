"""Utility functions for agents instructions.

This module provides shared utility functions used across multiple agents
to reduce code duplication and ensure consistent behavior.
"""

from pathlib import Path


def load_agent_instructions(
    agent_name: str,
    extras: str = "",
    include_core: bool = True,
    variables: dict[str, str] | None = None,
) -> str:
    """Load agent instructions from markdown files.

    This function loads the system prompt for an agent by combining
    the core rules (optional) with agent-specific instructions.

    Args:
        agent_name: The name of the agent, used to find the instruction file
            (e.g., "chatter", "python_developer", "prompt_enhancer").
        extras: Additional instructions to append to the prompt.
            Defaults to empty string.
        include_core: Whether to include the core_rules.md file.
            Defaults to True.
        variables: Optional mapping used for ``{{KEY}}`` template
            substitution in loaded instruction content.
            Defaults to None.

    Returns:
        The combined system prompt as a string.

    Example:
        >>> prompt = load_agent_instructions("chatter", "Focus on brevity")
        >>> prompt = load_agent_instructions(
        ...     "prompt_enhancer", include_core=False
        ... )
    """
    instructions_dir = Path(__file__).parent / "instructions"
    parts = []

    if include_core:
        core_path = instructions_dir / "core_rules.md"
        if core_path.exists():
            with open(core_path, mode="r", encoding="utf-8") as file:
                parts.append(file.read())

    instructions_path = instructions_dir / f"{agent_name}.md"
    if instructions_path.exists():
        with open(instructions_path, mode="r", encoding="utf-8") as file:
            parts.append(file.read())

    if extras:
        parts.append(f"# Additional Notes\n{extras}")

    content = "\n\n".join(parts)

    if variables:
        for key, value in variables.items():
            content = content.replace(f"{{{{{key}}}}}", value)

    return content
