"""Shared fixtures for browser tests.

Redirects all persisted browser content to a temp directory so tests
don't pollute the project's data/browser/ folder.
"""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _browser_content_tmpdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect BROWSER_CONTENT_DIR to a temp folder for every test."""
    browser_tmp = tmp_path / "browser"
    browser_tmp.mkdir()
    monkeypatch.setattr("aria.tools.browser.manager.BROWSER_CONTENT_DIR", browser_tmp)
