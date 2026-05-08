"""Background process management commands for the Aria CLI.

Provides lifecycle control for background processes (start, stop, status,
logs, list, restart, signal) via the process manager tool.

Example:
    ```bash
    aria processes start --name myproc --command "python server.py"
    aria processes list
    aria processes stop --name myproc
    aria processes logs --name myproc
    aria processes status --name myproc
    aria processes restart --name myproc
    aria processes signal --name myproc --signal SIGTERM
    ```
"""

import typer

app = typer.Typer(
    name="processes",
    help="Manage background processes (start, stop, status, logs, list, restart, signal).",
)


@app.command("start")
def start_cmd(
    name: str = typer.Option(..., "--name", "-n", help="Unique process name"),
    command: str = typer.Option(
        ..., "--command", "-c", help="Command to execute"
    ),
    args: list[str] | None = typer.Option(
        None, "--args", "-a", help="Command arguments (repeatable)"
    ),
    timeout: int | None = typer.Option(
        None, "--timeout", "-t", help="Auto-kill timeout in seconds"
    ),
    working_dir: str | None = typer.Option(
        None, "--working-dir", "-w", help="Working directory for the process"
    ),
    env: list[str] | None = typer.Option(
        None,
        "--env",
        "-e",
        help="Environment variables as KEY=VALUE (repeatable)",
    ),
    use_shell: bool = typer.Option(
        False,
        "--shell",
        "-s",
        help="Execute via system shell (enables pipes, redirects)",
    ),
):
    """Start a new background process."""
    from aria.tools.process.functions import process

    env_dict = _parse_env(env)
    result = process(
        reason="CLI process start",
        action="start",
        name=name,
        command=command,
        args=args,
        timeout=timeout,
        working_dir=working_dir,
        env=env_dict,
        use_shell=use_shell,
    )
    typer.echo(result)


@app.command("stop")
def stop_cmd(
    name: str = typer.Option(..., "--name", "-n", help="Process name to stop"),
):
    """Stop a running process."""
    from aria.tools.process.functions import process

    result = process(
        reason="CLI process stop",
        action="stop",
        name=name,
    )
    typer.echo(result)


@app.command("status")
def status_cmd(
    name: str = typer.Option(..., "--name", "-n", help="Process name"),
):
    """Get the status of a managed process."""
    from aria.tools.process.functions import process

    result = process(
        reason="CLI process status",
        action="status",
        name=name,
    )
    typer.echo(result)


@app.command("logs")
def logs_cmd(
    name: str = typer.Option(..., "--name", "-n", help="Process name"),
):
    """Get recent output from a process."""
    from aria.tools.process.functions import process

    result = process(
        reason="CLI process logs",
        action="logs",
        name=name,
    )
    typer.echo(result)


@app.command("list")
def list_cmd():
    """List all managed background processes."""
    from aria.tools.process.functions import process

    result = process(
        reason="CLI process list",
        action="list",
    )
    typer.echo(result)


@app.command("restart")
def restart_cmd(
    name: str = typer.Option(
        ..., "--name", "-n", help="Process name to restart"
    ),
    timeout: int | None = typer.Option(
        None, "--timeout", "-t", help="Auto-kill timeout in seconds"
    ),
    working_dir: str | None = typer.Option(
        None, "--working-dir", "-w", help="Working directory for the process"
    ),
    env: list[str] | None = typer.Option(
        None,
        "--env",
        "-e",
        help="Environment variables as KEY=VALUE (repeatable)",
    ),
    use_shell: bool = typer.Option(
        False, "--shell", "-s", help="Execute via system shell"
    ),
):
    """Restart a managed process (stop then start with same config)."""
    from aria.tools.process.functions import process

    env_dict = _parse_env(env)
    result = process(
        reason="CLI process restart",
        action="restart",
        name=name,
        timeout=timeout,
        working_dir=working_dir,
        env=env_dict,
        use_shell=use_shell,
    )
    typer.echo(result)


@app.command("signal")
def signal_cmd(
    name: str = typer.Option(..., "--name", "-n", help="Process name"),
    signal_name: str = typer.Option(
        ...,
        "--signal",
        help="Signal to send (SIGTERM, SIGINT, SIGHUP, SIGUSR1, SIGUSR2)",
    ),
):
    """Send a signal to a running process."""
    from aria.tools.process.functions import process

    result = process(
        reason="CLI process signal",
        action="signal",
        name=name,
        signal_name=signal_name,
    )
    typer.echo(result)


def _parse_env(env: list[str] | None) -> dict[str, str] | None:
    """Parse a list of KEY=VALUE strings into a dict."""
    if not env:
        return None
    result: dict[str, str] = {}
    for item in env:
        if "=" not in item:
            raise typer.BadParameter(
                f"Invalid env format '{item}'. Expected KEY=VALUE."
            )
        key, value = item.split("=", 1)
        result[key] = value
    return result
