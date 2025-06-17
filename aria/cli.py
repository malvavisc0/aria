import subprocess

import typer

app = typer.Typer(help="Aria backend management CLI.")


@app.command()
def run(
    host: str = "0.0.0.0", port: int = 8000, reload: bool = True, log_level: str = "info"
):
    """
    Run the Aria backend server using uv and uvicorn.
    """
    cmd = [
        "uv",
        "pip",
        "run",
        "uvicorn",
        "aria.main:app",
        "--host",
        host,
        "--port",
        str(port),
        "--log-level",
        log_level,
    ]
    if reload:
        cmd.append("--reload")
    subprocess.run(cmd)


if __name__ == "__main__":
    app()
