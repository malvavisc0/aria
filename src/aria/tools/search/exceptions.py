"""Search tool exceptions."""

from aria.tools.errors import ToolError


class SearchError(ToolError):
    """Base exception for search operations."""

    code = "SEARCH_ERROR"
    recoverable = True
    how_to_fix = "Retry the search."


class SearchNetworkError(SearchError):
    """Network connection failed."""

    code = "NETWORK_ERROR"
    how_to_fix = "Check internet connection and retry."


class SearchTimeoutError(SearchError):
    """Request timed out."""

    code = "TIMEOUT_ERROR"
    how_to_fix = "Retry the request."


class SearchRateLimitError(SearchError):
    """Rate limited by provider."""

    code = "RATE_LIMIT_ERROR"
    recoverable = True
    how_to_fix = "Wait a few minutes before retrying."
