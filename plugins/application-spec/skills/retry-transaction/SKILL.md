---
name: retry-transaction
description: Retry Transaction pattern for application services. Use when implementing operations that need to retry on transaction errors (e.g., deadlocks, connection issues) with exponential backoff.
user-invocable: false
disable-model-invocation: false
---

# Retry Transaction

Purpose: Provide decorator for retrying operations on transaction errors with exponential backoff

## Purpose

- Provide decorator for retrying operations on transaction errors.
- Handle database operational errors (e.g., deadlocks, connection issues) with exponential backoff.
- Log retry attempts for observability.

## Structure

- Define decorator function `retry_on_transaction_error()` with configurable parameters.
- Accept `max_attempts`, `initial_delay`, `backoff_factor`, and `cutoff` parameters.
- Catch specific exception types (e.g., `OperationalError`).
- Use exponential backoff with configurable cutoff.
- Log retry attempts with attempt count.

## Behavior checklist

- Only retry on specific exception types (transaction-related errors).
- Use exponential backoff: `delay = min(initial_delay * (backoff_factor ** attempts), cutoff)`.
- Log each retry attempt with error details.
- Re-raise exception after max attempts exceeded.
- Return decorator function that wraps the original function.

## Testing guidance

- Write unit tests that verify retry logic with different exception scenarios.
- Test that non-retryable exceptions are immediately re-raised.
- Verify exponential backoff calculation is correct.
- Test max attempts limit is respected.

---

## Template

```python
# flake8: noqa
import logging
import time
from typing import Any, Callable

__all__ = ["retry_on_transaction_error"]

def retry_on_transaction_error(
    max_attempts: int = 15,
    initial_delay: float = 1,
    backoff_factor: float = 2,
    cutoff: float = 10,
) -> Callable:
    _logger = logging.getLogger("RetryTransaction")

    def decorator(func: Callable) -> Callable:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempts: int = 0
            delay: float = initial_delay

            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if e.__class__.__name__ != "OperationalError":
                        raise

                    attempts += 1
                    if attempts >= max_attempts:
                        raise e

                    time.sleep(min(delay, cutoff))
                    delay *= backoff_factor

                    _logger.error(f"Transaction failed. Retrying... Attempt {attempts}/{max_attempts}")

        return wrapper

    return decorator
```

## Placeholders

This template is **fully generic** and requires no template variables. It can be used as-is in any project. The template includes:

- Standard Python imports (logging, time, typing)
- Configurable retry parameters with sensible defaults
- Generic exception handling for `OperationalError`
- Exponential backoff implementation

If you need to catch different exception types, modify the exception check in the template:

```python
if e.__class__.__name__ != "OperationalError":
```
