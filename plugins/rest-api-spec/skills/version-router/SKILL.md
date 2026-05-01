---
name: version-router
description: Version Router pattern for REST API versioning. Use when aggregating resource routers under a versioned URL prefix (e.g., /v1, /v2) for inclusion in a FastAPI app.
user-invocable: false
disable-model-invocation: false
---

# Version Router

## Purpose

- Aggregate all resource routers for an API version.
- Apply version prefix to all contained routes.
- Export single router for inclusion in main app.

## Structure

- Create `APIRouter` with version prefix (e.g., `/v1`).
- Import and include all resource routers.
- Export the version router.

## Template Parameters

- `{{ version_prefix }}` - URL prefix for the version (e.g., `/v1`)
- `{{ router_name }}` - Variable name for the router
- `{{ resource_routers }}` - List of resource routers to include

## Example

```python
from fastapi import APIRouter

from .conveyors import *
from .loads import *

__all__ = ["v1_router"]

v1_router = APIRouter(prefix="/v1")

v1_router.include_router(loads_router)
v1_router.include_router(conveyors_router)
```

## Router Hierarchy

```
FastAPI App
└── api/ (BASE_API_PREFIX: /api/my-service)
    ├── debug_router
    ├── healthcheck_router
    ├── service_info_router
    ├── v1_router (prefix: /v1)
    │   ├── loads_router (prefix: /loads)
    │   └── conveyors_router (prefix: /conveyors)
    └── v2_router (prefix: /v2)
        ├── loads_router (prefix: /loads)
        └── warehouse_metrics_router (prefix: /warehouse-metrics)
```

## Resulting URLs

- `/api/my-service/v1/loads`
- `/api/my-service/v1/loads/{loadId}`
- `/api/my-service/v1/conveyors`
- `/api/my-service/v2/loads`

## Usage in Entrypoint

```python
from my_service import api, constants

def create_fastapi() -> FastAPI:
    fastapi_app = FastAPI(...)

    fastapi_app.include_router(api.debug_router, prefix=constants.BASE_API_PREFIX)
    fastapi_app.include_router(api.healthcheck_router, prefix=constants.BASE_API_PREFIX)
    fastapi_app.include_router(api.service_info_router, prefix=constants.BASE_API_PREFIX)
    fastapi_app.include_router(api.v1_router, prefix=constants.BASE_API_PREFIX)
    fastapi_app.include_router(api.v2_router, prefix=constants.BASE_API_PREFIX)

    return fastapi_app
```

## Module Exports

In `endpoints/__init__.py`:

```python
from .debug import *
from .healthcheck import *
from .service_info import *
from .v1 import *
from .v2 import *

__all__ = (
    debug.__all__
    + healthcheck.__all__
    + service_info.__all__
    + v1.__all__
    + v2.__all__
)
```

## Testing Guidance

- Test that version prefix is applied to all routes.
- Test that all resource routers are accessible.
- Verify URL structure matches expected pattern.

---

## Template

```python
from fastapi import APIRouter

{% for router_import in resource_routers %}
from .{{ router_import.module }} import *
{% endfor %}

__all__ = ["{{ router_name }}"]

{{ router_name }} = APIRouter(prefix="{{ version_prefix }}")

{% for router in resource_routers %}
{{ router_name }}.include_router({{ router.router_var }})
{% endfor %}
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ version_prefix }}` | URL prefix for version | `/v1`, `/v2` |
| `{{ router_name }}` | Variable name for router | `v1_router` |
| `{{ resource_routers }}` | List of routers to include | See below |

### Router Definition Structure

```python
{
    "module": "conveyors",
    "router_var": "conveyors_router"
}
```
