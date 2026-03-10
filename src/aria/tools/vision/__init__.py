"""Vision tools for document intelligence.

Provides :func:`make_parse_pdf`, a factory that returns an async
``parse_pdf`` tool closure bound to a VL server URL and model name.
Used by the ChatterAgent to extract structured content from PDF files
via direct HTTP calls to the VL server.
"""

from .functions import make_parse_pdf

__all__ = ["make_parse_pdf"]
