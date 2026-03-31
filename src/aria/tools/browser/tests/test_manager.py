"""Tests for browser manager response helpers and recovery behavior."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from aria.tools.browser.manager import LightpandaManager


def _make_manager() -> LightpandaManager:
    """Create a manager with a placeholder binary path for unit tests."""
    return LightpandaManager(Path("/tmp/lightpanda"))


def test_is_running_false_when_not_started() -> None:
    manager = _make_manager()
    assert manager.is_running is False


def test_is_running_true_when_all_set() -> None:
    manager = _make_manager()
    manager._process = Mock()
    manager._browser = Mock()
    manager._page = Mock()
    assert manager.is_running is True


def test_success_and_error_use_safe_json() -> None:
    manager = _make_manager()

    ok_payload = json.loads(manager._success({"status": "ok"}))
    assert ok_payload == {"status": "ok"}

    err_payload = json.loads(manager._error("boom", recovery=True))
    assert err_payload["error"] == "boom"
    assert err_payload["recovery"] == "Browser crashed. Restarted. Retry."


def test_error_without_recovery() -> None:
    manager = _make_manager()
    payload = json.loads(manager._error("something broke"))
    assert payload == {"error": "something broke"}
    assert "recovery" not in payload


@pytest.mark.asyncio
async def test_with_recovery_returns_error_when_page_unavailable() -> None:
    manager = _make_manager()
    manager._ensure_page = AsyncMock(return_value=False)

    result = await manager._with_recovery("test", AsyncMock(return_value="ok"))
    payload = json.loads(result)
    assert payload["error"] == "Browser not available"


@pytest.mark.asyncio
async def test_with_recovery_calls_fn_on_valid_page() -> None:
    manager = _make_manager()
    page = Mock()
    manager._page = page
    manager._ensure_page = AsyncMock(return_value=True)

    fn = AsyncMock(return_value='{"ok": true}')
    result = await manager._with_recovery("test", fn)

    fn.assert_awaited_once_with(page)
    assert result == '{"ok": true}'


@pytest.mark.asyncio
async def test_with_recovery_returns_recovery_error_on_crash() -> None:
    manager = _make_manager()
    page = Mock()
    manager._page = page
    manager._ensure_page = AsyncMock(side_effect=[True, True])
    manager._is_page_valid = Mock(return_value=False)

    fn = AsyncMock(side_effect=Exception("crashed"))
    result = await manager._with_recovery("test", fn)
    payload = json.loads(result)

    assert payload["error"] == "crashed"
    assert payload["recovery"] == "Browser crashed. Restarted. Retry."


@pytest.mark.asyncio
async def test_with_recovery_returns_plain_error_when_page_still_valid() -> (
    None
):
    manager = _make_manager()
    page = Mock()
    manager._page = page
    manager._ensure_page = AsyncMock(return_value=True)
    manager._is_page_valid = Mock(return_value=True)

    fn = AsyncMock(side_effect=Exception("timeout"))
    result = await manager._with_recovery("test", fn)
    payload = json.loads(result)

    assert payload["error"] == "timeout"
    assert "recovery" not in payload


@pytest.mark.asyncio
async def test_navigate_returns_recovery_error_after_crash() -> None:
    manager = _make_manager()
    page = Mock()
    page.url = "https://example.com"
    page.goto = AsyncMock(side_effect=Exception("nav failed"))
    page.wait_for_load_state = AsyncMock()
    page.title = AsyncMock(return_value="Example")

    manager._process = Mock()
    manager._browser = Mock()
    manager._page = page

    # _ensure_page succeeds initially; after crash _is_page_valid returns
    # False so _with_recovery enters the crash-recovery branch, then
    # _ensure_page succeeds again for the restart.
    manager._is_page_valid = Mock(return_value=False)
    manager._ensure_page = AsyncMock(side_effect=[True, True])

    result = await manager.navigate("https://example.com")
    payload = json.loads(result)

    assert payload["error"] == "nav failed"
    assert payload["recovery"] == "Browser crashed. Restarted. Retry."


@pytest.mark.asyncio
async def test_click_returns_recovery_error_after_crash() -> None:
    manager = _make_manager()
    page = Mock()
    page.url = "https://example.com"
    page.click = AsyncMock(side_effect=Exception("click failed"))
    page.wait_for_load_state = AsyncMock()
    page.title = AsyncMock(return_value="Example")

    manager._process = Mock()
    manager._browser = Mock()
    manager._page = page

    # _ensure_page succeeds initially; after crash _is_page_valid returns
    # False so _with_recovery enters the crash-recovery branch.
    manager._is_page_valid = Mock(return_value=False)
    manager._ensure_page = AsyncMock(side_effect=[True, True])

    result = await manager.click("button.accept")
    payload = json.loads(result)

    assert payload["error"] == "click failed"
    assert payload["recovery"] == "Browser crashed. Restarted. Retry."


@pytest.mark.asyncio
async def test_get_page_content_returns_error_json_when_unavailable() -> None:
    manager = _make_manager()
    manager._ensure_page = AsyncMock(return_value=False)

    result = await manager.get_page_content()
    payload = json.loads(result)

    assert payload["error"] == "Browser not available"


@pytest.mark.asyncio
async def test_get_page_content_returns_cleaned_text() -> None:
    manager = _make_manager()
    page = Mock()
    page.evaluate = AsyncMock(return_value="  Line 1\n\n   Line 2  ")

    manager._process = Mock()
    manager._browser = Mock()
    manager._page = page
    manager._ensure_page = AsyncMock(return_value=True)

    result = await manager.get_page_content()

    assert result == "Line 1\nLine 2"


@pytest.mark.asyncio
async def test_get_page_content_falls_back_to_html_on_evaluate_error() -> None:
    manager = _make_manager()
    page = Mock()
    page.evaluate = AsyncMock(side_effect=RuntimeError("eval failed"))
    page.content = AsyncMock(return_value="<html><body>fallback</body></html>")

    manager._process = Mock()
    manager._browser = Mock()
    manager._page = page
    manager._ensure_page = AsyncMock(return_value=True)

    result = await manager.get_page_content()

    assert result == "<html><body>fallback</body></html>"


def test_navigation_failed_on_empty_content() -> None:
    assert LightpandaManager._is_navigation_failed("", "https://example.com")
    assert LightpandaManager._is_navigation_failed(
        "   ", "https://example.com"
    )


def test_navigation_failed_on_about_blank() -> None:
    assert LightpandaManager._is_navigation_failed(
        "some content", "about:blank"
    )


def test_navigation_failed_on_error_patterns() -> None:
    assert LightpandaManager._is_navigation_failed(
        "Navigation failed", "https://example.com"
    )
    assert LightpandaManager._is_navigation_failed(
        "net::ERR_CONNECTION_REFUSED", "https://example.com"
    )


def test_navigation_not_failed_on_valid_content() -> None:
    assert not LightpandaManager._is_navigation_failed(
        "Hello World", "https://example.com"
    )


def test_persist_content_writes_file(tmp_path: Path) -> None:
    manager = _make_manager()

    with patch(
        "aria.tools.browser.manager._build_content_filepath",
        return_value=tmp_path / "test.txt",
    ):
        path = manager._persist_content("hello", "https://example.com", "open")

    assert path.exists()
    assert path.read_text() == "hello"
