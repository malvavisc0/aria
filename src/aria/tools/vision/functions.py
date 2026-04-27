"""Document and image analysis tools for the vision-language model.

Provides :func:`make_parse_pdf` and :func:`make_analyze_image`, which
return async closures bound to a VL server URL and model name.

PDF analysis renders each page to PNG via ``pypdfium2``, base64-encodes
the PNG bytes, and sends them directly to the VL server using the OpenAI
multimodal chat format over ``httpx``.  No LlamaIndex LLM wrapper is
involved — the HTTP call is made directly.

Image analysis loads an image file, validates it, converts to PNG via
Pillow, and sends it to the VL server using the same multimodal format.

If the VL model fails (e.g., due to multimodal input not being supported),
the PDF tool falls back to text-based extraction using pypdfium2's text
extraction capabilities.
"""

import base64
import io
from datetime import datetime
from pathlib import Path
from typing import Callable

import httpx
from loguru import logger

from aria.tools import (
    get_function_name,
    tool_error_response,
    tool_success_response,
)
from aria.tools.decorators import log_tool_call
from aria.tools.vision.constants import (
    SUPPORTED_IMAGE_FORMATS,
    VISION_OUTPUT_DIR,
)
from aria.tools.vision.exceptions import (
    UnsupportedFormatError,
    VisionFileNotFoundError,
    VLModelError,
)

# HTTP exceptions to catch for fallback
_HTTP_EXCEPTIONS = (
    httpx.HTTPStatusError,
    httpx.TimeoutException,
    httpx.ConnectError,
)

# DPI used when rendering PDF pages to PNG.
_PDF_RENDER_DPI = 150

# Default extraction instruction sent alongside each page image.
_DEFAULT_PROMPT = (
    "Extract all text, tables, and structured content from this "
    "document page. Return the result as clean markdown, preserving "
    "headings, lists, and table structure."
)

# Default analysis instruction for images.
_DEFAULT_IMAGE_PROMPT = (
    "Describe this image in detail. Include any text, diagrams, "
    "charts, visual elements, and their relationships. Return the "
    "result as clean markdown."
)


async def _call_vl_model(
    client: httpx.AsyncClient,
    endpoint: str,
    model: str,
    png_bytes: bytes,
    prompt: str,
) -> str:
    """Send a single image to the VL server and return the text result.

    Args:
        client: An ``httpx.AsyncClient`` instance.
        endpoint: Full URL to the ``/chat/completions`` endpoint.
        model: Model name to pass in the request body.
        png_bytes: PNG-encoded image bytes.
        prompt: Text instruction for the VL model.

    Returns:
        The model's text response, stripped of whitespace.

    Raises:
        httpx.HTTPStatusError: On non-2xx responses.
        httpx.TimeoutException: On request timeout.
        httpx.ConnectError: On connection failure.
    """
    b64 = base64.b64encode(png_bytes).decode("ascii")
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{b64}",
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }
        ],
    }

    response = await client.post(
        endpoint,
        json=payload,
        headers={"Authorization": "Bearer sk-dummy"},
    )
    response.raise_for_status()

    data = response.json()
    text: str = (
        data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    )
    return text


def _persist_vision_result(
    tool_name: str,
    reason: str,
    source_path: Path,
    extracted_text: str,
    pages_processed: int | None = None,
) -> str:
    """Persist extracted markdown and return compact JSON metadata.

    Args:
        tool_name: Name of the tool (e.g. ``"parse_pdf"`` or
            ``"analyze_image"``).
        reason: Why the extraction was performed.
        source_path: Original file path.
        extracted_text: Full extracted/analysed text.
        pages_processed: Number of pages processed (PDF only).
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{source_path.stem}_extracted_{timestamp}.md"
    output_path = VISION_OUTPUT_DIR / output_filename
    output_path.write_text(extracted_text, encoding="utf-8")

    preview = extracted_text[:500]
    if len(extracted_text) > 500:
        preview += "..."

    data: dict = {
        "source_file": str(source_path),
        "output_file": str(output_path),
        "content_preview": preview,
        "total_chars": len(extracted_text),
    }
    if pages_processed is not None:
        data["pages_processed"] = pages_processed

    return tool_success_response(tool_name, reason, data)


def _render_pdf_pages(pdf_path: Path) -> list[bytes]:
    """Render every page of a PDF to PNG bytes at ``_PDF_RENDER_DPI`` DPI.

    Args:
        pdf_path: Absolute path to the PDF file.

    Returns:
        List of PNG bytes, one entry per page.

    Raises:
        ImportError: If ``pypdfium2`` is not installed.
    """
    try:
        import pypdfium2 as pdfium  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError(
            "pypdfium2 is required for PDF rendering. "
            "Install it with: uv add pypdfium2"
        ) from exc

    pages_png: list[bytes] = []
    doc = pdfium.PdfDocument(str(pdf_path))
    try:
        scale = int(_PDF_RENDER_DPI / 72.0)
        for page_index in range(len(doc)):
            page = doc[page_index]
            bitmap = page.render(scale=scale, rotation=0)
            pil_image = bitmap.to_pil()
            buf = io.BytesIO()
            pil_image.save(buf, format="PNG")
            pages_png.append(buf.getvalue())
            logger.debug(
                f"Rendered PDF page {page_index + 1}/{len(doc)} "
                f"({len(pages_png[-1])} bytes)"
            )
    finally:
        doc.close()

    return pages_png


def _extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from a PDF using pypdfium2's text extraction capabilities.

    This is a fallback method when the VL model fails to process
    multimodal input.

    Args:
        pdf_path: Absolute path to the PDF file.

    Returns:
        Extracted text content with page separators.

    Raises:
        ImportError: If pypdfium2 is not installed.
    """
    try:
        import pypdfium2 as pdfium  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError(
            "pypdfium2 is required for PDF text extraction fallback. "
            "Install it with: uv add pypdfium2"
        ) from exc

    pages_text: list[str] = []
    doc = pdfium.PdfDocument(str(pdf_path))
    try:
        for page_index in range(len(doc)):
            page = doc[page_index]
            # Get text from the page
            text = page.get_textpage().get_text_range()
            pages_text.append(f"--- Page {page_index + 1} ---\n\n{text}")
            logger.debug(
                f"Extracted text from PDF page {page_index + 1}/{len(doc)} "
                f"({len(text)} chars)"
            )
    finally:
        doc.close()

    return "\n\n".join(pages_text)


def _load_image_file(image_path: Path) -> bytes:
    """Load an image file and return its bytes as PNG.

    Validates the file extension against ``SUPPORTED_IMAGE_FORMATS``,
    opens with Pillow to verify it is a valid image, and converts
    to PNG format for consistent VL server input.

    Args:
        image_path: Absolute path to the image file.

    Returns:
        PNG-encoded image bytes.

    Raises:
        UnsupportedFormatError: If the file extension is not supported.
        VisionFileNotFoundError: If the file does not exist.
        ImportError: If Pillow is not installed.
    """
    try:
        from PIL import Image
    except ImportError as exc:
        raise ImportError(
            "Pillow is required for image loading. " "Install it with: uv add pillow"
        ) from exc

    if not image_path.exists():
        raise VisionFileNotFoundError(f"File not found: {image_path}")

    suffix = image_path.suffix.lower()
    if suffix not in SUPPORTED_IMAGE_FORMATS:
        raise UnsupportedFormatError(
            f"Unsupported image format '{suffix}'. "
            f"Supported formats: {', '.join(sorted(SUPPORTED_IMAGE_FORMATS))}."
        )

    img = Image.open(image_path)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def make_parse_pdf(api_base: str, model: str) -> Callable:
    """Return a ``parse_pdf`` async function bound to the VL server.

    This factory creates a closure so the tool function captures the VL server
    URL and model name without needing them as parameters (LlamaIndex tools
    must have plain, serialisable signatures).

    Each PDF page is rendered to PNG via ``pypdfium2``, base64-encoded, and
    sent to the VL server as an OpenAI multimodal chat completion request
    using ``httpx`` directly — no LlamaIndex LLM wrapper is involved.

    Args:
        api_base: Base URL of the OpenAI-compatible VL server, e.g.
            ``"http://localhost:9091/v1"``.
        model: Model name to pass in the request body, e.g.
            ``"granite-docling-258M-Q8_0.gguf"``.

    Returns:
        An async callable suitable for wrapping with
        :class:`~llama_index.core.tools.FunctionTool`.
    """

    async def parse_pdf(reason: str, file_path: str, prompt: str = "") -> str:
        """Extract text and tables from a PDF using a vision-language model.

        When to use:
            - Use this when you need to extract text, tables, or structured
              content from PDF files.
            - Use this with a custom prompt to target specific extraction
              (e.g., "Extract only tables as markdown").
            - Do NOT use this for non-PDF files — only PDF is supported.

        Why:
            Renders each PDF page as an image and sends it to a
            vision-language model, which excels at understanding complex
            layouts, tables, and multi-column text that pure text
            extraction often misses. Falls back to text extraction if
            the VL model fails.

        Args:
            reason: Why you're extracting (for logging/auditing).
            file_path: Absolute path to the PDF file.
            prompt: Optional extraction instruction. Defaults to full
                extraction of text, tables, and structured content.

        Returns:
            JSON with source_file, output_file, content_preview,
            total_chars, and pages_processed.

        Important:
            - Full extracted content is persisted to a markdown file
              in VISION_OUTPUT_DIR.
            - Falls back to text-based extraction if the VL server fails.
            - Requires a running VL server (configured at startup).
        """
        path = Path(file_path)
        if not path.exists():
            return tool_error_response(
                get_function_name(),
                reason,
                VisionFileNotFoundError(f"File not found: {file_path}"),
            )

        suffix = path.suffix.lower()
        if suffix != ".pdf":
            return tool_error_response(
                get_function_name(),
                reason,
                UnsupportedFormatError(
                    f"Unsupported file format '{suffix}'. "
                    "Only PDF files are supported."
                ),
            )

        user_prompt = prompt or _DEFAULT_PROMPT

        logger.info(f"Rendering PDF: {path.name}")
        pages = _render_pdf_pages(path)

        endpoint = api_base.rstrip("/") + "/chat/completions"
        parts: list[str] = []

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                for i, png_bytes in enumerate(pages, start=1):
                    logger.info(f"Analysing PDF page {i}/{len(pages)}: " f"{path.name}")

                    text = await _call_vl_model(
                        client, endpoint, model, png_bytes, user_prompt
                    )
                    parts.append(f"--- Page {i} ---\n\n{text}")

        except _HTTP_EXCEPTIONS as e:
            logger.warning(
                f"VL model failed to parse PDF: {e}. "
                "Falling back to text-based extraction"
            )
            # Fall back to text-based extraction
            extracted_text = _extract_text_from_pdf(path)
            return _persist_vision_result(
                "parse_pdf",
                reason,
                path,
                extracted_text,
                pages_processed=len(pages),
            )

        extracted_text = "\n\n".join(parts)
        return _persist_vision_result(
            "parse_pdf",
            reason,
            path,
            extracted_text,
            pages_processed=len(pages),
        )

    return log_tool_call(parse_pdf)


def make_analyze_image(api_base: str, model: str) -> Callable:
    """Return an ``analyze_image`` async function bound to the VL server.

    This factory creates a closure so the tool function captures the VL server
    URL and model name without needing them as parameters (LlamaIndex tools
    must have plain, serialisable signatures).

    The image is loaded, validated, converted to PNG via Pillow, and
    sent to the VL server as an OpenAI multimodal chat completion request
    using ``httpx`` directly — no LlamaIndex LLM wrapper is involved.

    Args:
        api_base: Base URL of the OpenAI-compatible VL server, e.g.
            ``"http://localhost:9091/v1"``.
        model: Model name to pass in the request body, e.g.
            ``"granite-docling-258M-Q8_0.gguf"``.

    Returns:
        An async callable suitable for wrapping with
        :class:`~llama_index.core.tools.FunctionTool`.
    """

    async def analyze_image(reason: str, file_path: str, prompt: str = "") -> str:
        """Analyze an image using a vision-language model.

        When to use:
            - Use this when you need to describe, analyze, or extract
              information from image files (PNG, JPEG, WebP, GIF, BMP, TIFF).
            - Use this with a custom prompt to target specific analysis
              (e.g., "Describe this diagram in detail").
            - Do NOT use this for PDF files — use parse_pdf instead.

        Why:
            Sends the image directly to a vision-language model which can
            understand and describe visual content including diagrams,
            screenshots, photos, charts, and other visual information.

        Args:
            reason: Why you are analyzing this image (for logging/auditing).
            file_path: Absolute path to the image file.
            prompt: Optional analysis instruction. Defaults to a general
                description of the image content.

        Returns:
            JSON with source_file, output_file, content_preview, total_chars.

        Important:
            - Full analysis result is persisted to a markdown file in
              VISION_OUTPUT_DIR.
            - Requires a running VL server (configured at startup).
        """
        path = Path(file_path)
        user_prompt = prompt or _DEFAULT_IMAGE_PROMPT

        logger.info(f"Loading image: {path.name}")
        try:
            png_bytes = _load_image_file(path)
        except (VisionFileNotFoundError, UnsupportedFormatError) as exc:
            return tool_error_response(get_function_name(), reason, exc)

        endpoint = api_base.rstrip("/") + "/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                logger.info(f"Analysing image: {path.name}")
                extracted_text = await _call_vl_model(
                    client, endpoint, model, png_bytes, user_prompt
                )
        except _HTTP_EXCEPTIONS as e:
            logger.error(f"VL model failed to analyze image: {e}")
            return tool_error_response(
                get_function_name(),
                reason,
                VLModelError(
                    f"VL model request failed: {e}. " "Ensure the VL server is running."
                ),
            )

        return _persist_vision_result("analyze_image", reason, path, extracted_text)

    return log_tool_call(analyze_image)
