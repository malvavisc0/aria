"""Tests for new preflight checks (LLM server, knowledge DB, tool loading)."""

from unittest.mock import MagicMock, patch

from aria.preflight import run_preflight_checks


class TestCheckLlmServer:
    """Test LLM server connectivity check (non-blocking)."""

    @patch("httpx.get")
    def test_llm_server_reachable(self, mock_get):
        """Should pass with model count when server responds."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": [{"id": "model-1"}]}
        mock_get.return_value = mock_resp

        from aria.preflight import _check_llm_server

        checks = []
        _check_llm_server(checks)
        assert len(checks) == 1
        assert checks[0].passed is True
        assert checks[0].category == "connectivity"
        assert "model" in checks[0].details

    @patch("httpx.get")
    def test_llm_server_unreachable_is_non_blocking(self, mock_get):
        """Should pass even when server is unreachable (non-blocking)."""
        import httpx

        mock_get.side_effect = httpx.ConnectError("refused")

        from aria.preflight import _check_llm_server

        checks = []
        _check_llm_server(checks)
        assert len(checks) == 1
        assert checks[0].passed is True
        assert checks[0].category == "connectivity"
        assert "not running" in checks[0].details.lower()


class TestCheckKnowledgeDb:
    """Test knowledge database check."""

    @patch("aria.tools.knowledge.database.KnowledgeDatabase.__new__")
    def test_knowledge_db_accessible(self, mock_new):
        """Should pass when knowledge DB is accessible."""
        mock_new.return_value = MagicMock()

        from aria.preflight import _check_knowledge_db

        checks = []
        _check_knowledge_db(checks)
        assert len(checks) == 1
        assert checks[0].passed is True
        assert checks[0].category == "storage"

    @patch(
        "aria.tools.knowledge.database.KnowledgeDatabase.__init__",
        side_effect=Exception("DB not found"),
    )
    def test_knowledge_db_fails(self, mock_init):
        """Should fail when knowledge DB raises an error."""
        from aria.preflight import _check_knowledge_db

        checks = []
        _check_knowledge_db(checks)
        assert len(checks) == 1
        assert checks[0].passed is False
        assert checks[0].category == "storage"


class TestCheckToolLoading:
    """Test tool loading check."""

    def test_tool_loading_ok(self):
        """Should pass when tools load correctly."""
        from aria.preflight import _check_tool_loading

        checks = []
        _check_tool_loading(checks)
        assert len(checks) == 1
        assert checks[0].passed is True
        assert checks[0].category == "tools"
        assert "11" in checks[0].details

    @patch("aria.tools.registry.get_tools")
    def test_tool_loading_fails(self, mock_get_tools):
        """Should fail when tool loading raises an error."""
        mock_get_tools.side_effect = Exception("Import error")

        from aria.preflight import _check_tool_loading

        checks = []
        _check_tool_loading(checks)
        assert len(checks) == 1
        assert checks[0].passed is False
        assert checks[0].category == "tools"


class TestRunPreflightChecks:
    """Test that run_preflight_checks includes new checks."""

    def test_includes_new_categories(self):
        """Preflight result should include connectivity and tools checks."""
        result = run_preflight_checks()
        categories = {c.category for c in result.checks}
        assert "connectivity" in categories
        assert "tools" in categories
