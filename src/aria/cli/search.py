"""Search & Web CLI commands.

Wraps the existing search tools as CLI sub-commands that output JSON.
The ``fetch`` command unifies ``download`` and ``open_url`` with
automatic URL classification.
"""

import asyncio
import json
from typing import Optional

import typer

app = typer.Typer(
    help=(
        "Search and URL acquisition commands. Use these to discover sources, "
        "fetch URLs, and save content as artifacts that Aria can inspect safely."
    )
)


@app.command("web")
def web_search_cmd(
    query: str = typer.Argument(..., help="Search query string"),
    max_results: Optional[int] = typer.Option(
        5, "--max-results", "-n", help="Maximum results"
    ),
):
    """Search the web for candidate sources.

    Returns search-result metadata only. Results are leads, not evidence.
    Fetch and verify promising URLs before citing them.
    """
    from aria.tools.search import web_search

    result = web_search(
        reason="CLI web search",
        query=query,
        max_results=max_results,
    )
    typer.echo(result)


@app.command("fetch")
def fetch_cmd(
    url: str = typer.Argument(..., help="URL to fetch"),
    content_mode: str = typer.Option(
        "text",
        "--content-mode",
        "-m",
        help="Website extraction mode: 'text' for cleaned body text or 'article' for main content.",
    ),
):
    """Fetch a URL and save its contents as an artifact.

    Performs a HEAD request to determine content type, then routes to:
    - Direct download (for files: PDFs, images, archives, data)
    - Browser rendering (for websites: HTML pages)

    Returns JSON metadata. Inspect returned file paths before summarizing,
    quoting, or citing content.
    """
    from aria.tools.search import download as _download
    from aria.tools.search._url_classifier import URLType, classify_url

    url_type = classify_url(url)

    if url_type == URLType.FILE:
        result = _download(
            reason="CLI fetch (auto-classified as file)", url=url
        )
    else:
        # Website — use browser for rendered content
        from aria.tools.browser.functions import open_url as _open_url

        result = asyncio.run(
            _open_url(
                reason="CLI fetch (auto-classified as website)",
                url=url,
                content_mode=content_mode,
            )
        )
    typer.echo(result)


@app.command("weather")
def weather_cmd(
    location: str = typer.Argument(..., help="City name or location"),
):
    """Get current weather conditions."""
    from aria.tools.search import get_current_weather

    result = get_current_weather(
        reason="CLI weather lookup", location=location
    )
    typer.echo(result)


@app.command("youtube")
def youtube_cmd(
    url: str = typer.Argument(..., help="YouTube video URL"),
    languages: Optional[str] = typer.Option(
        None,
        "--languages",
        "-l",
        help="Comma-separated language codes (e.g. de,en)",
    ),
):
    """Fetch a YouTube transcript and save it to disk.

    Returns JSON metadata with the saved transcript path.
    """
    from aria.tools.search import get_youtube_video_transcription

    lang_list = (
        [l.strip() for l in languages.split(",")] if languages else None
    )
    result = get_youtube_video_transcription(
        reason="CLI YouTube transcript",
        url=url,
        languages=lang_list,
    )
    typer.echo(result)
