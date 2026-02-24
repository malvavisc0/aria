"""Tests for GGUF model download utilities in gguf.py."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aria.scripts.gguf import (
    download_gguf_model,
    get_model_path,
    is_model_downloaded,
)

# ---------------------------------------------------------------------------
# get_model_path
# ---------------------------------------------------------------------------


class TestGetModelPath:
    """Tests for get_model_path()."""

    def test_returns_none_when_models_dir_does_not_exist(self, tmp_path: Path):
        """Returns None when the models directory does not exist."""
        missing_dir = tmp_path / "nonexistent"
        result = get_model_path("model-Q8_0.gguf", missing_dir)
        assert result is None

    def test_returns_none_when_file_not_found(self, tmp_path: Path):
        """Returns None when the file does not exist."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        result = get_model_path("model-Q8_0.gguf", models_dir)
        assert result is None

    def test_returns_path_when_file_exists(self, tmp_path: Path):
        """Returns the path when the file exists."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        model_file = models_dir / "model-Q8_0.gguf"
        model_file.touch()

        result = get_model_path("model-Q8_0.gguf", models_dir)
        assert result == model_file

    def test_exact_filename_match_required(self, tmp_path: Path):
        """Requires exact filename match, not partial."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        model_file = models_dir / "model-Q8_0.gguf"
        model_file.touch()

        # Partial name should not match
        result = get_model_path("model-Q8", models_dir)
        assert result is None

        # Exact match should work
        result = get_model_path("model-Q8_0.gguf", models_dir)
        assert result == model_file


# ---------------------------------------------------------------------------
# is_model_downloaded
# ---------------------------------------------------------------------------


class TestIsModelDownloaded:
    """Tests for is_model_downloaded()."""

    def test_returns_false_when_models_dir_does_not_exist(self, tmp_path: Path):
        """Returns False when the models directory does not exist."""
        missing_dir = tmp_path / "nonexistent"
        assert is_model_downloaded("model-Q8_0.gguf", missing_dir) is False

    def test_returns_false_when_file_not_found(self, tmp_path: Path):
        """Returns False when the file does not exist in models_dir."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        assert is_model_downloaded("model-Q8_0.gguf", models_dir) is False

    def test_returns_true_when_file_exists(self, tmp_path: Path):
        """Returns True when the file exists in models_dir."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "model-Q8_0.gguf").touch()
        assert is_model_downloaded("model-Q8_0.gguf", models_dir) is True


# ---------------------------------------------------------------------------
# download_gguf_model
# ---------------------------------------------------------------------------


class TestDownloadGgufModel:
    """Tests for download_gguf_model()."""

    def test_returns_existing_file_without_download(self, tmp_path: Path):
        """Returns existing file without downloading when force=False."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        existing_file = models_dir / "model-Q8_0.gguf"
        existing_file.touch()

        with patch("aria.scripts.gguf.hf_hub_download") as mock_download:
            result = download_gguf_model(
                repo_id="org/repo",
                filename="model-Q8_0.gguf",
                models_dir=models_dir,
                force=False,
            )

        mock_download.assert_not_called()
        assert result == existing_file

    def test_downloads_file_when_not_exists(self, tmp_path: Path):
        """Downloads file when it does not exist."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()

        # Create the file that hf_hub_download would create
        downloaded_file = models_dir / "model-Q8_0.gguf"

        with patch("aria.scripts.gguf.hf_hub_download") as mock_download:
            # Set up mock to create the file and return its path
            def fake_download(*args, **kwargs):
                downloaded_file.touch()
                return str(downloaded_file)

            mock_download.side_effect = fake_download

            result = download_gguf_model(
                repo_id="org/repo",
                filename="model-Q8_0.gguf",
                models_dir=models_dir,
            )

        mock_download.assert_called_once_with(
            repo_id="org/repo",
            filename="model-Q8_0.gguf",
            token=None,
            local_dir=str(models_dir),
            force_download=False,
        )
        assert result.name == "model-Q8_0.gguf"

    def test_force_redownloads_even_if_exists(self, tmp_path: Path):
        """Force re-downloads even if file exists."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        existing_file = models_dir / "model-Q8_0.gguf"
        existing_file.touch()

        with patch("aria.scripts.gguf.hf_hub_download") as mock_download:
            mock_download.return_value = str(existing_file)

            result = download_gguf_model(
                repo_id="org/repo",
                filename="model-Q8_0.gguf",
                models_dir=models_dir,
                force=True,
            )

        mock_download.assert_called_once()
        assert result == existing_file

    def test_passes_token_to_hf_hub_download(self, tmp_path: Path):
        """Passes token to hf_hub_download."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        downloaded_file = models_dir / "model-Q8_0.gguf"

        with patch("aria.scripts.gguf.hf_hub_download") as mock_download:

            def fake_download(*args, **kwargs):
                downloaded_file.touch()
                return str(downloaded_file)

            mock_download.side_effect = fake_download

            download_gguf_model(
                repo_id="org/repo",
                filename="model-Q8_0.gguf",
                models_dir=models_dir,
                token="hf_abc123",
            )

        mock_download.assert_called_once_with(
            repo_id="org/repo",
            filename="model-Q8_0.gguf",
            token="hf_abc123",
            local_dir=str(models_dir),
            force_download=False,
        )

    def test_raises_file_not_found_on_entry_not_found(self, tmp_path: Path):
        """Raises FileNotFoundError when file not found in repo."""
        from huggingface_hub.errors import EntryNotFoundError

        models_dir = tmp_path / "models"
        models_dir.mkdir()

        with patch("aria.scripts.gguf.hf_hub_download") as mock_download:
            mock_download.side_effect = EntryNotFoundError("not found")

            with pytest.raises(FileNotFoundError, match="not found"):
                download_gguf_model(
                    repo_id="org/repo",
                    filename="nonexistent.gguf",
                    models_dir=models_dir,
                )

    def test_raises_runtime_error_on_generic_error(self, tmp_path: Path):
        """Raises RuntimeError on generic download error."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()

        with patch("aria.scripts.gguf.hf_hub_download") as mock_download:
            mock_download.side_effect = Exception("network error")

            with pytest.raises(RuntimeError, match="Failed to download"):
                download_gguf_model(
                    repo_id="org/repo",
                    filename="model-Q8_0.gguf",
                    models_dir=models_dir,
                )

    def test_creates_models_dir_if_not_exists(self, tmp_path: Path):
        """Creates models_dir if it does not exist."""
        models_dir = tmp_path / "models"
        downloaded_file = models_dir / "model-Q8_0.gguf"

        with patch("aria.scripts.gguf.hf_hub_download") as mock_download:

            def fake_download(*args, **kwargs):
                # Simulate hf_hub_download creating the directory and file
                models_dir.mkdir(parents=True, exist_ok=True)
                downloaded_file.touch()
                return str(downloaded_file)

            mock_download.side_effect = fake_download

            download_gguf_model(
                repo_id="org/repo",
                filename="model-Q8_0.gguf",
                models_dir=models_dir,
            )

        assert models_dir.exists()
