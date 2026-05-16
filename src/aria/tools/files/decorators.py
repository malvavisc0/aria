"""
Decorators for file operations.

This module contains decorators used to add cross-cutting concerns like
error handling and validation to file operation functions.
"""

import inspect
from collections.abc import Callable
from functools import wraps

from loguru import logger

from aria.tools.files._internals import _error_response, _validate_inputs
from aria.tools.files.exceptions import FileOperationError, FileSecurityError


def with_file_operation_error_handling(operation_name: str) -> Callable:
    """Decorator for standardized error handling in file operations.

    Handles FileSecurityError, FileOperationError, and general exceptions,
    returning properly formatted error responses.

    Args:
        operation_name: Name of the operation for error reporting

    Returns:
        Decorator function that wraps file operations with error handling
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # First arg is `reason`. Try to extract a human-friendly identifier
            # for error reporting (file_name, dir_name, source, etc.).
            # Inject default if the LLM omitted reason — prevents crash.
            if not args and "reason" not in kwargs:
                kwargs["reason"] = "No reason provided"
            reason = args[0] if args else kwargs.get("reason", "")
            file_identifier = "unknown"
            if len(args) > 1 and isinstance(args[1], str):
                file_identifier = args[1]
            else:
                for key in (
                    "file_name",
                    "dir_name",
                    "path",
                    "source",
                    "destination",
                    "old_name",
                    "new_name",
                ):
                    if isinstance(kwargs.get(key), str):
                        file_identifier = kwargs[key]
                        break

            try:
                return func(*args, **kwargs)
            except FileSecurityError as exc:
                logger.warning(
                    f"Security validation failed for {file_identifier}: {exc}"
                )
                return _error_response(operation_name, file_identifier, exc, reason)
            except FileOperationError as exc:
                logger.error(f"File operation failed for {file_identifier}: {exc}")
                return _error_response(operation_name, file_identifier, exc, reason)
            except OSError as exc:
                logger.error(f"OS error for {file_identifier}: {exc}")
                return _error_response(operation_name, file_identifier, exc, reason)
            except Exception as exc:
                logger.exception(f"Unexpected error for {file_identifier}")
                return _error_response(operation_name, file_identifier, exc, reason)

        return wrapper

    return decorator


def with_input_validation(**validation_params) -> Callable:
    """Decorator for input validation in file operations.

    Validates inputs before the function executes. This decorator should be
    applied before the error handling decorator.

    Args:
        **validation_params: Parameters to pass to _validate_inputs
            - contents: str - Content to validate
            - chunk_size: int - Chunk size to validate
            - offset: int - Offset to validate
            - length: int - Length to validate
            - new_lines: list[str] - Lines to validate

    Returns:
        Decorator function that validates inputs before execution

    Example:
        @with_input_validation(contents=True, offset=True)
        def my_function(file_name: str, contents: str, offset: int):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get function signature to map args to param names
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Build validation kwargs
            validate_kwargs = {}

            # Always validate file_name (first argument)
            file_name = bound_args.arguments.get("file_name")
            if file_name:
                validate_kwargs["file_name"] = file_name

            # Add other validation parameters if specified
            for param_name, should_validate in validation_params.items():
                if should_validate and param_name in bound_args.arguments:
                    value = bound_args.arguments[param_name]
                    if value is not None:
                        validate_kwargs[param_name] = value

            # Perform validation if we have parameters to validate
            if validate_kwargs:
                try:
                    _validate_inputs(**validate_kwargs)
                except FileSecurityError as exc:
                    file_identifier = validate_kwargs.get("file_name", "unknown")
                    return _error_response("input_validation", file_identifier, exc)
                except FileOperationError as exc:
                    file_identifier = validate_kwargs.get("file_name", "unknown")
                    return _error_response("input_validation", file_identifier, exc)
                except Exception as exc:  # pragma: no cover
                    file_identifier = validate_kwargs.get("file_name", "unknown")
                    return _error_response("input_validation", file_identifier, exc)

            return func(*args, **kwargs)

        return wrapper

    return decorator
