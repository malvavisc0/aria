"""Process manager tool for background process management.

Provides full lifecycle control of background processes with support for
shell mode (pipes/redirects), custom working directories, environment
variables, signals, restart, and configurable concurrency limits.
"""

import os
import signal
import subprocess
import threading
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

from aria.tools import Reason, tool_response
from aria.tools.decorators import log_tool_call
from aria.tools.shell.validation import _extract_all_command_names

# Maximum lines of output to retain per stream
_MAX_LOG_LINES = 500

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


@dataclass
class ManagedProcess:
    """A background process with non-blocking output capture."""

    proc: subprocess.Popen
    command: str = ""
    raw_command: str = ""
    raw_args: list[str] | None = None
    working_dir: str = ""
    use_shell: bool = False
    env: dict[str, str] | None = None
    stdout_lines: deque = field(default_factory=lambda: deque(maxlen=_MAX_LOG_LINES))
    stderr_lines: deque = field(default_factory=lambda: deque(maxlen=_MAX_LOG_LINES))
    _threads: list = field(default_factory=list)
    _timeout_timer: threading.Timer | None = field(default=None, repr=False)

    def start_capture(self) -> None:
        """Start background threads to capture stdout/stderr."""
        if self.proc.stdout:
            t = threading.Thread(
                target=self._reader,
                args=(self.proc.stdout, self.stdout_lines),
                daemon=True,
            )
            t.start()
            self._threads.append(t)
        if self.proc.stderr:
            t = threading.Thread(
                target=self._reader,
                args=(self.proc.stderr, self.stderr_lines),
                daemon=True,
            )
            t.start()
            self._threads.append(t)

    @staticmethod
    def _reader(stream, buf: deque) -> None:
        """Read lines from *stream* into *buf* until EOF."""
        try:
            for line in stream:
                buf.append(line)
        except (ValueError, OSError):
            pass

    def cancel_timeout(self) -> None:
        """Cancel any pending timeout timer."""
        if self._timeout_timer is not None:
            self._timeout_timer.cancel()
            self._timeout_timer = None


# In-memory process registry
_processes: dict[str, ManagedProcess] = {}
_processes_lock = threading.Lock()


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


def _auto_kill(name: str) -> None:
    """Callback fired when a process exceeds its timeout."""
    managed = _processes.get(name)
    if managed is None:
        return
    if managed.proc.poll() is None:
        logger.warning(f"Process '{name}' exceeded timeout — terminating")
        managed.proc.terminate()
        try:
            managed.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            managed.proc.kill()


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

    When to use:
        - Start, stop, inspect, restart, signal, or read logs of
          background processes (dev servers, build watchers, pipelines).
        - Do NOT use for one-off commands — use `shell`.

    Args:
        reason: Required. Brief explanation of why you are calling this tool (e.g. "Start dev server for testing").
        action: start | stop | status | logs | list | restart | signal.
        name: Unique name for the process (required for most actions).
        command: Command to execute (required for start).
            When use_shell=True, supports pipes, redirects, env vars.
        args: Optional command arguments (ignored when use_shell=True).
        timeout: Auto-kill timeout in seconds. Process is terminated after
            this duration. None means run indefinitely.
        working_dir: Working directory for the process (default: cwd).
        env: Additional environment variables (merged with current env).
        use_shell: If True, execute via system shell (enables pipes,
            redirects, globs). Default: False.
        signal_name: Signal to send (for action="signal").
            Supports: SIGTERM, SIGINT, SIGHUP, SIGUSR1, SIGUSR2.

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

    with _processes_lock:
        if name in _processes:
            managed = _processes[name]
            if managed.proc.poll() is None:
                return tool_response(
                    tool="process",
                    reason=reason,
                    data={"error": f"Process '{name}' is already running."},
                )

        active_count = sum(1 for m in _processes.values() if m.proc.poll() is None)
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

    # Resolve working directory
    try:
        resolved_dir = _resolve_working_dir(working_dir)
    except (FileNotFoundError, NotADirectoryError) as exc:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": str(exc)},
        )

    # Build environment
    proc_env = None
    if env:
        proc_env = {**os.environ, **env}

    # Build command
    if use_shell:
        # Shell mode: command is a string, args are ignored
        full_command = command
        run_target = command
    else:
        cmd_list = [command] + (args or [])
        full_command = " ".join(cmd_list)
        run_target = cmd_list

    try:
        proc = subprocess.Popen(
            run_target,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=resolved_dir,
            env=proc_env,
            shell=use_shell,
        )
        managed = ManagedProcess(
            proc=proc,
            command=full_command,
            raw_command=command,
            raw_args=args,
            working_dir=str(resolved_dir),
            use_shell=use_shell,
            env=env,
        )
        managed.start_capture()

        # Set up auto-kill timer if timeout specified
        if timeout is not None and timeout > 0:
            timer = threading.Timer(timeout, _auto_kill, args=(name,))
            timer.daemon = True
            timer.start()
            managed._timeout_timer = timer

        with _processes_lock:
            _processes[name] = managed

        logger.info(f"Started process '{name}': {full_command}")
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

    managed = _processes.get(name)
    if managed is None or managed.proc.poll() is not None:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": f"Process '{name}' is not running."},
        )

    managed.cancel_timeout()
    managed.proc.terminate()
    try:
        managed.proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        managed.proc.kill()
        managed.proc.wait()

    logger.info(f"Stopped process '{name}'")
    return tool_response(
        tool="process",
        reason=reason,
        data={
            "action": "stop",
            "name": name,
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

    managed = _processes.get(name)
    if managed is None:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": f"Process '{name}' not found."},
        )

    return_code = managed.proc.poll()
    status = "running" if return_code is None else f"exited ({return_code})"
    return tool_response(
        tool="process",
        reason=reason,
        data={
            "action": "status",
            "name": name,
            "pid": managed.proc.pid,
            "status": status,
            "return_code": return_code,
            "command": managed.command,
            "working_dir": managed.working_dir,
        },
    )


def _action_logs(reason: str, name: str | None) -> str:
    """Get recent output from a process (non-blocking).

    Returns the last _MAX_LOG_LINES lines captured by background
    reader threads. Never blocks, even if the process is still running.
    """
    if not name:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": "Missing required 'name' parameter."},
        )

    managed = _processes.get(name)
    if managed is None:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": f"Process '{name}' not found."},
        )

    stdout = "".join(managed.stdout_lines)
    stderr = "".join(managed.stderr_lines)

    # Truncate to last 10 KB to keep response size reasonable
    max_size = 10_000
    if len(stdout) > max_size:
        stdout = stdout[-max_size:]
    if len(stderr) > max_size:
        stderr = stderr[-max_size:]

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


def _action_list(reason: str) -> str:
    """List all managed processes."""
    entries = []
    for name, managed in _processes.items():
        return_code = managed.proc.poll()
        entries.append(
            {
                "name": name,
                "pid": managed.proc.pid,
                "status": "running" if return_code is None else "exited",
                "return_code": return_code,
                "command": managed.command,
                "working_dir": managed.working_dir,
            }
        )

    return tool_response(
        tool="process",
        reason=reason,
        data={
            "action": "list",
            "count": len(entries),
            "processes": entries,
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

    managed = _processes.get(name)
    if managed is None:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": f"Process '{name}' not found. Use 'start' instead."},
        )

    # Preserve original config for restart
    original_raw_command = managed.raw_command
    original_raw_args = managed.raw_args
    original_working_dir = managed.working_dir
    original_use_shell = managed.use_shell
    original_env = managed.env

    # Stop if running
    if managed.proc.poll() is None:
        managed.cancel_timeout()
        managed.proc.terminate()
        try:
            managed.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            managed.proc.kill()
            managed.proc.wait()

    # Use original config unless overrides provided
    restart_working_dir = working_dir or original_working_dir
    restart_env = env if env is not None else original_env
    restart_shell = use_shell if use_shell else original_use_shell

    # Remove from registry so start doesn't see it as "already running"
    with _processes_lock:
        _processes.pop(name, None)

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

    managed = _processes.get(name)
    if managed is None or managed.proc.poll() is not None:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": f"Process '{name}' is not running."},
        )

    try:
        managed.proc.send_signal(sig)
        logger.info(f"Sent {sig_upper} to process '{name}' (PID: {managed.proc.pid})")
        return tool_response(
            tool="process",
            reason=reason,
            data={
                "action": "signal",
                "name": name,
                "signal": sig_upper,
                "pid": managed.proc.pid,
                "message": f"Sent {sig_upper} to '{name}'",
            },
        )
    except OSError as exc:
        return tool_response(
            tool="process",
            reason=reason,
            data={"error": f"Failed to send signal: {exc}"},
        )
