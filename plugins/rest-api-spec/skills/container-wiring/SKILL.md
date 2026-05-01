---
name: container-wiring
description: Container Wiring pattern for REST APIs. Use when connecting dependency injection containers to FastAPI endpoints, wiring sub-containers to specific modules, or attaching containers to the app for test overrides.
user-invocable: false
disable-model-invocation: false
---

# Container Wiring

## Purpose

- Connect dependency injection containers to API endpoints.
- Enable `@inject` decorator to resolve dependencies.
- Wire specific modules to sub-containers.

## Structure

- Main wiring for API package in `init_containers()`.
- Sub-container wiring for specific modules.
- Container attachment to FastAPI app.

## Wiring Patterns

### Package-Level Wiring

Wire entire API package to main container:

```python
from my_service import api, messaging

def init_containers(settings: Settings) -> Containers:
    containers = Containers(...)
    containers.config.from_pydantic(settings)
    containers.init_resources()

    # Wire main container to packages
    containers.wire(packages=[api, messaging])

    return containers
```

This enables `@inject` to work in all modules within `api/` package.

### Module-Level Wiring

Wire specific modules to sub-containers:

```python
def init_containers(settings: Settings) -> Containers:
    containers = Containers(...)
    # ... main wiring ...

    # Wire sub-containers to specific modules
    containers.core.wire(
        modules=[api.endpoints.service_info],
    )
    containers.datasources.wire(
        modules=[api.endpoints.healthcheck],
    )

    return containers
```

Required when:

- Module needs dependencies from sub-container
- Sub-container has dependencies not in main container
- Module uses `Provide[SubContainer.property]`

### When to Use Which

| Dependency Source | Wiring Approach |
| --- | --- |
| Main container (`Containers.xxx`) | Package wiring |
| Sub-container (`Core.xxx`) | Module wiring to sub-container |
| Multiple sub-containers | Multiple module wirings |

## Common Sub-Containers

### Core Container

Used for build info and metadata:

```python
class Core(containers.DeclarativeContainer):
    config = providers.Configuration()
    build_info: providers.Provider[Dict] = providers.Dict({
        "build_tag": config.info.tag,
        "build_date": config.info.date,
        "commit_hash": config.info.hash,
    })
```

Wire to service info endpoint:

```python
containers.core.wire(modules=[api.endpoints.service_info])
```

### Datasources Container

Used for database sessions:

```python
class Datasources(containers.DeclarativeContainer):
    config = providers.Configuration()
    postgres_session: providers.Provider[DatabaseSession] = providers.Singleton(
        DatabaseSession, ...
    )
```

Wire to healthcheck endpoint:

```python
containers.datasources.wire(modules=[api.endpoints.healthcheck])
```

## Container on FastAPI App

Store containers on the FastAPI app for access in tests:

```python
def create_fastapi() -> FastAPI:
    containers = init_containers(settings)

    fastapi_app = FastAPI(...)

    # Store containers for test access
    fastapi_app.containers = containers

    return fastapi_app
```

Access in tests:

```python
def test_endpoint(client):
    app = client.app
    app.containers.some_dependency.override(mock_dependency)
```

## Endpoint Dependency Injection

### From Main Container

```python
from my_service.containers import Containers

@router.get("/resources")
@inject
def get_resources(
    queries: ResourceQueries = Depends(Provide[Containers.resource_queries]),
):
    ...
```

### From Sub-Container

```python
from my_service.containers import Core

@router.get("/version")
@inject
def service_info(
    build_info: dict = Depends(Provide[Core.build_info]),
):
    ...
```

## Troubleshooting

### Dependency Not Found

**Error**: `Provide[X.y] dependency not found`

**Cause**: Module not wired to container

**Solution**: Add wiring:

```python
containers.wire(modules=[module_with_dependency])
# or for sub-container
sub_container.wire(modules=[module_with_dependency])
```

### Circular Import

**Error**: `ImportError: cannot import name 'Containers'`

**Cause**: Import at module level causes cycle

**Solution**: Use late import or restructure:

```python
# Instead of top-level import
from my_service.containers import Containers

# Use in function
def init_containers():
    from my_service.containers import Containers
    ...
```

### Override Not Working

**Error**: Test override doesn't affect endpoint

**Cause**: Container already wired before override

**Solution**: Override before wiring or reset:

```python
containers.some_dep.reset()
containers.some_dep.override(mock)
```

## Testing with Container Overrides

```python
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client(app):
    # Override before creating client
    app.containers.resource_queries.override(MockResourceQueries())
    yield TestClient(app)
    app.containers.resource_queries.reset()
```
