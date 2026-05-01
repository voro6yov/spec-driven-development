---
name: endpoint-visibility
description: Endpoint Visibility pattern for REST API endpoints. Use when marking endpoints as Public or Internal for OpenAPI documentation and access-level indication.
user-invocable: false
disable-model-invocation: false
---

# Endpoint Visibility

## Purpose

- Mark endpoints as Public or Internal for documentation purposes.
- Display visibility in OpenAPI documentation.
- Provide clear indication of endpoint access level.

## Structure

- Simple enum with visibility levels.
- Used in endpoint `openapi_extra` parameter.
- Combined with `MarkerRoute` for OpenAPI summary generation.

## Template Parameters

- `{{ visibility_levels }}` - List of visibility levels to define

## Visibility Levels

| Level | Description | Use Case |
| --- | --- | --- |
| `PUBLIC` | Accessible by external clients | User-facing API endpoints |
| `INTERNAL` | Service-to-service only | Internal operations, admin endpoints |

## Example

```python
from enum import Enum

__all__ = ["Visibility"]

class Visibility(Enum):
    PUBLIC = "Public"
    INTERNAL = "Internal"
```

## Usage in Endpoints

```python
from fastapi import APIRouter, status

from ..endpoint_marker import MarkerRoute
from ..endpoint_visibility import Visibility

router = APIRouter(route_class=MarkerRoute)

@router.get(
    "/resources",
    status_code=status.HTTP_200_OK,
    openapi_extra={"visibility": Visibility.PUBLIC},
    response_model=GetResourcesResponse,
)
def get_resources():
    ...

@router.post(
    "/internal/sync",
    status_code=status.HTTP_200_OK,
    openapi_extra={"visibility": Visibility.INTERNAL},
    response_model=SyncResponse,
)
def sync_data():
    ...
```

## OpenAPI Result

When combined with `MarkerRoute`, the endpoint summary becomes:

- `[Public] Get Resources`
- `[Internal] Sync Data`

This provides clear visual indication in Swagger UI and OpenAPI documentation.

## Testing Guidance

- Verify visibility enum values are correct.
- Test that endpoints with PUBLIC visibility are accessible.
- Test that INTERNAL endpoints have appropriate access controls.

---

## Template

```python
from enum import Enum

__all__ = ["Visibility"]

class Visibility(Enum):
{% for level in visibility_levels %}
    {{ level.name }} = "{{ level.value }}"
{% endfor %}
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ visibility_levels }}` | List of visibility level definitions | `[{"name": "PUBLIC", "value": "Public"}]` |
