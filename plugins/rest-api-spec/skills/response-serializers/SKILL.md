---
name: response-serializers
description: Response Serializers pattern for REST API. Use when transforming domain objects into JSON-serializable response payloads with consistent camelCase field naming.
user-invocable: false
disable-model-invocation: false
---

# Response Serializers

## Purpose

- Transform domain objects into JSON-serializable response format.
- Provide consistent camelCase field naming for API consumers.
- Encapsulate domain-to-API mapping logic.

## Structure

- Extend `ConfiguredResponseSerializer` base class.
- Define fields matching the API response contract.
- Implement `from_domain()` class method for transformation.
- Use type hints for all fields.

## Template Parameters

- `{{ serializer_name }}` - Name of the serializer class
- `{{ fields }}` - List of field definitions with name, type, and optional alias
- `{{ domain_type }}` - Type hint for the domain object parameter
- `{{ domain_import }}` - Import path for domain types (optional)
- `{{ field_mappings }}` - Mapping from domain object to serializer fields

## Response Types

### Single Resource Response

```python
from my_service.domain import Conveyor

from ...configured_base_serializer import ConfiguredResponseSerializer

__all__ = ["CreateConveyorResponse"]

class CreateConveyorResponse(ConfiguredResponseSerializer):
    id: str

    @classmethod
    def from_domain(cls, conveyor: Conveyor) -> "CreateConveyorResponse":
        return cls(id=conveyor.id)
```

### Resource with Multiple Fields

```python
from datetime import datetime
from typing import Any

from ...configured_base_serializer import ConfiguredResponseSerializer

__all__ = ["GetConveyorResponse"]

class GetConveyorResponse(ConfiguredResponseSerializer):
    id: str
    warehouse_id: str
    name: str
    status: str
    current_load_id: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, conveyor: dict[str, Any]) -> "GetConveyorResponse":
        return cls(
            id=conveyor["id"],
            warehouse_id=conveyor["warehouse_id"],
            name=conveyor["name"],
            status=conveyor["status"],
            current_load_id=conveyor.get("current_load_id"),
            created_at=conveyor["created_at"],
            updated_at=conveyor["updated_at"],
        )
```

### List Response with Pagination

```python
from datetime import datetime
from typing import Any

from pydantic import Field

from my_service.domain import ConveyorsInfo

from ...configured_base_serializer import ConfiguredResponseSerializer
from ...paginated_result_metadata import PaginatedResultMetadataSerializer

__all__ = ["GetConveyorsResponse"]

class BriefConveyorSerializer(ConfiguredResponseSerializer):
    id: str
    warehouse_id: str
    name: str
    status: str
    current_load_id: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, conveyor: dict[str, Any]) -> "BriefConveyorSerializer":
        return cls(
            id=conveyor["id"],
            warehouse_id=conveyor["warehouse_id"],
            name=conveyor["name"],
            status=conveyor["status"],
            current_load_id=conveyor.get("current_load_id"),
            created_at=conveyor["created_at"],
            updated_at=conveyor["updated_at"],
        )

class ConveyorsMetadataSerializer(PaginatedResultMetadataSerializer):
    pass

class GetConveyorsResponse(ConfiguredResponseSerializer):
    conveyors: list[BriefConveyorSerializer]
    metadata: ConveyorsMetadataSerializer

    @classmethod
    def from_domain(cls, conveyors_info: ConveyorsInfo) -> "GetConveyorsResponse":
        return cls(
            conveyors=[
                BriefConveyorSerializer.from_domain(conveyor)
                for conveyor in conveyors_info["conveyors"]
            ],
            metadata=ConveyorsMetadataSerializer.from_domain(conveyors_info["metadata"]),
        )
```

### Action Response

```python
from my_service.domain import Conveyor

from ...configured_base_serializer import ConfiguredResponseSerializer

__all__ = ["StopUnloadingResponse"]

class StopUnloadingResponse(ConfiguredResponseSerializer):
    id: str
    status: str

    @classmethod
    def from_domain(cls, conveyor: Conveyor) -> "StopUnloadingResponse":
        return cls(id=conveyor.id, status=conveyor.status.value)
```

## Advanced `from_domain()` Patterns

### Filtering and Sorting in Response

For complex responses where the API supports client-side filtering/sorting without re-querying:

```python
from enum import Enum

from pydantic import Field

from my_service.domain import Load

from ...configured_base_serializer import ConfiguredResponseSerializer

class LineItemSorting(Enum):
    STATUS = "status"
    TOTAL_QUANTITY = "totalQuantity"

class SortOrder(Enum):
    ASC = "asc"
    DESC = "desc"

class GetLoadResponse(ConfiguredResponseSerializer):
    id: str
    line_items: list[LineItemSerializer] = Field(..., alias="lineItems")

    @classmethod
    def from_domain(
        cls,
        load: Load,
        search: str | None = None,
        statuses: list[str] | None = None,
        sorting: list[str] | None = None,
    ) -> "GetLoadResponse":
        line_items = list(load.items)

        # Filter by status
        if statuses:
            normalized_statuses = [status.lower() for status in statuses]
            line_items = [item for item in line_items if item.status.lower() in normalized_statuses]

        # Filter by search term
        if search:
            search_lower = search.lower()
            line_items = [item for item in line_items if search_lower in item.product_name.lower()]

        # Apply sorting
        if sorting:
            parsed_sorting = cls._parse_sorting(sorting)
            line_items = cls._sort_line_items(line_items, parsed_sorting)

        return cls(
            id=load.id,
            line_items=[LineItemSerializer.from_domain(item) for item in line_items],
        )

    @staticmethod
    def _parse_sorting(sorting: list[str]) -> list[tuple[LineItemSorting, SortOrder]]:
        result = []
        for sort_item in sorting:
            parts = sort_item.split(":")
            if len(parts) == 2:
                sort_by = LineItemSorting(parts[0])
                sort_order = SortOrder(parts[1])
                result.append((sort_by, sort_order))
        return result

    @staticmethod
    def _sort_line_items(line_items: list, sorting: list[tuple[LineItemSorting, SortOrder]]) -> list:
        if not sorting:
            return line_items

        sorted_items = line_items[:]

        for sort_by, sort_order in reversed(sorting):
            reverse = sort_order == SortOrder.DESC

            if sort_by == LineItemSorting.STATUS:
                sorted_items = sorted(sorted_items, key=lambda item: item.status, reverse=reverse)
            elif sort_by == LineItemSorting.TOTAL_QUANTITY:
                sorted_items = sorted(sorted_items, key=lambda item: item.total_quantity, reverse=reverse)

        return sorted_items
```

### Usage in Endpoint

```python
@router.get("/{load_id}", response_model=GetLoadResponse)
@inject
def get_load(
    load_id: str,
    search: str | None = Query(default=None),
    statuses: list[str] | None = Query(default=None),
    sorting: list[str] | None = Query(default=None),
    load_commands: LoadCommands = Depends(Provide[Containers.load_commands]),
):
    load = load_commands.get_load(load_id=load_id)
    return GetLoadResponse.from_domain(load, search=search, statuses=statuses, sorting=sorting)
```

### When to Use Response-Level Filtering

Use this pattern when:

- Data is already loaded and filtering doesn't require DB query
- Client needs different views of the same data
- Sorting is purely presentational (not affecting pagination)

Avoid when:

- Large datasets that should be filtered at the database level
- Pagination is affected by filtering (total counts change)
- Complex filtering logic that belongs in the query layer

## Domain Input Types

The `from_domain()` method can accept:

1. **Domain entities/aggregates** - Full domain objects with methods
2. **TypedDicts** - Query result DTOs from the application layer
3. **dict[str, Any]** - Untyped dictionaries from queries
4. **Primitive values** - For simple responses

## Field Conventions

### camelCase Conversion

Fields are automatically converted to camelCase via the base class configuration:

```python
warehouse_id: str  # Serialized as "warehouseId"
created_at: datetime  # Serialized as "createdAt"
```

### Custom Aliases

Use `Field(alias="...")` for non-standard mappings:

```python
from pydantic import Field

estimated_time_of_arrival: str = Field(..., alias="eta")
```

### Optional Fields

```python
current_load_id: str | None  # Can be null in response
```

## Related Patterns

- [**Nested Response Serializers**](nested-response-serializers.md) - For complex hierarchical responses with multiple nested objects
- [**Polymorphic Response Serializers**](polymorphic-response-serializers.md) - For Union types with discriminator logic
- [**Pagination Serializers**](pagination-serializers.md) - For list responses with pagination metadata
- [**Literal Type Fields**](literal-type-fields.md) - For constraining status/category values

## Testing Guidance

- Test `from_domain()` with valid domain objects.
- Verify all fields are correctly mapped.
- Test with edge cases (None values, empty lists).
- Verify camelCase serialization in JSON output.
- Test filtering/sorting parameters when implemented.

---

## Template

```python
{% if domain_import %}
from {{ domain_import }} import {{ domain_type }}
{% else %}
from typing import Any
{% endif %}

from {{ base_serializer_module }} import ConfiguredResponseSerializer

__all__ = ["{{ serializer_name }}"]

class {{ serializer_name }}(ConfiguredResponseSerializer):
{% for field in fields %}
    {{ field.name }}: {{ field.type }}{% if field.alias %} = Field(..., alias="{{ field.alias }}"){% endif %}

{% endfor %}

    @classmethod
    def from_domain(cls, {{ domain_param }}: {{ domain_type }}) -> "{{ serializer_name }}":
        return cls(
{% for mapping in field_mappings %}
            {{ mapping.field }}={{ mapping.value }},
{% endfor %}
        )
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ serializer_name }}` | Name of the serializer class | `GetConveyorResponse` |
| `{{ domain_import }}` | Import path for domain types | `my_service.domain` |
| `{{ domain_type }}` | Type hint for domain parameter | `Conveyor`, `dict[str, Any]` |
| `{{ domain_param }}` | Parameter name for domain object | `conveyor`, `data` |
| `{{ base_serializer_module }}` | Import path for base serializer | `...configured_base_serializer` |
| `{{ fields }}` | List of field definitions | `[{"name": "id", "type": "str"}]` |
| `{{ field_mappings }}` | Field to domain mappings | `[{"field": "id", "value": "conveyor.id"}]` |
