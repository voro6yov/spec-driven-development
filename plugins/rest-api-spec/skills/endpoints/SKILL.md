---
name: endpoints
description: Endpoints pattern for REST API. Use when defining FastAPI router endpoints with dependency injection and serializers that map domain objects to HTTP responses.
user-invocable: false
disable-model-invocation: false
---

# Endpoints

## Purpose

- Define REST API endpoints with FastAPI router pattern.
- Integrate with dependency injection container.
- Map domain objects to HTTP responses via serializers.

## Structure

- Endpoints are functions decorated with router HTTP method decorators.
- Use `@inject` decorator for dependency injection.
- Dependencies are injected via `Depends(Provide[Containers.xxx])`.
- Response serializers use `from_domain()` to transform domain objects.

## Template Parameters

When using the template, replace these placeholders with your project-specific values:

- `{{ application_module }}` - Module path for application layer commands/queries
- `{{ containers_module }}` - Module path for DI containers
- `{{ containers_class_name }}` - Name of the containers class
- `{{ serializers_module }}` - Relative path to serializers
- `{{ router_prefix }}` - URL prefix for the router (e.g., `/conveyors`)
- `{{ router_tags }}` - OpenAPI tags list (e.g., `["Conveyors"]`)
- `{{ endpoint_function_name }}` - Name of the endpoint function
- `{{ http_method }}` - HTTP method (get, post, put, patch, delete)
- `{{ path }}` - Endpoint path (e.g., `""`, `"/{id}"`, `"/{id}/action"`)
- `{{ status_code }}` - HTTP status code for success response
- `{{ visibility }}` - Endpoint visibility (PUBLIC, INTERNAL)
- `{{ response_serializer }}` - Response model class name
- `{{ request_serializer }}` - Request model class name (optional)
- `{{ container_property }}` - Container property for injected dependency
- `{{ dependency_class }}` - Class name of the injected dependency
- `{{ dependency_param }}` - Parameter name for the dependency
- `{{ domain_method }}` - Method to call on the injected dependency
- `{{ method_params }}` - Parameters to pass to domain method

## Endpoint Types

### GET - Retrieve Resource

```python
@router.get(
    "/{resourceId}",
    status_code=status.HTTP_200_OK,
    openapi_extra={"visibility": Visibility.PUBLIC},
    response_model=GetResourceResponse,
)
@inject
def get_resource(
    resource_id: str = Path(..., alias="resourceId"),
    queries: ResourceQueries = Depends(Provide[Containers.resource_queries]),
):
    return GetResourceResponse.from_domain(queries.find_resource(resource_id))
```

### GET - List Resources

```python
@router.get(
    "",
    status_code=status.HTTP_200_OK,
    openapi_extra={"visibility": Visibility.PUBLIC},
    response_model=GetResourcesResponse,
)
@inject
def get_resources(
    request: GetResourcesRequest = Depends(),
    queries: ResourceQueries = Depends(Provide[Containers.resource_queries]),
):
    return GetResourcesResponse.from_domain(
        queries.find_resources(request.page, request.per_page)
    )
```

### POST - Create Resource

```python
@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    openapi_extra={"visibility": Visibility.PUBLIC},
    response_model=CreateResourceResponse,
)
@inject
def create_resource(
    request: CreateResourceRequest,
    commands: ResourceCommands = Depends(Provide[Containers.resource_commands]),
):
    return CreateResourceResponse.from_domain(
        commands.create(
            id_=request.id,
            name=request.name,
        ),
    )
```

### POST - Action on Resource

```python
@router.post(
    "/{resourceId}/start-processing",
    status_code=status.HTTP_200_OK,
    openapi_extra={"visibility": Visibility.PUBLIC},
    response_model=StartProcessingResponse,
)
@inject
def start_processing(
    resource_id: str = Path(..., alias="resourceId"),
    commands: ResourceCommands = Depends(Provide[Containers.resource_commands]),
):
    return StartProcessingResponse.from_domain(
        commands.start_processing(resource_id)
    )
```

### PUT - Full Resource Update

Use PUT for full replacement of a resource or sub-resource:

```python
@router.put(
    "/{conveyorId}/items",
    status_code=status.HTTP_200_OK,
    openapi_extra={"visibility": Visibility.INTERNAL},
    response_model=UpdateConveyorItemsResponse,
)
@inject
def update_conveyor_items(
    conveyor_id: str = Path(..., alias="conveyorId"),
    request: UpdateConveyorItemsRequest,
    conveyor_commands: ConveyorCommands = Depends(Provide[Containers.conveyor_commands]),
):
    return UpdateConveyorItemsResponse.from_domain(
        conveyor_commands.update_items(
            conveyor_id=conveyor_id,
            warehouse_id=request.warehouse_id,
            items=request.items,
        ),
    )
```

Use PUT when:

- Replacing an entire resource or collection
- Client sends complete state (not partial updates)
- Idempotent full updates

### PATCH - Partial Update or Batch Action

Use PATCH for partial updates or batch operations on multiple resources:

```python
@router.patch(
    "/restart",
    status_code=status.HTTP_200_OK,
    openapi_extra={"visibility": Visibility.PUBLIC},
    response_model=RestartTiresResponse,
)
@inject
def restart_tires(
    request: RestartTiresRequest = Depends(),
    tire_commands: TireCommands = Depends(Provide[Containers.tire_commands]),
):
    return RestartTiresResponse.from_domain(
        tire_commands.restart_identification(
            status=request.status,
            conveyor_id=request.conveyor_id,
            warehouse_id=request.warehouse_id,
            limit=request.limit,
        ),
    )
```

Use PATCH when:

- Updating a subset of resource fields
- Batch operations affecting multiple resources
- Operations with filter criteria (restart all with status X)

### POST - Nested Sub-Resource Action

For actions on child resources within a parent resource:

```python
@router.post(
    "/{loadId}/overages/{tireId}/confirm",
    status_code=status.HTTP_200_OK,
    openapi_extra={"visibility": Visibility.PUBLIC},
    response_model=ConfirmOverageResponse,
)
@inject
def confirm_overage(
    load_id: str = Path(..., alias="loadId"),
    tire_id: str = Path(..., alias="tireId"),
    warehouse_id: str = Query(..., alias="warehouseId"),
    load_commands: LoadCommands = Depends(Provide[Containers.load_commands]),
):
    return ConfirmOverageResponse.from_domain(
        load_commands.confirm_overage(load_id, warehouse_id, tire_id)
    )
```

Common nested action patterns:

| Pattern | URL Structure | Example |
| --- | --- | --- |
| Confirm | `/{parent_id}/{sub_resource}/{sub_id}/confirm` | `/loads/123/overages/456/confirm` |
| Defer | `/{parent_id}/{sub_resource}/{sub_id}/defer` | `/loads/123/failed-tires/456/defer` |
| Associate | `/{parent_id}/{sub_resource}/{sub_id}/associate` | `/loads/123/unexpected-tires/456/associate` |
| Retry | `/{parent_id}/{sub_resource}/{sub_id}/retry` | `/loads/123/failed-tires/456/retry` |

### Deprecated Endpoints

Mark endpoints as deprecated in the OpenAPI spec:

```python
@router.post(
    "/{loadId}/unrecognized-tires/{tireId}/mark-as-overage",
    status_code=status.HTTP_200_OK,
    openapi_extra={"visibility": Visibility.PUBLIC},
    response_model=MarkAsOverageResponse,
    deprecated=True,  # Marks endpoint as deprecated in OpenAPI
)
@inject
def mark_unrecognized_tire_as_overage(
    load_id: str = Path(..., alias="loadId"),
    tire_id: str = Path(..., alias="tireId"),
    warehouse_id: str = Query(..., alias="warehouseId"),
    load_commands: LoadCommands = Depends(Provide[Containers.load_commands]),
):
    return MarkAsOverageResponse.from_domain(
        load_commands.mark_unrecognized_tire_as_overage(load_id, warehouse_id, tire_id)
    )
```

Use `deprecated=True` when:

- A newer endpoint replaces this one
- The functionality is being phased out
- The API contract is changing in future versions

## Parameter Handling

### Path Parameters

```python
resource_id: str = Path(..., alias="resourceId")
```

### Query Parameters

```python
warehouse_id: str = Query(default="1", alias="warehouseId")
status: str | None = Query(default=None)
```

### Request Body

```python
request: CreateResourceRequest  # Pydantic model
```

### Query Params Class (Complex Queries)

```python
request: QueryResourcesParams = Depends()
```

## Example

```python
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Path, Query, status

from my_service.application import ConveyorCommands, ConveyorQueries
from my_service.containers import Containers

from ...endpoint_marker import MarkerRoute
from ...endpoint_visibility import Visibility
from ...serializers import (
    CreateConveyorRequest,
    CreateConveyorResponse,
    GetConveyorResponse,
    GetConveyorsRequest,
    GetConveyorsResponse,
)

__all__ = ["conveyors_router"]

conveyors_router = APIRouter(prefix="/conveyors", tags=["Conveyors"], route_class=MarkerRoute)

@conveyors_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    openapi_extra={"visibility": Visibility.PUBLIC},
    response_model=CreateConveyorResponse,
)
@inject
def create_conveyor(
    request: CreateConveyorRequest,
    conveyor_commands: ConveyorCommands = Depends(Provide[Containers.conveyor_commands]),
):
    return CreateConveyorResponse.from_domain(
        conveyor_commands.create(
            id_=request.id,
            name=request.name,
            warehouse_id=request.warehouse_id,
        ),
    )

@conveyors_router.get(
    "/{conveyorId}",
    status_code=status.HTTP_200_OK,
    openapi_extra={"visibility": Visibility.PUBLIC},
    response_model=GetConveyorResponse,
)
@inject
def get_conveyor(
    conveyor_id: str = Path(..., alias="conveyorId"),
    warehouse_id: str | None = Query(default=None, alias="warehouseId"),
    conveyor_queries: ConveyorQueries = Depends(Provide[Containers.conveyor_queries]),
):
    return GetConveyorResponse.from_domain(
        conveyor_queries.find_conveyor(conveyor_id, warehouse_id)
    )

@conveyors_router.get(
    "",
    status_code=status.HTTP_200_OK,
    openapi_extra={"visibility": Visibility.PUBLIC},
    response_model=GetConveyorsResponse,
)
@inject
def get_conveyors(
    request: GetConveyorsRequest = Depends(),
    conveyor_queries: ConveyorQueries = Depends(Provide[Containers.conveyor_queries]),
):
    return GetConveyorsResponse.from_domain(
        conveyor_queries.find_conveyors(request.page, request.per_page)
    )
```

## Testing Guidance

- Test endpoints with valid request data and verify response structure.
- Test validation errors with invalid request data.
- Test authorization for protected endpoints.
- Verify correct status codes for success and error cases.
- Mock application layer dependencies (commands/queries).
- Test nested sub-resource actions with all required path parameters.
- Verify deprecated endpoints still function but show deprecation in OpenAPI.

---

## Template

```python
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Path, Query, status

from {{ application_module }} import {{ dependency_class }}
from {{ containers_module }} import {{ containers_class_name }}

from {{ serializers_module }} import (
{% for serializer in serializers %}
    {{ serializer }},
{% endfor %}
)
from ...endpoint_marker import MarkerRoute
from ...endpoint_visibility import Visibility

__all__ = ["{{ router_name }}"]

{{ router_name }} = APIRouter(prefix="{{ router_prefix }}", tags={{ router_tags }}, route_class=MarkerRoute)

@{{ router_name }}.{{ http_method }}(
    "{{ path }}",
    status_code=status.{{ status_code }},
    openapi_extra={"visibility": Visibility.{{ visibility }}},
    response_model={{ response_serializer }},
)
@inject
def {{ endpoint_function_name }}(
{% for param in path_params %}
    {{ param.name }}: {{ param.type }} = Path(..., alias="{{ param.alias }}"),
{% endfor %}
{% for param in query_params %}
    {{ param.name }}: {{ param.type }} = Query({{ param.default }}, alias="{{ param.alias }}"),
{% endfor %}
{% if request_serializer %}
    request: {{ request_serializer }},
{% endif %}
    {{ dependency_param }}: {{ dependency_class }} = Depends(Provide[{{ containers_class_name }}.{{ container_property }}]),
):
    return {{ response_serializer }}.from_domain(
        {{ dependency_param }}.{{ domain_method }}({{ method_params }})
    )
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ application_module }}` | Module path for application layer | `my_service.application` |
| `{{ containers_module }}` | Module path for DI containers | `my_service.containers` |
| `{{ containers_class_name }}` | Name of the containers class | `Containers` |
| `{{ serializers_module }}` | Relative import path for serializers | `...serializers` |
| `{{ router_name }}` | Variable name for the router | `conveyors_router` |
| `{{ router_prefix }}` | URL prefix for the router | `/conveyors` |
| `{{ router_tags }}` | OpenAPI tags | `["Conveyors"]` |
| `{{ http_method }}` | HTTP method | `get`, `post`, `put`, `patch`, `delete` |
| `{{ path }}` | Endpoint path | `""`, `"/{conveyorId}"` |
| `{{ status_code }}` | HTTP status code constant | `HTTP_200_OK`, `HTTP_201_CREATED` |
| `{{ visibility }}` | Endpoint visibility | `PUBLIC`, `INTERNAL` |
| `{{ response_serializer }}` | Response model class | `GetConveyorResponse` |
| `{{ request_serializer }}` | Request model class (optional) | `CreateConveyorRequest` |
| `{{ endpoint_function_name }}` | Name of the endpoint function | `get_conveyor` |
| `{{ dependency_class }}` | Injected dependency class | `ConveyorQueries` |
| `{{ dependency_param }}` | Parameter name for dependency | `conveyor_queries` |
| `{{ container_property }}` | Container property name | `conveyor_queries` |
| `{{ domain_method }}` | Method to call on dependency | `find_conveyor` |
| `{{ method_params }}` | Parameters for domain method | `conveyor_id, warehouse_id` |
