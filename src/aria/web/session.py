"""Session management for the Aria web UI.

This module provides functions for:
- Creating and managing conversation memory per thread
- Waiting for application initialization
- Extracting file paths from uploaded files
- Restoring chat history when resuming a session

These utilities support the Chainlit chat interface by managing
persistent conversation state across messages and sessions.
"""

from __future__ import annotations

import base64
import shutil
import uuid
from pathlib import Path

import chainlit as cl
from chainlit.types import ThreadDict
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.memory import Memory
from loguru import logger

from aria.config.folders import Uploads as UploadsConfig
from aria.config.folders import Workspace as WorkspaceConfig
from aria.config.models import Embeddings as EmbeddingsConfig
from aria.llm import get_default_memory
from aria.web.state import ROOT_MESSAGE_TYPES, _state

# Image MIME types and extensions for detection
_IMAGE_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
    "image/bmp",
    "image/tiff",
}
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff"}


def create_memory(thread_id: str) -> Memory:
    """Create a new conversation memory instance for a thread.

    Initializes memory with vector database and embeddings model
    for storing conversation history.

    Args:
        thread_id: Unique identifier for the conversation thread.

    Returns:
        Memory: Configured memory instance for the thread.

    Raises:
        ValueError: If thread_id is None or empty.
    """
    if not thread_id:
        raise ValueError("thread_id cannot be None or empty")

    return get_default_memory(
        vector_db=_state.vector_db,
        thread_id=thread_id,
        embed_model=_state.embeddings,
        token_limit=EmbeddingsConfig.token_limit,
        llm=_state.llm,
    )


async def wait_for_initialization(timeout: float = 30.0) -> bool:
    """Wait for the application state to be fully initialized.

    Args:
        timeout: Maximum time to wait in seconds (default: 30.0).

    Returns:
        bool: True if initialization completed, False if timeout reached.
    """
    import asyncio

    try:
        await asyncio.wait_for(_state.startup_event.wait(), timeout=timeout)
        return True
    except asyncio.TimeoutError:
        return False


def extract_image_data(message: cl.Message) -> list[dict]:
    """Extract base64-encoded image data from uploaded file elements.

    Returns a list of dicts with keys:
        - mime_type: str (e.g. "image/jpeg")
        - base64: str (base64-encoded image data)
        - name: str (original filename)
    """
    if not message.elements:
        return []

    images = []
    for element in message.elements:
        path = getattr(element, "path", None)
        if not path:
            continue

        # Detect by MIME type or extension
        mime = getattr(element, "mime", "") or ""
        name = getattr(element, "name", "") or ""
        ext = Path(name).suffix.lower() if name else Path(str(path)).suffix.lower()

        is_image = (mime in _IMAGE_MIME_TYPES) or (ext in _IMAGE_EXTENSIONS)
        if not is_image:
            continue

        try:
            with open(path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
            images.append(
                {
                    "mime_type": mime or f"image/{ext.lstrip('.')}",
                    "base64": data,
                    "name": name,
                }
            )
        except OSError as e:
            logger.warning(f"Failed to read image {path}: {e}")

    return images


def extract_file_paths(message: cl.Message) -> list[str]:
    """Extract file paths from uploaded file elements in a message.

    Skips image files — those are handled separately by extract_image_data().
    """
    if not message.elements:
        return []

    UploadsConfig.path.mkdir(parents=True, exist_ok=True)

    paths = []
    for element in message.elements:
        path = getattr(element, "path", None)
        if not path:
            continue

        # Skip image files — handled by extract_image_data()
        mime = getattr(element, "mime", "") or ""
        name = getattr(element, "name", "") or ""
        ext = Path(name).suffix.lower() if name else Path(str(path)).suffix.lower()
        if (mime in _IMAGE_MIME_TYPES) or (ext in _IMAGE_EXTENSIONS):
            continue

        path_str = str(path)
        src = Path(path_str)
        name = getattr(element, "name", None)
        dest_name = name or src.name
        thread_id = getattr(message, "thread_id", None) or "thread"
        dest = UploadsConfig.path / (
            f"{thread_id}_{uuid.uuid4().hex}_{Path(dest_name).name}"
        )

        try:
            shutil.copy2(path_str, dest)
            path_str = str(dest)
        except OSError:
            logger.warning(f"Failed to copy uploaded file {path_str} to {dest}")

        paths.append(path_str)
    return paths


# MIME types / extensions supported by MarkItDown for document conversion
_MARKITDOWN_MIME_TYPES = {
    # Documents
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    # Structured data & markup
    "text/csv",
    "text/html",
    "application/json",
    "application/xml",
    "text/xml",
    "application/x-yaml",
    "text/yaml",
    "text/x-yaml",
    "application/toml",
    # Plain text & code
    "text/plain",
    "text/markdown",
    "text/x-python",
    "text/x-script",
}
_MARKITDOWN_EXTENSIONS = {
    # Documents
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    # Structured data & markup
    ".csv",
    ".html",
    ".htm",
    ".json",
    ".xml",
    ".yaml",
    ".yml",
    ".toml",
    # Plain text & code
    ".txt",
    ".md",
    ".rst",
    ".py",
    ".js",
    ".ts",
    ".sh",
    ".log",
    ".ini",
    ".cfg",
}


def convert_documents_to_markdown(
    file_paths: list[str],
) -> list[dict]:
    """Convert uploaded documents to markdown using MarkItDown.

    For each file path, attempts conversion via MarkItDown and saves
    the resulting markdown file into the agent workspace
    (``~/.aria/workspace/uploads/``).

    Args:
        file_paths: List of uploaded file paths to convert.

    Returns:
        A list of dicts with keys:
            - original_path: str (path to the uploaded file)
            - markdown_path: str | None (path to converted .md, or None on failure)
            - name: str (original filename)
            - lines: int (line count of converted file)
            - chars: int (character count of converted file)
            - error: str | None (error message if conversion failed)
    """
    if not file_paths:
        return []

    workspace_uploads = WorkspaceConfig.path / "uploads"
    workspace_uploads.mkdir(parents=True, exist_ok=True)

    results = []
    for file_path in file_paths:
        src = Path(file_path)
        ext = src.suffix.lower()

        # Check if file is convertible
        if ext not in _MARKITDOWN_EXTENSIONS:
            results.append(
                {
                    "original_path": file_path,
                    "markdown_path": None,
                    "name": src.name,
                    "lines": 0,
                    "chars": 0,
                    "error": None,
                }
            )
            continue

        try:
            from markitdown import MarkItDown

            result = MarkItDown().convert(file_path)
            md_content = result.text_content or ""

            md_name = f"{src.stem}.md"
            md_dest = workspace_uploads / md_name
            # Avoid collisions
            if md_dest.exists():
                md_dest = workspace_uploads / f"{src.stem}_{uuid.uuid4().hex[:8]}.md"

            md_dest.write_text(md_content, encoding="utf-8")

            results.append(
                {
                    "original_path": file_path,
                    "markdown_path": str(md_dest),
                    "name": src.name,
                    "lines": md_content.count("\n") + 1,
                    "chars": len(md_content),
                    "error": None,
                }
            )
            logger.debug(
                f"Converted {src.name} to markdown: {md_dest} "
                f"({md_content.count(chr(10)) + 1} lines, {len(md_content)} chars)"
            )
        except Exception as e:
            logger.warning(f"MarkItDown conversion failed for {src.name}: {e}")
            results.append(
                {
                    "original_path": file_path,
                    "markdown_path": None,
                    "name": src.name,
                    "lines": 0,
                    "chars": 0,
                    "error": str(e),
                }
            )

    return results


def _sanitize_chat_history(
    chat_history: list[ChatMessage],
) -> list[ChatMessage]:
    """Ensure chat history has strictly alternating user/assistant roles.

    The OpenAI-compatible API requires that after the optional system
    message, conversation roles must strictly alternate between user and
    assistant.  This helper enforces that invariant by:

    1. Collapsing consecutive messages of the same role into one
       (keeping the *last* message of each run).
    2. Dropping any leading assistant messages (conversation must start
       with a user message after the system prompt).
    3. Dropping any trailing user messages (so the next user turn
       maintains alternation).

    Args:
        chat_history: Raw chat messages (may have consecutive duplicates).

    Returns:
        A sanitised list with strictly alternating ``user → assistant``
        roles.
    """
    if not chat_history:
        return chat_history

    # Step 1: Collapse consecutive duplicate roles (keep last of each run).
    deduplicated: list[ChatMessage] = []
    for msg in chat_history:
        if deduplicated and deduplicated[-1].role == msg.role:
            deduplicated[-1] = msg  # replace — keep latest
        else:
            deduplicated.append(msg)

    # Step 2: Ensure it starts with a user message.
    while deduplicated and deduplicated[0].role != MessageRole.USER:
        deduplicated.pop(0)

    # Step 3: Ensure it ends with an assistant message so the next user
    # turn maintains alternation.
    while deduplicated and deduplicated[-1].role != MessageRole.ASSISTANT:
        deduplicated.pop()

    return deduplicated


async def restore_chat_history(thread: ThreadDict) -> Memory:
    """Restore conversation history from a thread dictionary.

    Creates memory for the thread and populates it with messages
    from the thread's history.

    Steps are collected regardless of their ``parentId`` because
    ``get_thread()`` returns the raw parent-child structure where
    assistant messages are children of user messages (not root-level).
    The history is then sanitised to guarantee strictly alternating
    ``user → assistant`` roles required by the LLM API.

    Args:
        thread: Thread dictionary containing conversation steps.

    Returns:
        Memory: Memory instance populated with conversation history.

    Raises:
        ValueError: If thread does not contain a valid 'id' field.
    """
    thread_id = thread.get("id")
    if not thread_id:
        raise ValueError("Thread dictionary must contain a valid 'id' field")

    thread_name = thread.get("name", "Unnamed")
    logger.debug(f"Restoring chat history for thread {thread_id} ({thread_name})")

    chat_steps = thread.get("steps", [])
    logger.debug(f"Thread contains {len(chat_steps)} total steps")

    # Include ALL user/assistant messages regardless of parentId.
    # get_thread() returns the raw tree where assistant messages are
    # children of user messages (parentId != None), so filtering on
    # parentId == None would silently drop every assistant reply.
    conversation_steps = [m for m in chat_steps if m.get("type") in ROOT_MESSAGE_TYPES]
    conversation_steps.sort(
        key=lambda message_step: (
            message_step.get("createdAt") or message_step.get("created_at") or "",
            message_step.get("id") or "",
        )
    )
    logger.debug(f"Found {len(conversation_steps)} conversation messages")

    memory = create_memory(thread_id)

    raw_history: list[ChatMessage] = []
    for message_step in conversation_steps:
        content = message_step.get("output", "")
        message_type = message_step.get("type")

        if not content:
            continue

        role = (
            MessageRole.USER
            if message_type == "user_message"
            else MessageRole.ASSISTANT
        )
        raw_history.append(ChatMessage(role=role, content=content))

    chat_history = _sanitize_chat_history(raw_history)
    if len(raw_history) != len(chat_history):
        logger.debug(
            f"Sanitised chat history: {len(raw_history)} → {len(chat_history)} "
            f"messages (removed non-alternating roles)"
        )

    # Use aput_messages instead of aset to enforce token_limit.
    # aset() bypasses _manage_queue() and dumps ALL messages unbounded.
    # aput_messages() triggers the waterfall logic: when the buffer
    # exceeds token_limit * chat_history_token_ratio, oldest messages
    # are flushed to memory blocks (FactExtraction, Vector).
    if chat_history:
        await memory.aput_messages(chat_history)

    logger.info(f"Restored {len(chat_history)} messages for thread {thread_id}")
    return memory
