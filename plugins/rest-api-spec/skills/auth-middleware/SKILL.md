---
name: auth-middleware
description: Auth Middleware pattern for REST API authentication. Use when implementing JWT-based request authentication, user context propagation, or distinguishing public, internal, and protected endpoints in a FastAPI service.
user-invocable: false
---

# Auth Middleware

## Purpose

- Extract user information from JWT tokens in request headers.
- Set user context for the current request.
- Skip authentication for public endpoints.

## Structure

- Define public endpoints that don't require authentication.
- Inject `AuthCommands` for token validation.
- Use context variables to store current user.
- Provide utility functions for accessing current user.

## Template Parameters

- `{{ application_module }}` - Application layer module path
- `{{ containers_module }}` - DI containers module path
- `{{ access_management_module }}` - Module containing user context var
- `{{ shared_domain_module }}` - Shared domain module exporting `Forbidden` / `Unauthorized`
- `{{ public_endpoints }}` - List of public endpoint paths
- `{{ internal_endpoints_prefix }}` - Prefix for internal endpoints

The module is expected to live inside the `api` package as `api/auth.py`, alongside a sibling `api/fastapi_auth.py` that defines `add_auth_to_openapi` and `api/error_handlers.py` that defines `json_error_handler`. Both are imported via direct submodule imports (`from .fastapi_auth import …`, `from .error_handlers import …`) rather than through the package namespace, because `auth.py` is typically loaded while `api/__init__.py` is still executing — at which point names re-exported through the package would not yet be bound.

## UserData TypedDict

`UserData` is defined once in the application layer (e.g. `application/auth/user_data.py`) and reused by both the `AuthCommands` interface and the infrastructure context var:

```python
from typing import TypedDict

class UserData(TypedDict):
    id: str
    email: str
    name: str
```

## AuthCommands Interface

The `AuthCommands` class in the application layer:

```python
from starlette.datastructures import Headers

from .user_data import UserData

class AuthCommands:
    def authorize(self, headers: Headers) -> UserData:
        return UserData(
            id="stub-user-id",
            email="stub@example.com",
            name="Stub User",
        )
```

## Middleware Registration

`register_auth` lives in the same `api/auth.py` module as `set_user_from_token` and is the public entrypoint exported via `__all__`. The application bootstrap calls `register_auth(app)` once during FastAPI startup; it wires `add_auth_to_openapi` and installs the `handle_authorization` middleware that delegates to `set_user_from_token` per request and translates `Unauthorized` / `Forbidden` into JSON error responses via `json_error_handler`.

## Endpoint Categories

### Public Endpoints

No authentication required:

- Documentation endpoints (`/docs`, `/openapi.json`)
- Health check endpoints
- Debug endpoints

### Internal Endpoints

Service-to-service calls, typically authenticated via service account:

- Prefixed with `/internal/`

### Protected Endpoints

All other endpoints require user authentication via JWT token.

## Testing Guidance

- Test public endpoints are accessible without token.
- Test protected endpoints return 401 without token.
- Test valid token sets user context correctly.
- Test invalid token returns appropriate error.
- Test internal endpoints bypass user auth.

---

## Template

```python
import logging
from http import HTTPStatus
from typing import Awaitable, Callable

from dependency_injector.wiring import Provide, inject
from fastapi import FastAPI, Request
from fastapi.responses import Response

from {{ application_module }} import AuthCommands, UserData
from {{ containers_module }} import Containers
from {{ access_management_module }} import user
from {{ shared_domain_module }} import Forbidden, Unauthorized

from .fastapi_auth import add_auth_to_openapi
from .error_handlers import json_error_handler

__all__ = ["register_auth"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PUBLIC_ENDPOINTS = (
{% for endpoint in public_endpoints %}
    "{{ endpoint }}",
{% endfor %}
)
INTERNAL_ENDPOINTS_PREFIX = "{{ internal_endpoints_prefix }}"

def register_auth(app: FastAPI) -> None:
    add_auth_to_openapi(app)

    @app.middleware("http")
    async def handle_authorization(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        try:
            set_user_from_token(request)

        except Unauthorized as err:
            return json_error_handler(err, HTTPStatus.UNAUTHORIZED)

        except Forbidden as err:
            return json_error_handler(err, HTTPStatus.FORBIDDEN)

        except Exception as err:
            return json_error_handler(err, HTTPStatus.INTERNAL_SERVER_ERROR)

        return await call_next(request)

@inject
def set_user_from_token(
    request: Request,
    auth_commands: AuthCommands = Provide[Containers.auth_commands],
) -> None:
    if request.url.path in PUBLIC_ENDPOINTS or INTERNAL_ENDPOINTS_PREFIX in request.url.path:
        return

    user_data = auth_commands.authorize(request.headers)

    set_current_user(user_data)

def set_current_user(user_data: UserData) -> None:
    user.set(user_data)

def get_current_user_email() -> str:
    current_user = user.get()
    return current_user["email"]

def get_current_user_id() -> str:
    current_user = user.get()
    return current_user["id"]
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ application_module }}` | Application layer module | `my_service.application` |
| `{{ containers_module }}` | DI containers module | `my_service.containers` |
| `{{ access_management_module }}` | User context var module | `my_service.infrastructure.access_management` |
| `{{ shared_domain_module }}` | Shared domain module exporting `Forbidden` / `Unauthorized` | `my_service.domain.shared` |
| `{{ public_endpoints }}` | List of public endpoint paths | `("/api/my-service/v1/docs", "/api/my-service/healthcheck", ...)` |
| `{{ internal_endpoints_prefix }}` | Internal endpoints prefix | `/api/my-service/internal/` |

## Rendered Snippet

For `application_module = my_service.application`, `containers_module = my_service.containers`, `access_management_module = my_service.infrastructure.access_management`, `shared_domain_module = my_service.domain.shared`, `internal_endpoints_prefix = /api/my-service/internal/`, and the public endpoints below, the head of the rendered file becomes:

```python
from my_service.application import AuthCommands, UserData
from my_service.containers import Containers
from my_service.infrastructure.access_management import user
from my_service.domain.shared import Forbidden, Unauthorized

from .fastapi_auth import add_auth_to_openapi
from .error_handlers import json_error_handler

__all__ = ["register_auth"]

PUBLIC_ENDPOINTS = (
    "/api/my-service/v1/docs",
    "/api/my-service/v1/openapi.json",
    "/api/my-service/debug/500",
    "/api/my-service/healthcheck",
    "/api/my-service/service-info/version",
    "/favicon.ico",
)
INTERNAL_ENDPOINTS_PREFIX = "/api/my-service/internal/"
```
