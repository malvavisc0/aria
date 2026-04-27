"""Unified web search tool.


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
    reason: str,
    query: str,
    category: Optional[str] = None,
    time_range: Optional[str] = None,
    max_results: Optional[int] = 5,
) -> str:
    """Search the web for information using the best available backend.

    When to use:
        - Use this when you need to find information on the internet
          (e.g., documentation, news, tutorials, facts).
        - Use this as the first step when researching a topic online.
        - Do NOT use this to download files — use `download`.
        - Do NOT use this to browse a specific website — use `open_url`.

    Why:
        Auto-selects the best available search backend (SearXNG if
        configured, otherwise DuckDuckGo). SearXNG supports category
        and time-range filters for more targeted results.

    Args:
        reason: Why you're searching (for logging/auditing).
        query: Search query string.
        category: Optional category filter (SearXNG only): general,
            files, news, videos, images.
        time_range: Optional freshness filter (SearXNG only): day,
            week, month, year.
        max_results: Maximum results (default: 10).

    Returns:
        JSON with results[{title, href}], error if failed.

    Important:
        - category and time_range only work when SEARXNG_URL is set.
        - Returns URLs, not page content — use `open_url` or `download`
          to get full content.
    """
    searxng_url = _get_searxng_url()
    max_results_value = max_results if max_results is not None else 5

    if searxng_url:
        logger.debug("Using SearXNG backend for web search")
        from aria.tools.search.searxng import searxng_web_search

        return searxng_web_search(
            reason=reason,
            query=query,
            category=(category or "general"),  # type: ignore[arg-type]
            time_range=(time_range or ""),  # type: ignore[arg-type]
            max_results=max_results_value,
        )
    else:
        logger.debug("Using DuckDuckGo backend for web search")
        from aria.tools.search.duckduckgo import duckduckgo_web_search

        return duckduckgo_web_search(
            reason=reason,
            query=query,
            max_results=max_results_value,
        )
