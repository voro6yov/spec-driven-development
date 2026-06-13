---
name: internal-router
description: Internal Router pattern for REST API endpoints. Use when grouping endpoints for service-to-service communication, bypassing user authentication, or separating internal API surface from public/external endpoints.
user-invocable: false
disable-model-invocation: false
---

# Internal Router

## When to Use

Use internal router pattern when:

- Exposing endpoints for other services to call
- Analytics or metrics endpoints consumed by internal tools
- Admin operations not exposed to end users
- Bulk operations or data synchronization endpoints

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

## Directory Structure

```
api/endpoints/
├── __init__.py
├── debug.py
├── healthcheck.py
├── service_info.py
├── internal/             # Internal endpoints directory
│   ├── __init__.py       # Internal router aggregation
│   ├── conveyors.py
│   └── tires.py
├── v1/
│   └── ...
└── v2/
    └── ...
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
| `{{ application_module }}` | Application layer module | `my_service.application` |
| `{{ containers_module }}` | Containers module | `my_service.containers` |
| `{{ router_name }}` | Router variable name | `tires_router` |
| `{{ router_prefix }}` | URL prefix | `/tires` |
| `{{ router_tags }}` | OpenAPI tags | `["Tires"]` |
