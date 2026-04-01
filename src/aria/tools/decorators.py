"""Shared decorators for tool functions."""

import inspect
from functools import wraps
from typing import Any, Callable

from loguru import logger


def log_tool_call(func: Callable) -> Callable:
    """Decorator that logs tool calls with reason parameter.

    Extracts the reason from the first argument (expected to be a string)
    and logs the function call with the function name and reason.

    Args:
        func: The function to wrap.

    Returns:
        Wrapped function that logs calls.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        reason = kwargs.get("reason") or (
            args[0] if args and isinstance(args[0], str) else "unknown"
        )
        logger.debug(f"Calling {func.__name__} — {reason}")
        return func(*args, **kwargs)

    @wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        reason = kwargs.get("reason") or (
            args[0] if args and isinstance(args[0], str) else "unknown"
        )
        logger.debug(f"Calling {func.__name__} — {reason}")
        return await func(*args, **kwargs)

    if inspect.iscoroutinefunction(func):
        return async_wrapper
    return wrapper


def tool_function(
    operation_name: str,
    *,
    validate: dict[str, bool] | None = None,
    error_handler: Callable | None = None,
    validation_decorator: Callable | None = None,
) -> Callable:
    """Compose logging, validation, and error handling for tool functions.

    Wrapper order (outermost -> innermost):
    1. log_tool_call
    2. validation decorator (optional)
    3. error handler decorator (optional)

    Args:
        operation_name: Operation name passed to the decorator factory.
        validate: Keyword args for validation_decorator.
        error_handler: Decorator factory that accepts operation_name.
        validation_decorator: Decorator factory that accepts validation kwargs.

    Returns:
        Callable: A decorator that applies the composed wrappers.
    """

    def decorator(func: Callable) -> Callable:
        result = func

        if error_handler is not None:
            result = error_handler(operation_name)(result)

        if validation_decorator is not None and validate is not None:
            result = validation_decorator(**validate)(result)

        result = log_tool_call(result)
        return result

    return decorator
