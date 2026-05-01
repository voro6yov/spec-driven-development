---
name: query-params
description: Query Params pattern for REST API endpoints. Use when defining complex query parameter handling with validation, aliases, custom parsing, or cross-field validation in FastAPI endpoints.
user-invocable: false
disable-model-invocation: false
---

# Query Params

## Purpose

- Handle complex query parameters with validation and transformation.
- Provide class-based query parameter definition.
- Support custom parsing logic (e.g., sorting parameters).

## Structure

- Class with `__init__` defining query parameters via FastAPI `Query()`.
- Store parsed values as instance attributes.
- Include custom parsing methods for complex parameters.

## Template Parameters

- `{{ class_name }}` - Name of the query params class
- `{{ params }}` - List of query parameter definitions
- `{{ parsing_methods }}` - Optional custom parsing methods

## When to Use

Use query params class instead of simple `Query()` parameters when:

- Multiple query parameters (more than 3-4)
- Complex validation logic needed
- Custom parsing required (e.g., sorting strings)
- Parameters need transformation before use

## Example

### Simple Query Params

```python
from pydantic import Field

from .configured_base_serializer import ConfiguredRequestSerializer

__all__ = ["GetConveyorsRequest"]

class GetConveyorsRequest(ConfiguredRequestSerializer):
    page: int = Field(default=0, ge=0)
    per_page: int = Field(default=10, ge=1, le=100)
```

### Complex Query Params with Custom Parsing

```python
from fastapi import Query

from my_service.application import LoadSorting, SortOrder

__all__ = ["QueryLoadsParams"]

class QueryLoadsParams:
    def __init__(
        self,
        search: str | None = None,
        load_ids: list[str] | None = Query(default=None, alias="loadIds"),
        eta_from: str | None = Query(default=None, alias="etaFrom"),
        eta_to: str | None = Query(default=None, alias="etaTo"),
        statuses: list[str] | None = Query(default=None),
        warehouse_ids: list[str] | None = Query(default=None, alias="warehouseIds"),
        sorting: list[str] | None = Query(default=None),
        page: int | None = Query(default=None, ge=1),
        per_page: int | None = Query(default=None, ge=1, alias="perPage"),
    ):
        self.search = search
        self.load_ids = load_ids
        self.eta_from = eta_from
        self.eta_to = eta_to
        self.statuses = statuses
        self.warehouse_ids = warehouse_ids
        self.sorting = self._parse_sorting(sorting) if sorting else None
        self.page = page
        self.per_page = per_page

    def _parse_sorting(self, sorting: list[str]) -> list[tuple[LoadSorting, SortOrder]]:
        result = []
        for sort_item in sorting:
            parts = sort_item.split(":")
            if len(parts) == 2:
                sort_by = LoadSorting(parts[0])
                sort_order = SortOrder(parts[1])
                result.append((sort_by, sort_order))
        return result
```

## Query Parameter Patterns

### Simple Parameter

```python
search: str | None = None
```

### Parameter with Alias

```python
warehouse_id: str = Query(default="1", alias="warehouseId")
```

### List Parameter

```python
statuses: list[str] | None = Query(default=None)
```

### Parameter with Validation

```python
page: int = Query(default=1, ge=1)
per_page: int = Query(default=10, ge=1, le=100, alias="perPage")
```

### Datetime Parameters with Short Aliases

For datetime range filters, short aliases improve URL readability:

```python
from datetime import datetime

from pydantic import Field

from .configured_base_serializer import ConfiguredRequestSerializer

class GetTiresRequestV2(ConfiguredRequestSerializer):
    conveyor_id: str | None = Field(default=None)
    creation_time_from: datetime | None = Field(default=None, alias="ctFrom")
    creation_time_to: datetime | None = Field(default=None, alias="ctTo")
```

Common datetime alias patterns:

| Field Name | Short Alias | Example URL |
| --- | --- | --- |
| `creation_time_from` | `ctFrom` | `?ctFrom=2024-01-01T00:00:00Z` |
| `creation_time_to` | `ctTo` | `?ctTo=2024-12-31T23:59:59Z` |
| `updated_from` | `updFrom` | `?updFrom=2024-06-01T00:00:00Z` |
| `eta_from` | `etaFrom` | `?etaFrom=2024-03-15T08:00:00Z` |

## Usage in Endpoints

### With Depends()

```python
@router.get("")
def query_loads(
    params: QueryLoadsParams = Depends(),
    load_queries: LoadQueries = Depends(Provide[Containers.load_queries]),
):
    loads_details = load_queries.query_loads(
        search=params.search,
        load_ids=params.load_ids,
        eta_from=params.eta_from,
        eta_to=params.eta_to,
        statuses=params.statuses,
        warehouse_ids=params.warehouse_ids,
        sorting=params.sorting,
        page=params.page,
        per_page=params.per_page,
    )
    return QueryLoadsResponse.from_domain(loads_details)
```

## Cross-Field Validation

When parameters have mutual exclusivity or conditional requirements, validate in `__init__`:

```python
from datetime import datetime

from fastapi import HTTPException, Query, status

from my_service.infrastructure.services import TimeRange

__all__ = ["WarehouseMetricsParams"]

class WarehouseMetricsParams:
    def __init__(
        self,
        warehouse_id: str | None = Query(default=None, alias="warehouseId"),
        load_id: str | None = Query(default=None, alias="loadId"),
        time_range: TimeRange | None = Query(default=None, alias="timeRange"),
        custom_time_range_start: datetime | None = Query(default=None, alias="customTimeRangeStart"),
        custom_time_range_end: datetime | None = Query(default=None, alias="customTimeRangeEnd"),
    ):
        self.warehouse_id = warehouse_id
        self.load_id = load_id

        has_time_range = time_range is not None
        has_custom_range = custom_time_range_start is not None or custom_time_range_end is not None

        # Mutual exclusivity validation
        if has_time_range and has_custom_range:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot specify both timeRange and customTimeRange. Please provide only one.",
            )

        # Conditional requirement validation
        if has_custom_range:
            if custom_time_range_start is None or custom_time_range_end is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Both customTimeRangeStart and customTimeRangeEnd must be provided "
                        "when using custom time range."
                    ),
                )
            self.time_range = None
            self.custom_time_range = [custom_time_range_start, custom_time_range_end]
        else:
            self.time_range = time_range
            self.custom_time_range = None
```

### Common Validation Patterns

| Pattern | Example |
| --- | --- |
| Mutual exclusivity | `time_range` OR `custom_time_range`, not both |
| Conditional requirement | If `start` provided, `end` must also be provided |
| At least one required | Either `warehouse_id` or `load_id` must be specified |
| Range validation | `date_from` must be before `date_to` |

### At Least One Required

```python
def __init__(
    self,
    warehouse_id: str | None = Query(default=None, alias="warehouseId"),
    load_id: str | None = Query(default=None, alias="loadId"),
):
    if warehouse_id is None and load_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either warehouseId or loadId must be provided.",
        )
    self.warehouse_id = warehouse_id
    self.load_id = load_id
```

### Range Validation

```python
def __init__(
    self,
    date_from: datetime | None = Query(default=None, alias="dateFrom"),
    date_to: datetime | None = Query(default=None, alias="dateTo"),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="dateFrom must be before dateTo.",
        )
    self.date_from = date_from
    self.date_to = date_to
```

## Sorting Parameter Format

Common sorting parameter format: `field:order`

- `?sorting=eta:asc` - Sort by ETA ascending
- `?sorting=eta:asc&sorting=status:desc` - Multi-field sorting

Parsing:

```python
def _parse_sorting(self, sorting: list[str]) -> list[tuple[SortField, SortOrder]]:
    result = []
    for sort_item in sorting:
        parts = sort_item.split(":")
        if len(parts) == 2:
            sort_by = SortField(parts[0])
            sort_order = SortOrder(parts[1])
            result.append((sort_by, sort_order))
    return result
```

## Testing Guidance

- Test default values are applied correctly.
- Test validation constraints (ge, le, etc.).
- Test alias mapping works for camelCase input.
- Test custom parsing methods with valid and invalid input.
- Test list parameters with multiple values.
- Test cross-field validation rules (mutual exclusivity, conditional requirements).
- Test HTTPException is raised with correct status code and message.

---

## Template

```python
from fastapi import Query

{% if sorting_enabled %}
from {{ application_module }} import {{ sort_field_enum }}, SortOrder
{% endif %}

__all__ = ["{{ class_name }}"]

class {{ class_name }}:
    def __init__(
        self,
{% for param in params %}
        {{ param.name }}: {{ param.type }} = {% if param.query %}Query({{ param.query }}){% else %}{{ param.default }}{% endif %},
{% endfor %}
    ):
{% for param in params %}
{% if param.transform %}
        self.{{ param.name }} = self._parse_{{ param.name }}({{ param.name }}) if {{ param.name }} else None
{% else %}
        self.{{ param.name }} = {{ param.name }}
{% endif %}
{% endfor %}
{% if sorting_enabled %}

    def _parse_sorting(self, sorting: list[str]) -> list[tuple[{{ sort_field_enum }}, SortOrder]]:
        result = []
        for sort_item in sorting:
            parts = sort_item.split(":")
            if len(parts) == 2:
                sort_by = {{ sort_field_enum }}(parts[0])
                sort_order = SortOrder(parts[1])
                result.append((sort_by, sort_order))
        return result
{% endif %}
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ class_name }}` | Name of the query params class | `QueryLoadsParams` |
| `{{ params }}` | List of parameter definitions | See below |
| `{{ application_module }}` | Module for sorting enums | `my_service.application` |
| `{{ sort_field_enum }}` | Enum for sort fields | `LoadSorting` |
| `{{ sorting_enabled }}` | Whether sorting is used | `true` |

### Parameter Definition Structure

```python
{
    "name": "page",
    "type": "int | None",
    "default": "None",
    "query": "default=None, ge=1",
    "transform": false
}
```
