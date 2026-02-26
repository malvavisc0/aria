"""Document analysis tool for the Docling vision-language agent.

Provides :func:`make_analyze_document`, which returns an async
``analyze_document`` closure bound to a vision-language LLM.

The tool accepts a local file path to a PDF and calls the VL model with
rendered PNG bytes via :class:`~llama_index.core.base.llms.types.ImageBlock`.

PDF rendering uses ``pypdfium2`` (pure-Python, no system dependencies).
Each page is rendered at 150 DPI and sent to the VL model individually;
results are concatenated into a single markdown document.
"""

import io
from pathlib import Path
from typing import Callable

from llama_index.core.base.llms.types import (
    ChatMessage,
    ImageBlock,
    MessageRole,
    TextBlock,
)
from llama_index.llms.openai_like import OpenAILike
from loguru import logger

# DPI used when rendering PDF pages to PNG.
_PDF_RENDER_DPI = 150


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
        scale = _PDF_RENDER_DPI / 72.0  # pdfium uses 72 DPI as base
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


async def _call_vl_llm(
    llm: OpenAILike,
    image_bytes: bytes,
    mime: str,
    user_prompt: str,
) -> str:
    """Send a single image to the VL LLM and return the text response.

    Args:
        llm: The vision-language :class:`OpenAILike` instance.
        image_bytes: Raw image bytes (PNG, JPEG, etc.).
        mime: MIME type of the image (e.g. ``"image/png"``).
        user_prompt: Instruction to send alongside the image.

    Returns:
        The model's text response.
    """
    message = ChatMessage(
        role=MessageRole.USER,
        blocks=[
            ImageBlock(image=image_bytes, image_mimetype=mime),
            TextBlock(text=user_prompt),
        ],
    )
    response = await llm.achat(messages=[message])
    return response.message.content or ""


def make_analyze_document(vl_llm: OpenAILike) -> Callable:
    """Return a ``parse_file_with_ocr`` async function bound to *vl_llm*.

    This factory creates a closure so the tool function captures the VL LLM
    instance without needing it as a parameter (LlamaIndex tools must have
    plain, serialisable signatures).

    Args:
        vl_llm: The vision-language :class:`OpenAILike` instance to use for
            inference.

    Returns:
        An async callable suitable for wrapping with
        :class:`~llama_index.core.tools.FunctionTool`.
    """

    async def parse_file_with_ocr(file_path: str, prompt: str = "") -> str:
        """Extract structured content from a PDF document using OCR.

        Renders each PDF page to PNG and sends it to the vision-language
        model, returning the concatenated markdown extraction.

        Args:
            file_path: Absolute path to the PDF file to analyse.
                Supported format: PDF only.
            prompt: Optional instruction to guide extraction (e.g.
                ``"Extract all table data"``). Defaults to a generic
                document extraction prompt.

        Returns:
            Extracted content as markdown. Each page is separated by a
            ``--- Page N ---`` heading.

        Raises:
            ValueError: If the file does not exist or is not a PDF.
        """
        path = Path(file_path)
        if not path.exists():
            raise ValueError(f"File not found: {file_path}")

        suffix = path.suffix.lower()
        if suffix != ".pdf":
            raise ValueError(
                f"Unsupported file format '{suffix}'. " "Only PDF files are supported."
            )

        user_prompt = prompt or (
            "Extract all text, tables, and structured content from this "
            "document page. Return the result as clean markdown, preserving "
            "headings, lists, and table structure."
        )

        logger.info(f"Rendering PDF: {path.name}")
        pages = _render_pdf_pages(path)
        parts: list[str] = []
        for i, png_bytes in enumerate(pages, start=1):
            logger.info(f"Analysing PDF page {i}/{len(pages)}: {path.name}")
            text = await _call_vl_llm(vl_llm, png_bytes, "image/png", user_prompt)
            parts.append(f"--- Page {i} ---\n\n{text.strip()}")
        return "\n\n".join(parts)

    return parse_file_with_ocr
