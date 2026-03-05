"""Reusable retry decorator for network-dependent tool operations."""

import asyncio
import logging
import time
from functools import wraps
from typing import Callable, Tuple, Type

logger = logging.getLogger(__name__)

DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 1.5


def with_retry(
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """Decorator for retrying operations on transient failures.

    Args:
        max_retries: Maximum number of retry attempts.
        backoff_factor: Multiplier for exponential backoff between retries.
        retryable_exceptions: Tuple of exception types that should trigger a retry.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = backoff_factor**attempt
                        logger.warning(
                            f"{func.__name__} attempt {attempt + 1}/{max_retries} "
                            f"failed: {e}. Retrying in {wait_time:.1f}s..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} attempts: {e}"
                        )
            raise last_exception  # type: ignore[misc]

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = backoff_factor**attempt
                        logger.warning(
                            f"{func.__name__} attempt {attempt + 1}/{max_retries} "
                            f"failed: {e}. Retrying in {wait_time:.1f}s..."
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_retries} attempts: {e}"
                        )
            raise last_exception  # type: ignore[misc]

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
