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
        async def aput_messages(self, messages):
            captured_messages.extend(messages)

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


@pytest.mark.asyncio
async def test_restore_chat_history_includes_child_assistant_messages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Assistant messages with parentId set must still be restored.

    get_thread() returns the raw parent-child tree where assistant
    messages are children of user messages (parentId != None).
    """
    captured_messages = []

    class _FakeMemory:
        async def aput_messages(self, messages):
            captured_messages.extend(messages)

    monkeypatch.setattr(
        session_module, "create_memory", lambda thread_id: _FakeMemory()
    )

    thread = {
        "id": "thread-child",
        "name": "Child test",
        "steps": [
            {
                "id": "u1",
                "parentId": None,
                "createdAt": "2026-03-27T10:00:00Z",
                "type": "user_message",
                "output": "Hello",
            },
            {
                "id": "a1",
                "parentId": "u1",
                "createdAt": "2026-03-27T10:00:01Z",
                "type": "assistant_message",
                "output": "Hi there!",
            },
            {
                "id": "u2",
                "parentId": None,
                "createdAt": "2026-03-27T10:00:02Z",
                "type": "user_message",
                "output": "How are you?",
            },
            {
                "id": "a2",
                "parentId": "u2",
                "createdAt": "2026-03-27T10:00:03Z",
                "type": "assistant_message",
                "output": "I'm great!",
            },
        ],
    }

    await session_module.restore_chat_history(thread)

    assert [m.content for m in captured_messages] == [
        "Hello",
        "Hi there!",
        "How are you?",
        "I'm great!",
    ]


@pytest.mark.asyncio
async def test_restore_chat_history_sanitises_consecutive_same_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Consecutive messages of the same role should collapse to the last."""
    captured_messages = []

    class _FakeMemory:
        async def aput_messages(self, messages):
            captured_messages.extend(messages)

    monkeypatch.setattr(
        session_module, "create_memory", lambda thread_id: _FakeMemory()
    )

    thread = {
        "id": "thread-dup",
        "name": "Dup test",
        "steps": [
            {
                "id": "u1",
                "parentId": None,
                "createdAt": "2026-03-27T10:00:00Z",
                "type": "user_message",
                "output": "first user",
            },
            {
                "id": "u2",
                "parentId": None,
                "createdAt": "2026-03-27T10:00:01Z",
                "type": "user_message",
                "output": "second user",
            },
            {
                "id": "a1",
                "parentId": "u2",
                "createdAt": "2026-03-27T10:00:02Z",
                "type": "assistant_message",
                "output": "reply",
            },
        ],
    }

    await session_module.restore_chat_history(thread)

    # The first user message is dropped (consecutive duplicate → keep last).
    assert [m.content for m in captured_messages] == [
        "second user",
        "reply",
    ]


@pytest.mark.asyncio
async def test_restore_chat_history_drops_trailing_user_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A trailing user message (no assistant reply) must be dropped."""
    captured_messages = []

    class _FakeMemory:
        async def aput_messages(self, messages):
            captured_messages.extend(messages)

    monkeypatch.setattr(
        session_module, "create_memory", lambda thread_id: _FakeMemory()
    )

    thread = {
        "id": "thread-trailing",
        "name": "Trailing test",
        "steps": [
            {
                "id": "u1",
                "parentId": None,
                "createdAt": "2026-03-27T10:00:00Z",
                "type": "user_message",
                "output": "Hello",
            },
            {
                "id": "a1",
                "parentId": "u1",
                "createdAt": "2026-03-27T10:00:01Z",
                "type": "assistant_message",
                "output": "Hi!",
            },
            {
                "id": "u2",
                "parentId": None,
                "createdAt": "2026-03-27T10:00:02Z",
                "type": "user_message",
                "output": "unanswered",
            },
        ],
    }

    await session_module.restore_chat_history(thread)

    # Trailing user message is dropped to maintain alternation.
    assert [m.content for m in captured_messages] == [
        "Hello",
        "Hi!",
    ]


def test_sanitize_chat_history_empty() -> None:
    assert session_module._sanitize_chat_history([]) == []


def test_sanitize_chat_history_already_alternating() -> None:
    from llama_index.core.base.llms.types import ChatMessage, MessageRole

    msgs = [
        ChatMessage(role=MessageRole.USER, content="a"),
        ChatMessage(role=MessageRole.ASSISTANT, content="b"),
        ChatMessage(role=MessageRole.USER, content="c"),
        ChatMessage(role=MessageRole.ASSISTANT, content="d"),
    ]
    result = session_module._sanitize_chat_history(msgs)
    assert [m.content for m in result] == ["a", "b", "c", "d"]


def test_sanitize_chat_history_leading_assistant_dropped() -> None:
    from llama_index.core.base.llms.types import ChatMessage, MessageRole

    msgs = [
        ChatMessage(role=MessageRole.ASSISTANT, content="orphan"),
        ChatMessage(role=MessageRole.USER, content="a"),
        ChatMessage(role=MessageRole.ASSISTANT, content="b"),
    ]
    result = session_module._sanitize_chat_history(msgs)
    assert [m.content for m in result] == ["a", "b"]
