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


# ---------------------------------------------------------------------------
# _describe_image — vision API call for image description
# ---------------------------------------------------------------------------


class TestDescribeImage:
    """Tests for the _describe_image helper."""

    @staticmethod
    def _patch_chat_config(monkeypatch):
        """Set ChatConfig attributes for tests (bypasses _Lazy descriptors).

        _Lazy is a non-data descriptor that caches its value internally.
        We patch the _value attribute directly to avoid triggering the
        factory (which requires env vars that aren't set in tests).
        """
        from aria.config.models import Chat as ChatConfigCls

        monkeypatch.setattr(
            ChatConfigCls.__dict__["api_url"], "_value", "http://test:9090/v1"
        )
        monkeypatch.setattr(ChatConfigCls.__dict__["model"], "_value", "test-model")
        monkeypatch.setattr(pipeline.VllmConfig, "api_key", "sk-test")

    @staticmethod
    def _make_mock_httpx(mock_client):
        """Build a mock httpx module with AsyncClient returning mock_client."""
        mock_httpx = MagicMock()
        mock_httpx.AsyncClient.return_value = mock_client
        return mock_httpx

    @pytest.mark.asyncio
    async def test_returns_description_on_success(self, monkeypatch) -> None:
        self._patch_chat_config(monkeypatch)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "A screenshot of a dashboard."}}]
        }

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        monkeypatch.setattr(pipeline, "httpx", self._make_mock_httpx(mock_client))

        result = await pipeline._describe_image("image/png", "base64data", "test.png")
        assert result == "A screenshot of a dashboard."

    @pytest.mark.asyncio
    async def test_raises_on_http_error(self, monkeypatch) -> None:
        import httpx as real_httpx

        self._patch_chat_config(monkeypatch)

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = real_httpx.HTTPStatusError(
            "Bad request",
            request=MagicMock(),
            response=MagicMock(status_code=400),
        )

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        monkeypatch.setattr(pipeline, "httpx", self._make_mock_httpx(mock_client))

        with pytest.raises(real_httpx.HTTPStatusError):
            await pipeline._describe_image("image/jpeg", "base64data", "bad.jpg")

    @pytest.mark.asyncio
    async def test_sends_correct_payload(self, monkeypatch) -> None:
        self._patch_chat_config(monkeypatch)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "desc"}}]
        }

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        monkeypatch.setattr(pipeline, "httpx", self._make_mock_httpx(mock_client))

        await pipeline._describe_image("image/png", "abc123", "img.png")

        call_kwargs = mock_client.post.call_args
        url = call_kwargs[0][0]
        assert url == "http://test:9090/v1/chat/completions"

        headers = call_kwargs[1]["headers"]
        assert headers["Authorization"] == "Bearer sk-test"

        body = call_kwargs[1]["json"]
        assert body["model"] == "test-model"
        assert body["max_tokens"] == 256
        content = body["messages"][0]["content"]
        assert content[1]["image_url"]["url"] == "data:image/png;base64,abc123"


# ---------------------------------------------------------------------------
# _handle_message — vision integration in prompt assembly
# ---------------------------------------------------------------------------


class TestHandleMessageVision:
    """Tests for _handle_message vision image processing."""

    @pytest.mark.asyncio
    async def test_appends_image_descriptions_when_vision_enabled(
        self, monkeypatch
    ) -> None:
        monkeypatch.setattr(pipeline.VllmConfig, "vision_enabled", True)
        monkeypatch.setattr(
            pipeline,
            "extract_image_data",
            lambda msg: [{"mime_type": "image/png", "base64": "b64", "name": "a.png"}],
        )
        monkeypatch.setattr(pipeline, "extract_file_paths", lambda msg: [])
        monkeypatch.setattr(
            pipeline,
            "_describe_image",
            AsyncMock(return_value="A red circle on white background."),
        )

        message = SimpleNamespace(
            content="What is this?",
            command=None,
            thread_id="t1",
            elements=[],
        )

        result = await pipeline._handle_message(message)

        assert "[Attached images]:" in result
        assert "[Image 1 (a.png)]: A red circle on white background." in result

    @pytest.mark.asyncio
    async def test_appends_disabled_notice_when_vision_off(self, monkeypatch) -> None:
        monkeypatch.setattr(pipeline.VllmConfig, "vision_enabled", False)
        monkeypatch.setattr(
            pipeline,
            "extract_image_data",
            lambda msg: [
                {"mime_type": "image/png", "base64": "b64", "name": "pic.png"}
            ],
        )
        monkeypatch.setattr(pipeline, "extract_file_paths", lambda msg: [])

        message = SimpleNamespace(
            content="Look at this",
            command=None,
            thread_id="t1",
            elements=[],
        )

        result = await pipeline._handle_message(message)

        assert "[Attached images]:" in result
        assert "vision disabled" in result
        assert "ARIA_VLLM_VISION_ENABLED" in result

    @pytest.mark.asyncio
    async def test_no_image_block_when_no_images(self, monkeypatch) -> None:
        monkeypatch.setattr(pipeline, "extract_image_data", lambda msg: [])
        monkeypatch.setattr(pipeline, "extract_file_paths", lambda msg: [])

        message = SimpleNamespace(
            content="Just text",
            command=None,
            thread_id="t1",
            elements=[],
        )

        result = await pipeline._handle_message(message)

        assert "[Attached images]:" not in result
        assert result.startswith("[Thread ID: t1]")

    @pytest.mark.asyncio
    async def test_mixed_files_and_images(self, monkeypatch) -> None:
        monkeypatch.setattr(pipeline.VllmConfig, "vision_enabled", True)
        monkeypatch.setattr(
            pipeline,
            "extract_file_paths",
            lambda msg: ["/tmp/report.pdf"],
        )
        monkeypatch.setattr(
            pipeline,
            "convert_documents_to_markdown",
            lambda paths: [
                {
                    "original_path": "/tmp/report.pdf",
                    "markdown_path": "/workspace/uploads/report.md",
                    "name": "report.pdf",
                    "lines": 42,
                    "chars": 1200,
                    "error": None,
                }
            ],
        )
        monkeypatch.setattr(
            pipeline,
            "extract_image_data",
            lambda msg: [
                {
                    "mime_type": "image/jpeg",
                    "base64": "b64",
                    "name": "chart.jpg",
                }
            ],
        )
        monkeypatch.setattr(
            pipeline,
            "_describe_image",
            AsyncMock(return_value="A bar chart."),
        )

        message = SimpleNamespace(
            content="Analyze these",
            command=None,
            thread_id="t2",
            elements=[],
        )

        result = await pipeline._handle_message(message)

        assert "[Uploaded files]:" in result
        assert "report.pdf" in result
        assert "report.md" in result
        assert "42 lines" in result
        assert "[Attached images]:" in result
        assert "A bar chart." in result

    @pytest.mark.asyncio
    async def test_fallback_when_vision_api_fails(self, monkeypatch) -> None:
        monkeypatch.setattr(pipeline.VllmConfig, "vision_enabled", True)
        monkeypatch.setattr(
            pipeline,
            "extract_image_data",
            lambda msg: [
                {"mime_type": "image/png", "base64": "b64", "name": "fail.png"}
            ],
        )
        monkeypatch.setattr(pipeline, "extract_file_paths", lambda msg: [])
        monkeypatch.setattr(
            pipeline,
            "_describe_image",
            AsyncMock(side_effect=Exception("connection refused")),
        )

        message = SimpleNamespace(
            content="What's this?",
            command=None,
            thread_id="t3",
            elements=[],
        )

        result = await pipeline._handle_message(message)

        assert "[Attached images]:" in result
        assert "<description unavailable>" in result


class TestEditDetection:
    """Tests for metadata-based edit detection."""

    @pytest.mark.asyncio
    async def test_mark_message_processed(self, monkeypatch) -> None:
        """_mark_message_processed persists _aria_processed in metadata."""
        created_steps = []
        mock_data_layer = MagicMock()
        mock_data_layer.create_step = AsyncMock(
            side_effect=lambda d: created_steps.append(d)
        )
        monkeypatch.setattr(
            pipeline,
            "get_data_layer_handler",
            lambda: mock_data_layer,
        )

        message = MagicMock()
        message.id = "msg-1"
        message.metadata = {"location": "http://localhost"}
        message.to_dict.return_value = {
            "id": "msg-1",
            "type": "user_message",
            "output": "Hello",
            "metadata": {"location": "http://localhost"},
        }

        await pipeline._mark_message_processed(message)

        assert len(created_steps) == 1
        meta = created_steps[0]["metadata"]
        assert meta["_aria_processed"] is True
        assert meta["location"] == "http://localhost"

    @pytest.mark.asyncio
    async def test_edit_detected_when_processed_flag_set(self, monkeypatch) -> None:
        """on_message_handler detects edit via _aria_processed metadata."""
        # Track whether _reset_memory_for_edit was called
        reset_called = []
        mock_memory = MagicMock()
        mock_memory.session_id = "thread-1"
        mock_memory.aget = AsyncMock(return_value=[])
        mock_memory.set = MagicMock()

        async def mock_reset(thread_id):
            reset_called.append(thread_id)
            return mock_memory

        monkeypatch.setattr(pipeline, "_reset_memory_for_edit", mock_reset)
        monkeypatch.setattr(pipeline, "_mark_message_processed", AsyncMock())

        # Mock all the dependencies — use object.__setattr__ to bypass
        # Pydantic's frozen/strict __setattr__ on AppState.
        mock_workflow = MagicMock()
        object.__setattr__(pipeline._state, "agents_workflow", mock_workflow)
        object.__setattr__(
            pipeline._state,
            "validate_initialized",
            lambda: None,
        )

        # Mock _handle_message
        monkeypatch.setattr(
            pipeline,
            "_handle_message",
            AsyncMock(return_value="prompt"),
        )

        # Mock user_session
        mock_session = {"memory": mock_memory}
        monkeypatch.setattr(
            pipeline.cl,
            "user_session",
            SimpleNamespace(
                get=lambda k: mock_session.get(k),
                set=lambda k, v: mock_session.__setitem__(k, v),
            ),
        )

        # Mock the workflow run + streaming
        monkeypatch.setattr(
            pipeline,
            "_stream_agent_response",
            AsyncMock(return_value=True),
        )

        mock_handler = MagicMock()
        pipeline._state.agents_workflow.run = MagicMock(return_value=mock_handler)

        # Mock cl.Message for output
        mock_output = MagicMock()
        mock_output.send = AsyncMock()
        mock_output.remove = AsyncMock()
        monkeypatch.setattr(
            pipeline.cl,
            "Message",
            lambda **kw: mock_output,
        )

        # Create message WITH _aria_processed (simulating edit)
        message = SimpleNamespace(
            id="msg-1",
            content="Edited hello",
            command=None,
            thread_id="thread-1",
            elements=[],
            metadata={"_aria_processed": True},
        )

        await pipeline.on_message_handler(message)

        assert reset_called == ["thread-1"]

    @pytest.mark.asyncio
    async def test_no_reset_on_first_message(self, monkeypatch) -> None:
        """on_message_handler does NOT reset memory on first message."""
        reset_called = []

        async def mock_reset(thread_id):
            reset_called.append(thread_id)
            return MagicMock()

        monkeypatch.setattr(pipeline, "_reset_memory_for_edit", mock_reset)
        monkeypatch.setattr(pipeline, "_mark_message_processed", AsyncMock())

        mock_workflow = MagicMock()
        object.__setattr__(pipeline._state, "agents_workflow", mock_workflow)
        object.__setattr__(pipeline._state, "validate_initialized", lambda: None)
        monkeypatch.setattr(
            pipeline,
            "_handle_message",
            AsyncMock(return_value="prompt"),
        )

        mock_memory = MagicMock()
        mock_memory.session_id = "thread-1"
        mock_memory.aget = AsyncMock(return_value=[])
        mock_memory.set = MagicMock()
        mock_session = {"memory": mock_memory}
        monkeypatch.setattr(
            pipeline.cl,
            "user_session",
            SimpleNamespace(
                get=lambda k: mock_session.get(k),
                set=lambda k, v: mock_session.__setitem__(k, v),
            ),
        )

        monkeypatch.setattr(
            pipeline,
            "_stream_agent_response",
            AsyncMock(return_value=True),
        )

        mock_handler = MagicMock()
        pipeline._state.agents_workflow.run = MagicMock(return_value=mock_handler)

        mock_output = MagicMock()
        mock_output.send = AsyncMock()
        mock_output.remove = AsyncMock()
        monkeypatch.setattr(
            pipeline.cl,
            "Message",
            lambda **kw: mock_output,
        )

        # First message — no _aria_processed in metadata
        message = SimpleNamespace(
            id="msg-1",
            content="Hello",
            command=None,
            thread_id="thread-1",
            elements=[],
            metadata={},
        )

        await pipeline.on_message_handler(message)

        assert reset_called == []

    @pytest.mark.asyncio
    async def test_reset_memory_for_edit(self, monkeypatch) -> None:
        """_reset_memory_for_edit rebuilds memory from DB."""
        mock_vector_db = MagicMock()
        monkeypatch.setattr(pipeline._state, "vector_db", mock_vector_db)

        mock_memory = MagicMock()
        monkeypatch.setattr(pipeline, "create_memory", lambda tid: mock_memory)

        mock_thread = {
            "id": "thread-1",
            "name": "Test",
            "steps": [],
        }
        mock_data_layer = MagicMock()
        mock_data_layer.get_thread = AsyncMock(return_value=mock_thread)
        monkeypatch.setattr(
            pipeline,
            "get_data_layer_handler",
            lambda: mock_data_layer,
        )

        restored_memory = MagicMock()
        monkeypatch.setattr(
            pipeline,
            "restore_chat_history",
            AsyncMock(return_value=restored_memory),
        )

        result = await pipeline._reset_memory_for_edit("thread-1")

        mock_vector_db.delete_collection.assert_called_once_with("thread-1")
        mock_data_layer.get_thread.assert_awaited_once_with("thread-1")
        assert result is restored_memory
