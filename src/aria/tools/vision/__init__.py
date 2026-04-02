"""Vision tools for document and image intelligence.

Provides :func:`make_parse_pdf` and :func:`make_analyze_image`, factories
that return async tool closures bound to a VL server URL and model name.
Used by the ChatterAgent to extract structured content from PDF files
and analyze images via direct HTTP calls to the VL server.
"""

from .functions import make_analyze_image, make_parse_pdf

__all__ = ["make_parse_pdf", "make_analyze_image"]
