"""Tests for [`aria.web.lifecycle`](../lifecycle.py)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from aria.web.lifecycle import on_app_startup_handler
from aria.web.state import _state


@pytest.mark.asyncio
async def test_startup_fails_when_vllm_fails(tmp_path: Path) -> None:
    """Startup must abort if [`_init_vllm_servers()`](../lifecycle.py) fails."""
    _state.startup_complete = False
    _state.startup_event.clear()

    cleanup = AsyncMock()

    with (
        patch("chainlit.config.FILES_DIRECTORY", tmp_path),
        patch("aria.web.lifecycle.DebugConfig.path", tmp_path / "logs"),
        patch(
            "aria.web.lifecycle.DebugConfig.startup_error_path",
            tmp_path / "logs" / "startup-error.txt",
        ),
        patch("aria.web.lifecycle._init_langfuse"),
        patch("aria.web.lifecycle._init_logging"),
        patch("aria.web.lifecycle._init_storage_mount"),
        patch("aria.web.lifecycle._init_database"),
        patch("aria.web.lifecycle._load_embeddings_sync"),
        patch(
            "aria.web.lifecycle._init_vllm_servers",
            side_effect=RuntimeError("vllm failed"),
        ),
        patch("aria.web.lifecycle._cleanup_on_failure", cleanup),
    ):
        with pytest.raises(SystemExit, match="1"):
            await on_app_startup_handler()

    cleanup.assert_awaited_once()
    assert _state.startup_complete is False
    assert _state.startup_event.is_set() is False
