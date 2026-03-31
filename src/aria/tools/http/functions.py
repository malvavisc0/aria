"""HTTP request tool for making API calls."""

from typing import Dict, Optional

import httpx
from loguru import logger

from aria.tools import tool_response
from aria.tools.constants import DEFAULT_TIMEOUT, MAX_TIMEOUT
from aria.tools.decorators import log_tool_call

# Allowed HTTP methods
_ALLOWED_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}


@log_tool_call
def http_request(
    intent: str,
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    body: Optional[str] = None,
    timeout: Optional[int] = None,
) -> str:
    """Make HTTP requests to web APIs.

    Supports GET, POST, PUT, DELETE, PATCH methods with configurable
    headers and body.

    Args:
        intent: Why you're making this request.
        method: HTTP method (GET, POST, PUT, DELETE, PATCH).
        url: The URL to request.
        headers: Optional request headers.
        body: Optional request body (for POST/PUT/PATCH).
        timeout: Timeout in seconds (default: 30, max: 300).

    Returns:
        JSON with status_code, headers, and body.
    """
    method = method.upper().strip()

    if method not in _ALLOWED_METHODS:
        return tool_response(
            tool="http_request",
            intent=intent,
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

        return tool_response(
            tool="http_request",
            intent=intent,
            data={
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.text,
                "url": str(response.url),
            },
        )

    except httpx.TimeoutException:
        return tool_response(
            tool="http_request",
            intent=intent,
            data={"error": f"Request timed out after {actual_timeout}s"},
        )
    except httpx.ConnectError as exc:
        return tool_response(
            tool="http_request",
            intent=intent,
            data={"error": f"Connection failed: {exc}"},
        )
    except Exception as exc:
        logger.exception("HTTP request failed")
        return tool_response(
            tool="http_request",
            intent=intent,
            data={"error": f"Request failed: {exc}"},
        )
