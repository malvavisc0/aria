"""Tests for aria.config.folders PATH augmentation helpers."""

import os
import sys
from pathlib import Path

from aria.config.folders import get_augmented_env, get_augmented_path


class TestGetAugmentedPath:
    """Tests for get_augmented_path()."""

    def test_includes_bin(self, tmp_path, monkeypatch):
        """~/.aria/bin should be in the returned PATH."""
        import aria.config.folders as folders

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        monkeypatch.setattr(folders.Bin, "path", bin_dir)

        result = get_augmented_path()
        assert str(bin_dir) in result.split(os.pathsep)

    def test_bin_is_prepended(self, tmp_path, monkeypatch):
        """~/.aria/bin should come before the existing PATH."""
        import aria.config.folders as folders

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        monkeypatch.setattr(folders.Bin, "path", bin_dir)

        result = get_augmented_path()
        parts = result.split(os.pathsep)
        assert parts[0] == str(bin_dir)

    def test_includes_venv_bin(self, tmp_path, monkeypatch):
        """The current Python env's bin dir should be in PATH."""
        import aria.config.folders as folders

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        monkeypatch.setattr(folders.Bin, "path", bin_dir)

        result = get_augmented_path()
        python_bin = os.path.join(sys.prefix, "Scripts" if os.name == "nt" else "bin")
        if os.path.isdir(python_bin):
            assert python_bin in result.split(os.pathsep)

    def test_includes_existing_path(self, tmp_path, monkeypatch):
        """The original PATH should be preserved."""
        import aria.config.folders as folders

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        monkeypatch.setattr(folders.Bin, "path", bin_dir)

        monkeypatch.setenv("PATH", "/custom/path")
        result = get_augmented_path()
        assert "/custom/path" in result.split(os.pathsep)

    def test_creates_bin_dir_if_missing(self, tmp_path, monkeypatch):
        """get_augmented_path should create bin/ if it doesn't exist."""
        import aria.config.folders as folders

        bin_dir = tmp_path / "bin"
        # Do NOT create it
        monkeypatch.setattr(folders.Bin, "path", bin_dir)

        get_augmented_path()
        assert bin_dir.exists()


class TestGetAugmentedEnv:
    """Tests for get_augmented_env()."""

    def test_returns_dict(self, tmp_path, monkeypatch):
        """Should return a dict[str, str]."""
        import aria.config.folders as folders

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        monkeypatch.setattr(folders.Bin, "path", bin_dir)

        result = get_augmented_env()
        assert isinstance(result, dict)
        assert "PATH" in result

    def test_path_is_augmented(self, tmp_path, monkeypatch):
        """Returned PATH should contain ~/.aria/bin."""
        import aria.config.folders as folders

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        monkeypatch.setattr(folders.Bin, "path", bin_dir)

        result = get_augmented_env()
        assert str(bin_dir) in result["PATH"].split(os.pathsep)

    def test_preserves_other_env_vars(self, tmp_path, monkeypatch):
        """Other environment variables should be preserved."""
        import aria.config.folders as folders

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        monkeypatch.setattr(folders.Bin, "path", bin_dir)

        monkeypatch.setenv("TEST_VAR_12345", "hello")
        result = get_augmented_env()
        assert result.get("TEST_VAR_12345") == "hello"

    def test_does_not_mutate_os_environ(self, tmp_path, monkeypatch):
        """os.environ should not be modified."""
        import aria.config.folders as folders

        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        monkeypatch.setattr(folders.Bin, "path", bin_dir)

        original_path = os.environ.get("PATH", "")
        get_augmented_env()
        assert os.environ.get("PATH", "") == original_path
