"""SearXNG-backed web search tool."""

from os import getenv
from typing import Any, Literal, TypedDict
from urllib.parse import urlencode

import httpx

from aria.tools import (
    Reason,
    get_function_name,
    tool_error_response,
    tool_success_response,
)
from aria.tools.decorators import log_tool_call

SEARXNG_URL = getenv("SEARXNG_URL", "").rstrip("/")
_REQUEST_TIMEOUT_SECONDS = 10.0

Categories = Literal[
    "general",
    "files",
    "news",
    "videos",
    "images",
]
TimeRange = Literal["", "day", "week", "month", "year"]


class FieldSpec(TypedDict):
    name: str
    required: bool
    default: Any


class SearchPageStats(TypedDict):
    requested: int
    succeeded: int
    failed: int


# Field mappings per category.
_CATEGORY_FIELD_MAP: dict[str, list[FieldSpec]] = {
    "general": [
        {"name": "url", "required": True, "default": None},
        {"name": "title", "required": True, "default": None},
        {"name": "content", "required": True, "default": None},
    ],
    "news": [
        {"name": "url", "required": True, "default": None},
        {"name": "title", "required": True, "default": None},
        {"name": "content", "required": True, "default": None},
        {"name": "source", "required": False, "default": ""},
        {"name": "thumbnail", "required": False, "default": ""},
        {"name": "pubdate", "required": False, "default": ""},
    ],
    "images": [
        {"name": "url", "required": True, "default": None},
        {"name": "title", "required": True, "default": None},
        {"name": "img_src", "required": True, "default": None},
        {"name": "thumbnail_src", "required": False, "default": ""},
    ],
    "videos": [
        {"name": "url", "required": True, "default": None},
        {"name": "title", "required": True, "default": None},
        {"name": "content", "required": True, "default": None},
        {"name": "iframe_src", "required": False, "default": ""},
        {"name": "thumbnail", "required": False, "default": ""},
        {"name": "engine", "required": False, "default": ""},
    ],
    "files": [
        {"name": "url", "required": True, "default": None},
        {"name": "title", "required": True, "default": None},
        {"name": "content", "required": True, "default": None},
        {"name": "filename", "required": True, "default": None},
        {"name": "size", "required": False, "default": ""},
        {"name": "mimetype", "required": False, "default": ""},
    ],
}


@log_tool_call
def searxng_web_search(
    reason: Reason,
    query: str,
    category: Categories = "general",
    time_range: TimeRange = "",
    max_results: int = 5,
) -> str:
    """Search the web via SearXNG and return structured JSON results.

    Use this when you need more control over web search with category
    filtering, time range, or self-hosted privacy. Returns normalized
    results with text cleaning.

    Args:
        reason: Required. Brief explanation of why you are searching.
        query: Search query text.
        category: Result type to request. Use `general` for normal web search.
        time_range: Optional freshness filter (day/week/month/year).
        max_results: Maximum total results to return (default: 10).

    Returns:
        A JSON string with:
        - `result.count`: Number of accepted results.
        - `result.findings`: Normalized search results.
        - `error`: Empty on full success, or summary when pages fail.
        - `metadata`: Request parameters, success flags, stats.
    """
    if not SEARXNG_URL:
        return tool_error_response(
            get_function_name(),
            reason,
            RuntimeError("SEARXNG_URL environment variable is not set"),
        )
    if not query:
        return tool_error_response(
            get_function_name(), reason, RuntimeError("query cannot be empty")
        )
    if max_results < 1:
        return tool_error_response(
            get_function_name(),
            reason,
            RuntimeError("max_results must be positive"),
        )

    # Calculate pages needed (approx 10 results per page)
    pages = max(1, (max_results + 9) // 10)

    results: list[dict[str, Any]] = []
    page_errors: list[dict[str, Any]] = []
    dropped_results = 0
    stats: SearchPageStats = {"requested": pages, "succeeded": 0, "failed": 0}
    field_map = _CATEGORY_FIELD_MAP.get(category, _CATEGORY_FIELD_MAP["general"])

    try:
        with httpx.Client(timeout=_REQUEST_TIMEOUT_SECONDS) as client:
            for page_number in range(1, pages + 1):
                params = {
                    "safesearch": "0",
                    "format": "json",
                    "time_range": time_range,
                    "categories": category,
                    "q": query,
                    "pageno": page_number,
                }
                page_result, page_error, page_dropped = _fetch_page(
                    client=client,
                    category=category,
                    field_map=field_map,
                    params=params,
                    page_number=page_number,
                )

                dropped_results += page_dropped
                if page_error:
                    stats["failed"] += 1
                    page_errors.append(page_error)
                    continue

                stats["succeeded"] += 1
                results.extend(page_result)

                # Stop if we have enough results
                if len(results) >= max_results:
                    break

    except Exception as exc:
        return tool_error_response(get_function_name(), reason, exc)

    # Trim to max_results
    results = results[:max_results]

    success = stats["succeeded"] > 0
    error_message = _build_error_message(stats=stats, page_errors=page_errors)

    return tool_success_response(
        get_function_name(),
        reason,
        {
            "count": len(results),
            "findings": results,
            "error": error_message,
            "params": {
                "query": query,
                "category": category,
                "time_range": time_range,
                "max_results": max_results,
                "pages_requested": pages,
            },
            "success": success,
            "partial_success": success and stats["failed"] > 0,
            "page_stats": stats,
            "dropped_results": dropped_results,
            "page_errors": page_errors,
        },
    )


def _fetch_page(
    *,
    client: httpx.Client,
    category: str,
    field_map: list[FieldSpec],
    params: dict[str, Any],
    page_number: int,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, int]:
    """Fetch and normalize a single search results page."""
    url = f"{SEARXNG_URL}/search?{urlencode(params)}"

    try:
        response = client.get(url)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        return [], _page_error(page_number, "http_error", str(exc)), 0

    try:
        payload = response.json()
    except ValueError as exc:
        return [], _page_error(page_number, "invalid_json", str(exc)), 0

    raw_results = payload.get("results")
    if not isinstance(raw_results, list):
        return (
            [],
            _page_error(
                page_number,
                "invalid_payload",
                "Missing or invalid 'results' list",
            ),
            0,
        )

    rows: list[dict[str, Any]] = []
    dropped_results = 0
    for raw_result in raw_results:
        if not isinstance(raw_result, dict):
            dropped_results += 1
            continue

        row = _build_row(raw_result, category, field_map)
        if row is None:
            dropped_results += 1
            continue
        rows.append(row)

    return rows, None, dropped_results


def _build_row(
    result: dict[str, Any], category: str, field_map: list[FieldSpec]
) -> dict[str, Any] | None:
    """Build a normalized result row based on category field mapping."""
    row: dict[str, Any] = {}
    for spec in field_map:
        field_name = spec["name"]
        required = spec["required"]
        default = spec["default"]

        value = result.get(field_name, default)
        if required and not value:
            return None

        row[field_name] = value

    row["category"] = category
    return row


def _page_error(page_number: int, error_type: str, detail: str) -> dict[str, Any]:
    """Build a structured per-page error payload."""
    return {
        "page": page_number,
        "type": error_type,
        "detail": detail,
    }


def _build_error_message(
    *, stats: SearchPageStats, page_errors: list[dict[str, Any]]
) -> str:
    """Build a top-level error summary for callers."""
    if stats["failed"] == 0:
        return ""
    if stats["succeeded"] == 0:
        return "All search requests failed"
    first_error = page_errors[0]["detail"] if page_errors else "Unknown error"
    return (
        f"Partial search failure: {stats['failed']} of {stats['requested']} "
        f"page requests failed. First error: {first_error}"
    )
