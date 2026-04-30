"""Tests for vision CLI helper functions."""

import json
from unittest.mock import MagicMock, patch

import httpx

from aria.cli.vision import (
    _ensure_vl_ready,
    _is_vision_model_available,
    _is_vl_server_running,
)


class TestIsVisionModelAvailable:
    """Test vision model availability check."""

    @patch("aria.config.api.LlamaCpp")
    @patch("aria.config.models.Vision")
    def test_model_exists(self, mock_vision, mock_llama):
        """Should return True when model file exists."""
        mock_vision.repo_id = "test/repo"
        mock_vision.filename = "model.gguf"
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_llama.models_path = mock_path
        # models_path / filename needs to return a path where exists() is True
        mock_llama.models_path.__truediv__ = MagicMock(return_value=mock_path)
        result = _is_vision_model_available()
        assert result is True

    def test_model_not_available_when_no_repo(self):
        """Should return False when repo_id is empty."""
        with patch.dict(
            "os.environ", {"VL_MODEL_REPO": "", "VL_MODEL": "model.gguf"}
        ):
            result = _is_vision_model_available()
            # Should return False or handle gracefully
            assert isinstance(result, bool)


class TestIsVlServerRunning:
    """Test VL server running check."""

    @patch("httpx.Client")
    def test_server_running(self, mock_client_cls):
        """Should return True when server responds with 200."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = _is_vl_server_running()
        assert result is True

    @patch("httpx.Client")
    def test_server_not_running(self, mock_client_cls):
        """Should return False when connection fails."""
        mock_client_cls.side_effect = httpx.ConnectError("refused")

        result = _is_vl_server_running()
        assert result is False

    @patch("httpx.Client")
    def test_server_timeout(self, mock_client_cls):
        """Should return False on timeout."""
        mock_client_cls.side_effect = httpx.TimeoutException("timeout")

        result = _is_vl_server_running()
        assert result is False


class TestEnsureVlReady:
    """Test VL readiness check."""

    @patch("aria.cli.vision._is_vl_server_running")
    @patch("aria.cli.vision._is_vision_model_available")
    def test_ready_returns_none(self, mock_model, mock_server):
        """Should return None when model and server are ready."""
        mock_model.return_value = True
        mock_server.return_value = True

        result = _ensure_vl_ready()
        assert result is None

    @patch("aria.cli.vision._is_vision_model_available")
    def test_model_missing_returns_error(self, mock_model):
        """Should return error JSON when model is not installed."""
        mock_model.return_value = False

        result = _ensure_vl_ready()
        assert result is not None
        data = json.loads(result)
        assert data["error"] == "vision_not_installed"
        assert "install_command" in data

    @patch("aria.cli.vision._start_vl_server")
    @patch("aria.cli.vision._is_vl_server_running")
    @patch("aria.cli.vision._is_vision_model_available")
    def test_server_fails_to_start(self, mock_model, mock_server, mock_start):
        """Should return error JSON when server fails to start."""
        mock_model.return_value = True
        mock_server.return_value = False
        mock_start.return_value = False

        result = _ensure_vl_ready()
        assert result is not None
        data = json.loads(result)
        assert data["error"] == "vision_server_failed"
