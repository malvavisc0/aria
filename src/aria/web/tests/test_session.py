from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from aria.web import session as session_module


def test_extract_file_paths_uses_unique_destination_names(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir()
    monkeypatch.setattr(session_module.UploadsConfig, "path", uploads_dir)

    src_a = tmp_path / "source-a.txt"
    src_b = tmp_path / "source-b.txt"
    src_a.write_text("first", encoding="utf-8")
    src_b.write_text("second", encoding="utf-8")

    message = SimpleNamespace(
        thread_id="thread-123",
        elements=[
            SimpleNamespace(path=str(src_a), name="report.txt"),
            SimpleNamespace(path=str(src_b), name="report.txt"),
        ],
    )

    paths = session_module.extract_file_paths(message)

    assert len(paths) == 2
    assert paths[0] != paths[1]
    assert Path(paths[0]).read_text(encoding="utf-8") == "first"
    assert Path(paths[1]).read_text(encoding="utf-8") == "second"


@pytest.mark.asyncio
async def test_restore_chat_history_sorts_root_messages_chronologically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_messages = []

    class _FakeMemory:
        async def aset(self, history):
            captured_messages.extend(history)

    monkeypatch.setattr(
        session_module, "create_memory", lambda thread_id: _FakeMemory()
    )

    thread = {
        "id": "thread-1",
        "name": "Example",
        "steps": [
            {
                "id": "2",
                "parentId": None,
                "createdAt": "2026-03-27T10:00:01Z",
                "type": "assistant_message",
                "output": "second",
            },
            {
                "id": "1",
                "parentId": None,
                "createdAt": "2026-03-27T10:00:00Z",
                "type": "user_message",
                "output": "first",
            },
        ],
    }

    await session_module.restore_chat_history(thread)

    assert [message.content for message in captured_messages] == [
        "first",
        "second",
    ]
