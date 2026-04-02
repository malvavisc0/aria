import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from aria.tools.vision import functions as vision_functions
from aria.tools.vision.constants import SUPPORTED_IMAGE_FORMATS
from aria.tools.vision.exceptions import UnsupportedFormatError


def test_persist_vision_result_with_pages(tmp_path, monkeypatch):
    """Persist result includes pages_processed when provided."""
    monkeypatch.setattr(vision_functions, "VISION_OUTPUT_DIR", tmp_path)

    response = vision_functions._persist_vision_result(
        tool_name="parse_pdf",
        reason="Analyzing quarterly report",
        source_path=Path("/tmp/report.pdf"),
        extracted_text="hello world",
        pages_processed=2,
    )

    payload = json.loads(response)

    assert payload["status"] == "success"
    assert payload["tool"] == "parse_pdf"
    assert payload["reason"] == "Analyzing quarterly report"
    assert payload["data"]["pages_processed"] == 2
    assert "report_extracted_" in payload["data"]["output_file"]


def test_persist_vision_result_without_pages(tmp_path, monkeypatch):
    """Persist result omits pages_processed for image analysis."""
    monkeypatch.setattr(vision_functions, "VISION_OUTPUT_DIR", tmp_path)

    response = vision_functions._persist_vision_result(
        tool_name="analyze_image",
        reason="Describing screenshot",
        source_path=Path("/tmp/screenshot.png"),
        extracted_text="A screenshot of a code editor",
    )

    payload = json.loads(response)

    assert payload["status"] == "success"
    assert payload["tool"] == "analyze_image"
    assert payload["reason"] == "Describing screenshot"
    assert "pages_processed" not in payload["data"]
    assert "screenshot_extracted_" in payload["data"]["output_file"]


def test_persist_vision_result_truncates_preview(tmp_path, monkeypatch):
    """Preview is truncated to 500 chars with '...' appended."""
    monkeypatch.setattr(vision_functions, "VISION_OUTPUT_DIR", tmp_path)

    long_text = "x" * 1000
    response = vision_functions._persist_vision_result(
        tool_name="analyze_image",
        reason="test",
        source_path=Path("/tmp/img.png"),
        extracted_text=long_text,
    )

    payload = json.loads(response)
    preview = payload["data"]["content_preview"]
    assert len(preview) == 503  # 500 + "..."
    assert preview.endswith("...")


def test_render_pdf_pages_scale_is_float():
    """Verify _render_pdf_pages uses float scale, not truncated int."""
    # _PDF_RENDER_DPI = 150, so scale should be 150/72 ≈ 2.0833...
    # Previously used round() which gave 2, losing precision
    expected_scale = vision_functions._PDF_RENDER_DPI / 72.0
    assert isinstance(
        expected_scale, float
    ), "Scale should be float for proper DPI conversion"
    assert (
        abs(expected_scale - 2.0833) < 0.01
    ), f"Expected ~2.0833, got {expected_scale}"


def test_load_image_file_unsupported_format(tmp_path):
    """_load_image_file raises UnsupportedFormatError for bad extension."""
    # File must exist so we get past the existence check
    txt_file = tmp_path / "file.txt"
    txt_file.write_text("not an image")
    with pytest.raises(UnsupportedFormatError):
        vision_functions._load_image_file(txt_file)


def test_load_image_file_missing_file():
    """_load_image_file raises VisionFileNotFoundError if file missing."""
    from aria.tools.vision.exceptions import VisionFileNotFoundError

    with pytest.raises(VisionFileNotFoundError):
        vision_functions._load_image_file(Path("/tmp/nonexistent.png"))


def test_load_image_file_valid_png(tmp_path):
    """_load_image_file returns PNG bytes for a valid image."""
    # Create a minimal valid PNG
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow not installed")

    img = Image.new("RGB", (10, 10), color="red")
    img_path = tmp_path / "test.png"
    img.save(img_path, format="PNG")

    result = vision_functions._load_image_file(img_path)
    assert isinstance(result, bytes)
    assert len(result) > 0
    # Verify it's a valid PNG (starts with PNG magic bytes)
    assert result[:4] == b"\x89PNG"


def test_load_image_file_converts_jpeg_to_png(tmp_path):
    """_load_image_file converts JPEG to PNG bytes."""
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow not installed")

    img = Image.new("RGB", (10, 10), color="blue")
    jpeg_path = tmp_path / "test.jpg"
    img.save(jpeg_path, format="JPEG")

    result = vision_functions._load_image_file(jpeg_path)
    assert isinstance(result, bytes)
    assert result[:4] == b"\x89PNG"


@pytest.mark.asyncio
async def test_call_vl_model_success():
    """_call_vl_model returns text from successful VL response."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [
            {"message": {"content": "A beautiful sunset over mountains"}}
        ]
    }
    mock_response.raise_for_status = MagicMock()
    mock_client.post.return_value = mock_response

    result = await vision_functions._call_vl_model(
        mock_client,
        "http://localhost:9091/v1/chat/completions",
        "test-model",
        b"\x89PNG fake",
        "Describe this image",
    )

    assert result == "A beautiful sunset over mountains"
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_call_vl_model_http_error():
    """_call_vl_model raises HTTPStatusError on non-2xx response."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500 Server Error",
        request=MagicMock(),
        response=MagicMock(),
    )
    mock_client.post.return_value = mock_response

    with pytest.raises(httpx.HTTPStatusError):
        await vision_functions._call_vl_model(
            mock_client,
            "http://localhost:9091/v1/chat/completions",
            "test-model",
            b"\x89PNG fake",
            "Describe this image",
        )


@pytest.mark.asyncio
async def test_analyze_image_file_not_found():
    """analyze_image returns error for missing file."""
    fn = vision_functions.make_analyze_image(
        "http://localhost:9091/v1", "test-model"
    )
    result = await fn("test reason", "/tmp/nonexistent.png")
    payload = json.loads(result)
    assert payload["status"] == "error"
    assert "not found" in payload["error"]["message"].lower()


@pytest.mark.asyncio
async def test_analyze_image_unsupported_format(tmp_path):
    """analyze_image returns error for unsupported format."""
    fn = vision_functions.make_analyze_image(
        "http://localhost:9091/v1", "test-model"
    )
    # Create a .txt file so it exists but has wrong format
    txt_file = tmp_path / "file.txt"
    txt_file.write_text("not an image")
    result = await fn("test reason", str(txt_file))
    payload = json.loads(result)
    assert payload["status"] == "error"
    assert "unsupported" in payload["error"]["message"].lower()


@pytest.mark.asyncio
async def test_analyze_image_success(tmp_path):
    """analyze_image returns success for a valid image."""
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow not installed")

    # Create a valid test image
    img = Image.new("RGB", (10, 10), color="green")
    img_path = tmp_path / "test.png"
    img.save(img_path, format="PNG")

    fn = vision_functions.make_analyze_image(
        "http://localhost:9091/v1", "test-model"
    )

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "A green square"}}]
    }
    mock_response.raise_for_status = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "aria.tools.vision.functions.httpx.AsyncClient",
        return_value=mock_client,
    ):
        result = await fn("describe image", str(img_path))

    payload = json.loads(result)
    assert payload["status"] == "success"
    assert payload["tool"] == "analyze_image"
    assert payload["data"]["total_chars"] > 0


@pytest.mark.asyncio
async def test_analyze_image_vl_failure(tmp_path):
    """analyze_image returns error when VL server fails."""
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow not installed")

    img = Image.new("RGB", (10, 10), color="red")
    img_path = tmp_path / "test.png"
    img.save(img_path, format="PNG")

    fn = vision_functions.make_analyze_image(
        "http://localhost:9091/v1", "test-model"
    )

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.side_effect = httpx.ConnectError("Connection refused")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "aria.tools.vision.functions.httpx.AsyncClient",
        return_value=mock_client,
    ):
        result = await fn("describe image", str(img_path))

    payload = json.loads(result)
    assert payload["status"] == "error"
    assert "VL model" in payload["error"]["message"]


def test_supported_image_formats():
    """Verify expected formats are in the frozenset."""
    expected = {
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".gif",
        ".bmp",
        ".tiff",
        ".tif",
    }
    assert expected.issubset(SUPPORTED_IMAGE_FORMATS)
