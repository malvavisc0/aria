"""DuckDuckGo-backed web search tool."""

from typing import Dict, List, Optional

from ddgs import DDGS
from loguru import logger

from aria.tools import get_function_name, log_tool_call, tool_error_response
from aria.tools.constants import DEFAULT_TIMEOUT
from aria.tools.search.constants import MAX_RESULTS_LIMIT


@log_tool_call
def duckduckgo_web_search(
    reason: str, query: str, max_results: Optional[int] = 5
) -> str:
    """
    Search the web and return a small set of {title, href} results.

    Args:
        reason: Why you're searching (e.g., "Finding documentation")
        query: Search query string
        max_results: Maximum results (default: 5, max: 50)

    Returns:
        JSON with results[{title, href}], error if failed.
        Use open_url to read web pages from the results.
        Use download to download files (PDFs, images, etc.).
    """
    # Validate inputs
    validation_error = _validate_inputs(query, max_results)
    if validation_error:
        return tool_error_response(
            get_function_name(), reason, RuntimeError(validation_error)
        )

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
                    logger.warning(f"Skipping result with missing fields: {result}")
            except (KeyError, TypeError) as field_error:
                logger.warning(f"Skipping malformed result: {field_error}")
                continue

    except Exception as exc:
        error_msg = f"Web search failed: {str(exc)}"
        logger.error(error_msg)
        # Log the full exception for debugging
        logger.debug(f"Full exception details: {type(exc).__name__}: {exc}")
        return tool_error_response(get_function_name(), reason, exc)

    # Create and return final response
    from aria.tools import tool_success_response

    return tool_success_response(get_function_name(), reason, {"results": results})


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
