"""
Retry Utilities
===============
Retry logic for transient failures (network, API, database).
"""

import time
import logging
from typing import Callable, TypeVar, Optional, List, Tuple
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


def retry_on_failure(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Exception, ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None
):
    """
    Decorator to retry a function on failure.
    
    Args:
        max_attempts: Maximum number of attempts (default: 3)
        delay: Initial delay between retries in seconds (default: 1.0)
        backoff: Multiplier for delay after each retry (default: 2.0)
        exceptions: Tuple of exceptions to catch and retry (default: all exceptions)
        on_retry: Optional callback function called on each retry (attempt_num, exception)
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts:
                        if on_retry:
                            on_retry(attempt, e)
                        else:
                            logger.warning(
                                f"{func.__name__} failed (attempt {attempt}/{max_attempts}): {e}. "
                                f"Retrying in {current_delay:.1f}s..."
                            )
                        
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
            
            # If we get here, all attempts failed
            raise last_exception
        
        return wrapper
    return decorator


def retry_with_exponential_backoff(
    func: Callable[..., T],
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Exception, ...] = (Exception,)
) -> T:
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Function to retry
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exceptions: Exceptions to catch and retry
    
    Returns:
        Function result
    
    Raises:
        Last exception if all attempts fail
    """
    delay = initial_delay
    
    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except exceptions as e:
            if attempt < max_attempts:
                logger.warning(
                    f"Attempt {attempt}/{max_attempts} failed: {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                time.sleep(min(delay, max_delay))
                delay *= 2
            else:
                logger.error(f"All {max_attempts} attempts failed: {e}")
                raise
    
    # Should never reach here, but just in case
    raise Exception("Retry logic error")


class RetryableOperation:
    """Context manager for retryable operations."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        exceptions: Tuple[Exception, ...] = (Exception,)
    ):
        self.max_attempts = max_attempts
        self.delay = delay
        self.backoff = backoff
        self.exceptions = exceptions
        self.attempt = 0
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type and issubclass(exc_type, self.exceptions):
            self.attempt += 1
            if self.attempt < self.max_attempts:
                time.sleep(self.delay)
                self.delay *= self.backoff
                return True  # Suppress exception and retry
        return False  # Don't suppress exception


# Common retry configurations
retry_network = retry_on_failure(
    max_attempts=3,
    delay=1.0,
    backoff=2.0,
    exceptions=(ConnectionError, TimeoutError, OSError)
)

retry_api = retry_on_failure(
    max_attempts=3,
    delay=0.5,
    backoff=2.0,
    exceptions=(ConnectionError, TimeoutError, ValueError)
)

retry_database = retry_on_failure(
    max_attempts=3,
    delay=0.1,
    backoff=1.5,
    exceptions=(Exception,)  # Database errors vary by driver
)
