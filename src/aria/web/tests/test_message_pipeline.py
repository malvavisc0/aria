from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from aria.web import message_pipeline as pipeline


class TestStreamAgentResponse:
    """Tests for the simplified _stream_agent_response."""

    @staticmethod
    def _make_handler(*events):
        """Build a mock handler yielding the given events."""

        async def _stream():
            for ev in events:
                yield ev

        _result = SimpleNamespace(response=SimpleNamespace(content=None))

        async def _await_result():
            return _result

        class _MockHandler:
            """Minimal awaitable mock for WorkflowHandler."""

            stream_events = staticmethod(_stream)

            def __await__(self):
                return _await_result().__await__()

        return _MockHandler()

    @staticmethod
    def _make_output():
        output = MagicMock()
        output.stream_token = AsyncMock()
        return output

    @pytest.mark.asyncio
    async def test_streams_text_delta(self) -> None:
        from llama_index.core.agent.workflow import AgentStream

        event = AgentStream(
            delta="hello",
            response="hello",
            current_agent_name="test",
        )
        handler = self._make_handler(event)
        output = self._make_output()

        emitted = await pipeline._stream_agent_response(handler, output)

        assert emitted is True
        output.stream_token.assert_any_await("hello")

    @pytest.mark.asyncio
    async def test_streams_thinking_delta_as_blockquote(self) -> None:
        from llama_index.core.agent.workflow import AgentStream

        event = AgentStream(
            delta="",
            response="",
            current_agent_name="test",
            thinking_delta="pondering",
        )
        handler = self._make_handler(event)
        output = self._make_output()

        emitted = await pipeline._stream_agent_response(handler, output)
        assert emitted is True

        output.stream_token.assert_any_await(pipeline._BLOCKQUOTE_PREFIX)
        output.stream_token.assert_any_await("pondering")

    @pytest.mark.asyncio
    async def test_closes_thinking_block_on_regular_delta(self) -> None:
        from llama_index.core.agent.workflow import AgentStream

        thinking = AgentStream(
            delta="",
            response="",
            current_agent_name="test",
            thinking_delta="thought",
        )
        regular = AgentStream(
            delta="answer",
            response="answer",
            current_agent_name="test",
        )
        handler = self._make_handler(thinking, regular)
        output = self._make_output()

        emitted = await pipeline._stream_agent_response(handler, output)

        assert emitted is True
        calls = [c.args[0] for c in output.stream_token.call_args_list]
        assert calls == [
            pipeline._BLOCKQUOTE_PREFIX,
            "thought",
            pipeline._BLOCKQUOTE_END,
            "answer",
        ]

    @pytest.mark.asyncio
    async def test_agent_output_fallback_when_no_streamed_content(
        self,
    ) -> None:
        from llama_index.core.agent.workflow import AgentOutput
        from llama_index.core.llms import ChatMessage

        event = AgentOutput(
            response=ChatMessage(content="fallback answer"),
            current_agent_name="test",
        )
        handler = self._make_handler(event)
        output = self._make_output()

        emitted = await pipeline._stream_agent_response(handler, output)

        assert emitted is True
        output.stream_token.assert_any_await("fallback answer")


# ---------------------------------------------------------------------------
# _sanitize_memory — repairs broken alternation in the Memory chat store
# ---------------------------------------------------------------------------


class TestSanitizeMemory:
    """Tests for the _sanitize_memory helper."""

    @staticmethod
    def _make_memory(*messages):
        """Build a fake Memory backed by an in-memory list."""

        class _FakeMemory:
            def __init__(self, msgs):
                self._msgs = list(msgs)

            async def aget(self, input=None):
                return list(self._msgs)

            def set(self, messages):
                self._msgs = list(messages)

        return _FakeMemory(messages)

    @pytest.mark.asyncio
    async def test_empty_memory_is_noop(self) -> None:
        from llama_index.core.base.llms.types import ChatMessage, MessageRole

        memory = self._make_memory()
        await pipeline._sanitize_memory(memory)
        assert await memory.aget() == []

    @pytest.mark.asyncio
    async def test_already_alternating_is_unchanged(self) -> None:
        from llama_index.core.base.llms.types import ChatMessage, MessageRole

        msgs = [
            ChatMessage(role=MessageRole.USER, content="hi"),
            ChatMessage(role=MessageRole.ASSISTANT, content="hello"),
        ]
        memory = self._make_memory(*msgs)
        await pipeline._sanitize_memory(memory)
        result = await memory.aget()
        assert len(result) == 2
        assert result[0].content == "hi"
        assert result[1].content == "hello"

    @pytest.mark.asyncio
    async def test_consecutive_user_messages_collapsed(self) -> None:
        from llama_index.core.base.llms.types import ChatMessage, MessageRole

        msgs = [
            ChatMessage(role=MessageRole.USER, content="first"),
            ChatMessage(role=MessageRole.USER, content="second"),
            ChatMessage(role=MessageRole.ASSISTANT, content="reply"),
        ]
        memory = self._make_memory(*msgs)
        await pipeline._sanitize_memory(memory)
        result = await memory.aget()
        assert [m.content for m in result] == ["second", "reply"]

    @pytest.mark.asyncio
    async def test_trailing_user_message_removed(self) -> None:
        """A dangling user message from a failed run is dropped."""
        from llama_index.core.base.llms.types import ChatMessage, MessageRole

        msgs = [
            ChatMessage(role=MessageRole.USER, content="q"),
            ChatMessage(role=MessageRole.ASSISTANT, content="a"),
            ChatMessage(role=MessageRole.USER, content="unanswered"),
        ]
        memory = self._make_memory(*msgs)
        await pipeline._sanitize_memory(memory)
        result = await memory.aget()
        assert [m.content for m in result] == ["q", "a"]


# ---------------------------------------------------------------------------
# _rollback_memory — removes dangling user message after failure
# ---------------------------------------------------------------------------


class TestRollbackMemory:
    """Tests for the _rollback_memory helper."""

    @staticmethod
    def _make_memory(*messages):
        class _FakeMemory:
            def __init__(self, msgs):
                self._msgs = list(msgs)

            async def aget(self, input=None):
                return list(self._msgs)

            def set(self, messages):
                self._msgs = list(messages)

        return _FakeMemory(messages)

    @pytest.mark.asyncio
    async def test_none_memory_is_noop(self) -> None:
        # Should not raise
        await pipeline._rollback_memory(None)

    @pytest.mark.asyncio
    async def test_empty_memory_is_noop(self) -> None:
        memory = self._make_memory()
        await pipeline._rollback_memory(memory)
        assert await memory.aget() == []

    @pytest.mark.asyncio
    async def test_removes_trailing_user_message(self) -> None:
        from llama_index.core.base.llms.types import ChatMessage, MessageRole

        msgs = [
            ChatMessage(role=MessageRole.USER, content="q"),
            ChatMessage(role=MessageRole.ASSISTANT, content="a"),
            ChatMessage(role=MessageRole.USER, content="dangling"),
        ]
        memory = self._make_memory(*msgs)
        await pipeline._rollback_memory(memory)
        result = await memory.aget()
        assert [m.content for m in result] == ["q", "a"]

    @pytest.mark.asyncio
    async def test_leaves_valid_alternation_unchanged(self) -> None:
        from llama_index.core.base.llms.types import ChatMessage, MessageRole

        msgs = [
            ChatMessage(role=MessageRole.USER, content="q"),
            ChatMessage(role=MessageRole.ASSISTANT, content="a"),
        ]
        memory = self._make_memory(*msgs)
        await pipeline._rollback_memory(memory)
        result = await memory.aget()
        assert len(result) == 2
