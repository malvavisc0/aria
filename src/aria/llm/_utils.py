"""Miscellaneous utility helpers for agent identity and instruction context."""

import platform
import shutil
import uuid
from datetime import datetime
from pathlib import Path


def generate_agent_id(agent_name: str) -> str:
    """Generate a unique, human-readable identifier for an agent.

    The generated ID is deterministic in shape but random in value:

    ``{agent_name}_{8-hex-chars}``

    Args:
        agent_name: Prefix identifying the agent.

    Returns:
        A unique agent ID string.
        Example: ``"aria_1a2b3c4d"``.
    """
    return f"{agent_name}_{uuid.uuid4().hex[:8]}"


def get_instructions_extras(agent_name: str, add_agent_id: bool = True) -> str:
    """
    Generates a formatted string containing additional information for
    instructions.

    This combines the current date and time with a unique agent ID (if
    requested) to provide context.
    It includes the following information in the output:
    - Current date (formatted as 'Month Day<suffix> Year',
      e.g. 'January 15th 2026')
    - Current time (formatted as 'HH:MM')
    - The system's timezone
    - Host operating system name and version
    - A unique ID generated for the agent (if add_agent_id is True)

    Args:
        agent_name (str): The name of the agent, used for generating a unique
            agent ID.
        add_agent_id (bool): Whether to include the unique agent ID in the
            output string. Defaults to True.

    Returns:
        str: A formatted string containing the current date, time, timezone,
            host information, and optionally agent ID.
    """

    def _ordinal_suffix(day: int) -> str:
        # 11th, 12th, 13th are special-cased.
        if 11 <= (day % 100) <= 13:
            return "th"
        return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

    timestamp = datetime.now()
    host = f"{platform.system()} {platform.release()}"

    day = timestamp.day
    date_str = (
        f"{timestamp.strftime('%B')} {day}{_ordinal_suffix(day)} {timestamp.year}"
    )

    tz = timestamp.astimezone().tzinfo

    shell_path = shutil.which("bash") or shutil.which("zsh") or "unknown"
    shell_name = Path(shell_path).name if shell_path != "unknown" else "unknown"

    lines: list[str] = [
        f"- **Date**: {date_str} {timestamp.strftime('%H:%M')} ({tz})",
        f"- **System OS**: {host}",
        f"- **Shell**: {shell_name}",
    ]
    if add_agent_id:
        lines.append(f"- **Agent ID**: {generate_agent_id(agent_name)}")

    # Inject available CLI extras from the virtual environment
    try:
        from aria.cli.extras import get_venv_extras

        extras_md = get_venv_extras()
        if extras_md and "No virtual environment" not in extras_md:
            lines.append("")
            lines.append(extras_md)
    except Exception:
        pass  # Never fail instructions generation over extras

    return "\n".join(lines)
