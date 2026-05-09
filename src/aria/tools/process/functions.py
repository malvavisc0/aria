"""Process manager tool for background process management.

Provides full lifecycle control of background processes with support for
shell mode (pipes/redirects), custom working directories, environment
variables, signals, restart, and configurable concurrency limits.

Process state is persisted to ``data/processes.json`` so the manager
can track processes started by other invocations (e.g. CLI to agent).
stdout/stderr are redirected to log files so child processes survive
parent exit.
"""

import os
import signal
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from aria.config.folders import Data
from aria.server.process_utils import (
    is_process_running,
    load_state,
    save_state,
    stop_process,
)
from aria.tools import Reason, tool_response
from aria.tools.decorators import log_tool_call
from aria.tools.shell.validation import _extract_all_command_names

# State file for cross-invocation persistence
_STATE_FILE = Data.path / "processes.json"

# Directory for stdout/stderr log files
_LOG_DIR = Data.path / "process_logs"

# Maximum bytes to return from log files (last N bytes to keep response small)
_MAX_LOG_BYTES = 10_000

# Configurable concurrency limit (default: 10)
_MAX_PROCESSES = int(os.environ.get("ARIA_MAX_PROCESSES", "10"))

# Blocked command names (same approach as shell tool — by command name, not substring)
_BLOCKED_COMMANDS = [
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "mkfs",
    "dd",
    "shred",
    "wipe",
]


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------


def _load_processes() -> dict[str, dict]:
    """Load persisted process entries from disk.

    Dead processes are kept in state so logs remain accessible.
    Use _prune_stale() explicitly when cleanup is desired.
    """
    state = load_state(_STATE_FILE)
    return dict(state.get("processes", {}))


def _prune_stale(entries: dict[str, dict]) -> dict[str, dict]:
    """Remove entries for processes that are no longer running."""
    pruned = False
    for name in list(entries):
        pid = entries[name].get("pid")
        if pid is None or not is_process_running(pid):
            _cleanup_logs(name)
            del entries[name]
            pruned = True

    if pruned:
        _save_processes(entries)

    return entries


def _save_processes(entries: dict[str, dict]) -> None:
    """Persist process entries to disk."""
    save_state(_STATE_FILE, {"processes": entries})


def _cleanup_logs(name: str) -> None:
    """Remove log files for a process."""
    for suffix in (".stdout.log", ".stderr.log"):
        log_file = _LOG_DIR / f"{name}{suffix}"
        try:
            if log_file.exists():
                log_file.unlink()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _is_command_blocked(command: str) -> bool:
    """Check if a command contains blocked command names.

    Uses proper command-name extraction (handles pipes, chains, env prefixes)
    instead of fragile substring matching.
    """
    cmd_names = _extract_all_command_names(command)
    return any(name in _BLOCKED_COMMANDS for name in cmd_names)


def _resolve_working_dir(working_dir: str | None) -> Path:
    """Resolve and validate working directory."""
    if working_dir is None:
        return Path.cwd()
    path = Path(working_dir).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Working directory does not exist: {working_dir}")
    if not path.is_dir():
        raise NotADirectoryError(f"Not a directory: {working_dir}")
    return path


# ---------------------------------------------------------------------------
# Timeout helper (works with PIDs since we detach)
# ---------------------------------------------------------------------------


def _auto_kill(pid: int, name: str) -> None:
    """Callback fired when a process exceeds its timeout.

    Uses SIGKILL directly since the timeout has already expired —
    no need for a graceful shutdown grace period.
    """
    if is_process_running(pid):
        logger.warning(f"Process '{name}' exceeded timeout — killing")
        try:
            os.kill(pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            pass
    # Remove from state after kill
    entries = _load_processes()
    entries.pop(name, None)
    _save_processes(entries)
    _cleanup_logs(name)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


@log_tool_call
def process(
    reason: Reason,
    action: str,
    name: str | None = None,
    command: str | None = None,
    args: list[str] | None = None,
    timeout: int | None = None,
    working_dir: str | None = None,
    env: dict[str, str] | None = None,
    use_shell: bool = False,
    signal_name: str | None = None,
) -> str:
    """Manage long-running background processes.

    Actions: ``start``, ``stop``, ``status``, ``logs``, ``list``,
    ``restart``, ``signal``.

    Args:
        reason: Required. Brief explanation of why you are calling this tool.
        action: Process action to perform.
        name: Process name (required for most actions).
        command: Command to execute (required for ``start``).
        args: Optional command arguments when ``use_shell`` is False.
        timeout: Optional auto-kill timeout in seconds.
        working_dir: Working directory for the process.
        env: Additional environment variables.
        use_shell: Execute through the system shell.
        signal_name: Signal to send for ``action="signal"``.

    Returns:
        JSON with action-specific process data.
    """
    action = action.lower().strip()

    actions = {
        "start": lambda: _action_start(
            reason, name, command, args, timeout, working_dir, env, use_shell
        ),
        "stop": lambda: _action_stop(reason, name),
        "status": lambda: _action_status(reason, name),
        "logs": lambda: _action_logs(reason, name),
        "list": lambda: _action_list(reason),
        "restart": lambda: _action_restart(
            reason, name, timeout, working_dir, env, use_shell
        ),
        "signal": lambda: _action_signal(reason, name, signal_name),
    }

    handler = actions.get(action)
    if handler is None:
        return tool_response(
            tool="process",
            reason=reason,
            data={
                "error": f"Unknown action '{action}'. "
                f"Valid: {', '.join(actions.keys())}",
            },
        )
    return handler()


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


def _action_start(
    reason: str,
    name: str | None,
    command: str | None,
    args: list[str] | None,
    timeout: int | None,
    working_dir: str | None,
    env: dict[str, str] | None,
    use_shell: bool,
) -> str:
    """Start a new background process."""
    if not name:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": "Missing required 'name' parameter."},
        )
    if not command:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": "Missing required 'command' parameter."},
        )

    if _is_command_blocked(command):
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": "Command contains blocked patterns."},
        )

    entries = _load_processes()
    if name in entries:
        pid = entries[name].get("pid")
        if pid and is_process_running(pid):
            return tool_response(
                tool="process",
                reason=reason,
                data={"error": f"Process '{name}' is already running (PID: {pid})."},
            )

    active_count = sum(
        1 for e in entries.values() if e.get("pid") and is_process_running(e["pid"])
    )
    if active_count >= _MAX_PROCESSES:
        return tool_response(
            tool="process",
            reason=reason,
            data={
                "error": (
                    f"Maximum of {_MAX_PROCESSES} concurrent processes "
                    f"reached ({active_count} running). Stop one first."
                ),
            },
        )

    try:
        resolved_dir = _resolve_working_dir(working_dir)
    except (FileNotFoundError, NotADirectoryError) as exc:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": str(exc)},
        )

    proc_env = {**os.environ}

    # Ensure the current Python environment's bin directory is on PATH
    _bin_dir = os.path.join(sys.prefix, "Scripts" if os.name == "nt" else "bin")
    if os.path.isdir(_bin_dir):
        _path = proc_env.get("PATH", "")
        if _bin_dir not in _path.split(os.pathsep):
            proc_env["PATH"] = _bin_dir + os.pathsep + _path

    if env:
        proc_env.update(env)

    if use_shell:
        full_command = command
        run_target = command
    else:
        cmd_list = [command] + (args or [])
        full_command = " ".join(cmd_list)
        run_target = cmd_list

    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    stdout_log = _LOG_DIR / f"{name}.stdout.log"
    stderr_log = _LOG_DIR / f"{name}.stderr.log"

    try:
        stdout_fh = open(stdout_log, "w")
        stderr_fh = open(stderr_log, "w")

        proc = subprocess.Popen(
            run_target,
            stdout=stdout_fh,
            stderr=stderr_fh,
            text=True,
            cwd=resolved_dir,
            env=proc_env,
            shell=use_shell,
            start_new_session=True,  # Detach from parent process group
        )

        # Close file handles in parent — child owns them now
        stdout_fh.close()
        stderr_fh.close()

        entries[name] = {
            "pid": proc.pid,
            "command": full_command,
            "raw_command": command,
            "raw_args": args,
            "working_dir": str(resolved_dir),
            "use_shell": use_shell,
            "env": env,
            "stdout_log": str(stdout_log),
            "stderr_log": str(stderr_log),
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        _save_processes(entries)

        if timeout is not None and timeout > 0:
            timer = threading.Timer(timeout, _auto_kill, args=(proc.pid, name))
            timer.daemon = True
            timer.start()

        logger.info(f"Started process '{name}': {full_command} (PID: {proc.pid})")
        return tool_response(
            tool="process",
            reason=reason,
            data={
                "action": "start",
                "name": name,
                "pid": proc.pid,
                "command": full_command,
                "working_dir": str(resolved_dir),
                "use_shell": use_shell,
                "timeout": timeout,
                "message": f"Process '{name}' started (PID: {proc.pid})",
            },
        )
    except FileNotFoundError:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": f"Command not found: {command}"},
        )
    except Exception as exc:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": f"Failed to start process: {exc}"},
        )


def _action_stop(reason: str, name: str | None) -> str:
    """Stop a running process."""
    if not name:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": "Missing required 'name' parameter."},
        )

    entries = _load_processes()
    entry = entries.get(name)
    if entry is None:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": f"Process '{name}' not found."},
        )

    pid = entry.get("pid")
    if pid is None or not is_process_running(pid):
        # Already dead — clean up state
        entries.pop(name, None)
        _save_processes(entries)
        _cleanup_logs(name)
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": f"Process '{name}' is not running."},
        )

    stopped = stop_process(pid, timeout=5)

    entries.pop(name, None)
    _save_processes(entries)
    _cleanup_logs(name)

    logger.info(f"Stopped process '{name}' (PID: {pid})")
    return tool_response(
        tool="process",
        reason=reason,
        data={
            "action": "stop",
            "name": name,
            "pid": pid,
            "message": f"Process '{name}' stopped",
        },
    )


def _action_status(reason: str, name: str | None) -> str:
    """Get process status."""
    if not name:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": "Missing required 'name' parameter."},
        )

    entries = _load_processes()
    entry = entries.get(name)
    if entry is None:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": f"Process '{name}' not found."},
        )

    pid = entry.get("pid")
    running = pid is not None and is_process_running(pid)

    return tool_response(
        tool="process",
        reason=reason,
        data={
            "action": "status",
            "name": name,
            "pid": pid,
            "status": "running" if running else "exited",
            "command": entry.get("command", ""),
            "working_dir": entry.get("working_dir", ""),
            "started_at": entry.get("started_at", ""),
        },
    )


def _action_logs(reason: str, name: str | None) -> str:
    """Get recent output from a process by reading log files.

    Returns the tail of stdout/stderr log files. Works across CLI
    invocations since output is written to disk.
    """
    if not name:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": "Missing required 'name' parameter."},
        )

    entries = _load_processes()
    entry = entries.get(name)
    if entry is None:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": f"Process '{name}' not found."},
        )

    stdout = _read_log_tail(entry.get("stdout_log", ""))
    stderr = _read_log_tail(entry.get("stderr_log", ""))

    return tool_response(
        tool="process",
        reason=reason,
        data={
            "action": "logs",
            "name": name,
            "stdout": stdout,
            "stderr": stderr,
        },
    )


def _read_log_tail(path: str) -> str:
    """Read the last N bytes of a log file."""
    if not path:
        return ""
    log_file = Path(path)
    if not log_file.exists():
        return ""
    try:
        size = log_file.stat().st_size
        with open(log_file) as f:
            if size > _MAX_LOG_BYTES:
                f.seek(size - _MAX_LOG_BYTES)
                # Skip partial line
                f.readline()
                return f.read()
            return f.read()
    except OSError:
        return ""


def _action_list(reason: str) -> str:
    """List all managed processes."""
    entries = _load_processes()
    result_entries = []
    for name, entry in entries.items():
        pid = entry.get("pid")
        running = pid is not None and is_process_running(pid)
        result_entries.append(
            {
                "name": name,
                "pid": pid,
                "status": "running" if running else "exited",
                "command": entry.get("command", ""),
                "working_dir": entry.get("working_dir", ""),
                "started_at": entry.get("started_at", ""),
            }
        )

    return tool_response(
        tool="process",
        reason=reason,
        data={
            "action": "list",
            "count": len(result_entries),
            "processes": result_entries,
        },
    )


def _action_restart(
    reason: str,
    name: str | None,
    timeout: int | None,
    working_dir: str | None,
    env: dict[str, str] | None,
    use_shell: bool,
) -> str:
    """Restart a process (stop then start with same or new config)."""
    if not name:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": "Missing required 'name' parameter."},
        )

    entries = _load_processes()
    entry = entries.get(name)
    if entry is None:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": f"Process '{name}' not found. Use 'start' instead."},
        )

    original_raw_command = entry.get("raw_command", entry.get("command", ""))
    original_raw_args = entry.get("raw_args")
    original_working_dir = entry.get("working_dir", "")
    original_use_shell = entry.get("use_shell", False)
    original_env = entry.get("env")

    pid = entry.get("pid")
    if pid and is_process_running(pid):
        stop_process(pid, timeout=5)

    entries.pop(name, None)
    _save_processes(entries)
    _cleanup_logs(name)

    restart_working_dir = working_dir or original_working_dir
    restart_env = env if env is not None else original_env
    restart_shell = use_shell if use_shell else original_use_shell

    return _action_start(
        reason=reason,
        name=name,
        command=original_raw_command,
        args=original_raw_args,
        timeout=timeout,
        working_dir=restart_working_dir,
        env=restart_env,
        use_shell=restart_shell,
    )


_SIGNAL_MAP = {
    "SIGTERM": signal.SIGTERM,
    "SIGINT": signal.SIGINT,
    "SIGHUP": signal.SIGHUP,
    "SIGUSR1": signal.SIGUSR1,
    "SIGUSR2": signal.SIGUSR2,
    "SIGKILL": signal.SIGKILL,
}


def _action_signal(reason: str, name: str | None, signal_name: str | None) -> str:
    """Send a signal to a running process."""
    if not name:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": "Missing required 'name' parameter."},
        )
    if not signal_name:
        return tool_response(
            tool="process",
            reason=reason,
            data={
                "error": "Missing required 'signal_name' parameter. "
                f"Valid: {', '.join(_SIGNAL_MAP.keys())}",
            },
        )

    sig_upper = signal_name.upper()
    if not sig_upper.startswith("SIG"):
        sig_upper = f"SIG{sig_upper}"

    sig = _SIGNAL_MAP.get(sig_upper)
    if sig is None:
        return tool_response(
            tool="process",
            reason=reason,
            data={
                "error": f"Unknown signal '{signal_name}'. "
                f"Valid: {', '.join(_SIGNAL_MAP.keys())}",
            },
        )

    entries = _load_processes()
    entry = entries.get(name)
    if entry is None:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": f"Process '{name}' not found."},
        )

    pid = entry.get("pid")
    if pid is None or not is_process_running(pid):
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": f"Process '{name}' is not running."},
        )

    try:
        os.kill(pid, sig)
        logger.info(f"Sent {sig_upper} to process '{name}' (PID: {pid})")
        return tool_response(
            tool="process",
            reason=reason,
            data={
                "action": "signal",
                "name": name,
                "signal": sig_upper,
                "pid": pid,
                "message": f"Sent {sig_upper} to '{name}'",
            },
        )
    except OSError as exc:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": f"Failed to send signal: {exc}"},
        )
