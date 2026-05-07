"""Development CLI commands.

Wraps the Python execution tool as a CLI sub-command.
"""

import typer

app = typer.Typer(
    help="Run Python code in a sandboxed subprocess.",
)


@app.command("run")
def run_cmd(
    path: str = typer.Argument(..., help="Path to a Python file to execute"),
    timeout: int = typer.Option(30, "--timeout", "-t", help="Timeout in seconds"),
    check_only: bool = typer.Option(
        False,
        "--check",
        "-c",
        help="Validate syntax only, do not execute",
    ),
):
    """Execute a Python file in a sandboxed environment."""
    from pathlib import Path

    from aria.tools.development.python import python

    file_path = Path(path)
    if not file_path.exists():
        typer.echo(f"Error: file not found: {path}", err=True)
        raise typer.Exit(1)

    result = python(
        reason="CLI Python execution",
        file=str(file_path.resolve()),
        timeout=timeout,
        check_only=check_only,
    )
    typer.echo(result)
