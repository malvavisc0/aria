from __future__ import annotations

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

        handler = MagicMock()
        handler.stream_events = _stream
        handler.__await__ = lambda self: iter(
            [MagicMock(response=MagicMock(content=None))]
        )
        return handler

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

        output.stream_token.assert_any_await(pipeline._THINKING_OPEN)
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
            pipeline._THINKING_OPEN,
            "thought",
            pipeline._THINKING_CLOSE,
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
