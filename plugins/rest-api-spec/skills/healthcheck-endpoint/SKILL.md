---
name: healthcheck-endpoint
description: Healthcheck Endpoint pattern for REST API services. Use when adding a container-orchestration health probe that verifies database connectivity and returns 200/503 status codes.
user-invocable: false
disable-model-invocation: false
---

# Healthcheck Endpoint

## Purpose

- Provide endpoint for container orchestration health checks.
- Verify database connectivity.
- Return appropriate status codes for service health.

## Structure

- Router with `/healthcheck` endpoint.
- Inject database session via dependency injection.
- Return 200 OK if healthy, 503 Service Unavailable if not.

## Template Parameters

- `{{ project_module }}` - Root module path
- `{{ containers_module }}` - DI containers module
- `{{ datasources_container }}` - Datasources container name
- `{{ database_session_class }}` - Database session class name
- `{{ database_property }}` - Property name for database in container

## Example

```python
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from my_service.api.endpoint_marker import MarkerRoute
from my_service.api.endpoint_visibility import Visibility
from my_service.containers import Datasources
from my_service.extras import DatabaseSession

__all__ = ["healthcheck_router"]

healthcheck_router = APIRouter(route_class=MarkerRoute)

@healthcheck_router.get(
    "/healthcheck",
    tags=["Debug"],
    openapi_extra={"visibility": Visibility.INTERNAL},
)
@inject
def service_healthcheck(
    datasource: DatabaseSession = Depends(Provide[Datasources.postgres_session])
):
    try:
        datasource.healthcheck()
    except Exception:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={})
    return JSONResponse(status_code=status.HTTP_200_OK, content={})
```

## Health Check Logic

1. **Inject database session** from DI container.
2. **Call healthcheck method** which typically executes `SELECT 1`.
3. **Return 200** if successful.
4. **Return 503** if any exception occurs.

## Database Session Healthcheck

The `DatabaseSession` class should have a `healthcheck()` method:

```python
class DatabaseSession:
    def healthcheck(self) -> None:
        with self.session_scope() as session:
            session.execute(text("SELECT 1"))
```

## Response Codes

| Status | Meaning | When |
| --- | --- | --- |
| 200 OK | Service healthy | Database connection successful |
| 503 Service Unavailable | Service unhealthy | Database connection failed |

## Kubernetes Integration

```yaml
livenessProbe:
  httpGet:
    path: /api/my-service/healthcheck
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5

readinessProbe:
  httpGet:
    path: /api/my-service/healthcheck
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 3
```

## Container Wiring

The healthcheck module needs explicit wiring since it uses a sub-container:

```python
def init_containers(settings: Settings) -> Containers:
    containers = Containers(...)
    # ...
    containers.datasources.wire(
        modules=[api.endpoints.healthcheck],
    )
    return containers
```

## Testing Guidance

- Test 200 response when database is available.
- Test 503 response when database is unavailable.
- Mock database session for unit tests.
- Integration test with actual database.

---

## Template

```python
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from {{ project_module }}.api.endpoint_marker import MarkerRoute
from {{ project_module }}.api.endpoint_visibility import Visibility
from {{ containers_module }} import {{ datasources_container }}
from {{ project_module }}.extras import {{ database_session_class }}

__all__ = ["healthcheck_router"]

healthcheck_router = APIRouter(route_class=MarkerRoute)

@healthcheck_router.get(
    "/healthcheck",
    tags=["Debug"],
    openapi_extra={"visibility": Visibility.INTERNAL},
)
@inject
def service_healthcheck(
    datasource: {{ database_session_class }} = Depends(Provide[{{ datasources_container }}.{{ database_property }}])
):
    try:
        datasource.healthcheck()
    except Exception:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={})
    return JSONResponse(status_code=status.HTTP_200_OK, content={})
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ project_module }}` | Root module path | `my_service` |
| `{{ containers_module }}` | DI containers module | `my_service.containers` |
| `{{ datasources_container }}` | Datasources container name | `Datasources` |
| `{{ database_session_class }}` | Database session class | `DatabaseSession` |
| `{{ database_property }}` | Property for database | `postgres_session` |
