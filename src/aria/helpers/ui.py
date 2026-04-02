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
    # Core tools
    "reasoning": "🧠",
    "scratchpad": "🗒️",
    "plan": "📋",
    "knowledge": "💡",
    "web_search": "🔍",
    "download": "⬇️",
    "shell": "🖥️",
    "get_current_weather": "🌦️",
    # File tools
    "read_file": "📜",
    "write_file": "💾",
    "edit_file": "✏️",
    "file_info": "🏷️",
    "list_files": "📂",
    "search_files": "🔭",
    "copy_file": "🗃️",
    "delete_file": "💣",
    "rename_file": "🏷️",
    # Development
    "python": "🐍",
    # Browser
    "open_url": "🌐",
    "browser_click": "🖱️",
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
    # Entertainment
    "get_youtube_video_transcription": "📹",
    # System
    "http_request": "🔗",
    "process": "⚙️",
    # Vision / OCR
    "parse_pdf": "🐾",
    "analyze_image": "🖼️",
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
    Label preference: `reason`, else `reason`, else tool name.
    """

    tool_name = (event.tool_name or "").strip() or "<unknown_tool>"
    tool_kwargs = event.tool_kwargs or {}
    label = tool_kwargs.get("reason", None)
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
    the descriptive reason text.

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
