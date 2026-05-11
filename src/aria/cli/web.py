"""Web CLI — search, browse, fetch, and interact with the internet.

All internet-facing commands live here:

    aria web search "query"        Search the web
    aria web fetch "url"           Download a file or raw URL content
    aria web open "url"            Open a page in the browser (stays open for click)
    aria web click "selector"      Click an element on the opened page
    aria web close                 Close the current browser page
    aria web weather "city"        Get weather conditions
    aria web youtube "url"         Fetch a YouTube transcript
"""

import asyncio

import typer

app = typer.Typer(
    help="Search the web, browse pages, fetch content, and interact with websites."
)


# ------------------------------------------------------------------
# Search
# ------------------------------------------------------------------


@app.command("search")
def search_cmd(
    query: str = typer.Argument(..., help="Search query"),
    max_results: int | None = typer.Option(
        5, "--max-results", "-n", help="Number of results to return"
    ),
):
    """Search the web and return matching results.

    Returns metadata only — results are leads, not evidence.
    Use ``aria web fetch`` or ``aria web open`` to verify before citing.
    """
    from aria.tools.search import web_search

    result = web_search(
        reason="CLI web search",
        query=query,
        max_results=max_results,
    )
    typer.echo(result)


# ------------------------------------------------------------------
# Fetch / Open / Click / Close (browser & download)
# ------------------------------------------------------------------


@app.command("fetch")
def fetch_cmd(
    url: str = typer.Argument(..., help="URL to fetch"),
    content_mode: str = typer.Option(
        "text",
        "--content-mode",
        "-m",
        help="Extraction mode for websites: 'text' or 'article'.",
    ),
):
    """Download a file or fetch raw URL content.

    Auto-detects whether the URL points to a file (PDF, image, archive)
    or a website. Files are downloaded directly; websites are rendered
    via the browser and saved as text artifacts.

    For interactive browsing (open → click → close), use ``aria web open``.
    """
    from aria.tools.search import download as _download
    from aria.tools.search._url_classifier import URLType, classify_url

    url_type = classify_url(url)

    if url_type == URLType.FILE:
        result = _download(reason="CLI fetch (auto-classified as file)", url=url)
    else:
        from aria.tools.browser.functions import open_url as _open_url

        result = asyncio.run(
            _open_url(
                reason="CLI fetch (auto-classified as website)",
                url=url,
                content_mode=content_mode,
            )
        )
    typer.echo(result)


@app.command("open")
def open_cmd(
    url: str = typer.Argument(..., help="URL to open in the browser"),
    content_mode: str = typer.Option(
        "text",
        "--content-mode",
        "-m",
        help="Extraction mode: 'text' or 'article'.",
    ),
):
    """Open a web page in the browser and extract its content.

    The page stays open so you can interact with it using
    ``aria web click``. When done, close it with ``aria web close``.
    """
    from aria.tools.browser.functions import open_url as _open_url

    result = asyncio.run(
        _open_url(
            reason="CLI browser open",
            url=url,
            content_mode=content_mode,
        )
    )
    typer.echo(result)


@app.command("click")
def click_cmd(
    selector: str = typer.Argument(
        ..., help="CSS selector (e.g. 'button.accept', '#submit')"
    ),
    content_mode: str = typer.Option(
        "text",
        "--content-mode",
        "-m",
        help="Extraction mode for the updated page: 'text' or 'article'.",
    ),
):
    """Click an element on the currently open page.

    Use after ``aria web open`` has loaded a page. Returns the updated
    page content after the click.
    """
    from aria.tools.browser.functions import browser_click

    result = asyncio.run(
        browser_click(
            reason="CLI browser click",
            selector=selector,
            content_mode=content_mode,
        )
    )
    typer.echo(result)


@app.command("close")
def close_cmd():
    """Close the current browser page.

    Navigates back to a blank page. The browser itself stays running.
    """
    from aria.tools.browser.functions import browser_close

    result = asyncio.run(browser_close(reason="CLI browser close"))
    typer.echo(result)


# ------------------------------------------------------------------
# Weather / YouTube (internet lookups)
# ------------------------------------------------------------------


@app.command("weather")
def weather_cmd(
    location: str = typer.Argument(..., help="City name or location"),
):
    """Get current weather conditions for a location."""
    from aria.tools.search import get_current_weather

    result = get_current_weather(reason="CLI weather lookup", location=location)
    typer.echo(result)


@app.command("youtube")
def youtube_cmd(
    url: str = typer.Argument(..., help="YouTube video URL"),
    languages: str | None = typer.Option(
        None,
        "--languages",
        "-l",
        help="Comma-separated language codes (e.g. de,en)",
    ),
):
    """Fetch a YouTube video transcript and save it to disk."""
    from aria.tools.search import get_youtube_video_transcription

    lang_list = [lang.strip() for lang in languages.split(",")] if languages else None
    result = get_youtube_video_transcription(
        reason="CLI YouTube transcript",
        url=url,
        languages=lang_list,
    )
    typer.echo(result)
