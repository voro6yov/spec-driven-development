---
name: result-set-serializer
description: Result Set Serializer pattern for REST API list responses. Use when a response needs simple count/total metadata without full pagination (page numbers, perPage, totalPages).
user-invocable: false
disable-model-invocation: false
---

# Result Set Serializer

## Purpose

- Provide simple count/total metadata for list responses.
- Offer a lightweight alternative to full pagination metadata.
- Support responses where page information isn't needed.

## Structure

- Extend `ConfiguredResponseSerializer` base class.
- Contains `count` (items in current result) and `total` (total available).
- Implement `from_domain()` accepting a TypedDict or dict.

## Template Parameters

- `{{ serializer_name }}` - Name of the serializer class (default: `ResultSetSerializer`)
- `{{ domain_type }}` - Type hint for the domain input
- `{{ domain_import }}` - Import path for domain type

## When to Use

Use result set serializer when:

- Response needs count/total but not page numbers
- All results are returned in a single response
- Client needs to know "X of Y items" without pagination
- Simpler than full `PaginatedResultMetadataSerializer`

## Comparison with Pagination Serializers

| Aspect | ResultSetSerializer | PaginatedResultMetadataSerializer |
| --- | --- | --- |
| Fields | `count`, `total` | `count`, `total`, `page`, `perPage`, `totalPages` |
| Use case | All items or subset | Paginated results |
| Complexity | Simple | Full pagination |

## Example

### Basic Result Set Serializer

```python
from my_service.domain import ResultSetInfo

from .configured_base_serializer import ConfiguredResponseSerializer

__all__ = ["ResultSetSerializer"]

class ResultSetSerializer(ConfiguredResponseSerializer):
    count: int
    total: int

    @classmethod
    def from_domain(cls, result_set: ResultSetInfo) -> "ResultSetSerializer":
        return cls(**result_set)
```

### Domain Type Definition

The domain layer typically defines the result set info as a TypedDict:

```python
from typing import TypedDict

class ResultSetInfo(TypedDict):
    count: int
    total: int
```

### Usage in Response Serializer

```python
from pydantic import Field

from my_service.domain import ItemsInfo

from ...configured_base_serializer import ConfiguredResponseSerializer
from ...result_set import ResultSetSerializer

__all__ = ["GetItemsResponse"]

class ItemSerializer(ConfiguredResponseSerializer):
    id: str
    name: str

    @classmethod
    def from_domain(cls, item: dict) -> "ItemSerializer":
        return cls(id=item["id"], name=item["name"])

class GetItemsResponse(ConfiguredResponseSerializer):
    items: list[ItemSerializer]
    result_set: ResultSetSerializer = Field(..., alias="resultSet")

    @classmethod
    def from_domain(cls, items_info: ItemsInfo) -> "GetItemsResponse":
        return cls(
            items=[ItemSerializer.from_domain(item) for item in items_info["items"]],
            result_set=ResultSetSerializer.from_domain(items_info["result_set"]),
        )
```

### Query Result Structure

```python
from typing import TypedDict

class ResultSetInfo(TypedDict):
    count: int
    total: int

class ItemsInfo(TypedDict):
    items: list[dict]
    result_set: ResultSetInfo
```

## Response JSON Format

```json
{
  "items": [
    {"id": "1", "name": "Item 1"},
    {"id": "2", "name": "Item 2"}
  ],
  "resultSet": {
    "count": 2,
    "total": 150
  }
}
```

## Testing Guidance

- Test `from_domain()` with valid result set info.
- Verify count and total are correctly mapped.
- Test camelCase serialization (`resultSet` in JSON).
- Test with edge cases (count=0, count=total).

### Test Example

```python
def test_result_set_serializer():
    result_set_info = {"count": 10, "total": 100}
    
    serializer = ResultSetSerializer.from_domain(result_set_info)
    
    assert serializer.count == 10
    assert serializer.total == 100

def test_result_set_json_output():
    result_set_info = {"count": 5, "total": 50}
    
    serializer = ResultSetSerializer.from_domain(result_set_info)
    json_output = serializer.model_dump(by_alias=True)
    
    assert json_output == {"count": 5, "total": 50}
```

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
    count: int
    total: int

    @classmethod
    def from_domain(cls, result_set: {{ domain_type }}) -> "{{ serializer_name }}":
        return cls(**result_set)
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ serializer_name }}` | Name of the serializer class | `ResultSetSerializer` |
| `{{ base_serializer_module }}` | Import path for base serializer | `.configured_base_serializer` |
| `{{ domain_import }}` | Module path for domain type | `my_service.domain` |
| `{{ domain_type }}` | Type hint for domain input | `ResultSetInfo`, `dict[str, Any]` |
