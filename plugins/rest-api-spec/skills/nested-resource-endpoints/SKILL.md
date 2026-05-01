---
name: nested-resource-endpoints
description: Nested Resource Endpoints pattern for REST APIs. Use when defining endpoints that operate on child resources scoped to a parent, expressing hierarchical relationships in URLs and passing parent + child identifiers to the domain layer.
user-invocable: false
disable-model-invocation: false
---

# Nested Resource Endpoints

## Purpose

- Handle operations on resources that exist within the context of a parent resource.
- Express hierarchical relationships in URL structure.
- Scope actions to specific parent-child combinations.

## Structure

- URL pattern: `/{parent_id}/{child_collection}/{child_id}/action`
- Multiple path parameters identifying the resource hierarchy.
- Parent context passed alongside child identifier to domain layer.

## When to Use

Use nested resource endpoints when:

- Child resource only makes sense in context of parent (e.g., tire within a load)
- Action requires both parent and child identifiers
- Business logic validates parent-child relationship
- API consumers expect hierarchical navigation

## Example

### Basic Nested Resource Action

```python
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, status

from my_service.application import LoadCommands
from my_service.containers import Containers

from ...endpoint_marker import MarkerRoute
from ...endpoint_visibility import Visibility
from ...serializers.v2.loads import ConfirmOverageResponse

__all__ = ["loads_router"]

loads_router = APIRouter(prefix="/loads", tags=["Loads"], route_class=MarkerRoute)

@loads_router.post(
    "/{load_id}/overages/{tire_id}/confirm",
    status_code=status.HTTP_200_OK,
    openapi_extra={"visibility": Visibility.PUBLIC},
    response_model=ConfirmOverageResponse,
)
@inject
def confirm_overage(
    load_id: str,
    tire_id: str,
    warehouse_id: str = Query(..., alias="warehouseId"),
    load_commands: LoadCommands = Depends(Provide[Containers.load_commands]),
):
    return ConfirmOverageResponse.from_domain(
        load_commands.confirm_overage(load_id, warehouse_id, tire_id)
    )
```

### Multiple Nested Resource Types

When a parent has multiple child collection types:

```python
# Overages
@loads_router.post(
    "/{load_id}/overages/{tire_id}/confirm",
    status_code=status.HTTP_200_OK,
    openapi_extra={"visibility": Visibility.PUBLIC},
    response_model=ConfirmOverageResponse,
)
@inject
def confirm_overage(load_id: str, tire_id: str, ...):
    ...

@loads_router.post(
    "/{load_id}/overages/{tire_id}/defer",
    status_code=status.HTTP_200_OK,
    openapi_extra={"visibility": Visibility.PUBLIC},
    response_model=DeferOverageResponse,
)
@inject
def defer_overage(load_id: str, tire_id: str, ...):
    ...

@loads_router.post(
    "/{load_id}/overages/{tire_id}/associate",
    status_code=status.HTTP_200_OK,
    openapi_extra={"visibility": Visibility.PUBLIC},
    response_model=AssociateOverageResponse,
)
@inject
def associate_overage(
    load_id: str,
    tire_id: str,
    warehouse_id: str = Query(..., alias="warehouseId"),
    item_number: str = Query(..., alias="itemNumber"),
    order_number: str = Query(..., alias="orderNumber"),
    load_commands: LoadCommands = Depends(Provide[Containers.load_commands]),
):
    return AssociateOverageResponse.from_domain(
        load_commands.associate_overage_with_line_item(
            load_id, warehouse_id, tire_id, item_number, order_number
        )
    )

# Unexpected Tires
@loads_router.post(
    "/{load_id}/unexpected-tires/{tire_id}/confirm",
    status_code=status.HTTP_200_OK,
    openapi_extra={"visibility": Visibility.PUBLIC},
    response_model=ConfirmUnexpectedTireResponse,
)
@inject
def confirm_unexpected_tire(load_id: str, tire_id: str, ...):
    ...

# Unrecognized Tires
@loads_router.post(
    "/{load_id}/unrecognized-tires/{tire_id}/confirm",
    status_code=status.HTTP_200_OK,
    openapi_extra={"visibility": Visibility.PUBLIC},
    response_model=ConfirmUnrecognizedTireResponse,
)
@inject
def confirm_unrecognized_tire(load_id: str, tire_id: str, ...):
    ...

# Failed Tires
@loads_router.post(
    "/{load_id}/failed-tires/{tire_id}/retry",
    status_code=status.HTTP_200_OK,
    openapi_extra={"visibility": Visibility.PUBLIC},
    response_model=RetryFailedTireResponse,
)
@inject
def retry_failed_tire(load_id: str, tire_id: str, ...):
    ...
```

### Nested Resource GET

```python
@loads_router.get(
    "/{load_id}/line-items/{item_number}",
    status_code=status.HTTP_200_OK,
    openapi_extra={"visibility": Visibility.PUBLIC},
    response_model=GetLineItemResponse,
)
@inject
def get_line_item(
    load_id: str,
    item_number: str,
    warehouse_id: str = Query(..., alias="warehouseId"),
    load_queries: LoadQueries = Depends(Provide[Containers.load_queries]),
):
    return GetLineItemResponse.from_domain(
        load_queries.get_line_item(load_id, warehouse_id, item_number)
    )
```

## URL Design Patterns

### Action on Nested Resource

```
POST /{parent_id}/{child_collection}/{child_id}/{action}
```

Examples:

- `POST /loads/{load_id}/overages/{tire_id}/confirm`
- `POST /loads/{load_id}/failed-tires/{tire_id}/retry`
- `POST /loads/{load_id}/unrecognized-tires/{tire_id}/defer`

### CRUD on Nested Resource

```
GET    /{parent_id}/{child_collection}           # List children
GET    /{parent_id}/{child_collection}/{child_id} # Get specific child
POST   /{parent_id}/{child_collection}           # Create child
PUT    /{parent_id}/{child_collection}/{child_id} # Update child
DELETE /{parent_id}/{child_collection}/{child_id} # Delete child
```

## Child Collection Naming

Use hyphenated, pluralized names for child collections:

| Child Type | Collection Name |
| --- | --- |
| Overage tire | `overages` |
| Unexpected tire | `unexpected-tires` |
| Unrecognized tire | `unrecognized-tires` |
| Failed tire | `failed-tires` |
| Recognized tire | `recognized-tires` |
| Line item | `line-items` |

## Common Actions per Child Type

| Child Type | Common Actions |
| --- | --- |
| Exception items | `confirm`, `defer`, `associate` |
| Failed items | `retry`, `defer`, `associate` |
| Matched items | `disassociate` |

## Parameter Ordering Convention

Follow consistent ordering in function signature:

1. Parent path parameter(s)
2. Child path parameter(s)
3. Required query parameters (context identifiers)
4. Optional query parameters (action parameters)
5. Injected dependencies

```python
def associate_overage(
    load_id: str,                                           # 1. Parent path param
    tire_id: str,                                           # 2. Child path param
    warehouse_id: str = Query(..., alias="warehouseId"),    # 3. Required context
    item_number: str = Query(..., alias="itemNumber"),      # 4. Action param
    order_number: str = Query(..., alias="orderNumber"),    # 4. Action param
    load_commands: LoadCommands = Depends(...),             # 5. Dependency
):
```

## Error Handling Considerations

Nested resource endpoints may raise additional exception types:

| Exception | HTTP Status | Scenario |
| --- | --- | --- |
| `ParentNotFound` | 404 | Parent resource doesn't exist |
| `ChildNotFound` | 404 | Child doesn't exist under parent |
| `InvalidRelationship` | 400 | Child doesn't belong to parent |
| `InvalidStateTransition` | 409 | Action not allowed in current state |

## Testing Guidance

- Test with valid parent and child IDs.
- Test child not found under parent (404).
- Test parent not found (404).
- Test action with all required parameters.
- Test state-dependent actions (e.g., can't confirm already confirmed).

### Test Example

```python
def test_confirm_overage_success(client, mock_load_commands):
    mock_load_commands.confirm_overage.return_value = Load(id="LD001", ...)
    
    response = client.post(
        "/api/my-service/v2/loads/LD001/overages/TIRE001/confirm",
        params={"warehouseId": "WH001"},
    )
    
    assert response.status_code == 200
    mock_load_commands.confirm_overage.assert_called_once_with(
        "LD001", "WH001", "TIRE001"
    )

def test_confirm_overage_tire_not_found(client, mock_load_commands):
    mock_load_commands.confirm_overage.side_effect = TireNotFound("TIRE999")
    
    response = client.post(
        "/api/my-service/v2/loads/LD001/overages/TIRE999/confirm",
        params={"warehouseId": "WH001"},
    )
    
    assert response.status_code == 404
```

---

## Template

```python
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, status

from {{ application_module }} import {{ command_class }}
from {{ containers_module }} import Containers

from ...endpoint_marker import MarkerRoute
from ...endpoint_visibility import Visibility
from ...serializers.{{ version }}.{{ parent_resource }} import {{ response_serializer }}

__all__ = ["{{ parent_resource }}_router"]

{{ parent_resource }}_router = APIRouter(
    prefix="/{{ parent_resource_plural }}", 
    tags=["{{ tag }}"], 
    route_class=MarkerRoute
)

@{{ parent_resource }}_router.post(
    "/{{{ parent_resource }}_id}/{{ child_collection }}/{{{ child_resource }}_id}/{{ action }}",
    status_code=status.HTTP_200_OK,
    openapi_extra={"visibility": Visibility.{{ visibility }}},
    response_model={{ response_serializer }},
)
@inject
def {{ action_name }}(
    {{ parent_resource }}_id: str,
    {{ child_resource }}_id: str,
{% for param in context_params %}
    {{ param.name }}: {{ param.type }} = Query(..., alias="{{ param.alias }}"),
{% endfor %}
{% for param in action_params %}
    {{ param.name }}: {{ param.type }} = Query(..., alias="{{ param.alias }}"),
{% endfor %}
    {{ command_var }}: {{ command_class }} = Depends(Provide[Containers.{{ container_key }}]),
):
    return {{ response_serializer }}.from_domain(
        {{ command_var }}.{{ command_method }}(
            {{ parent_resource }}_id, 
{% for param in context_params %}
            {{ param.name }},
{% endfor %}
            {{ child_resource }}_id,
{% for param in action_params %}
            {{ param.name }},
{% endfor %}
        )
    )
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ parent_resource }}` | Parent resource (singular) | `load` |
| `{{ parent_resource_plural }}` | Parent resource (plural) | `loads` |
| `{{ child_collection }}` | Child collection name | `overages` |
| `{{ child_resource }}` | Child resource (singular) | `tire` |
| `{{ action }}` | Action path segment | `confirm` |
| `{{ action_name }}` | Python function name | `confirm_overage` |
| `{{ response_serializer }}` | Response class | `ConfirmOverageResponse` |
| `{{ context_params }}` | Context query params | `[{"name": "warehouse_id", ...}]` |
| `{{ action_params }}` | Action-specific params | `[{"name": "item_number", ...}]` |
