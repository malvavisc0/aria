from __future__ import annotations

import pytest

from aria.web import message_pipeline as pipeline
from aria.web.message_pipeline import ThinkingBlockDetector


def test_extract_response_text_from_content() -> None:
    class _Response:
        content = "hello"

    assert pipeline._extract_response_text(_Response()) == "hello"


def test_extract_response_text_from_blocks() -> None:
    class _Block:
        def __init__(self, text: str) -> None:
            self.text = text

    class _Response:
        content = None
        blocks = [_Block("one"), _Block("two")]

    assert pipeline._extract_response_text(_Response()) == "one\ntwo"


def test_final_response_is_not_suppressed_after_tool_calls() -> None:
    stream_buffer: list[str] = []
    handler_result = type(
        "HandlerResult",
        (),
        {"response": type("Response", (), {"content": "final answer"})()},
    )()

    content = "".join(stream_buffer).strip() or pipeline._extract_response_text(
        getattr(handler_result, "response", None)
    )

    assert content == "final answer"


class TestThinkingBlockDetectorBasic:
    """Basic open/close detection in single deltas."""

    def test_initial_state_is_not_in_thinking(self) -> None:
        detector = ThinkingBlockDetector()
        assert detector.in_thinking is False

    def test_plain_text_does_not_enter_thinking(self) -> None:
        detector = ThinkingBlockDetector()
        entered, exited = detector.process_delta("hello world")
        assert entered is False
        assert exited is False
        assert detector.in_thinking is False

    def test_open_think_tag_enters_thinking(self) -> None:
        detector = ThinkingBlockDetector()
        entered, exited = detector.process_delta("<think>")
        assert entered is True
        assert exited is False
        assert detector.in_thinking is True

    def test_close_think_tag_exits_thinking(self) -> None:
        detector = ThinkingBlockDetector()
        detector.process_delta("<think>")
        entered, exited = detector.process_delta("</think>")
        assert entered is False
        assert exited is True
        assert detector.in_thinking is False

    def test_emoji_opens_and_closes_thinking(self) -> None:
        detector = ThinkingBlockDetector()
        entered, exited = detector.process_delta("💭")
        assert entered is True
        assert detector.in_thinking is True

        entered, exited = detector.process_delta("💭")
        assert exited is True
        assert detector.in_thinking is False


class TestThinkingBlockDetectorAllPatterns:
    """All open/close patterns are recognized."""

    @pytest.mark.parametrize(
        "open_tag,close_tag",
        [
            ("<think>", "</think>"),
            ("<reasoning", "</reasoning>"),
            ("<reflection", "</reflection>"),
            ("💭", "💭"),
        ],
    )
    def test_pattern_pair(self, open_tag: str, close_tag: str) -> None:
        detector = ThinkingBlockDetector()
        entered, _ = detector.process_delta(open_tag)
        assert entered is True
        assert detector.in_thinking is True

        _, exited = detector.process_delta(close_tag)
        assert exited is True
        assert detector.in_thinking is False

    def test_case_insensitive_think_tag(self) -> None:
        detector = ThinkingBlockDetector()
        entered, _ = detector.process_delta("<THINK>")
        assert entered is True
        assert detector.in_thinking is True

        _, exited = detector.process_delta("</THINK>")
        assert exited is True
        assert detector.in_thinking is False

    def test_case_insensitive_reasoning_tag(self) -> None:
        detector = ThinkingBlockDetector()
        entered, _ = detector.process_delta("<Reasoning")
        assert entered is True

        _, exited = detector.process_delta("</Reasoning>")
        assert exited is True


class TestThinkingBlockDetectorSplitTags:
    """Tags split across multiple deltas are detected."""

    def test_think_tag_split_across_two_deltas(self) -> None:
        detector = ThinkingBlockDetector()
        entered, _ = detector.process_delta("<thin")
        # Not yet detected — partial tag
        assert entered is False
        assert detector.in_thinking is False

        entered, _ = detector.process_delta("k>")
        # Now the pending buffer contains "<think>" and triggers
        assert entered is True
        assert detector.in_thinking is True

    def test_close_tag_split_across_deltas(self) -> None:
        detector = ThinkingBlockDetector()
        detector.process_delta("<think>")
        assert detector.in_thinking is True

        _, exited = detector.process_delta("</thi")
        assert exited is False
        assert detector.in_thinking is True

        _, exited = detector.process_delta("nk>")
        assert exited is True
        assert detector.in_thinking is False

    def test_tag_split_into_single_characters(self) -> None:
        detector = ThinkingBlockDetector()
        for char in "<think":
            entered, _ = detector.process_delta(char)
            assert entered is False

        entered, _ = detector.process_delta(">")
        assert entered is True
        assert detector.in_thinking is True


class TestThinkingBlockDetectorMultipleBlocks:
    """Multiple thinking blocks in sequence."""

    def test_two_consecutive_thinking_blocks(self) -> None:
        detector = ThinkingBlockDetector()

        entered, _ = detector.process_delta("<think>")
        assert entered is True

        _, exited = detector.process_delta("</think>")
        assert exited is True
        assert detector.in_thinking is False

        # Second block
        entered, _ = detector.process_delta("<think>")
        assert entered is True
        assert detector.in_thinking is True

        _, exited = detector.process_delta("</think>")
        assert exited is True
        assert detector.in_thinking is False


class TestThinkingBlockDetectorBufferBounding:
    """Pending buffer does not grow unbounded."""

    def test_buffer_truncated_after_50_chars(self) -> None:
        detector = ThinkingBlockDetector()
        # Feed 60 plain characters — no tag detected
        detector.process_delta("x" * 60)
        # Internal buffer should have been truncated to last 20 chars
        assert len(detector._pending) == 20

    def test_buffer_cleared_on_match(self) -> None:
        detector = ThinkingBlockDetector()
        detector.process_delta("<think>")
        # After a match, the pending buffer is cleared
        assert detector._pending == ""

    def test_tag_still_detected_after_buffer_truncation(self) -> None:
        """A tag arriving after a large non-matching payload is still found."""
        detector = ThinkingBlockDetector()
        # Push nonsense past the truncation boundary
        detector.process_delta("a" * 60)
        assert len(detector._pending) == 20

        # Now send a proper tag — should be detected fresh
        entered, _ = detector.process_delta("<think>")
        assert entered is True
