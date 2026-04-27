"""HTTP request tool for making API calls."""

from typing import Dict, Optional

import httpx
from loguru import logger

from aria.tools import tool_response
from aria.tools.constants import (
    DEFAULT_TIMEOUT,
    MAX_TIMEOUT,
    MAX_TOOL_OUTPUT_CHARS,
)
from aria.tools.decorators import log_tool_call

# Allowed HTTP methods
_ALLOWED_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}


@log_tool_call
def http_request(
    reason: str,
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    body: Optional[str] = None,
    timeout: Optional[int] = None,
) -> str:
    """Make HTTP requests to web APIs with redirect following.

    When to use:
        - Use this to call REST APIs, fetch JSON data, or interact with
          web services.
        - Use this when you need full control over HTTP method, headers,
          and body (e.g., POST with JSON payload).
        - Do NOT use this to browse websites — use `open_url` for pages
          that need JavaScript rendering.
        - Do NOT use this to download files — use `download`.

    Why:
        Provides a general-purpose HTTP client (httpx) for API
        integration. Follows redirects and never raises — errors are
        returned in the response JSON.

    Args:
        reason: Why you're making this request (for logging/auditing).
        method: HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD,
            OPTIONS).
        url: The URL to request.
        headers: Optional request headers (dict).
        body: Optional request body string (for POST/PUT/PATCH).
        timeout: Timeout in seconds (default: 30, max: 300).

    Returns:
        JSON with status_code, headers, body, url. Never raises —
        errors are returned in the response data.

    Important:
        - This tool never raises exceptions; errors are returned as JSON.
        - Follows HTTP redirects automatically.
    """
    method = method.upper().strip()

    if method not in _ALLOWED_METHODS:
        return tool_response(
            tool="http_request",
            reason=reason,
            data={
                "error": (
                    f"Method '{method}' not allowed. "
                    f"Use: {', '.join(sorted(_ALLOWED_METHODS))}"
                ),
            },
        )

    actual_timeout = min(
        timeout if timeout is not None else DEFAULT_TIMEOUT,
        MAX_TIMEOUT,
    )

    try:
        with httpx.Client(
            timeout=actual_timeout,
            follow_redirects=True,
        ) as client:
            response = client.request(
                method=method,
                url=url,
                headers=headers,
                content=body,
            )

        body = response.text
        if len(body) > MAX_TOOL_OUTPUT_CHARS:
            body = body[:MAX_TOOL_OUTPUT_CHARS] + (
                f"\n\n[...truncated — response was "
                f"{len(response.text):,} chars, "
                f"limit is {MAX_TOOL_OUTPUT_CHARS:,}]"
            )

        return tool_response(
            tool="http_request",
            reason=reason,
            data={
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": body,
                "url": str(response.url),
            },
        )

    except httpx.TimeoutException:
        return tool_response(
            tool="http_request",
            reason=reason,
            data={"error": f"Request timed out after {actual_timeout}s"},
        )
    except httpx.ConnectError as exc:
        return tool_response(
            tool="http_request",
            reason=reason,
            data={"error": f"Connection failed: {exc}"},
        )
    except Exception as exc:
        logger.exception("HTTP request failed")
        return tool_response(
            tool="http_request",
            reason=reason,
            data={"error": f"Request failed: {exc}"},
        )
