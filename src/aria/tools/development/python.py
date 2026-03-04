"""Python execution and syntax-check tools."""

import ast
import inspect
import traceback
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from aria.tools.constants import DEFAULT_TIMEOUT, MAX_TIMEOUT
from aria.tools.development._internals import (
    _build_response,
    _capture_execution_output,
    _create_safe_globals,
    _execute_without_capture,
    _read_file_safely,
    _validate_timeout,
)
from aria.tools.development.constants import RESTRICTED_BUILTINS
from aria.tools.development.decorators import (
    with_input_validation,
    with_runner_error_handling,
)


@with_input_validation(code=True, filename=True)
@with_runner_error_handling("check_python_syntax")
def check_python_syntax(intent: str, code: str) -> str:
    """
    Check Python syntax of a code string.

    Args:
        intent: Why you're checking (e.g., "Validating before execution")
        code: Python code string to validate

    Returns:
        JSON with valid (bool), error_type, message, line_number, column
    """
    frame = inspect.currentframe()
    if frame:
        func_name = frame.f_code.co_name
        logger.debug(f"Calling {func_name} to achieve: {intent}")

    filename = "<block>"
    logger.info(f"Checking Python syntax for: {filename}")

    try:
        # Parse code with AST
        ast.parse(code)

        logger.info(f"Syntax validation passed for: {filename}")
        return _build_response(
            operation="check_python_syntax",
            result={"valid": True, "message": "Syntax is valid"},
            filename=filename,
        )

    except SyntaxError as e:
        logger.error(
            f"Syntax error in {filename} at line {e.lineno or 0}: {e.msg}"
        )
        return _build_response(
            operation="check_python_syntax",
            result={
                "valid": False,
                "error_type": "SyntaxError",
                "message": e.msg or "Syntax error",
                "line_number": e.lineno,
                "column": e.offset,
                "text": e.text.rstrip() if e.text else None,
            },
            filename=filename,
        )


@with_input_validation(file_path=True)
@with_runner_error_handling("check_python_file_syntax")
def check_python_file_syntax(intent: str, file_path: str) -> str:
    """
    Check Python syntax of a file.

    Args:
        intent: Why you're checking (e.g., "Validating saved file")
        file_path: Path to Python file relative to BASE_DIR

    Returns:
        JSON with valid (bool), error_type, message, line_number, column
    """

    frame = inspect.currentframe()
    if frame:
        func_name = frame.f_code.co_name
        logger.debug(f"Calling {func_name} to achieve: {intent}")
    logger.info(f"Checking syntax of file: {file_path}")

    code = _read_file_safely(file_path)

    try:
        # Parse code with AST
        ast.parse(source=code, filename=Path(file_path))

        logger.info(f"Syntax validation passed for: {file_path}")
        return _build_response(
            operation="check_python_file_syntax",
            result={"valid": True, "message": "Syntax is valid"},
            filename=file_path,
        )

    except SyntaxError as e:
        logger.error(
            f"Syntax error in {file_path} at line {e.lineno or 0}: {e.msg}"
        )
        return _build_response(
            operation="check_python_file_syntax",
            result={
                "valid": False,
                "error_type": "SyntaxError",
                "message": e.msg or "Syntax error",
                "line_number": e.lineno,
                "column": e.offset,
                "text": e.text.rstrip() if e.text else None,
            },
            filename=file_path,
        )


@with_input_validation(code=True, timeout=True)
@with_runner_error_handling("execute_python_code")
def execute_python_code(
    intent: str,
    code: str,
    timeout: Optional[int] = DEFAULT_TIMEOUT,
    capture_output: Optional[bool] = True,
    argv: Optional[List[str]] = None,
) -> str:
    """
    Execute a Python code string with optional timeout/output capture.

    Args:
        intent: Why you're executing (e.g., "Testing algorithm")
        code: Python code to execute
        timeout: Max seconds (default: 30, max: 300)
        capture_output: Capture stdout/stderr (default: True)
        argv: CLI arguments for sys.argv

    Returns:
        JSON with success, stdout, stderr, error_type, traceback
    """
    filename = "<block>"
    logger.info(f"Executing Python code from: {filename} (timeout={timeout}s)")

    # Validate timeout
    if not timeout:
        raise ValueError(
            f"Invalid timeout: {timeout} (must be 1-{MAX_TIMEOUT} seconds)"
        )
    _validate_timeout(timeout)

    # Log reason
    frame = inspect.currentframe()
    if frame:
        func_name = frame.f_code.co_name
        logger.debug(f"Calling {func_name} to achieve: {intent}")

    try:
        # Create safe execution environment
        safe_globals = _create_safe_globals()

        # Execute with or without output capture
        if capture_output:
            stdout_text, stderr_text = _capture_execution_output(
                code, safe_globals, timeout, filename, argv
            )
        else:
            _execute_without_capture(
                code, safe_globals, timeout, filename, argv
            )
            stdout_text, stderr_text = "", ""

        logger.info(
            f"Code executed successfully from: {filename} "
            f"(stdout: {len(stdout_text)} bytes, "
            f"stderr: {len(stderr_text)} bytes)"
        )

        return _build_response(
            operation="execute_python_code",
            result={
                "success": True,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "has_output": bool(stdout_text or stderr_text),
            },
            filename=filename,
            timeout=timeout,
        )

    except SystemExit as e:
        # Handle sys.exit() calls (e.g., from argparse --help)
        exit_code = e.code if e.code is not None else 0
        logger.info(f"Script exited with code {exit_code} in {filename}")
        return _build_response(
            operation="execute_python_code",
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
        )

    except TimeoutError as e:
        logger.error(f"Execution timeout for {filename}: {e}")
        return _build_response(
            operation="execute_python_code",
            result={
                "success": False,
                "error_type": "TimeoutError",
                "message": str(e),
                "stdout": "",
                "stderr": "",
            },
            filename=filename,
            timeout=timeout,
        )

    except NameError as e:
        # Likely trying to use restricted builtin
        logger.error(
            f"NameError in {filename} (possible security violation): {e}"
        )
        tb = traceback.format_exc()
        return _build_response(
            operation="execute_python_code",
            result={
                "success": False,
                "error_type": "NameError",
                "message": str(e),
                "traceback": tb,
                "stdout": "",
                "stderr": "",
                "security_note": "This may be due to restricted builtins",
            },
            filename=filename,
            timeout=timeout,
        )

    except ImportError as e:
        # Import blocked by security restrictions
        logger.error(f"ImportError in {filename} (security restriction): {e}")
        tb = traceback.format_exc()
        return _build_response(
            operation="execute_python_code",
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
        )

    except Exception as e:
        logger.error(f"Execution error in {filename}: {e}")
        tb = traceback.format_exc()

        return _build_response(
            operation="execute_python_code",
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
        )


@with_input_validation(file_path=True, timeout=True)
@with_runner_error_handling("execute_file")
def execute_python_file(
    intent: str,
    file_path: str,
    timeout: Optional[int] = DEFAULT_TIMEOUT,
    capture_output: Optional[bool] = True,
    argv: Optional[List[str]] = None,
) -> str:
    """
    Execute a Python file with optional timeout/output capture.

    Args:
        intent: Why you're executing (e.g., "Running test suite")
        file_path: Path to Python file relative to BASE_DIR
        timeout: Max seconds (default: 30, max: 300)
        capture_output: Capture stdout/stderr (default: True)
        argv: CLI arguments for sys.argv

    Returns:
        JSON with success, stdout, stderr, error_type, traceback.
        Sets __file__ and __dir__ in execution context.
    """
    import os

    logger.info(f"Executing Python file: {file_path} (timeout={timeout}s)")

    # Log reason
    frame = inspect.currentframe()
    if frame:
        func_name = frame.f_code.co_name
        logger.debug(f"Calling {func_name} to achieve: {intent}")

    # Validate timeout
    if not timeout:
        raise ValueError(
            f"Invalid timeout: {timeout} (must be 1-{MAX_TIMEOUT} seconds)"
        )
    _validate_timeout(timeout)

    # Read the file (handles BASE_DIR resolution)
    code = _read_file_safely(file_path)

    # Use absolute path if file exists, otherwise use as-is
    filename = (
        os.path.abspath(file_path) if os.path.exists(file_path) else file_path
    )

    try:
        # Create safe execution environment
        safe_globals = _create_safe_globals()

        # Add __file__ and __dir__ to globals for file context
        safe_globals["__file__"] = os.path.abspath(filename)
        safe_globals["__dir__"] = os.path.dirname(os.path.abspath(filename))
        logger.debug(f"Set __file__ to: {safe_globals['__file__']}")
        logger.debug(f"Set __dir__ to: {safe_globals['__dir__']}")

        # Execute with or without output capture
        if capture_output:
            stdout_text, stderr_text = _capture_execution_output(
                code, safe_globals, timeout, filename, argv
            )
        else:
            _execute_without_capture(
                code, safe_globals, timeout, filename, argv
            )
            stdout_text, stderr_text = "", ""

        logger.info(
            f"File executed successfully: {filename} "
            f"(stdout: {len(stdout_text)} bytes, "
            f"stderr: {len(stderr_text)} bytes)"
        )

        return _build_response(
            operation="execute_python_file",
            result={
                "success": True,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "has_output": bool(stdout_text or stderr_text),
            },
            filename=filename,
            timeout=timeout,
        )

    except SystemExit as e:
        # Handle sys.exit() calls
        exit_code = e.code if e.code is not None else 0
        logger.info(f"Script exited with code {exit_code} in {filename}")
        return _build_response(
            operation="execute_python_file",
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
        )

    except TimeoutError as e:
        logger.error(f"Execution timeout for {filename}: {e}")
        return _build_response(
            operation="execute_python_file",
            result={
                "success": False,
                "error_type": "TimeoutError",
                "message": str(e),
                "stdout": "",
                "stderr": "",
            },
            filename=filename,
            timeout=timeout,
        )

    except NameError as e:
        # Likely trying to use restricted builtin
        logger.error(
            f"NameError in {filename} (possible security violation): {e}"
        )
        tb = traceback.format_exc()
        return _build_response(
            operation="execute_python_file",
            result={
                "success": False,
                "error_type": "NameError",
                "message": str(e),
                "traceback": tb,
                "stdout": "",
                "stderr": "",
                "security_note": "This may be due to restricted builtins",
            },
            filename=filename,
            timeout=timeout,
        )

    except ImportError as e:
        # Import blocked by security restrictions
        logger.error(f"ImportError in {filename} (security restriction): {e}")
        tb = traceback.format_exc()
        return _build_response(
            operation="execute_python_file",
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
        )

    except Exception as e:
        logger.error(f"Execution error in {filename}: {e}")
        tb = traceback.format_exc()

        return _build_response(
            operation="execute_python_file",
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
        )


def get_restricted_builtins(intent: str) -> List[str]:
    """
    Return restricted builtins (security policy).

    Args:
        intent: Why you're checking (e.g., "Understanding security limits")

    Returns:
        List of blocked builtin names (e.g., eval, exec, open)
    """
    # Log reason
    frame = inspect.currentframe()
    if frame:
        func_name = frame.f_code.co_name
        logger.debug(f"Calling {func_name} to achieve: {intent}")

    return sorted(RESTRICTED_BUILTINS)


def get_timeout_limits(intent: str) -> Dict[str, int]:
    """
    Return timeout configuration limits.

    Args:
        intent: Why you're checking (e.g., "Planning long-running task")

    Returns:
        Dict with default (30) and maximum (300) timeout in seconds
    """
    # Log reason
    frame = inspect.currentframe()
    if frame:
        func_name = frame.f_code.co_name
        logger.debug(f"Calling {func_name} to achieve: {intent}")

    return {"default": DEFAULT_TIMEOUT, "maximum": MAX_TIMEOUT}
