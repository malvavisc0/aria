from unittest.mock import patch

from typer.testing import CliRunner

from aria.cli.server import app

runner = CliRunner()


def _preflight_ok():
    class _Result:
        passed = True

        @staticmethod
        def group_by_category():
            return {}

    return _Result()


def test_server_run_shows_clean_failure_panel() -> None:
    with (
        patch("aria.cli.server._ensure_lightpanda_installed"),
        patch(
            "aria.cli.server._get_captured_startup_error",
            return_value="vLLM startup failed: model load error",
        ),
        patch(
            "aria.cli.server.run_preflight_checks",
            return_value=_preflight_ok(),
        ),
        patch("aria.cli.server._print_preflight_result", return_value=True),
        patch("aria.cli.server.ServerManager") as mock_manager_cls,
    ):
        mock_manager = mock_manager_cls.return_value
        mock_manager.host = "127.0.0.1"
        mock_manager.port = 9876
        mock_manager.run.side_effect = RuntimeError("Web UI exited with status 1")

        result = runner.invoke(app, ["run"])

    assert result.exit_code == 1
    assert "Startup failed" in result.output
    assert "model load error" in result.output
    assert "vllm.log" in result.output


def test_server_run_shows_captured_error_after_clean_return() -> None:
    with (
        patch("aria.cli.server._ensure_lightpanda_installed"),
        patch(
            "aria.cli.server._get_captured_startup_error",
            return_value="vLLM startup failed: model load error",
        ),
        patch(
            "aria.cli.server.run_preflight_checks",
            return_value=_preflight_ok(),
        ),
        patch("aria.cli.server._print_preflight_result", return_value=True),
        patch("aria.cli.server.ServerManager") as mock_manager_cls,
    ):
        mock_manager = mock_manager_cls.return_value
        mock_manager.host = "127.0.0.1"
        mock_manager.port = 9876
        mock_manager.run.side_effect = Exception("silent startup failure")

        result = runner.invoke(app, ["run"])

    assert result.exit_code == 1
    assert "Startup failed" in result.output
    assert "model load error" in result.output


def test_server_start_shows_clean_timeout_panel() -> None:
    with (
        patch("aria.cli.server._ensure_lightpanda_installed"),
        patch(
            "aria.cli.server._get_captured_startup_error",
            return_value="vLLM startup failed: model load error",
        ),
        patch(
            "aria.cli.server.run_preflight_checks",
            return_value=_preflight_ok(),
        ),
        patch("aria.cli.server._print_preflight_result", return_value=True),
        patch("aria.cli.server._wait_for_health", return_value=False),
        patch("aria.cli.server.ServerManager") as mock_manager_cls,
    ):
        mock_manager = mock_manager_cls.return_value
        mock_manager.host = "127.0.0.1"
        mock_manager.port = 9876
        mock_manager.is_running.return_value = False
        mock_manager.start.return_value = True

        result = runner.invoke(app, ["start"])

    assert result.exit_code == 1
    assert "Startup failed" in result.output
    assert "model load error" in result.output


def test_ensure_vllm_running_shows_clean_failure_panel() -> None:
    with (
        patch("aria.cli.server._ensure_lightpanda_installed"),
        patch(
            "aria.cli.server.run_preflight_checks",
            return_value=_preflight_ok(),
        ),
        patch("aria.cli.server._print_preflight_result", return_value=True),
        patch(
            "aria.cli.server._get_captured_startup_error",
            return_value="vLLM startup failed: model load error",
        ),
        patch("aria.cli.server._is_vllm_healthy", return_value=False),
        patch(
            "aria.server.vllm.VllmServerManager.start_all",
            side_effect=RuntimeError("boom"),
        ),
        patch("aria.cli.server.ServerManager") as mock_manager_cls,
    ):
        mock_manager = mock_manager_cls.return_value
        mock_manager.is_running.return_value = True
        mock_manager.host = "127.0.0.1"
        mock_manager.port = 9876

        result = runner.invoke(app, ["start"])

    assert result.exit_code == 1
    assert "Startup failed" in result.output
    assert "model load error" in result.output
