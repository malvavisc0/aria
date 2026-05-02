"""Development CLI commands.

Wraps the Python execution tool as a CLI sub-command.
"""

import typer

app = typer.Typer(
    help="Run Python code in a sandboxed subprocess.",
)


@app.command("run")
def run_cmd(
    code: str = typer.Argument(..., help="Python code to execute"),
    timeout: int = typer.Option(30, "--timeout", "-t", help="Timeout in seconds"),
):
    """Execute Python code in a sandboxed environment."""
    from aria.tools.development.python import python

    result = python(
        reason="CLI Python execution",
        code=code,
        timeout=timeout,
    )
    typer.echo(result)
