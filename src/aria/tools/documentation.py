"""On-demand tool documentation.

This module provides `tool_help()` (see
[`src/aria2/tools/documentation.py`](src/aria2/tools/documentation.py:1)),
which allows agents to fetch detailed tool documentation from markdown files in
  [`src/aria2/tools/instructions/`](src/aria2/tools/instructions/files_functions.md:1)
at runtime.

Rationale: keep tool docstrings minimal to reduce prompt/tool-schema tokens,
while retaining rich docs on-demand.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import Iterable, Optional

from loguru import logger

_INSTRUCTIONS_DIR = Path(__file__).parent / "instructions"


def _iter_doc_files() -> Iterable[Path]:
    if not _INSTRUCTIONS_DIR.exists():
        return []
    return sorted(p for p in _INSTRUCTIONS_DIR.glob("*.md") if p.is_file())


def _extract_section(markdown: str, *, tool_name: str) -> Optional[str]:
    """Extract the markdown section describing a tool.

    Matches headings that contain the tool name (case-insensitive), typically:
    - ### `read_file_chunk(reason: ..., ...)`

    Returns the matched heading and its content until the next heading of the
    same or higher level.
    """

    # Match headings like:
    # ### `tool_name(`
    # ##  `tool_name(`
    # ### tool_name
    # We accept backticks optionally because existing docs vary.
    heading_re = re.compile(
        rf"^(?P<level>###+)\s+`?{re.escape(tool_name)}\b.*$",
        flags=re.IGNORECASE,
    )

    lines = markdown.splitlines()
    start_idx: Optional[int] = None
    level_len: Optional[int] = None

    for i, line in enumerate(lines):
        m = heading_re.match(line.strip())
        if m:
            start_idx = i
            level_len = len(m.group("level"))
            break

    if start_idx is None or level_len is None:
        return None

    out: list[str] = [lines[start_idx]]
    next_heading_re = re.compile(r"^(?P<level>###+)\s+.*$")

    for j in range(start_idx + 1, len(lines)):
        m2 = next_heading_re.match(lines[j].strip())
        if m2 and len(m2.group("level")) <= level_len:
            break
        out.append(lines[j])

    return "\n".join(out).strip()


def _available_tool_names() -> list[str]:
    """Return the list of tool names exported for agents."""

    # Import locally to avoid circular imports during package init.
    from aria2.tools import development, files, reasoning, search

    names: set[str] = set()
    names.update(getattr(files, "__all__", []))
    names.update(getattr(search, "__all__", []))
    names.update(getattr(development, "__all__", []))
    names.update(getattr(reasoning, "__all__", []))
    names.add("tool_help")
    return sorted(names)


def tool_help(intent: str, function_name: str) -> str:
    """Return detailed documentation for a tool.

    Exact tool-name lookup only (no fuzzy matching). If the tool is unknown or
    undocumented, returns a message listing known tool names.
    """

    frame = inspect.currentframe()
    if frame:
        func_name = frame.f_code.co_name
        logger.debug(f"Calling {func_name} to achieve: {intent}")

    tool_name = (function_name or "").strip()
    if not tool_name:
        available = ", ".join(_available_tool_names())
        return (
            "tool_help requires a non-empty function_name. "
            f"Available tools: {available}"
        )

    # Prevent path tricks (exact tool name only).
    if "/" in tool_name or "\\\\" in tool_name:
        available = ", ".join(_available_tool_names())
        return f"Unknown tool: {tool_name}. Available tools: {available}"

    for doc_file in _iter_doc_files():
        try:
            content = doc_file.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning(f"Failed reading tool docs file {doc_file}: {exc}")
            continue

        section = _extract_section(content, tool_name=tool_name)
        if section:
            return section

    available = ", ".join(_available_tool_names())
    return (
        f"No documentation found for tool: {tool_name}. "
        f"Available tools: {available}"
    )


__all__ = ["tool_help"]
