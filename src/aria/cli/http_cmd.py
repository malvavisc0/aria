"""HTTP request CLI commands.

Wraps the http_request tool as a CLI sub-command.
"""

import json

import typer

app = typer.Typer(
    help=(
        "HTTP API commands. Responses are persisted to disk and returned as "
        "JSON metadata instead of large inline bodies."
    )
)


@app.command("request")
def http_cmd(
    method: str = typer.Argument(..., help="HTTP method (GET, POST, PUT, etc.)"),
    url: str = typer.Argument(..., help="URL to request"),
    headers: str | None = typer.Option(
        None, "--headers", "-H", help="JSON string of headers"
    ),
    body: str | None = typer.Option(None, "--body", "-b", help="Request body string"),
    timeout: int | None = typer.Option(
        30, "--timeout", "-t", help="Timeout in seconds"
    ),
):
    """Make an HTTP request to an API or endpoint.

    Returns JSON metadata including status, headers, final URL, and a saved
    response-body file.
    """
    from aria.tools.http.functions import http_request

    parsed_headers: dict[str, str] | None = None
    if headers:
        parsed_headers = json.loads(headers)

    result = http_request(
        reason="CLI HTTP request",
        method=method,
        url=url,
        headers=parsed_headers,
        body=body,
        timeout=timeout,
    )
    typer.echo(result)
