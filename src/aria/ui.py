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
    "handoff": "🔄",
    # Reasoning tools
    "start_reasoning": "🤔",
    "add_reasoning_step": "➕",
    "add_reflection": "💭",
    "use_scratchpad": "📝",
    "evaluate_reasoning": "✅",
    "get_reasoning_summary": "📋",
    "reset_reasoning": "🔄",
    "end_reasoning": "🎯",
    "list_reasoning_sessions": "📑",
    # Files
    "file_exists": "📄",
    "get_file_info": "ℹ️",
    "get_file_permissions": "🔒",
    "read_file_chunk": "📖",
    "read_full_file": "📖",
    "write_full_file": "✍️",
    "append_to_file": "➕",
    "insert_lines_at": "🔢",
    "replace_lines_range": "✏️",
    "delete_lines_range": "❌",
    "delete_file": "🗑️",
    "create_directory": "📁",
    "get_directory_tree": "🌲",
    "list_files": "📂",
    "search_files_by_name": "🔍",
    "search_in_files": "🔍",
    "copy_file": "📄",
    "move_file": "🔄",
    "rename_file": "✏️",
    # Web/search
    "web_search": "🌐",
    "get_file_from_url": "🔗",
    "get_youtube_video_transcription": "🎥",
    "get_current_weather": "🌤️",
    # Development
    "execute_python_code": "🐍",
    "execute_python_file": "🐍",
    "check_python_syntax": "🔍",
    "check_python_file_syntax": "🔍",
    # Tool docs
    "tool_help": "❓",
    # Finance
    "fetch_current_stock_price": "📈",
    "fetch_company_information": "🏢",
    "fetch_ticker_news": "📰",
}


async def send_tool_step(event: ToolCall) -> cl.Step:
    """Create + send a tool Step for a ToolCall event."""

    label = _step_label_from_tool_call(event)
    step = _make_tool_step(label)
    await step.send()
    return step


async def maybe_remove_step(step: Optional[cl.Step]) -> None:
    """Remove a Step if present."""

    if step is None:
        return
    await step.remove()
    step = None
    return step


def _step_label_from_tool_call(event: ToolCall) -> str:
    """Best-effort label for a tool call.

    Keeps current behavior: prefer `intent`, else `reason`, else tool name.
    """

    tool_name = (event.tool_name or "").strip() or "<unknown_tool>"
    tool_kwargs = event.tool_kwargs or {}
    label = tool_kwargs.get("intent", None)
    if not label:
        label = tool_kwargs.get("reason", None)

    prefix = TOOL_EMOJI.get(tool_name, ":-|")

    # Keep the existing preference order for human labels, but always include
    # the tool name for clarity when `intent`/`reason` is used.
    if isinstance(label, str) and label.strip():
        if label.strip() == tool_name:
            return f"{prefix} {tool_name}"
        return f"{prefix} {tool_name}: {label.strip()}"

    return f"{prefix} {tool_name}"


def _make_tool_step(label: str) -> cl.Step:
    """Create a tool Step with the current UI preferences.

    Keeps current behavior: `show_input=False`, `default_open=False`.
    """

    return cl.Step(
        name=label, type="tool", show_input=False, default_open=False
    )
