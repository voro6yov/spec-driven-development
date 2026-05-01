---
name: auth-middleware
description: Auth Middleware pattern for REST API authentication. Use when extracting user information from JWT tokens, setting per-request user context, or skipping authentication for public/internal endpoints.
user-invocable: false
disable-model-invocation: false
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

- `{{ project_module }}` - Root module path
- `{{ application_module }}` - Application layer module path
- `{{ containers_module }}` - DI containers module path
- `{{ access_management_module }}` - Module containing user context var
- `{{ base_api_prefix }}` - Base API URL prefix
- `{{ public_endpoints }}` - List of public endpoint paths
- `{{ internal_endpoints_prefix }}` - Prefix for internal endpoints

## Example

```python
import logging

from dependency_injector.wiring import Provide, inject
from fastapi import Request

from my_service.application import AuthCommands, UserData
from my_service.containers import Containers
from my_service.infrastructure.access_management import user

__all__ = ["set_user_from_token"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PUBLIC_ENDPOINTS = (
    "/api/my-service/v1/docs",
    "/api/my-service/v1/openapi.json",
    "/api/my-service/debug/500",
    "/api/my-service/healthcheck",
    "/api/my-service/service-info/version",
    "/favicon.ico",
)
INTERNAL_ENDPOINTS_PREFIX = "/api/my-service/internal/"

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

## Context Variable Setup

In `infrastructure/access_management/context_vars.py`:

```python
from contextvars import ContextVar
from typing import TypedDict

class UserData(TypedDict):
    id: str
    email: str
    name: str

user: ContextVar[UserData] = ContextVar("user")
```

## AuthCommands Interface

The `AuthCommands` class in the application layer:

```python
from starlette.datastructures import Headers

from my_service.application.auth import UserData

class AuthCommands:
    def authorize(self, headers: Headers) -> UserData:
        # Extract and validate JWT token from Authorization header
        # Return user data if valid, raise Unauthorized/Forbidden otherwise
        ...
```

## Middleware Registration

In the entrypoint, register auth as middleware:

```python
from http import HTTPStatus
from typing import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import Response

from my_service import api
from my_service.api.error_handlers import json_error_handler
from my_service.domain import Forbidden, Unauthorized

def register_auth(app: FastAPI):
    api.add_auth_to_openapi(app)

    @app.middleware("http")
    async def handle_authorization(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        try:
            api.auth.set_user_from_token(request)

        except Unauthorized as err:
            return json_error_handler(err, HTTPStatus.UNAUTHORIZED)

        except Forbidden as err:
            return json_error_handler(err, HTTPStatus.FORBIDDEN)

        except Exception as err:
            return json_error_handler(err, HTTPStatus.INTERNAL_SERVER_ERROR)

        return await call_next(request)
```

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

from dependency_injector.wiring import Provide, inject
from fastapi import Request

from {{ application_module }} import AuthCommands, UserData
from {{ containers_module }} import Containers
from {{ access_management_module }} import user

__all__ = ["set_user_from_token"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PUBLIC_ENDPOINTS = (
{% for endpoint in public_endpoints %}
    "{{ endpoint }}",
{% endfor %}
)
INTERNAL_ENDPOINTS_PREFIX = "{{ internal_endpoints_prefix }}"

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
| `{{ public_endpoints }}` | List of public endpoint paths | See example |
| `{{ internal_endpoints_prefix }}` | Internal endpoints prefix | `/api/my-service/internal/` |
