"""Background process management commands for the Aria CLI.

Provides lifecycle control for background processes (start, stop, status,
logs, list) via the process manager tool.

Example:
    ```bash
    aria processes list
    aria processes start --name myproc --command "python server.py"
    aria processes stop --name myproc
    aria processes logs --name myproc
    ```
"""

import typer

app = typer.Typer(
    name="processes",
    help="Manage background processes (start, stop, status, logs, list).",
)


@app.callback(invoke_without_command=True)
def processes_cmd(
    ctx: typer.Context,
    action: str = typer.Argument(
        "list", help="Action: start, stop, status, logs, list, restart"
    ),
    name: str | None = typer.Option(None, "--name", "-n", help="Process name"),
    command: str | None = typer.Option(
        None, "--command", "-c", help="Command to execute (for start)"
    ),
):
    """Manage background processes (start, stop, status, logs, list)."""
    from aria.tools.process.functions import process

    result = process(
        reason="CLI process management",
        action=action,
        name=name,
        command=command,
    )
    typer.echo(result)
