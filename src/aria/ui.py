"""UI-related constants/helpers for displaying tool activity."""

from typing import Dict

from chainlit import Message as ChainlitMessage
from llama_index.core.agent.workflow import ToolCall

# Emoji prefix for tool-call notifications in the UI.
# Keep this minimal (token + visual noise), but explicit for common tools.

TOOL_EMOJI: Dict[str, str] = {
    # Workflow
    "handoff": "🤝",
    # Reasoning tools
    "start_reasoning": "🧠",
    "add_reasoning_step": "🧩",
    "add_reflection": "🔎",
    "use_scratchpad": "🗒️",
    "evaluate_reasoning": "✅",
    "get_reasoning_summary": "🧾",
    "reset_reasoning": "🔄",
    "end_reasoning": "🏁",
    "list_reasoning_sessions": "📚",
    # Files
    "file_exists": "✅",
    "get_file_info": "ℹ️",
    "get_file_permissions": "🔐",
    "read_file_chunk": "📄",
    "read_full_file": "📄",
    "write_full_file": "📝",
    "append_to_file": "➕",
    "insert_lines_at": "➕",
    "replace_lines_range": "✏️",
    "delete_lines_range": "🗑️",
    "delete_file": "🗑️",
    "create_directory": "📁",
    "get_directory_tree": "🌳",
    "list_files": "🗂️",
    "search_files_by_name": "🔎",
    "search_in_files": "🔍",
    "copy_file": "📋",
    "move_file": "📦",
    "rename_file": "✏️",
    # Web/search
    "web_search": "🌐",
    "get_file_from_url": "⬇️",
    "get_youtube_video_transcription": "🎞️",
    "get_current_weather": "🌦️",
    # Development
    "execute_python_code": "🐍",
    "execute_python_file": "🐍",
    "check_python_syntax": "✅",
    "check_python_file_syntax": "✅",
    # Tool docs
    "tool_help": "❓",
    # Finance
    "fetch_current_stock_price": "💹",
    "fetch_company_information": "🏢",
    "fetch_ticker_news": "📰",
}


async def display_ui_feedback(event: ToolCall, message: ChainlitMessage):
    """
    Logs a tool call event to the debug log and streams the tool call
    information to the user message.

    Args:
        event (ToolCall): The tool call event containing details about the tool
            being called and its parameters.
        message (cl.Message): The Chainlit message object to which the tool
            call information will be streamed.

    Returns:
        None: This function does not return any value. It logs the event and
            streams information to the message.
    """
    tool_name = (event.tool_name or "").strip() or "<unknown_tool>"
    emoji = TOOL_EMOJI.get(tool_name, "❔")
    tool_kwargs = event.tool_kwargs or {}
    label = tool_kwargs.get("intent", None)
    if not label:
        label = tool_kwargs.get("reason", None)
    if isinstance(label, str) and label.strip():
        line = f"{emoji} {label.strip().capitalize()}"
    else:
        line = f"{emoji} [{tool_name}]"

    # Avoid Markdown blockquote (`>`) because it can unintentionally capture
    # subsequent streamed tokens until a blank line is emitted.
    await message.stream_token(f"\n- *{line}*\n\n")
