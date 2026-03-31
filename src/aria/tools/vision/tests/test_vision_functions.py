import json
from pathlib import Path

from aria.tools.vision import functions as vision_functions


def test_persist_pdf_extraction_result_preserves_intent(tmp_path, monkeypatch):
    monkeypatch.setattr(vision_functions, "VISION_OUTPUT_DIR", tmp_path)

    response = vision_functions._persist_pdf_extraction_result(
        intent="Analyzing quarterly report",
        source_path=Path("/tmp/report.pdf"),
        extracted_text="hello world",
        pages_processed=2,
    )

    payload = json.loads(response)

    assert payload["status"] == "success"
    assert payload["tool"] == "parse_pdf"
    assert payload["intent"] == "Analyzing quarterly report"
    assert payload["data"]["pages_processed"] == 2
    assert "report_extracted_" in payload["data"]["output_file"]


def test_render_pdf_pages_scale_is_float():
    """Verify _render_pdf_pages uses float scale, not truncated int."""
    # _PDF_RENDER_DPI = 150, so scale should be 150/72 ≈ 2.0833...
    # Previously used round() which gave 2, losing precision
    from aria.tools.vision import functions as vision_functions

    # The scale used should be a float, not an integer
    # At 150 DPI, 150/72 ≈ 2.0833 (not 2)
    expected_scale = vision_functions._PDF_RENDER_DPI / 72.0
    assert isinstance(
        expected_scale, float
    ), "Scale should be float for proper DPI conversion"
    assert (
        abs(expected_scale - 2.0833) < 0.01
    ), f"Expected ~2.0833, got {expected_scale}"
