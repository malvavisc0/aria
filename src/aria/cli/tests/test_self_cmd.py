"""Tests for self-awareness CLI commands."""

import json
import sys
from pathlib import Path

from typer.testing import CliRunner

from aria.cli.self_cmd import app

runner = CliRunner()


class TestTestTools:
    """Test the test-tools command."""

    def _invoke(self):
        """Invoke test-tools."""
        result = runner.invoke(app, ["test-tools"])
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


class TestShowPath:
    """Test the path command."""

    def _invoke(self):
        """Invoke path and return parsed JSON."""
        result = runner.invoke(app, ["path"])
        assert result.exit_code == 0, result.output
        return json.loads(result.output)

    def test_returns_valid_json(self):
        """path should return valid JSON."""
        data = self._invoke()
        assert isinstance(data, dict)

    def test_has_expected_keys(self):
        """Output should have package_dir and python_bin keys."""
        data = self._invoke()
        assert "package_dir" in data
        assert "python_bin" in data

    def test_package_dir_exists(self):
        """package_dir should be an existing directory."""
        data = self._invoke()
        assert Path(data["package_dir"]).is_dir()

    def test_package_dir_has_init(self):
        """package_dir should contain __init__.py."""
        data = self._invoke()
        assert (Path(data["package_dir"]) / "__init__.py").exists()

    def test_python_bin_exists(self):
        """python_bin should be an existing file."""
        data = self._invoke()
        assert Path(data["python_bin"]).exists()

    def test_python_bin_matches_sys(self):
        """python_bin should match sys.executable."""
        data = self._invoke()
        assert data["python_bin"] == sys.executable
