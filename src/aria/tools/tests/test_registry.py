"""Tests for tool registry."""

from aria.tools.registry import (
    ALL_CATEGORIES,
    CORE,
    DEVELOPMENT,
    ENTERTAINMENT,
    FILES,
    FINANCE,
    SYSTEM,
    WEB,
    get_core_tools,
    get_domain_tools,
    get_file_tools,
    get_tools,
)


class TestToolRegistry:
    """Test suite for tool registry."""

    def test_get_core_tools_returns_tools(self):
        """Test that core tools are loaded."""
        tools = get_core_tools()
        assert len(tools) >= 7
        tool_names = {t.metadata.name for t in tools}
        assert "reasoning" in tool_names
        assert "knowledge" in tool_names
        assert "web_search" in tool_names
        assert "download" in tool_names
        assert "shell" in tool_names
        assert "get_current_weather" in tool_names

    def test_get_file_tools_returns_tools(self):
        """Test that file tools are loaded."""
        tools = get_file_tools()
        assert len(tools) >= 5
        tool_names = {t.metadata.name for t in tools}
        assert "read_file" in tool_names
        assert "write_file" in tool_names
        assert "edit_file" in tool_names

    def test_get_tools_all_categories(self):
        """Test loading all categories."""
        tools = get_tools(None)
        assert len(tools) >= 10
        # Should include core + files at minimum
        tool_names = {t.metadata.name for t in tools}
        assert "reasoning" in tool_names
        assert "read_file" in tool_names

    def test_get_tools_specific_categories(self):
        """Test loading specific categories."""
        tools = get_tools([CORE])
        tool_names = {t.metadata.name for t in tools}
        assert "reasoning" in tool_names
        # File tools should NOT be in core-only
        assert "write_file" not in tool_names
        assert "read_file" not in tool_names

    def test_no_duplicate_tools_across_categories(self):
        """Test that loading multiple categories doesn't produce duplicates."""
        tools = get_tools([CORE, FILES])
        tool_names = [t.metadata.name for t in tools]
        assert len(tool_names) == len(set(tool_names)), (
            f"Duplicate tools found: "
            f"{[n for n in tool_names if tool_names.count(n) > 1]}"
        )

    def test_get_tools_unknown_category(self):
        """Test that unknown categories are skipped gracefully."""
        tools = get_tools(["nonexistent_category"])
        assert len(tools) == 0

    def test_get_domain_tools_development(self):
        """Test loading development domain tools."""
        tools = get_domain_tools(DEVELOPMENT)
        tool_names = {t.metadata.name for t in tools}
        assert "python" in tool_names

    def test_get_domain_tools_finance(self):
        """Test loading finance domain tools."""
        tools = get_domain_tools(FINANCE)
        tool_names = {t.metadata.name for t in tools}
        assert "fetch_current_stock_price" in tool_names

    def test_get_domain_tools_system(self):
        """Test loading system domain tools."""
        tools = get_domain_tools(SYSTEM)
        tool_names = {t.metadata.name for t in tools}
        assert "http_request" in tool_names
        assert "process" in tool_names

    def test_get_domain_tools_entertainment(self):
        """Test loading entertainment domain tools."""
        tools = get_domain_tools(ENTERTAINMENT)
        tool_names = {t.metadata.name for t in tools}
        # All 7 IMDb tools
        assert "search_imdb_titles" in tool_names
        assert "get_movie_details" in tool_names
        assert "get_person_details" in tool_names
        assert "get_person_filmography" in tool_names
        assert "get_all_series_episodes" in tool_names
        assert "get_movie_reviews" in tool_names
        assert "get_movie_trivia" in tool_names
        # YouTube transcription
        assert "get_youtube_video_transcription" in tool_names

    def test_all_categories_defined(self):
        """Test that all expected categories are defined."""
        expected = {
            CORE,
            FILES,
            WEB,
            DEVELOPMENT,
            FINANCE,
            ENTERTAINMENT,
            SYSTEM,
        }
        assert set(ALL_CATEGORIES) == expected
