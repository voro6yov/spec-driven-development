---
name: command-action-endpoint
description: Command Action Endpoint pattern for exposing domain commands as POST endpoints performing non-CRUD actions on resources. Use when implementing state transitions, toggles, or business operations that trigger workflows or side effects on a resource.
user-invocable: false
disable-model-invocation: false
---

# Command Action Endpoint

## Purpose

- Expose domain commands as POST endpoints that perform actions on resources.
- Follow REST conventions for non-CRUD operations.
- Return minimal responses confirming action completion.

## Structure

- POST method to `/{resource_id}/action-name` path.
- Accept required parameters via query params (with camelCase aliases).
- Inject domain command service via dependency injection.
- Return simple response serializer with resource ID.

## When to Use

Use command action endpoints when:

- Performing state transitions on a resource (start, stop, pause, resume)
- Executing business operations that aren't CRUD (confirm, defer, retry)
- Triggering workflows or processes on a resource
- Action has side effects beyond simple data modification

## Example

### Basic Command Action Endpoint

```python
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, status

from my_service.application import LoadCommands
from my_service.containers import Containers

from ...endpoint_marker import MarkerRoute
from ...endpoint_visibility import Visibility
from ...serializers.v2.loads import StartReceivingResponse

__all__ = ["loads_router"]

loads_router = APIRouter(prefix="/loads", tags=["Loads"], route_class=MarkerRoute)

@loads_router.post(
    "/{load_id}/start-receiving",
    status_code=status.HTTP_200_OK,
    openapi_extra={"visibility": Visibility.PUBLIC},
    response_model=StartReceivingResponse,
)
@inject
def start_receiving(
    load_id: str,
    warehouse_id: str = Query(..., alias="warehouseId"),
    load_commands: LoadCommands = Depends(Provide[Containers.load_commands]),
):
    return StartReceivingResponse.from_domain(
        load_commands.start_receiving(load_id, warehouse_id)
    )
```

### Command with Optional Parameters

```python
from my_service.domain import ReceivingLocation

@loads_router.post(
    "/{load_id}/start-receiving",
    status_code=status.HTTP_200_OK,
    openapi_extra={"visibility": Visibility.PUBLIC},
    response_model=StartReceivingResponse,
)
@inject
def start_receiving(
    load_id: str,
    warehouse_id: str = Query(..., alias="warehouseId"),
    receiving_location: ReceivingLocation | None = Query(default=None, alias="receivingLocation"),
    load_commands: LoadCommands = Depends(Provide[Containers.load_commands]),
):
    return StartReceivingResponse.from_domain(
        load_commands.start_receiving(load_id, warehouse_id, receiving_location=receiving_location)
    )
```

### Toggle Actions (Enable/Disable)

```python
@loads_router.post(
    "/{load_id}/enable-bypass-mode",
    status_code=status.HTTP_200_OK,
    openapi_extra={"visibility": Visibility.PUBLIC},
    response_model=EnableBypassModeResponse,
)
@inject
def enable_bypass_mode(
    load_id: str,
    warehouse_id: str = Query(..., alias="warehouseId"),
    load_commands: LoadCommands = Depends(Provide[Containers.load_commands]),
):
    return EnableBypassModeResponse.from_domain(
        load_commands.enable_bypass_mode(load_id, warehouse_id)
    )

@loads_router.post(
    "/{load_id}/disable-bypass-mode",
    status_code=status.HTTP_200_OK,
    openapi_extra={"visibility": Visibility.PUBLIC},
    response_model=DisableBypassModeResponse,
)
@inject
def disable_bypass_mode(
    load_id: str,
    warehouse_id: str = Query(..., alias="warehouseId"),
    load_commands: LoadCommands = Depends(Provide[Containers.load_commands]),
):
    return DisableBypassModeResponse.from_domain(
        load_commands.disable_bypass_mode(load_id, warehouse_id)
    )
```

## Common Action Naming Conventions

| Action Type | Path Pattern | Example |
| --- | --- | --- |
| State transition | `/{id}/start-{action}` | `/loads/{id}/start-receiving` |
| State transition | `/{id}/finish-{action}` | `/loads/{id}/finish-unloading` |
| Pause/Resume | `/{id}/pause-{action}` | `/loads/{id}/pause-receiving` |
| Pause/Resume | `/{id}/resume-{action}` | `/loads/{id}/resume-receiving` |
| Toggle on | `/{id}/enable-{feature}` | `/loads/{id}/enable-bypass-mode` |
| Toggle off | `/{id}/disable-{feature}` | `/loads/{id}/disable-bypass-mode` |
| Confirmation | `/{id}/confirm` | `/tires/{id}/confirm` |
| Deferral | `/{id}/defer` | `/tires/{id}/defer` |
| Retry | `/{id}/retry` | `/tires/{id}/retry` |
| Close/Complete | `/{id}/close` | `/loads/{id}/close` |

## Response Pattern

Command action endpoints typically return minimal responses. See [Simple Command Response](simple-command-response.md) for the serializer pattern.

```python
class StartReceivingResponse(ConfiguredResponseSerializer):
    id: str

    @classmethod
    def from_domain(cls, load: Load) -> "StartReceivingResponse":
        return cls(id=load.id)
```

## Query Parameter Pattern

Use `Query()` with alias for required parameters that identify context:

```python
warehouse_id: str = Query(..., alias="warehouseId")
```

The `...` (Ellipsis) makes the parameter required. Use `Query(default=None, alias="...")` for optional parameters.

## HTTP Status Codes

| Scenario | Status Code |
| --- | --- |
| Action successful | `200 OK` |
| Action created new state | `201 Created` |
| Invalid state transition | `400 Bad Request` (via error handler) |
| Resource not found | `404 Not Found` (via error handler) |
| Conflict (already in state) | `409 Conflict` (via error handler) |

## Deprecating Command Endpoints

When replacing a command with a new version:

```python
@loads_router.post(
    "/{load_id}/mark-as-overage",
    status_code=status.HTTP_200_OK,
    openapi_extra={"visibility": Visibility.PUBLIC},
    response_model=MarkAsOverageResponse,
    deprecated=True,  # Marks endpoint as deprecated in OpenAPI
)
@inject
def mark_as_overage(...):
    ...
```

## Testing Guidance

- Test successful command execution returns expected response.
- Test required query parameters are validated.
- Test domain exceptions are mapped to correct HTTP status codes.
- Test optional parameters work when provided and when omitted.
- Mock domain command service to verify correct method calls.

### Test Example

```python
def test_start_receiving_success(client, mock_load_commands):
    mock_load_commands.start_receiving.return_value = Load(id="LD001", ...)
    
    response = client.post(
        "/api/my-service/v2/loads/LD001/start-receiving",
        params={"warehouseId": "WH001"},
    )
    
    assert response.status_code == 200
    assert response.json() == {"id": "LD001"}
    mock_load_commands.start_receiving.assert_called_once_with("LD001", "WH001")

def test_start_receiving_missing_warehouse_id(client):
    response = client.post("/api/my-service/v2/loads/LD001/start-receiving")
    
    assert response.status_code == 422  # Validation error
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
from ...serializers.{{ version }}.{{ resource }} import {{ response_serializer }}

__all__ = ["{{ resource }}_router"]

{{ resource }}_router = APIRouter(prefix="/{{ resource_plural }}", tags=["{{ tag }}"], route_class=MarkerRoute)

@{{ resource }}_router.post(
    "/{{{ resource }}_id}/{{ action_path }}",
    status_code=status.HTTP_200_OK,
    openapi_extra={"visibility": Visibility.{{ visibility }}},
    response_model={{ response_serializer }},
)
@inject
def {{ action_name }}(
    {{ resource }}_id: str,
{% for param in required_params %}
    {{ param.name }}: {{ param.type }} = Query(..., alias="{{ param.alias }}"),
{% endfor %}
{% for param in optional_params %}
    {{ param.name }}: {{ param.type }} | None = Query(default=None, alias="{{ param.alias }}"),
{% endfor %}
    {{ command_var }}: {{ command_class }} = Depends(Provide[Containers.{{ container_key }}]),
):
    return {{ response_serializer }}.from_domain(
        {{ command_var }}.{{ command_method }}({{ resource }}_id{% for param in all_params %}, {{ param.name }}={{ param.name }}{% endfor %})
    )
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ application_module }}` | Application layer module | `my_service.application` |
| `{{ command_class }}` | Command service class | `LoadCommands` |
| `{{ containers_module }}` | Containers module | `my_service.containers` |
| `{{ version }}` | API version | `v2` |
| `{{ resource }}` | Resource name (singular) | `load` |
| `{{ resource_plural }}` | Resource name (plural) | `loads` |
| `{{ tag }}` | OpenAPI tag | `Loads` |
| `{{ action_path }}` | Action path segment | `start-receiving` |
| `{{ action_name }}` | Python function name | `start_receiving` |
| `{{ response_serializer }}` | Response serializer class | `StartReceivingResponse` |
| `{{ visibility }}` | Endpoint visibility | `PUBLIC` |
| `{{ command_var }}` | Command service variable | `load_commands` |
| `{{ container_key }}` | Container provider key | `load_commands` |
| `{{ command_method }}` | Command method to call | `start_receiving` |
| `{{ required_params }}` | List of required query params | See below |
| `{{ optional_params }}` | List of optional query params | See below |

### Parameter Definition Structure

```python
{
    "name": "warehouse_id",
    "type": "str",
    "alias": "warehouseId"
}
```
