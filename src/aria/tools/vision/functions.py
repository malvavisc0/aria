"""Document analysis tool for the vision-language model.

Provides :func:`make_parse_pdf`, which returns an async ``parse_pdf``
closure bound to a VL server URL and model name.

The tool accepts a local file path to a PDF, renders each page to PNG
via ``pypdfium2``, base64-encodes the PNG bytes, and sends them directly
to the VL server using the OpenAI multimodal chat format over ``httpx``.
No LlamaIndex LLM wrapper is involved — the HTTP call is made directly.

PDF rendering uses ``pypdfium2`` (pure-Python, no system dependencies).
Each page is rendered at 150 DPI and sent to the VL model individually;
results are concatenated into a single markdown document.
"""

import base64
import io
from pathlib import Path
from typing import Callable

import httpx
from loguru import logger

# DPI used when rendering PDF pages to PNG.
_PDF_RENDER_DPI = 150

# Default extraction instruction sent alongside each page image.
_DEFAULT_PROMPT = (
    "Extract all text, tables, and structured content from this "
    "document page. Return the result as clean markdown, preserving "
    "headings, lists, and table structure."
)


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
        scale = int(_PDF_RENDER_DPI / 72.0)  # pdfium uses 72 DPI as base
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

    async def parse_pdf(file_path: str, prompt: str = "") -> str:
        """Extract text and tables from a PDF using the vision-language model.

        Renders each page to PNG via pypdfium2, base64-encodes it, and sends
        it to the VL server at api_base using the OpenAI multimodal chat
        format.

        Args:
            file_path: Absolute path to the PDF file.
            prompt: Optional extraction instruction. Defaults to full
                extraction of text, tables, and structured content.

        Returns:
            Extracted content as markdown. Each page is separated by
            a ``--- Page N ---`` heading.

        Raises:
            ValueError: If the file does not exist or is not a PDF.
            httpx.HTTPStatusError: If the VL server returns an error response.
        """
        path = Path(file_path)
        if not path.exists():
            raise ValueError(f"File not found: {file_path}")

        suffix = path.suffix.lower()
        if suffix != ".pdf":
            raise ValueError(
                f"Unsupported file format '{suffix}'. " "Only PDF files are supported."
            )

        user_prompt = prompt or _DEFAULT_PROMPT

        logger.info(f"Rendering PDF: {path.name}")
        pages = _render_pdf_pages(path)

        endpoint = api_base.rstrip("/") + "/chat/completions"
        parts: list[str] = []

        async with httpx.AsyncClient(timeout=120.0) as client:
            for i, png_bytes in enumerate(pages, start=1):
                logger.info(f"Analysing PDF page {i}/{len(pages)}: {path.name}")

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
                                        "url": f"data:image/png;base64,{b64}"
                                    },
                                },
                                {
                                    "type": "text",
                                    "text": user_prompt,
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
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )
                parts.append(f"--- Page {i} ---\n\n{text}")

        return "\n\n".join(parts)

    return parse_pdf
