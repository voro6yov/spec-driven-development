---
name: entrypoint
description: Entrypoint pattern for REST API applications. Use when initializing a FastAPI app, wiring DI containers, registering routers/error handlers/middleware, and exposing process entry points.
user-invocable: false
disable-model-invocation: false
---

# Entrypoint

## Purpose

- Initialize and configure FastAPI application.
- Wire dependency injection containers.
- Register routers, error handlers, and middleware.
- Provide entry points for API and other processes.

## Structure

- `init_containers()` - Initialize DI containers and wiring.
- `create_fastapi()` - Create and configure FastAPI app.
- `register_auth()` - Register authentication middleware.
- `run_api()` - Start uvicorn server.

## Template Parameters

- `{{ project_module }}` - Root module path
- `{{ project_name }}` - Project name for FastAPI title
- `{{ base_api_prefix }}` - Base API URL prefix
- `{{ routers }}` - List of routers to include

## Example

```python
import logging
import os
from http import HTTPStatus
from typing import Awaitable, Callable

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import Response

from my_service import api, constants, messaging
from my_service.api.error_handlers import (
    json_error_handler,
    register_error_handler,
)
from my_service.containers import Containers
from my_service.domain import Forbidden, Unauthorized
from my_service.infrastructure.access_management import user
from my_service.settings import Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_containers(settings: Settings) -> Containers:
    containers = Containers(messaging_driver_settings=settings.messaging_driver_settings)
    containers.config.from_pydantic(settings)
    containers.init_resources()
    containers.wire(
        packages=[api, messaging],
    )

    containers.message_brokers.broker_client().user_context = user

    containers.core.wire(
        modules=[api.endpoints.service_info],
    )
    containers.datasources.wire(
        modules=[api.endpoints.healthcheck],
    )

    return containers

def create_fastapi() -> FastAPI:
    settings = Settings()
    containers: Containers = init_containers(settings)

    fastapi_app = FastAPI(
        title=constants.PROJECT_NAME,
        version=containers.config.version(),
        docs_url=f"{constants.V1_API_PREFIX}{constants.SWAGGER_DOC_URL}"
        if containers.config.documentation_enabled()
        else None,
        description=constants.DESCRIPTION,
        openapi_url=f"{constants.V1_API_PREFIX}/openapi.json"
        if containers.config.documentation_enabled()
        else None,
    )

    fastapi_app.include_router(api.debug_router, prefix=constants.BASE_API_PREFIX)
    fastapi_app.include_router(api.healthcheck_router, prefix=constants.BASE_API_PREFIX)
    fastapi_app.include_router(api.service_info_router, prefix=constants.BASE_API_PREFIX)
    fastapi_app.include_router(api.v1_router, prefix=constants.BASE_API_PREFIX)
    fastapi_app.include_router(api.v2_router, prefix=constants.BASE_API_PREFIX)

    fastapi_app.containers = containers

    register_error_handler(fastapi_app)
    register_auth(fastapi_app)

    if containers.config.instrumentation_enabled():
        from deps_observability_instrumentation import instrument_fast_api
        instrument_fast_api(fastapi_app)

    return fastapi_app

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

def run_api():
    use_web_concurrency = "WEB_CONCURRENCY" in os.environ
    env = os.getenv("ENV", "prod")
    options = {
        "host": "0.0.0.0",
        "port": 8000,
        "log_level": os.getenv("LOG_LEVEL", "debug").lower(),
        "workers": os.getenv("WEB_CONCURRENCY") if use_web_concurrency else 3,
        "reload": env == "development",
        "debug": env == "development",
    }

    uvicorn.run("my_service.entrypoint:create_fastapi", **options)
```

## Key Components

### Container Initialization

1. Create containers with settings
2. Load configuration from pydantic settings
3. Initialize resources (database connections, etc.)
4. Wire packages for dependency injection
5. Wire sub-containers for specific modules

### FastAPI Configuration

1. Create app with title, version, description
2. Configure docs URL (conditional)
3. Include all routers with base prefix
4. Store containers on app for access
5. Register error handlers and auth middleware

### Authentication Middleware

1. Add OpenAPI security schema
2. Register HTTP middleware
3. Extract and validate JWT token
4. Set user context for request
5. Handle auth errors with appropriate status codes

### Server Configuration

| Setting | Default | Description |
| --- | --- | --- |
| host | 0.0.0.0 | Bind address |
| port | 8000 | Listen port |
| workers | 3 | Worker processes |
| log_level | debug | Logging level |
| reload | false | Hot reload (dev only) |

## Testing Guidance

- Test `create_fastapi()` returns configured app.
- Test all routers are included.
- Test error handlers are registered.
- Test auth middleware is applied.
- Integration test with actual requests.

---

## Template

```python
import logging
import os
from http import HTTPStatus
from typing import Awaitable, Callable

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import Response

from {{ project_module }} import api, constants{% if messaging_enabled %}, messaging{% endif %}

from {{ project_module }}.api.error_handlers import (
    json_error_handler,
    register_error_handler,
)
from {{ project_module }}.containers import Containers
from {{ project_module }}.domain import Forbidden, Unauthorized
from {{ project_module }}.infrastructure.access_management import user
from {{ project_module }}.settings import Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_containers(settings: Settings) -> Containers:
    containers = Containers({% if messaging_enabled %}messaging_driver_settings=settings.messaging_driver_settings{% endif %})
    containers.config.from_pydantic(settings)
    containers.init_resources()
    containers.wire(
        packages=[api{% if messaging_enabled %}, messaging{% endif %}],
    )
{% if messaging_enabled %}

    containers.message_brokers.broker_client().user_context = user
{% endif %}

    containers.core.wire(
        modules=[api.endpoints.service_info],
    )
    containers.datasources.wire(
        modules=[api.endpoints.healthcheck],
    )

    return containers

def create_fastapi() -> FastAPI:
    settings = Settings()
    containers: Containers = init_containers(settings)

    fastapi_app = FastAPI(
        title=constants.PROJECT_NAME,
        version=containers.config.version(),
        docs_url=f"{constants.V1_API_PREFIX}{constants.SWAGGER_DOC_URL}"
        if containers.config.documentation_enabled()
        else None,
        description=constants.DESCRIPTION,
        openapi_url=f"{constants.V1_API_PREFIX}/openapi.json"
        if containers.config.documentation_enabled()
        else None,
    )

{% for router in routers %}
    fastapi_app.include_router(api.{{ router.name }}, prefix=constants.{{ router.prefix_constant }})
{% endfor %}

    fastapi_app.containers = containers

    register_error_handler(fastapi_app)
    register_auth(fastapi_app)

    if containers.config.instrumentation_enabled():
        from deps_observability_instrumentation import instrument_fast_api
        instrument_fast_api(fastapi_app)

    return fastapi_app

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

def run_api():
    use_web_concurrency = "WEB_CONCURRENCY" in os.environ
    env = os.getenv("ENV", "prod")
    options = {
        "host": "0.0.0.0",
        "port": 8000,
        "log_level": os.getenv("LOG_LEVEL", "debug").lower(),
        "workers": os.getenv("WEB_CONCURRENCY") if use_web_concurrency else 3,
        "reload": env == "development",
        "debug": env == "development",
    }

    uvicorn.run("{{ project_module }}.entrypoint:create_fastapi", **options)
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ project_module }}` | Root module path | `my_service` |
| `{{ messaging_enabled }}` | Whether messaging is used | `true` |
| `{{ routers }}` | List of routers to include | See below |

### Router Definition Structure

```python
{
    "name": "v1_router",
    "prefix_constant": "BASE_API_PREFIX"
}
```
