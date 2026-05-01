---
name: service-info-endpoint
description: Service Info Endpoint pattern for REST APIs. Use when exposing build and version information (tag, date, commit hash) via an internal API endpoint for deployment verification.
user-invocable: false
disable-model-invocation: false
---

# Service Info Endpoint

## Purpose

- Expose build and version information via API.
- Provide deployment verification capability.
- Return build tag, date, and commit hash.

## Structure

- Router with `/service-info/version` endpoint.
- Inject build info from DI container.
- Return structured build information.

## Template Parameters

- `{{ project_module }}` - Root module path
- `{{ containers_module }}` - DI containers module
- `{{ core_container }}` - Core container name
- `{{ serializer_module }}` - Serializers module path

## Example

```python
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from my_service.api.endpoint_marker import MarkerRoute
from my_service.api.endpoint_visibility import Visibility
from my_service.api.serializers import BuildInfoSerializer
from my_service.containers import Core

__all__ = ["service_info_router"]

service_info_router = APIRouter(prefix="/service-info", tags=["Service Info"], route_class=MarkerRoute)

@service_info_router.get(
    "/version",
    openapi_extra={"visibility": Visibility.INTERNAL},
    response_model=BuildInfoSerializer,
)
@inject
def service_info(build_info: dict = Depends(Provide[Core.build_info])):
    return build_info
```

## BuildInfo Serializer

```python
from pydantic import Field

from .configured_base_serializer import ConfiguredResponseSerializer

__all__ = ["BuildInfoSerializer"]

class BuildInfoSerializer(ConfiguredResponseSerializer):
    build_tag: str = Field(..., alias="buildTag")
    build_date: str = Field(..., alias="buildDate")
    commit_hash: str = Field(..., alias="commitHash")
```

## Container Configuration

In the containers module:

```python
class Core(containers.DeclarativeContainer):
    config = providers.Configuration()
    build_info: providers.Provider[Dict] = providers.Dict(
        {
            "build_tag": config.info.tag,
            "build_date": config.info.date,
            "commit_hash": config.info.hash,
        },
    )
```

## Settings Configuration

Build info comes from environment variables or configuration:

```python
class InfoSettings(BaseSettings):
    tag: str = Field(default="local", alias="BUILD_TAG")
    date: str = Field(default="unknown", alias="BUILD_DATE")
    hash: str = Field(default="unknown", alias="COMMIT_HASH")
```

## Response Format

```json
{
  "buildTag": "v1.2.3",
  "buildDate": "2024-01-15T10:30:00Z",
  "commitHash": "abc123def456"
}
```

## Container Wiring

The service info module needs explicit wiring:

```python
def init_containers(settings: Settings) -> Containers:
    containers = Containers(...)
    # ...
    containers.core.wire(
        modules=[api.endpoints.service_info],
    )
    return containers
```

## Testing Guidance

- Test endpoint returns correct build info.
- Test response matches BuildInfoSerializer format.
- Verify container wiring provides build info correctly.

---

## Template

```python
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from {{ project_module }}.api.endpoint_marker import MarkerRoute
from {{ project_module }}.api.endpoint_visibility import Visibility
from {{ serializer_module }} import BuildInfoSerializer
from {{ containers_module }} import {{ core_container }}

__all__ = ["service_info_router"]

service_info_router = APIRouter(prefix="/service-info", tags=["Service Info"], route_class=MarkerRoute)

@service_info_router.get(
    "/version",
    openapi_extra={"visibility": Visibility.INTERNAL},
    response_model=BuildInfoSerializer,
)
@inject
def service_info(build_info: dict = Depends(Provide[{{ core_container }}.build_info])):
    return build_info
```

### build_info.py

```python
from pydantic import Field

from {{ base_serializer_module }} import ConfiguredResponseSerializer

__all__ = ["BuildInfoSerializer"]

class BuildInfoSerializer(ConfiguredResponseSerializer):
    build_tag: str = Field(..., alias="buildTag")
    build_date: str = Field(..., alias="buildDate")
    commit_hash: str = Field(..., alias="commitHash")
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ project_module }}` | Root module path | `my_service` |
| `{{ containers_module }}` | DI containers module | `my_service.containers` |
| `{{ core_container }}` | Core container name | `Core` |
| `{{ serializer_module }}` | Serializers module | `my_service.api.serializers` |
| `{{ base_serializer_module }}` | Base serializer path | `.configured_base_serializer` |
