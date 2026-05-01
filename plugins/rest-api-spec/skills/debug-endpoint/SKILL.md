---
name: debug-endpoint
description: Debug Endpoint pattern for REST APIs. Use when adding intentional error endpoints to verify error handlers, logging, and observability tooling in deployed environments.
user-invocable: false
disable-model-invocation: false
---

# Debug Endpoint

## Purpose

- Provide intentional error endpoints for testing error handling.
- Verify error handlers and logging work correctly in deployed environments.
- Test observability tools (Sentry, Application Insights, etc.) capture errors.

## Structure

- Simple router with `/debug` prefix.
- Endpoints that intentionally raise errors.
- Marked with `Visibility.INTERNAL` to hide from public docs.
- No authentication required (listed in public endpoints).

## Template Parameters

- `{{ debug_prefix }}` - URL prefix (default: `/debug`)
- `{{ error_endpoints }}` - List of error types to expose

## Example

```python
from fastapi import APIRouter, status

from my_service.api.endpoint_marker import MarkerRoute
from my_service.api.endpoint_visibility import Visibility

__all__ = ["debug_router"]

debug_router = APIRouter(prefix="/debug", tags=["Debug"], route_class=MarkerRoute)

@debug_router.get(
    "/500",
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    openapi_extra={"visibility": Visibility.INTERNAL},
)
def raise_internal_server_error():
    raise ValueError("Intentional error for testing")
```

## Available Debug Endpoints

| Endpoint | Status Code | Error Type | Purpose |
| --- | --- | --- | --- |
| `/debug/500` | 500 | `ValueError` | Test unhandled exception handling |
| `/debug/400` | 400 | `DomainException` | Test domain error handling |
| `/debug/404` | 404 | `NotFound` | Test not found handling |
| `/debug/timeout` | 504 | `TimeoutError` | Test timeout handling |

## Extended Example

```python
from fastapi import APIRouter, HTTPException, status

from my_service.api.endpoint_marker import MarkerRoute
from my_service.api.endpoint_visibility import Visibility
from my_service.domain import DomainException, NotFound

__all__ = ["debug_router"]

debug_router = APIRouter(prefix="/debug", tags=["Debug"], route_class=MarkerRoute)

@debug_router.get(
    "/500",
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    openapi_extra={"visibility": Visibility.INTERNAL},
)
def raise_internal_server_error():
    raise ValueError("Intentional 500 error for testing")

@debug_router.get(
    "/400",
    status_code=status.HTTP_400_BAD_REQUEST,
    openapi_extra={"visibility": Visibility.INTERNAL},
)
def raise_bad_request():
    raise DomainException("Intentional domain error for testing")

@debug_router.get(
    "/404",
    status_code=status.HTTP_404_NOT_FOUND,
    openapi_extra={"visibility": Visibility.INTERNAL},
)
def raise_not_found():
    raise NotFound("Resource not found for testing")

@debug_router.get(
    "/http-exception",
    openapi_extra={"visibility": Visibility.INTERNAL},
)
def raise_http_exception():
    raise HTTPException(
        status_code=status.HTTP_418_IM_A_TEAPOT,
        detail="I'm a teapot (debug endpoint)",
    )
```

## Auth Configuration

Add debug endpoints to public endpoints list:

```python
# In auth.py
PUBLIC_ENDPOINTS = (
    "/api/my-service/v1/docs",
    "/api/my-service/v1/openapi.json",
    "/api/my-service/debug/500",  # Add debug endpoints
    "/api/my-service/healthcheck",
    "/api/my-service/service-info/version",
    "/favicon.ico",
)
```

## Entrypoint Registration

```python
def create_fastapi() -> FastAPI:
    # ... FastAPI app creation
    
    fastapi_app.include_router(api.debug_router, prefix=constants.BASE_API_PREFIX)
    fastapi_app.include_router(api.healthcheck_router, prefix=constants.BASE_API_PREFIX)
    # ...
```

## Security Considerations

- Mark all debug endpoints as `Visibility.INTERNAL`.
- Consider disabling in production via feature flag.
- Don't expose sensitive information in error messages.
- Log when debug endpoints are called.

### Optional: Environment-Based Disable

```python
import os

from fastapi import APIRouter

debug_router = APIRouter(prefix="/debug", tags=["Debug"])

if os.getenv("ENV") != "production":
    @debug_router.get("/500")
    def raise_internal_server_error():
        raise ValueError("Intentional error for testing")
```

## Testing Guidance

- Test error response format matches `ErrorSerializer`.
- Test error is logged correctly.
- Test observability tools capture the error.
- Verify endpoint is accessible without authentication.

---

## Template

```python
from fastapi import APIRouter, status

from {{ project_module }}.api.endpoint_marker import MarkerRoute
from {{ project_module }}.api.endpoint_visibility import Visibility
{% if domain_exceptions %}
from {{ project_module }}.domain import {{ domain_exceptions | join(', ') }}
{% endif %}

__all__ = ["debug_router"]

debug_router = APIRouter(prefix="{{ debug_prefix }}", tags=["Debug"], route_class=MarkerRoute)

@debug_router.get(
    "/500",
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    openapi_extra={"visibility": Visibility.INTERNAL},
)
def raise_internal_server_error():
    raise ValueError("Intentional error for testing")
{% for endpoint in additional_endpoints %}

@debug_router.get(
    "/{{ endpoint.path }}",
    status_code=status.{{ endpoint.status_code }},
    openapi_extra={"visibility": Visibility.INTERNAL},
)
def {{ endpoint.function_name }}():
    raise {{ endpoint.exception }}("{{ endpoint.message }}")
{% endfor %}
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ project_module }}` | Root module path | `my_service` |
| `{{ debug_prefix }}` | URL prefix | `/debug` |
| `{{ domain_exceptions }}` | Domain exceptions to import | `["DomainException", "NotFound"]` |
| `{{ additional_endpoints }}` | Extra debug endpoints | See below |

### Additional Endpoint Structure

```python
{
    "path": "400",
    "status_code": "HTTP_400_BAD_REQUEST",
    "function_name": "raise_bad_request",
    "exception": "DomainException",
    "message": "Intentional domain error for testing"
}
```
