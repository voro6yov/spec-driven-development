---
name: error-serializer
description: Error Serializer pattern for REST API error responses. Use when defining a consistent error response format across endpoints, structuring error information for API consumers, or enabling client-side error handling based on error codes.
user-invocable: false
disable-model-invocation: false
---

# Error Serializer

## Purpose

- Define a consistent error response format across all endpoints.
- Provide structured error information for API consumers.
- Enable client-side error handling based on error codes.

## Structure

- Simple Pydantic model with `code` and `message` fields.
- No camelCase aliasing (standard JSON field names).
- Used by all exception handlers.

## Template Parameters

- `{{ additional_fields }}` - Optional extra fields (details, trace_id, etc.)

## Example

### Basic Error Serializer

```python
from pydantic import BaseModel

__all__ = ["ErrorSerializer"]

class ErrorSerializer(BaseModel):
    code: str
    message: str
```

### Error Response Format

```json
{
  "code": "not_found",
  "message": "Load with id 'abc123' not found"
}
```

### Extended Error Serializer

For APIs requiring additional error context:

```python
from pydantic import BaseModel

__all__ = ["ErrorSerializer"]

class ErrorSerializer(BaseModel):
    code: str
    message: str
    details: dict | None = None
    trace_id: str | None = None
```

Extended response:

```json
{
  "code": "validation_error",
  "message": "Request validation failed",
  "details": {
    "field": "email",
    "error": "invalid email format"
  },
  "trace_id": "abc123-def456"
}
```

## Usage in Error Handlers

```python
from fastapi.responses import JSONResponse

from my_service.api.serializers.error import ErrorSerializer

def json_error_handler(error: DomainException, status_code: int):
    error_message = ErrorSerializer(
        code=error.code,
        message=str(error),
    ).model_dump()
    return JSONResponse(status_code=status_code, content=error_message)
```

## Usage in Auth Middleware

```python
from http import HTTPStatus

from my_service.api.serializers.error import ErrorSerializer

def handle_auth_error(error: Exception, status_code: int):
    return JSONResponse(
        status_code=status_code,
        content=ErrorSerializer(
            code=error.code if hasattr(error, 'code') else 'auth_error',
            message=str(error),
        ).model_dump(),
    )
```

## Error Codes Convention

Use snake_case for error codes:

| Code | Description |
| --- | --- |
| `not_found` | Resource not found |
| `unauthorized` | Authentication required |
| `forbidden` | Permission denied |
| `conflict` | Resource state conflict |
| `bad_request` | Invalid request data |
| `validation_error` | Request validation failed |
| `unhandled_error` | Unexpected server error |

## Domain Exception Integration

Domain exceptions should expose a `code` property:

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

## File Location

```
api/serializers/
├── __init__.py
├── error.py                  # Error serializer
├── configured_base_serializer.py
└── ...
```

## Exports

In `api/serializers/__init__.py`:

```python
from .error import *

# ... other exports
```

## Pydantic V1 vs V2

Note: Use `model_dump()` for Pydantic V2:

```python
# Pydantic V2
ErrorSerializer(...).model_dump()

# Pydantic V1 (deprecated)
ErrorSerializer(...).dict()
```

## Testing Guidance

- Test error response has correct structure.
- Test all exception types produce valid error responses.
- Test error code matches exception type.
- Test message is human-readable.

---

## Template

```python
from pydantic import BaseModel

__all__ = ["ErrorSerializer"]

class ErrorSerializer(BaseModel):
    code: str
    message: str
{% for field in additional_fields %}
    {{ field.name }}: {{ field.type }}{% if field.default %} = {{ field.default }}{% endif %}

{% endfor %}
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ additional_fields }}` | Extra error fields | `[{"name": "details", "type": "dict |
