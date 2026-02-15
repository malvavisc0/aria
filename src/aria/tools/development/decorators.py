"""
Decorators for Python runner operations.

This module contains decorators used to add cross-cutting concerns like
error handling and validation to Python code execution functions.
"""

import inspect
from functools import wraps
from typing import Callable

from loguru import logger

from aria.tools.development._internals import (
    _error_response,
    _validate_inputs,
)
from aria.tools.development.exceptions import (
    PythonExecutionError,
    PythonExecutionTimeoutError,
    PythonRunnerError,
    PythonSecurityError,
    PythonSyntaxValidationError,
)


def with_runner_error_handling(operation_name: str) -> Callable:
    """Decorator for standardized error handling in Python runner operations.

    Handles PythonRunnerError subclasses and general exceptions,
    returning properly formatted error responses.

    Args:
        operation_name: Name of the operation for error reporting

    Returns:
        Decorator function that wraps runner operations with error handling
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> str:
            # Get identifier (code snippet or filename)
            identifier = args[0] if args else "unknown"
            if isinstance(identifier, str) and len(identifier) > 50:
                identifier = identifier[:47] + "..."

            try:
                return func(*args, **kwargs)
            except PythonSecurityError as exc:
                logger.warning(f"Security violation in {operation_name}: {exc}")
                return _error_response(operation_name, identifier, exc)
            except PythonSyntaxValidationError as exc:
                logger.warning(f"Syntax validation failed in {operation_name}: {exc}")
                return _error_response(operation_name, identifier, exc)
            except PythonExecutionTimeoutError as exc:
                logger.warning(f"Execution timeout in {operation_name}: {exc}")
                return _error_response(operation_name, identifier, exc)
            except PythonExecutionError as exc:
                logger.error(f"Execution error in {operation_name}: {exc}")
                return _error_response(operation_name, identifier, exc)
            except PythonRunnerError as exc:
                logger.error(f"Runner error in {operation_name}: {exc}")
                return _error_response(operation_name, identifier, exc)
            except (FileNotFoundError, PermissionError, OSError) as exc:
                logger.error(f"File access error in {operation_name}: {exc}")
                return _error_response(operation_name, identifier, exc)
            except Exception as exc:
                logger.exception(f"Unexpected error in {operation_name}")
                return _error_response(operation_name, identifier, exc)

        return wrapper

    return decorator


def with_input_validation(**validation_params) -> Callable:
    """Decorator for input validation in Python runner operations.

    Validates inputs before the function executes. This decorator should be
    applied before the error handling decorator.

    Args:
        **validation_params: Parameters to pass to _validate_inputs
            - code: str - Python code to validate
            - timeout: int - Timeout value to validate
            - filename: str - Filename to validate
            - capture_output: bool - Whether output capture is enabled

    Returns:
        Decorator function that validates inputs before execution

    Example:
        @with_input_validation(code=True, timeout=True)
        def my_function(code: str, timeout: int):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> str:
            # Get function signature to map args to param names
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Build validation kwargs
            validate_kwargs = {}

            # Add validation parameters if specified
            for param_name, should_validate in validation_params.items():
                if should_validate and param_name in bound_args.arguments:
                    value = bound_args.arguments[param_name]
                    if value is not None:
                        validate_kwargs[param_name] = value

            # Perform validation if we have parameters to validate
            if validate_kwargs:
                _validate_inputs(**validate_kwargs)

            return func(*args, **kwargs)

        return wrapper

    return decorator
