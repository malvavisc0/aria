from __future__ import annotations

from aria.web import message_pipeline as pipeline


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

    content = "".join(
        stream_buffer
    ).strip() or pipeline._extract_response_text(
        getattr(handler_result, "response", None)
    )

    assert content == "final answer"
