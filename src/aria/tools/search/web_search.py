"""Unified web search tool.

Phase 6 consolidation: duckduckgo_web_search + searxng_web_search → web_search

Auto-selects backend based on SEARXNG_URL environment variable.
"""

from typing import Optional

from loguru import logger

from aria.tools import log_tool_call

# Lazy imports to avoid hard dependency on DDGS when SearXNG is available
_SEARXNG_URL: str = ""


def _get_searxng_url() -> str:
    """Get SearXNG URL from environment (cached)."""
    global _SEARXNG_URL
    if not _SEARXNG_URL:
        from os import getenv

        _SEARXNG_URL = getenv("SEARXNG_URL", "").rstrip("/")
    return _SEARXNG_URL


@log_tool_call
def web_search(
    intent: str,
    query: str,
    category: Optional[str] = None,
    time_range: Optional[str] = None,
    max_results: Optional[int] = 10,
) -> str:
    """Search the web using the best available backend.

    Auto-selects DuckDuckGo or SearXNG based on configuration.
    If SEARXNG_URL is set, uses SearXNG (supports category, time_range).
    Otherwise falls back to DuckDuckGo.

    Args:
        intent: Why you're searching (e.g., "Finding documentation")
        query: Search query string
        category: Optional category filter (SearXNG only):
            general, files, news, videos, images
        time_range: Optional freshness filter (SearXNG only):
            day, week, month, year
        max_results: Maximum results (default: 10)

    Returns:
        JSON with results[{title, href}], error if failed.
    """
    searxng_url = _get_searxng_url()
    max_results_value = max_results if max_results is not None else 10

    if searxng_url:
        logger.debug("Using SearXNG backend for web search")
        from aria.tools.search.searxng import searxng_web_search

        return searxng_web_search(
            intent=intent,
            query=query,
            category=(category or "general"),  # type: ignore[arg-type]
            time_range=(time_range or ""),  # type: ignore[arg-type]
            max_results=max_results_value,
        )
    else:
        logger.debug("Using DuckDuckGo backend for web search")
        from aria.tools.search.duckduckgo import duckduckgo_web_search

        return duckduckgo_web_search(
            intent=intent,
            query=query,
            max_results=max_results_value,
        )
