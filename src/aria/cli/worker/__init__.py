"""Worker CLI — spawn, list, status, logs, cancel, clean.

Workers are background agents that run autonomous tasks as subprocesses.
They share the same tool registry as Aria but cannot spawn sub-workers.
"""

import json
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from aria.config.folders import Data, Storage
from aria.server.process_utils import (
    is_process_running,
    load_state,
    save_state,
    stop_process,
)

app = typer.Typer(
    help=(
        "Background worker management. Use workers for long-running or "
        "multi-step tasks that should continue asynchronously."
    )
)
console = Console()

WORKERS_DIR = Data.path / "workers"
STORAGE_DIR = Storage.path


def _worker_id() -> str:
    return f"worker_{uuid.uuid4().hex[:8]}"


def _audit_path(wid: str) -> Path:
    return WORKERS_DIR / f"{wid}.json"


def _output_dir(wid: str) -> Path:
    return STORAGE_DIR / wid


@app.command("spawn")
def spawn(
    prompt: str = typer.Option(
        ...,
        "--prompt",
        "-p",
        help="Self-contained task prompt with objective, context, scope, constraints, and success criteria.",
    ),
    reason: str = typer.Option(
        ...,
        "--reason",
        "-r",
        help="Why this task is being delegated to a background worker.",
    ),
    expected: str = typer.Option(
        ...,
        "--expected",
        "-e",
        help="Expected deliverable or result the worker should produce.",
    ),
    instructions: Optional[str] = typer.Option(
        None,
        "--instructions",
        "-i",
        help="Optional extra instructions. Avoid vague additions; the worker should not need follow-up questions.",
    ),
):
    """Spawn a background worker agent.

    The worker executes autonomously, so the prompt should be specific and
    self-contained.
    """
    wid = _worker_id()
    out_dir = _output_dir(wid)
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "aria.cli.worker._runner",
        "--worker-id",
        wid,
        "--prompt",
        prompt,
        "--output-dir",
        str(out_dir),
    ]
    if instructions:
        cmd.extend(["--instructions", instructions])

    log_handle = open(out_dir / "stdout.log", "w")
    process = subprocess.Popen(
        cmd,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

    # Write audit
    WORKERS_DIR.mkdir(parents=True, exist_ok=True)
    audit = {
        "worker_id": wid,
        "pid": process.pid,
        "status": "running",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "prompt": prompt,
        "reason": reason,
        "expected_results": expected,
        "extra_instructions": instructions,
        "output_dir": str(out_dir),
        "result": None,
        "error": None,
        "tool_calls": [],
    }
    save_state(_audit_path(wid), audit)

    typer.echo(
        json.dumps(
            {
                "worker_id": wid,
                "pid": process.pid,
                "output_dir": str(out_dir),
                "status": "running",
            }
        )
    )


@app.command("list")
def list_workers():
    """List all workers."""
    if not WORKERS_DIR.exists():
        typer.echo(json.dumps({"workers": []}))
        return

    workers = []
    for f in sorted(WORKERS_DIR.glob("worker_*.json")):
        audit = load_state(f)
        if not audit:
            continue
        # Detect zombies
        if audit.get("status") == "running" and not is_process_running(
            audit.get("pid", 0)
        ):
            audit["status"] = "zombie"
            save_state(f, audit)
        workers.append(audit)

    typer.echo(json.dumps({"workers": workers}))


@app.command("status")
def status(
    worker_id: str = typer.Argument(...),
):
    """Get status of a specific worker."""
    path = _audit_path(worker_id)
    if not path.exists():
        typer.echo(json.dumps({"error": f"Worker {worker_id} not found"}))
        raise typer.Exit(1)

    audit = load_state(path)
    if audit.get("status") == "running" and not is_process_running(
        audit.get("pid", 0)
    ):
        audit["status"] = "zombie"
        save_state(path, audit)

    typer.echo(json.dumps(audit))


@app.command("logs")
def logs(
    worker_id: str = typer.Argument(...),
    tail: int = typer.Option(50, "--tail", "-n"),
):
    """View worker logs."""
    log_file = _output_dir(worker_id) / "stdout.log"
    if not log_file.exists():
        typer.echo(json.dumps({"error": "No logs found"}))
        raise typer.Exit(1)
    lines = log_file.read_text().splitlines()
    for line in lines[-tail:]:
        console.print(line)


@app.command("cancel")
def cancel(
    worker_id: str = typer.Argument(...),
):
    """Cancel a running worker."""
    path = _audit_path(worker_id)
    if not path.exists():
        typer.echo(json.dumps({"error": "Not found"}))
        raise typer.Exit(1)

    audit = load_state(path)
    if audit.get("status") != "running":
        typer.echo(json.dumps(audit))
        return

    stop_process(audit.get("pid", 0))
    audit["status"] = "cancelled"
    audit["completed_at"] = datetime.now(timezone.utc).isoformat()
    save_state(path, audit)
    typer.echo(json.dumps(audit))


@app.command("clean")
def clean(
    days: int = typer.Option(7, "--days", "-d"),
):
    """Remove workers older than N days."""
    if not WORKERS_DIR.exists():
        return

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    removed = 0
    for f in WORKERS_DIR.glob("worker_*.json"):
        audit = load_state(f)
        if not audit:
            continue
        try:
            created = datetime.fromisoformat(audit["created_at"])
        except (ValueError, KeyError):
            continue
        if created < cutoff:
            f.unlink(missing_ok=True)
            out = _output_dir(audit.get("worker_id", f.stem))
            if out.exists():
                shutil.rmtree(out, ignore_errors=True)
            removed += 1
    typer.echo(json.dumps({"removed": removed}))
