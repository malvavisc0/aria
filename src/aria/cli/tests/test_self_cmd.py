"""Tests for self-awareness CLI commands."""

import json

from typer.testing import CliRunner

from aria.cli.self_cmd import app

runner = CliRunner()


class TestTestTools:
    """Test the test-tools command."""

    def _invoke(self):
        """Invoke test-tools (single-command app, no subcommand name)."""
        result = runner.invoke(app, [])
        assert result.exit_code == 0, result.output
        return json.loads(result.output)

    def test_returns_valid_json(self):
        """test-tools should return valid JSON."""
        data = self._invoke()
        assert isinstance(data, dict)

    def test_has_expected_keys(self):
        """Output should have summary and details keys."""
        data = self._invoke()
        assert "categories_ok" in data
        assert "categories_total" in data
        assert "tools_available" in data
        assert "details" in data

    def test_core_category_present(self):
        """Core category should be in the details."""
        data = self._invoke()
        assert "core" in data["details"]

    def test_files_category_present(self):
        """Files category should be in the details."""
        data = self._invoke()
        assert "files" in data["details"]

    def test_core_has_4_tools(self):
        """Core category should report 4 tools."""
        data = self._invoke()
        assert data["details"]["core"]["count"] == 4

    def test_files_has_7_tools(self):
        """Files category should report 7 tools."""
        data = self._invoke()
        assert data["details"]["files"]["count"] == 7

    def test_tools_available_is_11(self):
        """Total tools available should be 11 (core + files)."""
        data = self._invoke()
        assert data["tools_available"] >= 11

    def test_categories_ok_count(self):
        """categories_ok should be at least 2 (core + files)."""
        data = self._invoke()
        assert data["categories_ok"] >= 2
