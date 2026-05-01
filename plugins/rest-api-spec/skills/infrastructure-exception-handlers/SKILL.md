---
name: infrastructure-exception-handlers
description: Infrastructure Exception Handlers pattern for REST API services. Use when mapping infrastructure layer exceptions (database, external service, I/O) to HTTP status codes separately from domain errors.
user-invocable: false
disable-model-invocation: false
---

# Infrastructure Exception Handlers

## Purpose

- Map infrastructure layer exceptions to HTTP status codes.
- Separate infrastructure errors from domain errors for clearer error handling.
- Provide consistent error responses for database, external service, and I/O failures.

## Structure

- Register separate exception handler for `InfrastructureException` base class.
- Use exception mapper pattern to map specific exceptions to status codes.
- Return standardized `ErrorSerializer` response.

## Template Parameters

- `{{ project_module }}` - Root module path for imports
- `{{ infrastructure_exceptions }}` - List of infrastructure exception mappings

## When to Use

Use infrastructure exception handlers when:

- Service has infrastructure layer with its own exception hierarchy
- Need to distinguish infrastructure failures from domain validation errors
- External service calls can fail with specific error types

## Example

### Infrastructure Exception Hierarchy

```python
# infrastructure/exceptions.py
class InfrastructureException(Exception):
    def __init__(self, message: str, code: str = "infrastructure_error"):
        self.code = code
        super().__init__(message)

class InfrastructureNotFound(InfrastructureException):
    def __init__(self, message: str):
        super().__init__(message, code="not_found")

class ExternalServiceUnavailable(InfrastructureException):
    def __init__(self, message: str):
        super().__init__(message, code="service_unavailable")
```

### Handler Registration

```python
import logging
from http import HTTPStatus

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.requests import Request

from my_service.api.serializers.error import ErrorSerializer
from my_service.infrastructure.exceptions import (
    InfrastructureException,
    InfrastructureNotFound,
    ExternalServiceUnavailable,
)

logger = logging.getLogger(__name__)

def json_error_handler(error: Exception, status_code: int):
    error_message = ErrorSerializer(code=error.code, message=str(error)).model_dump()
    return JSONResponse(status_code=status_code, content=error_message)

def register_error_handler(app: FastAPI) -> None:
    @app.exception_handler(InfrastructureException)
    def handle_infrastructure_exception(req: Request, error: InfrastructureException):
        mapper = [
            (InfrastructureNotFound, HTTPStatus.NOT_FOUND),
            (ExternalServiceUnavailable, HTTPStatus.SERVICE_UNAVAILABLE),
            (InfrastructureException, HTTPStatus.BAD_REQUEST),
        ]

        for error_type, status_code in mapper:
            if issubclass(type(error), error_type):
                return json_error_handler(error, status_code)
```

## Exception Mapper Pattern

The mapper pattern provides ordered exception matching:

```python
mapper = [
    (SpecificException1, HTTPStatus.SPECIFIC_STATUS),
    (SpecificException2, HTTPStatus.ANOTHER_STATUS),
    (BaseException, HTTPStatus.DEFAULT_STATUS),  # Catch-all last
]

for error_type, status_code in mapper:
    if issubclass(type(error), error_type):
        return json_error_handler(error, status_code)
```

**Key rules:**

1. Order matters - more specific exceptions first
2. Base exception class last as catch-all
3. Use `issubclass(type(error), error_type)` for inheritance support

## Common Infrastructure Exception Mappings

| Exception | HTTP Status | Use Case |
| --- | --- | --- |
| `InfrastructureNotFound` | 404 NOT_FOUND | External resource not found |
| `ExternalServiceUnavailable` | 503 SERVICE_UNAVAILABLE | Dependent service down |
| `DatabaseConnectionError` | 503 SERVICE_UNAVAILABLE | Database unreachable |
| `TimeoutError` | 504 GATEWAY_TIMEOUT | External call timeout |
| `InfrastructureException` | 400 BAD_REQUEST | Generic infrastructure error |

## Combined Domain and Infrastructure Handlers

Register both handlers in the same function:

```python
def register_error_handler(app: FastAPI) -> None:
    @app.exception_handler(DomainException)
    def handle_domain_exception(req: Request, error: DomainException):
        mapper = [
            (Unauthorized, HTTPStatus.UNAUTHORIZED),
            (Forbidden, HTTPStatus.FORBIDDEN),
            (NotFound, HTTPStatus.NOT_FOUND),
            (Conflict, HTTPStatus.CONFLICT),
            (DomainException, HTTPStatus.BAD_REQUEST),
        ]
        for error_type, status_code in mapper:
            if issubclass(type(error), error_type):
                return json_error_handler(error, status_code)

    @app.exception_handler(InfrastructureException)
    def handle_infrastructure_exception(req: Request, error: InfrastructureException):
        mapper = [
            (InfrastructureNotFound, HTTPStatus.NOT_FOUND),
            (ExternalServiceUnavailable, HTTPStatus.SERVICE_UNAVAILABLE),
            (InfrastructureException, HTTPStatus.BAD_REQUEST),
        ]
        for error_type, status_code in mapper:
            if issubclass(type(error), error_type):
                return json_error_handler(error, status_code)

    @app.exception_handler(ValidationError)
    def bad_request(req: Request, exc: ValidationError):
        return JSONResponse(
            status_code=HTTPStatus.BAD_REQUEST,
            content=ErrorSerializer(code="bad_request", message=str(exc)).model_dump(),
        )

    @app.exception_handler(Exception)
    def handle_all_errors(req: Request, error: Exception):
        logger.error(f"Unhandled error {error}")
        return JSONResponse(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            content=ErrorSerializer(code="unhandled_error", message=str(error)).model_dump(),
        )
```

## Testing Guidance

- Test each infrastructure exception returns correct HTTP status.
- Test exception inheritance works (subclass triggers parent handler if not mapped).
- Test error response format matches `ErrorSerializer` structure.
- Test unhandled exceptions fall through to generic handler.

---

## Template

```python
import logging
from http import HTTPStatus

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.requests import Request

from {{ project_module }}.api.serializers.error import ErrorSerializer
from {{ project_module }}.infrastructure.exceptions import (
    InfrastructureException,
{% for exc in infrastructure_exceptions %}
    {{ exc.class }},
{% endfor %}
)

logger = logging.getLogger(__name__)

def json_{{ project_name }}_error_handler(error: Exception, status_code: int):
    error_message = ErrorSerializer(code=error.code, message=str(error)).model_dump()
    return JSONResponse(status_code=status_code, content=error_message)

def register_infrastructure_error_handler(app: FastAPI) -> None:
    @app.exception_handler(InfrastructureException)
    def handle_infrastructure_exception(req: Request, error: InfrastructureException):
        mapper = [
{% for exc in infrastructure_exceptions %}
            ({{ exc.class }}, HTTPStatus.{{ exc.status }}),
{% endfor %}
            (InfrastructureException, HTTPStatus.BAD_REQUEST),
        ]

        for error_type, status_code in mapper:
            if issubclass(type(error), error_type):
                return json_{{ project_name }}_error_handler(error, status_code)
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ project_module }}` | Root module path | `my_service` |
| `{{ project_name }}` | Project name for function naming | `my_service` |
| `{{ infrastructure_exceptions }}` | List of exception mappings | See below |

### Exception Mapping Structure

```python
{
    "class": "InfrastructureNotFound",
    "status": "NOT_FOUND"
}
```
