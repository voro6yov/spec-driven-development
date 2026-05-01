---
name: internal-router
description: Internal Router pattern for REST API endpoints. Use when grouping endpoints for service-to-service communication, bypassing user authentication, or separating internal API surface from public/external endpoints.
user-invocable: false
disable-model-invocation: false
---

# Internal Router

## Purpose

- Group endpoints for service-to-service communication.
- Bypass user authentication (may use service account auth).
- Separate internal API surface from public/external endpoints.

## Structure

- Dedicated `internal/` directory under `endpoints/`.
- Router with `/internal` prefix.
- Endpoints marked with `Visibility.INTERNAL`.
- Aggregates multiple internal resource routers.

## Template Parameters

- `{{ project_module }}` - Root module path
- `{{ internal_prefix }}` - URL prefix (usually from constants)
- `{{ resource_routers }}` - List of internal resource routers to include

## When to Use

Use internal router pattern when:

- Exposing endpoints for other services to call
- Analytics or metrics endpoints consumed by internal tools
- Admin operations not exposed to end users
- Bulk operations or data synchronization endpoints

## Example

### Internal Router Aggregation

```python
from fastapi import APIRouter

from my_service.constants import INTERNAL_PREFIX

from .conveyors import *
from .tires import *

__all__ = ["internal_router"]

internal_router = APIRouter(prefix=INTERNAL_PREFIX)

internal_router.include_router(conveyors_router)
internal_router.include_router(tires_router)
```

### Internal Resource Endpoint

```python
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status

from my_service.application import TireQueries
from my_service.containers import Containers

from ...endpoint_marker import MarkerRoute
from ...endpoint_visibility import Visibility

__all__ = ["tires_router"]

tires_router = APIRouter(prefix="/tires", tags=["Tires"], route_class=MarkerRoute)

@tires_router.get(
    "/analytics",
    status_code=status.HTTP_200_OK,
    openapi_extra={"visibility": Visibility.INTERNAL},
    response_model=GetTiresAnalyticsResponse,
)
@inject
def get_tires_analytics(
    request: GetTiresAnalyticsRequest = Depends(),
    tire_queries: TireQueries = Depends(Provide[Containers.tire_queries]),
):
    return GetTiresAnalyticsResponse.from_domain(
        tire_queries.get_analytics(
            conveyor_id=request.conveyor_id,
            creation_time_from=request.creation_time_from,
            creation_time_to=request.creation_time_to,
        ),
    )
```

## Directory Structure

```
api/endpoints/
├── __init__.py           # Exports all routers including internal
├── debug.py
├── healthcheck.py
├── service_info.py
├── internal/             # Internal endpoints directory
│   ├── __init__.py       # Internal router aggregation
│   ├── conveyors.py      # Internal conveyor endpoints
│   └── tires.py          # Internal tire endpoints
├── v1/
│   └── ...
└── v2/
    └── ...
```

## Authentication Handling

Internal endpoints typically bypass user authentication:

```python
# In auth.py
INTERNAL_ENDPOINTS_PREFIX = "/api/my-service/internal/"

@inject
def set_user_from_token(request: Request, ...):
    # Skip auth for internal endpoints
    if INTERNAL_ENDPOINTS_PREFIX in request.url.path:
        return
    
    # Normal auth flow for other endpoints
    user_data = auth_commands.authorize(request.headers)
    set_current_user(user_data)
```

For service-to-service authentication, consider:

- API keys in headers
- Service account tokens
- mTLS (mutual TLS)

## Entrypoint Registration

```python
def create_fastapi() -> FastAPI:
    # ... FastAPI app creation
    
    fastapi_app.include_router(api.v1_router, prefix=constants.BASE_API_PREFIX)
    fastapi_app.include_router(api.v2_router, prefix=constants.BASE_API_PREFIX)
    fastapi_app.include_router(api.internal_router, prefix=constants.BASE_API_PREFIX)
    
    # ...
```

## Endpoints Aggregation Export

Update `api/endpoints/__init__.py`:

```python
from .debug import *
from .healthcheck import *
from .internal import *
from .service_info import *
from .v1 import *
from .v2 import *

__all__ = (
    debug.__all__
    + healthcheck.__all__
    + service_info.__all__
    + v1.__all__
    + internal.__all__
    + v2.__all__
)
```

## Common Internal Endpoint Types

| Type | Purpose | Example |
| --- | --- | --- |
| Analytics | Aggregated metrics | `/internal/tires/analytics` |
| Bulk Operations | Batch processing | `/internal/items/bulk-update` |
| Admin | Administrative actions | `/internal/cache/invalidate` |
| Sync | Data synchronization | `/internal/sync/conveyors` |
| Health | Deep health checks | `/internal/health/dependencies` |

## Testing Guidance

- Test internal endpoints are accessible without user token.
- Test internal endpoints are NOT accessible from public routes.
- Verify service account auth works if implemented.
- Test internal endpoint responses match expected format.

---

## Template

### Internal Router (`internal/__init__.py`)

```python
from fastapi import APIRouter

from {{ project_module }}.constants import INTERNAL_PREFIX

{% for router in resource_routers %}
from .{{ router.module }} import *
{% endfor %}

__all__ = ["internal_router"]

internal_router = APIRouter(prefix=INTERNAL_PREFIX)

{% for router in resource_routers %}
internal_router.include_router({{ router.name }})
{% endfor %}
```

### Internal Resource Endpoint

```python
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status

from {{ application_module }} import {{ query_class }}
from {{ containers_module }} import Containers

from ...endpoint_marker import MarkerRoute
from ...endpoint_visibility import Visibility
from ...serializers import {{ request_serializer }}, {{ response_serializer }}

__all__ = ["{{ router_name }}"]

{{ router_name }} = APIRouter(prefix="{{ router_prefix }}", tags={{ router_tags }}, route_class=MarkerRoute)

@{{ router_name }}.{{ http_method }}(
    "{{ path }}",
    status_code=status.{{ status_code }},
    openapi_extra={"visibility": Visibility.INTERNAL},
    response_model={{ response_serializer }},
)
@inject
def {{ endpoint_function }}(
    request: {{ request_serializer }} = Depends(),
    {{ query_param }}: {{ query_class }} = Depends(Provide[Containers.{{ container_property }}]),
):
    return {{ response_serializer }}.from_domain(
        {{ query_param }}.{{ method }}({{ method_params }})
    )
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ project_module }}` | Root module path | `my_service` |
| `{{ resource_routers }}` | List of router configs | `[{"module": "tires", "name": "tires_router"}]` |
| `{{ application_module }}` | Application layer module | `my_service.application` |
| `{{ containers_module }}` | Containers module | `my_service.containers` |
| `{{ router_name }}` | Router variable name | `tires_router` |
| `{{ router_prefix }}` | URL prefix | `/tires` |
| `{{ router_tags }}` | OpenAPI tags | `["Tires"]` |
