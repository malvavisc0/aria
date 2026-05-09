"""Python execution and syntax-check tools."""

import ast
import os
import traceback

from loguru import logger

from aria.tools import Reason
from aria.tools.constants import DEFAULT_TIMEOUT, MAX_TIMEOUT
from aria.tools.decorators import tool_function
from aria.tools.development._internals import (
    _build_response,
    _capture_execution_output,
    _create_safe_globals,
    _read_file_safely,
    _validate_timeout,
)
from aria.tools.development.decorators import (
    with_input_validation,
    with_runner_error_handling,
)
from aria.tools.development.exceptions import PythonSecurityError


@tool_function(
    "python",
    validate={},
    error_handler=with_runner_error_handling,
    validation_decorator=with_input_validation,
)
def python(
    reason: Reason,
    code: str | None = None,
    file: str | None = None,
    args: list[str] | None = None,
    timeout: int | None = DEFAULT_TIMEOUT,
    check_only: bool = False,
) -> str:
    """Execute or validate Python code with sandboxed output capture.

    When to use:
        - Run Python code snippets, scripts, or test files.
        - Use check_only=True to validate syntax without executing.
        - Do NOT use for shell commands (git, pip, npm) — use `shell`.

    Args:
        reason: Required. Brief explanation of why you are running this code.
        code: Python code string to execute or validate.
        file: Path to a Python file to execute or validate.
        args: CLI arguments for sys.argv (execution only).
        timeout: Max seconds (default: 30, max: 300).
        check_only: If True, validate syntax without executing.

    Returns:
        JSON with result data (stdout, stderr, traceback, etc.).
    """
    if code is None and file is None:
        raise PythonSecurityError("Provide exactly one of 'code' or 'file'.")
    if code is not None and file is not None:
        raise PythonSecurityError("Provide exactly one of 'code' or 'file', not both.")

    if check_only:
        return _python_check(reason, code, file)
    else:
        return _python_execute(reason, code, file, args, timeout)


def _python_check(
    reason: str,
    code: str | None,
    file: str | None,
) -> str:
    """Validate Python syntax without executing."""
    if code is not None:
        filename: str = "<block>"
        source: str = code
    else:
        filename = file  # type: ignore[assignment]
        source = _read_file_safely(file)  # type: ignore[arg-type]

    logger.info(f"Checking Python syntax for: {filename}")

    try:
        ast.parse(source, filename=filename)
        logger.info(f"Syntax validation passed for: {filename}")
        return _build_response(
            operation="python",
            result={"valid": True, "message": "Syntax is valid"},
            filename=filename,
            source="code" if code is not None else "file",
        )

    except SyntaxError as e:
        logger.error(f"Syntax error in {filename} at line {e.lineno or 0}: {e.msg}")
        return _build_response(
            operation="python",
            result={
                "valid": False,
                "error_type": "SyntaxError",
                "message": e.msg or "Syntax error",
                "line_number": e.lineno,
                "column": e.offset,
                "text": e.text.rstrip() if e.text else None,
            },
            filename=filename,
            source="code" if code is not None else "file",
        )


def _python_execute(
    reason: str,
    code: str | None,
    file: str | None,
    args: list[str] | None,
    timeout: int | None,
) -> str:
    """Execute Python code or file."""
    is_file = file is not None

    if is_file:
        filename = file
        source = _read_file_safely(file)
    else:
        filename = "<block>"
        source = code

    logger.info(
        f"Executing Python {'file' if is_file else 'code'}: "
        f"{filename} (timeout={timeout}s)"
    )

    if not timeout:
        raise ValueError(
            f"Invalid timeout: {timeout} (must be 1-{MAX_TIMEOUT} seconds)"
        )
    _validate_timeout(timeout)

    if is_file:
        filename = os.path.abspath(file) if os.path.exists(file) else file

    try:
        safe_globals = _create_safe_globals()

        # Add __file__ and __dir__ for file context
        if is_file:
            safe_globals["__file__"] = os.path.abspath(filename)
            safe_globals["__dir__"] = os.path.dirname(os.path.abspath(filename))
            logger.debug(f"Set __file__ to: {safe_globals['__file__']}")

        stdout_text, stderr_text = _capture_execution_output(
            source,  # type: ignore[arg-type]
            safe_globals,
            timeout,
            filename,  # type: ignore[arg-type]
            args,
        )

        logger.info(
            f"{'File' if is_file else 'Code'} executed successfully: "
            f"{filename} "
            f"(stdout: {len(stdout_text)} bytes, "
            f"stderr: {len(stderr_text)} bytes)"
        )

        return _build_response(
            operation="python",
            result={
                "success": True,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "has_output": bool(stdout_text or stderr_text),
            },
            filename=filename,
            timeout=timeout,
            source="file" if is_file else "code",
        )

    except SystemExit as e:
        exit_code = e.code if e.code is not None else 0
        logger.info(f"Script exited with code {exit_code} in {filename}")
        return _build_response(
            operation="python",
            result={
                "success": exit_code == 0,
                "exit_code": exit_code,
                "message": (
                    f"Script exited with code {exit_code}"
                    if exit_code != 0
                    else "Script completed successfully"
                ),
                "stdout": "",
                "stderr": "",
            },
            filename=filename,
            timeout=timeout,
            source="file" if is_file else "code",
        )

    except TimeoutError as e:
        logger.error(f"Execution timeout for {filename}: {e}")
        return _build_response(
            operation="python",
            result={
                "success": False,
                "error_type": "TimeoutError",
                "message": str(e),
                "stdout": "",
                "stderr": "",
            },
            filename=filename,
            timeout=timeout,
            source="file" if is_file else "code",
        )

    except NameError as e:
        logger.error(f"NameError in {filename} (possible security violation): {e}")
        tb = traceback.format_exc()
        return _build_response(
            operation="python",
            result={
                "success": False,
                "error_type": "NameError",
                "message": str(e),
                "traceback": tb,
                "stdout": "",
                "stderr": "",
                "security_note": ("This may be due to restricted builtins"),
            },
            filename=filename,
            timeout=timeout,
            source="file" if is_file else "code",
        )

    except ImportError as e:
        logger.error(f"ImportError in {filename} (security restriction): {e}")
        tb = traceback.format_exc()
        return _build_response(
            operation="python",
            result={
                "success": False,
                "error_type": "ImportError",
                "message": str(e),
                "traceback": tb,
                "stdout": "",
                "stderr": "",
                "security_note": "Imports are restricted for security",
            },
            filename=filename,
            timeout=timeout,
            source="file" if is_file else "code",
        )

    except Exception as e:
        logger.error(f"Execution error in {filename}: {e}")
        tb = traceback.format_exc()

        return _build_response(
            operation="python",
            result={
                "success": False,
                "error_type": type(e).__name__,
                "message": str(e),
                "traceback": tb,
                "stdout": "",
                "stderr": "",
            },
            filename=filename,
            timeout=timeout,
            source="file" if is_file else "code",
        )
