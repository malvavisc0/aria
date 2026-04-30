"""Browser interaction CLI commands.

Provides the ``click`` command for interacting with page elements
after ``aria search fetch`` has opened a website in the browser.
"""

import asyncio

import typer

app = typer.Typer(
    help=(
        "Browser interaction commands for pages already opened through "
        "URL fetch/navigation."
    )
)


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
    """Click an element on the current page by CSS selector.

    Use after ``aria search fetch`` has opened a website in the browser.
    Returns JSON metadata for the saved post-click artifact.
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
