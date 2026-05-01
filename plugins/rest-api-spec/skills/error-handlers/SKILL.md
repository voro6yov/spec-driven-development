---
name: error-handlers
description: Error Handlers pattern for REST API exception-to-HTTP mapping. Use when registering FastAPI exception handlers that translate domain and infrastructure exceptions into consistent JSON error responses.
user-invocable: false
disable-model-invocation: false
---

# Error Handlers

# Error Handlers

## Purpose

- Map domain and infrastructure exceptions to appropriate HTTP status codes.
- Provide consistent error response format across all endpoints.
- Centralize error handling logic.

## Structure

- Register exception handlers with FastAPI app.
- Map exception types to HTTP status codes.
- Use `ErrorSerializer` for consistent response format.

## Template Parameters

- `{{ project_module }}` - Root module path for the project
- `{{ domain_exceptions }}` - List of domain exception types to handle
- `{{ infrastructure_exceptions }}` - List of infrastructure exception types
- `{{ error_serializer_module }}` - Import path for ErrorSerializer

## Exception Mapping

| Exception Type | HTTP Status Code |
| --- | --- |
| `Unauthorized` | 401 UNAUTHORIZED |
| `Forbidden` | 403 FORBIDDEN |
| `NotFound` | 404 NOT_FOUND |
| `Conflict` | 409 CONFLICT |
| `DomainException` | 400 BAD_REQUEST |
| `InfrastructureNotFound` | 404 NOT_FOUND |
| `InfrastructureException` | 400 BAD_REQUEST |
| `ValidationError` | 400 BAD_REQUEST |
| `Exception` | 500 INTERNAL_SERVER_ERROR |

## Error Response Format

```json
{
  "code": "not_found",
  "message": "Resource with id 'abc123' not found"
}
```

## Example

```python
import logging
from http import HTTPStatus

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.requests import Request

from my_service.api.serializers.error import ErrorSerializer
from my_service.domain import (
    Conflict,
    DomainException,
    Forbidden,
    NotFound,
    Unauthorized,
)
from my_service.infrastructure.exceptions import (
    InfrastructureException,
    InfrastructureNotFound,
)

logger = logging.getLogger(__name__)

def json_error_handler(error: DomainException, status_code: int):
    error_message = ErrorSerializer(code=error.code, message=str(error)).model_dump()
    return JSONResponse(status_code=status_code, content=error_message)

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

## Domain Exception Requirements

Domain exceptions should have a `code` property:

```python
class DomainException(Exception):
    code: str = "domain_error"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

class NotFound(DomainException):
    code: str = "not_found"

class Conflict(DomainException):
    code: str = "conflict"
```

## Error Serializer

```python
from pydantic import BaseModel

__all__ = ["ErrorSerializer"]

class ErrorSerializer(BaseModel):
    code: str
    message: str
```

## Pydantic Version Note

The templates use `.model_dump()` which is the Pydantic v2 API. If using Pydantic v1, replace with `.dict()`:

| Pydantic Version | Method |
| --- | --- |
| v2.x (recommended) | `.model_dump()` |
| v1.x (legacy) | `.dict()` |

Ensure consistency across your codebase - don't mix both methods.

## Registration

Error handlers are registered in the entrypoint:

```python
def create_fastapi() -> FastAPI:
    # ... FastAPI app creation
    register_error_handler(fastapi_app)
    # ...
```

## Testing Guidance

- Test each exception type maps to correct HTTP status.
- Verify error response format matches `ErrorSerializer`.
- Test validation errors from Pydantic.
- Test catch-all handler for unexpected exceptions.

---

## Template

```python
import logging
from http import HTTPStatus

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.requests import Request

from {{ error_serializer_module }} import ErrorSerializer
from {{ project_module }}.domain import (
{% for exc in domain_exceptions %}
    {{ exc }},
{% endfor %}
)
from {{ project_module }}.infrastructure.exceptions import (
{% for exc in infrastructure_exceptions %}
    {{ exc }},
{% endfor %}
)

logger = logging.getLogger(__name__)

def json_error_handler(error: DomainException, status_code: int):
    error_message = ErrorSerializer(code=error.code, message=str(error)).model_dump()
    return JSONResponse(status_code=status_code, content=error_message)

def register_error_handler(app: FastAPI) -> None:
    @app.exception_handler(DomainException)
    def handle_domain_exception(req: Request, error: DomainException):
        mapper = [
{% for mapping in domain_exception_mappings %}
            ({{ mapping.exception }}, HTTPStatus.{{ mapping.status }}),
{% endfor %}
        ]

        for error_type, status_code in mapper:
            if issubclass(type(error), error_type):
                return json_error_handler(error, status_code)

    @app.exception_handler(InfrastructureException)
    def handle_infrastructure_exception(req: Request, error: InfrastructureException):
        mapper = [
{% for mapping in infrastructure_exception_mappings %}
            ({{ mapping.exception }}, HTTPStatus.{{ mapping.status }}),
{% endfor %}
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

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ project_module }}` | Root module path | `my_service` |
| `{{ error_serializer_module }}` | Path to ErrorSerializer | `my_service.api.serializers.error` |
| `{{ domain_exceptions }}` | List of domain exception imports | `["DomainException", "NotFound", "Forbidden"]` |
| `{{ infrastructure_exceptions }}` | List of infrastructure exceptions | `["InfrastructureException", "InfrastructureNotFound"]` |
| `{{ domain_exception_mappings }}` | Exception to status mappings | See example above |
