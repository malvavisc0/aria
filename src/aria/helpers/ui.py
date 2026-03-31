"""UI-related constants/helpers for displaying tool activity."""

from __future__ import annotations

from typing import Dict, Optional

import chainlit as cl
from llama_index.core.agent.workflow import ToolCall

# Prefix for tool-call notifications in the UI.
#
# Preference: text faces / emoticons ("looks.wtf" style) instead of emoji.
# This reduces font/width issues while keeping the UI playful.

TOOL_EMOJI: Dict[str, str] = {
    # Workflow
    "handoff": "🤝",
    # Reasoning tools
    "start_reasoning": "🧠",
    "add_reasoning_step": "🪜",
    "add_reflection": "🪞",
    "use_scratchpad": "🗒️",
    "evaluate_reasoning": "⚖️",
    "get_reasoning_summary": "📊",
    "reset_reasoning": "🔁",
    "end_reasoning": "🏁",
    "list_reasoning_sessions": "🗂️",
    # Files
    "file_exists": "🔎",
    "get_file_info": "🏷️",
    "get_file_permissions": "🛡️",
    "read_file_chunk": "📰",
    "read_full_file": "📜",
    "write_full_file": "💾",
    "append_to_file": "✏️",
    "insert_lines_at": "📌",
    "replace_lines_range": "🔀",
    "delete_lines_range": "🗑️",
    "delete_file": "💣",
    "create_directory": "🗄️",
    "get_directory_tree": "🌳",
    "list_files": "📋",
    "search_files_by_name": "🔭",
    "search_in_files": "🕵️",
    "copy_file": "🗃️",
    "move_file": "🚚",
    "rename_file": "🏷️",
    # Web/search
    "duckduckgo_web_search": "🔍",
    "grab_from_url": "⬇️",
    "get_youtube_video_transcription": "📹",
    "get_current_weather": "🌦️",
    # Development
    "execute_python_code": "⚡",
    "execute_python_file": "🐍",
    "check_python_syntax": "🧪",
    "check_python_file_syntax": "🔬",
    "get_restricted_builtins": "🚧",
    "get_timeout_limits": "⏳",
    # Shell
    "execute_command": "🖥️",
    "execute_command_batch": "⚙️",
    "get_platform_info": "💡",
    # Vision / OCR
    "parse_pdf": "🐾",
    # Tool docs
    "tool_help": "❓",
    # Finance
    "fetch_current_stock_price": "💹",
    "fetch_company_information": "🏦",
    "fetch_ticker_news": "📡",
    # IMDB
    "search_imdb_titles": "🎬",
    "get_movie_details": "🎞️",
    "get_person_details": "🎭",
    "get_person_filmography": "🏆",
    "get_all_series_episodes": "📺",
    "get_movie_reviews": "🌟",
    "get_movie_trivia": "🎪",
}


async def send_tool_step(event: ToolCall) -> cl.Step:
    """Create + send a tool Step for a ToolCall event."""

    label = _step_label_from_tool_call(event)
    tool_name = (event.tool_name or "").strip() or "tool"
    step = _make_tool_step(label, tool_name)
    await step.send()
    return step


async def maybe_remove_step(step: Optional[cl.Step]) -> None:
    """Remove a Step if present."""
    if step is None:
        return
    await step.remove()


def _step_label_from_tool_call(event: ToolCall) -> str:
    """Best-effort label for a tool call.

    Prepends the tool emoji (from TOOL_EMOJI) when available.
    Label preference: `intent`, else `reason`, else tool name.
    """

    tool_name = (event.tool_name or "").strip() or "<unknown_tool>"
    tool_kwargs = event.tool_kwargs or {}
    label = tool_kwargs.get("intent", None)
    if not label:
        label = tool_kwargs.get("reason", None)

    if isinstance(label, str):
        label = label.strip()
    else:
        label = tool_name

    emoji = TOOL_EMOJI.get(tool_name, "")
    prefix = f"{emoji} " if emoji else ""
    return f"{prefix}{label}"


def _make_tool_step(label: str, tool_name: str = "tool") -> cl.Step:
    """Create a tool Step with the current UI preferences.

    Uses a sanitized name for the step to ensure compatibility with
    Chainlit's avatar system (which requires names matching the pattern
    ^[a-zA-Z0-9_ .-]+$ - emojis are not allowed).

    The step name is used for both display and avatar lookup. We strip
    emojis from the label to make it avatar-compatible while preserving
    the descriptive intent text.

    Args:
        label: The display label with emoji (e.g., "📰 Reading file...")
        tool_name: The tool name for fallback (e.g., "read_file")

    Returns:
        A configured cl.Step instance
    """
    import re

    # Strip emojis and other non-ASCII characters for avatar compatibility
    # Chainlit's avatar endpoint requires: ^[a-zA-Z0-9_ .-]+$
    # Keep ASCII letters, numbers, spaces, underscores, dots, and hyphens
    safe_label = re.sub(r"[^\x00-\x7F]+", "", label).strip()

    # If stripping leaves nothing, fall back to tool name
    if not safe_label:
        safe_label = tool_name.replace("-", "_")

    return cl.Step(
        name=safe_label,
        type="tool",
        show_input=False,
        default_open=False,
    )
