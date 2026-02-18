"""Tests for GGUF model download utilities in gguf.py."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aria.scripts.gguf import (
    _find_gguf_filename,
    download_gguf_model,
    get_model_path,
    is_model_downloaded,
)

# ---------------------------------------------------------------------------
# _find_gguf_filename
# ---------------------------------------------------------------------------


class TestFindGgufFilename:
    """Tests for _find_gguf_filename()."""

    def test_finds_exact_quantization_match(self):
        """Returns the filename that contains the quantization string."""
        files = [
            "model-Q4_K_M.gguf",
            "model-Q8_0.gguf",
            "model-F16.gguf",
        ]
        with patch("aria.scripts.gguf.list_repo_files", return_value=iter(files)):
            result = _find_gguf_filename("org/repo", "Q8_0")
        assert result == "model-Q8_0.gguf"

    def test_case_insensitive_match(self):
        """Quantization matching is case-insensitive."""
        files = ["model-q8_0.gguf"]
        with patch("aria.scripts.gguf.list_repo_files", return_value=iter(files)):
            result = _find_gguf_filename("org/repo", "Q8_0")
        assert result == "model-q8_0.gguf"

    def test_raises_file_not_found_when_no_gguf_files(self):
        """Raises FileNotFoundError when repo has no .gguf files."""
        files = ["README.md", "config.json"]
        with patch("aria.scripts.gguf.list_repo_files", return_value=iter(files)):
            with pytest.raises(FileNotFoundError, match="No .gguf files found"):
                _find_gguf_filename("org/repo", "Q8_0")

    def test_raises_file_not_found_when_quantization_not_found(self):
        """Raises FileNotFoundError when no file matches the quantization."""
        files = ["model-Q4_K_M.gguf", "model-F16.gguf"]
        with patch("aria.scripts.gguf.list_repo_files", return_value=iter(files)):
            with pytest.raises(FileNotFoundError, match="No GGUF file matching"):
                _find_gguf_filename("org/repo", "Q8_0")

    def test_raises_repository_not_found_error(self):
        """Raises RepositoryNotFoundError when repo does not exist."""
        from huggingface_hub.errors import RepositoryNotFoundError

        # Use a MagicMock as the response so the constructor doesn't fail
        mock_response = MagicMock()
        mock_response.headers = {}

        with patch(
            "aria.scripts.gguf.list_repo_files",
            side_effect=RepositoryNotFoundError("not found", response=mock_response),
        ):
            with pytest.raises(RepositoryNotFoundError):
                _find_gguf_filename("nonexistent/repo", "Q8_0")

    def test_returns_first_match_when_multiple(self):
        """Returns the first match when multiple files match the quantization."""
        files = ["model-Q8_0-part1.gguf", "model-Q8_0-part2.gguf"]
        with patch("aria.scripts.gguf.list_repo_files", return_value=iter(files)):
            result = _find_gguf_filename("org/repo", "Q8_0")
        assert result == "model-Q8_0-part1.gguf"

    def test_passes_token_to_list_repo_files(self):
        """Passes the token argument to list_repo_files."""
        files = ["model-Q8_0.gguf"]
        with patch(
            "aria.scripts.gguf.list_repo_files", return_value=iter(files)
        ) as mock_list:
            _find_gguf_filename("org/repo", "Q8_0", token="hf_abc123")
            mock_list.assert_called_once_with("org/repo", token="hf_abc123")


# ---------------------------------------------------------------------------
# is_model_downloaded
# ---------------------------------------------------------------------------


class TestIsModelDownloaded:
    """Tests for is_model_downloaded()."""

    def test_returns_false_when_models_dir_does_not_exist(self, tmp_path: Path):
        """Returns False when the models directory does not exist."""
        missing_dir = tmp_path / "nonexistent"
        assert is_model_downloaded("org/repo", "Q8_0", missing_dir) is False

    def test_returns_false_when_no_matching_gguf(self, tmp_path: Path):
        """Returns False when no .gguf file matches the quantization."""
        (tmp_path / "model-Q4_K_M.gguf").touch()
        assert is_model_downloaded("org/repo", "Q8_0", tmp_path) is False

    def test_returns_true_when_matching_gguf_exists(self, tmp_path: Path):
        """Returns True when a .gguf file matching the quantization exists."""
        (tmp_path / "model-Q8_0.gguf").touch()
        assert is_model_downloaded("org/repo", "Q8_0", tmp_path) is True

    def test_case_insensitive_quantization_check(self, tmp_path: Path):
        """Quantization check is case-insensitive."""
        (tmp_path / "model-q8_0.gguf").touch()
        assert is_model_downloaded("org/repo", "Q8_0", tmp_path) is True

    def test_returns_false_when_dir_is_empty(self, tmp_path: Path):
        """Returns False when the models directory is empty."""
        assert is_model_downloaded("org/repo", "Q8_0", tmp_path) is False


# ---------------------------------------------------------------------------
# get_model_path
# ---------------------------------------------------------------------------


class TestGetModelPath:
    """Tests for get_model_path()."""

    def test_returns_none_when_models_dir_does_not_exist(self, tmp_path: Path):
        """Returns None when the models directory does not exist."""
        missing_dir = tmp_path / "nonexistent"
        assert get_model_path("org/repo", "Q8_0", missing_dir) is None

    def test_returns_none_when_no_matching_file(self, tmp_path: Path):
        """Returns None when no matching .gguf file is found."""
        (tmp_path / "model-Q4_K_M.gguf").touch()
        assert get_model_path("org/repo", "Q8_0", tmp_path) is None

    def test_returns_path_when_matching_file_exists(self, tmp_path: Path):
        """Returns the path to the matching .gguf file."""
        # Filename must contain both the repo name segment and the quantization.
        model_file = tmp_path / "repo-Q8_0.gguf"
        model_file.touch()
        result = get_model_path("org/repo", "Q8_0", tmp_path)
        assert result == model_file


# ---------------------------------------------------------------------------
# download_gguf_model
# ---------------------------------------------------------------------------


class TestDownloadGgufModel:
    """Tests for download_gguf_model()."""

    def test_skips_download_when_already_downloaded(self, tmp_path: Path):
        """Skips download when model already exists and force=False."""
        # Filename must contain both the repo name segment and the quantization
        # so that get_model_path() can locate it after the skip check.
        existing = tmp_path / "repo-Q8_0.gguf"
        existing.touch()

        with patch("aria.scripts.gguf.hf_hub_download") as mock_dl:
            result = download_gguf_model(
                repo_id="org/repo",
                quantization="Q8_0",
                models_dir=tmp_path,
                force=False,
            )
            mock_dl.assert_not_called()

        assert result == existing

    def test_force_redownloads_existing_model(self, tmp_path: Path):
        """Re-downloads when force=True even if model exists."""
        existing = tmp_path / "model-Q8_0.gguf"
        existing.touch()

        downloaded_file = tmp_path / "model-Q8_0.gguf"
        downloaded_file.write_text("new content")

        with patch(
            "aria.scripts.gguf._find_gguf_filename", return_value="model-Q8_0.gguf"
        ):
            with patch(
                "aria.scripts.gguf.hf_hub_download",
                return_value=str(downloaded_file),
            ):
                result = download_gguf_model(
                    repo_id="org/repo",
                    quantization="Q8_0",
                    models_dir=tmp_path,
                    force=True,
                )

        assert result.name == "model-Q8_0.gguf"

    def test_downloads_model_successfully(self, tmp_path: Path):
        """Downloads model when not already present."""
        # Use an empty directory so the skip-if-already-downloaded path is not taken.
        empty_dir = tmp_path / "models"
        downloaded_file = empty_dir / "repo-Q8_0.gguf"

        def fake_download(**kwargs):
            empty_dir.mkdir(parents=True, exist_ok=True)
            downloaded_file.write_text("model data")
            return str(downloaded_file)

        with patch(
            "aria.scripts.gguf._find_gguf_filename", return_value="repo-Q8_0.gguf"
        ):
            with patch(
                "aria.scripts.gguf.hf_hub_download",
                side_effect=fake_download,
            ):
                result = download_gguf_model(
                    repo_id="org/repo",
                    quantization="Q8_0",
                    models_dir=empty_dir,
                )

        assert result == downloaded_file

    def test_creates_models_dir_if_not_exists(self, tmp_path: Path):
        """Creates the models directory if it does not exist."""
        new_dir = tmp_path / "new_models"
        downloaded_file = new_dir / "model-Q8_0.gguf"

        def fake_download(**kwargs):
            new_dir.mkdir(parents=True, exist_ok=True)
            downloaded_file.write_text("data")
            return str(downloaded_file)

        with patch(
            "aria.scripts.gguf._find_gguf_filename", return_value="model-Q8_0.gguf"
        ):
            with patch("aria.scripts.gguf.hf_hub_download", side_effect=fake_download):
                download_gguf_model(
                    repo_id="org/repo",
                    quantization="Q8_0",
                    models_dir=new_dir,
                )

        assert new_dir.exists()

    def test_passes_token_to_hf_hub_download(self, tmp_path: Path):
        """Passes the token to hf_hub_download."""
        # Use a fresh subdirectory so no pre-existing model file triggers the
        # skip-if-already-downloaded path.
        empty_dir = tmp_path / "empty_models"
        downloaded_file = empty_dir / "model-Q8_0.gguf"

        def fake_download(**kwargs):
            empty_dir.mkdir(parents=True, exist_ok=True)
            downloaded_file.write_text("data")
            return str(downloaded_file)

        with patch(
            "aria.scripts.gguf._find_gguf_filename", return_value="model-Q8_0.gguf"
        ):
            with patch(
                "aria.scripts.gguf.hf_hub_download",
                side_effect=fake_download,
            ) as mock_dl:
                download_gguf_model(
                    repo_id="org/repo",
                    quantization="Q8_0",
                    models_dir=empty_dir,
                    token="hf_abc123",
                )
                assert mock_dl.called
                call_kwargs = mock_dl.call_args.kwargs
                assert call_kwargs.get("token") == "hf_abc123"

    def test_raises_runtime_error_on_download_failure(self, tmp_path: Path):
        """Raises RuntimeError when hf_hub_download fails."""
        with patch(
            "aria.scripts.gguf._find_gguf_filename", return_value="model-Q8_0.gguf"
        ):
            with patch(
                "aria.scripts.gguf.hf_hub_download",
                side_effect=Exception("network error"),
            ):
                with pytest.raises(RuntimeError, match="Failed to download"):
                    download_gguf_model(
                        repo_id="org/repo",
                        quantization="Q8_0",
                        models_dir=tmp_path,
                    )

    def test_raises_file_not_found_when_filename_not_found(self, tmp_path: Path):
        """Raises FileNotFoundError when _find_gguf_filename raises it."""
        with patch(
            "aria.scripts.gguf._find_gguf_filename",
            side_effect=FileNotFoundError("No GGUF file matching"),
        ):
            with pytest.raises(FileNotFoundError):
                download_gguf_model(
                    repo_id="org/repo",
                    quantization="Q8_0",
                    models_dir=tmp_path,
                )
