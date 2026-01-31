from __future__ import annotations

from aria.tools.documentation import tool_help


def test_tool_help_returns_section_for_known_tool() -> None:
    out = tool_help(
        "Need correct signature and semantics for chunked file reads",
        "read_file_chunk",
    )

    # Should return the matching markdown section (header + body).
    assert "read_file_chunk" in out
    assert out.lstrip().startswith("###")


def test_tool_help_rejects_empty_function_name() -> None:
    out = tool_help("Need tool docs", "")
    assert "requires a non-empty function_name" in out
    assert "Available tools:" in out


def test_tool_help_returns_helpful_list_for_unknown_tool() -> None:
    out = tool_help("Need tool docs", "definitely_not_a_real_tool")
    assert "No documentation found for tool" in out
    assert "Available tools:" in out


def test_tool_help_blocks_path_tricks() -> None:
    out = tool_help("Attempted path traversal", "../secrets")
    assert out.startswith("Unknown tool:")
    assert "Available tools:" in out
