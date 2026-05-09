"""Tests for [`ServerManager`](../manager.py)."""

from unittest.mock import MagicMock, patch

import pytest

from aria.server.manager import ServerManager


def _make_manager() -> ServerManager:
    with patch("aria.server.manager.load_state", return_value={}):
        return ServerManager()


class TestServerManagerRun:
    """Tests for [`ServerManager.run()`](../manager.py)."""

    def test_run_raises_when_web_ui_exits_nonzero(self) -> None:
        manager = _make_manager()

        with (
            patch.object(manager, "_build_command", return_value=["chainlit"]),
            patch("aria.server.manager.subprocess.run") as mock_run,
            patch("aria.config.folders.get_augmented_env", return_value={}),
            patch.object(manager, "_clear_state") as mock_clear,
            patch.object(manager, "_save_state"),
        ):
            mock_run.return_value = MagicMock(returncode=1)

            with pytest.raises(RuntimeError, match="status 1"):
                manager.run()

        mock_clear.assert_called_once()

    def test_run_redirects_output_to_debug_log(self) -> None:
        manager = _make_manager()

        with (
            patch.object(manager, "_build_command", return_value=["chainlit"]),
            patch("aria.server.manager.subprocess.run") as mock_run,
            patch("aria.config.folders.get_augmented_env", return_value={}),
            patch.object(manager, "_clear_state"),
            patch.object(manager, "_save_state"),
        ):
            mock_run.return_value = MagicMock(returncode=0)
            manager.run()

        _, kwargs = mock_run.call_args
        assert kwargs["stdout"] is kwargs["stderr"]
