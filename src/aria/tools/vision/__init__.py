"""Vision tools for document intelligence.

Provides :func:`make_analyze_document`, a factory that returns an async
``analyze_document`` tool closure bound to a vision-language LLM.
Used by the Docling agent to extract structured content from images and PDFs.
"""

from .functions import make_analyze_document

__all__ = ["make_analyze_document"]
