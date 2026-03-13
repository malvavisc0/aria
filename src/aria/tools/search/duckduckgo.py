"""DuckDuckGo-backed web search tool."""

from typing import Any, Dict, List, Optional

from ddgs import DDGS
from loguru import logger

from aria.tools import log_tool_call, safe_json, utc_timestamp
from aria.tools.constants import DEFAULT_TIMEOUT
from aria.tools.search.constants import MAX_RESULTS_LIMIT


@log_tool_call
def web_search(intent: str, query: str, max_results: Optional[int] = 5) -> str:
    """
    Search the web and return a small set of {title, href} results.

    Args:
        intent: Why you're searching (e.g., "Finding documentation")
        query: Search query string
        max_results: Maximum results (default: 5, max: 50)

    Returns:
        JSON with results[{title, href}], error if failed.
        Use open_url to read web pages from the results.
        Use get_file_from_url to download files (PDFs, images, etc.).
    """
    # Validate inputs
    validation_error = _validate_inputs(query, max_results)
    if validation_error:
        return _create_error_response(validation_error)

    # Prepare response structure
    timestamp = utc_timestamp()
    metadata: Dict[str, Any] = {"timestamp": timestamp, "error": None}
    results: List[Dict[str, str]] = []

    try:
        # Perform the search with timeout
        search_results = DDGS(timeout=DEFAULT_TIMEOUT).text(
            query=query.strip(), max_results=max_results
        )

        # Process results
        for result in search_results:
            try:
                title = result.get("title", "")
                url = result.get("href", "")

                # Keep response minimal - only title and href
                processed_result = {"title": title, "href": url}
                # Skip results with missing required fields
                if processed_result["title"] and processed_result["href"]:
                    results.append(processed_result)
                else:
                    logger.warning(
                        f"Skipping result with missing fields: {result}"
                    )
            except (KeyError, TypeError) as field_error:
                logger.warning(f"Skipping malformed result: {field_error}")
                continue

    except Exception as exc:
        error_msg = f"Web search failed: {str(exc)}"
        metadata["error"] = error_msg
        logger.error(error_msg)
        # Log the full exception for debugging
        logger.debug(f"Full exception details: {type(exc).__name__}: {exc}")

    # Create and return final response
    response = {
        "operation": "web_search",
        "result": results,
        "metadata": metadata,
    }
    return safe_json(response)


def _validate_inputs(query: str, max_results: Optional[int]) -> Optional[str]:
    """
    Validate input parameters for the web search function.

    This internal function performs validation on the query and max_results
    parameters before they are used in the web search. It ensures that the
    inputs meet the requirements for a successful search operation.

    Args:
        query (str): Search query string to validate (must be non-empty).
        max_results (int): Number of results (1..MAX_RESULTS_LIMIT).

    Returns:
        Optional[str]: Error message if validation fails, otherwise None.

        Possible errors include:
            - "Invalid query: must be a string"
            - "Invalid query: must be a non-empty string"
            - "Invalid max_results: must be an integer"
            - "Invalid max_results: must be a positive integer"
            - f"Invalid max_results: must not exceed {MAX_RESULTS_LIMIT}"

    Note:
        This is an internal helper function used by web_search(). It's not
        intended to be called directly by external code.

    Examples:
        >>> _validate_inputs("python programming", 5)
        None  # Validation passes

        >>> _validate_inputs("", 5)
        'Invalid query: must be a non-empty string'

        >>> _validate_inputs("python", 100)
        'Invalid max_results: must not exceed 50'

        >>> _validate_inputs(123, 5)
        'Invalid query: must be a string'
    """
    if not isinstance(query, str):
        return "Invalid query: must be a string"

    if not query.strip():
        return "Invalid query: must be a non-empty string"

    if not isinstance(max_results, int):
        return "Invalid max_results: must be an integer"

    if max_results <= 0:
        return "Invalid max_results: must be a positive integer"

    if max_results > MAX_RESULTS_LIMIT:
        return f"Invalid max_results: must not exceed {MAX_RESULTS_LIMIT}"

    return None


def _create_error_response(error_message: str) -> str:
    """
    Create a standardized error response JSON string.

    This internal function generates a consistent error response format when
    validation fails or when search operations encounter issues. The response
    follows the same structure as successful searches but with empty results
    and error metadata.

    Args:
        error_message (str): The error message to include in the response.
            This should be a descriptive error message from validation or
            exception handling.

    Returns:
        str: A JSON formatted string containing:
            - operation (str): The operation performed ("web_search")
            - result (List[Dict]): Empty list since no results were found
            - metadata (Dict): Additional information including:
                * timestamp (str): ISO timestamp of when the error occurred
                * error (str): The provided error message

    Note:
        This is an internal helper function used by web_search(). It's not
        intended to be called directly by external code.

    Example:
        >>> error_response = _create_error_response(
        ...     "Invalid query: must be a string"
        ... )
        >>> print(error_response)
        {
          "operation": "web_search",
          "result": [],
          "metadata": {
            "timestamp": "2023-01-01T12:00:00.000000",
            "error": "Invalid query: must be a string"
          }
        }
    """
    response = {
        "operation": "web_search",
        "result": [],
        "metadata": {
            "timestamp": utc_timestamp(),
            "error": error_message,
        },
    }
    return safe_json(response)
