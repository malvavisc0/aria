"""Browser automation tools using Lightpanda with Playwright CDP.

Tools for:
1. Opening URLs and getting page content
2. Clicking elements (accept cookies, pagination, etc.)

The browser is started automatically when the Aria server starts.
Lightpanda must be installed first:
    aria lightpanda download

Example:
    ```python
    from aria.tools.browser import open_url, browser_click

    # Open a URL and get page content
    result = open_url("Reading documentation", "https://example.com")

    # Click an element by CSS selector
    result = browser_click("Accepting cookies", "button.accept")
    ```
"""

from aria.tools import get_function_name
from aria.tools.browser.manager import get_browser_manager
from aria.tools.decorators import log_tool_call


def _get_manager():
    """Get the browser manager, raising if unavailable."""
    manager = get_browser_manager()
    if manager is None:
        raise RuntimeError(
            "Browser is not available. Either Lightpanda is not installed "
            "(run 'aria lightpanda download') or the browser "
            "failed to start."
        )
    if not manager.is_running:
        raise RuntimeError(
            "Browser is not running. It should have been started "
            "during app startup. Check the server logs for errors."
        )
    return manager


@log_tool_call
async def open_url(reason: str, url: str, content_mode: str = "text") -> str:
    """Open a URL in the headless browser and get page content.

    When to use:
        - Use this when you need to browse a website that requires JavaScript
          rendering, cookie consent, or anti-bot bypass.
        - Use this when you need the rendered DOM content of a page.
        - Do NOT use this to download files (PDFs, images, archives) — use
          the `download` tool instead.
        - Do NOT use this for simple HTTP API calls — use `http_request`.

    Why:
        Lightpanda provides a real browser via CDP that bypasses anti-bot
        protection, unlike plain HTTP requests which get blocked by many
        modern websites. The browser is already running at server startup.

    Args:
        reason: Why you are opening this URL (for logging/auditing).
        url: The URL to navigate to.
        content_mode: Extraction mode: `text` for cleaned body text or
            `article` for likely main-content extraction.

    Returns:
        JSON with URL, title, and persisted content metadata
        (content_file, content_preview, content_size).

    Important:
        - The browser is already running — this just navigates to the URL.
        - Page content is persisted to disk; the response contains a preview
          and file path, not the full content inline.
        - Requires Lightpanda to be installed (`aria lightpanda download`).
    """
    manager = _get_manager()
    return await manager.navigate(
        url,
        tool=get_function_name(),
        reason=reason,
        content_mode=content_mode,
    )


@log_tool_call
async def browser_click(
    reason: str,
    selector: str,
    content_mode: str = "text",
) -> str:
    """Click an element on the current page by CSS selector.

    When to use:
        - Use this after `open_url` to interact with page elements such as
          accepting cookie consent banners, clicking 'Load more' buttons,
          navigating pagination, or following links.
        - Do NOT use this without first calling `open_url` — there must be
          an active page in the browser.

    Why:
        Many websites hide content behind interactions (consent walls,
        lazy-loaded sections, paginated results). This tool lets you
        interact with the page to reveal the content you need.

    Args:
        reason: Why you are clicking this element (for logging/auditing).
        selector: CSS selector for the element, e.g. 'button.accept',
            'a[href="/next"]', '#submit-button'.
        content_mode: Extraction mode for the updated page content.

    Returns:
        JSON with updated page content metadata after the click.

    Important:
        - Always call `open_url` first to navigate to a page before clicking.
        - Use specific selectors (class, ID, data attributes) rather than
          generic tag selectors to avoid clicking the wrong element.
    """
    manager = _get_manager()
    return await manager.click(
        selector,
        tool=get_function_name(),
        reason=reason,
        content_mode=content_mode,
    )


@log_tool_call
async def browser_close(reason: str) -> str:
    """Close the current browser page.

    When to use:
        - Use this after you're done interacting with a page that was
          opened with `open_url`.
        - Closes the current page by navigating to about:blank. The
          browser itself stays running for future use.

    Args:
        reason: Why you are closing the page (for logging/auditing).

    Returns:
        JSON confirming the page was closed.
    """
    manager = _get_manager()
    return await manager.close_page(
        tool=get_function_name(),
        reason=reason,
    )
