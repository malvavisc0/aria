"""IMDB tool exceptions."""

from aria.tools.errors import ToolError


class IMDBError(ToolError):
    """Base exception for IMDB operations."""

    code = "IMDB_ERROR"
    recoverable = True
    how_to_fix = "Retry the IMDB request."


class IMDBNetworkError(IMDBError):
    """Network error during IMDB request."""

    code = "NETWORK_ERROR"
    recoverable = True
    how_to_fix = "Check internet connection and retry."


class IMDBTimeoutError(IMDBError):
    """Request timed out."""

    code = "TIMEOUT_ERROR"
    recoverable = True
    how_to_fix = "Retry the request."


class IMDBRateLimitError(IMDBError):
    """Rate limited by IMDB."""

    code = "RATE_LIMIT_ERROR"
    recoverable = True
    how_to_fix = "Wait a few minutes before retrying."


class IMDBNotFoundError(IMDBError):
    """Movie or person not found."""

    code = "NOT_FOUND"
    recoverable = False
    how_to_fix = "Verify the IMDB ID or search with different terms."
