"""Tests for browser manager response helpers and recovery behavior."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from aria.tools.browser.manager import LightpandaManager


def _make_manager() -> LightpandaManager:
    """Create a manager with a placeholder binary path for unit tests."""
    return LightpandaManager(Path("/tmp/lightpanda"))


def test_require_running_page_raises_when_not_running() -> None:
    manager = _make_manager()

    with pytest.raises(RuntimeError, match="Browser is not running"):
        manager._require_running_page()


def test_require_running_page_raises_when_page_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = _make_manager()

    monkeypatch.setattr(
        LightpandaManager,
        "is_running",
        property(lambda self: True),
    )

    with pytest.raises(RuntimeError, match="Page is not open"):
        manager._require_running_page()


def test_require_running_page_returns_page_when_valid() -> None:
    manager = _make_manager()
    page = Mock()
    manager._process = Mock()
    manager._browser = Mock()
    manager._page = page

    assert manager._require_running_page() is page


def test_success_and_error_use_safe_json() -> None:
    manager = _make_manager()

    ok_payload = json.loads(manager._success({"status": "ok"}))
    assert ok_payload == {"status": "ok"}

    err_payload = json.loads(manager._error("boom", recovery=True))
    assert err_payload["error"] == "boom"
    assert err_payload["recovery"] == "Browser crashed. Restarted. Retry."


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

    manager._is_page_valid = Mock(side_effect=[True, False])
    manager._ensure_page = AsyncMock(return_value=True)

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

    manager._is_page_valid = Mock(side_effect=[True, False])
    manager._ensure_page = AsyncMock(return_value=True)

    result = await manager.click("button.accept")
    payload = json.loads(result)

    assert payload["error"] == "click failed"
    assert payload["recovery"] == "Browser crashed. Restarted. Retry."


@pytest.mark.asyncio
async def test_screenshot_returns_recovery_error_after_crash() -> None:
    manager = _make_manager()
    page = Mock()
    page.wait_for_load_state = AsyncMock()
    page.screenshot = AsyncMock(side_effect=Exception("shot failed"))

    manager._process = Mock()
    manager._browser = Mock()
    manager._page = page

    manager._is_page_valid = Mock(side_effect=[True, False])
    manager._ensure_page = AsyncMock(return_value=True)

    result = await manager.screenshot("/tmp/screen.png")
    payload = json.loads(result)

    assert payload["error"] == "shot failed"
    assert payload["recovery"] == "Browser crashed. Restarted. Retry."


@pytest.mark.asyncio
async def test_get_page_content_returns_error_json_when_unavailable() -> None:
    manager = _make_manager()

    result = await manager.get_page_content()
    payload = json.loads(result)

    assert payload["error"] == "Browser is not running"


@pytest.mark.asyncio
async def test_get_page_content_returns_cleaned_text() -> None:
    manager = _make_manager()
    page = Mock()
    page.evaluate = AsyncMock(return_value="  Line 1\n\n   Line 2  ")

    manager._process = Mock()
    manager._browser = Mock()
    manager._page = page
    manager._is_page_valid = Mock(return_value=True)

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
    manager._is_page_valid = Mock(return_value=True)

    result = await manager.get_page_content()

    assert result == "<html><body>fallback</body></html>"
