---
name: pagination-serializers
description: Pagination Serializers pattern for REST API list responses. Use when building list endpoints that need consistent pagination metadata (count/total) transformed from domain pagination info to API format.
user-invocable: false
disable-model-invocation: false
---

# Pagination Serializers

## Purpose

- Provide consistent pagination metadata in list responses.
- Transform domain pagination info to API format.
- Support count and total for result sets.

## Structure

- `ResultSetSerializer` - Contains count and total.
- `PaginatedResultMetadataSerializer` - Wraps result set.
- Both extend `ConfiguredResponseSerializer`.
- Both have `from_domain()` class methods.

## Template Parameters

- `{{ domain_module }}` - Import path for domain types
- `{{ base_serializer_module }}` - Import path for base serializers

## Example

### ResultSetSerializer

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

### PaginatedResultMetadataSerializer

```python
from pydantic import Field

from my_service.domain import PaginatedResultMetadataInfo

from .configured_base_serializer import ConfiguredResponseSerializer
from .result_set import ResultSetSerializer

__all__ = ["PaginatedResultMetadataSerializer"]

class PaginatedResultMetadataSerializer(ConfiguredResponseSerializer):
    result_set: ResultSetSerializer = Field(..., alias="resultSet")

    @classmethod
    def from_domain(cls, metadata: PaginatedResultMetadataInfo) -> "PaginatedResultMetadataSerializer":
        return cls(
            result_set=ResultSetSerializer.from_domain(result_set=metadata["result_set"]),
        )
```

## Domain Types

### ResultSetInfo

```python
from typing import TypedDict

class ResultSetInfo(TypedDict):
    count: int
    total: int
```

### PaginatedResultMetadataInfo

```python
from typing import TypedDict

class PaginatedResultMetadataInfo(TypedDict):
    result_set: ResultSetInfo
```

## Usage in List Response

```python
from .configured_base_serializer import ConfiguredResponseSerializer
from .paginated_result_metadata import PaginatedResultMetadataSerializer

class ConveyorsMetadataSerializer(PaginatedResultMetadataSerializer):
    pass

class GetConveyorsResponse(ConfiguredResponseSerializer):
    conveyors: list[BriefConveyorSerializer]
    metadata: ConveyorsMetadataSerializer

    @classmethod
    def from_domain(cls, conveyors_info: ConveyorsInfo) -> "GetConveyorsResponse":
        return cls(
            conveyors=[
                BriefConveyorSerializer.from_domain(c)
                for c in conveyors_info["conveyors"]
            ],
            metadata=ConveyorsMetadataSerializer.from_domain(conveyors_info["metadata"]),
        )
```

## Response Format

```json
{
  "conveyors": [...],
  "metadata": {
    "resultSet": {
      "count": 10,
      "total": 100
    }
  }
}
```

## Testing Guidance

- Test `ResultSetSerializer.from_domain()` with valid data.
- Test `PaginatedResultMetadataSerializer.from_domain()` with nested structure.
- Verify camelCase output (`resultSet`, not `result_set`).
- Test with zero count and total.

---

## Template

### result_set.py

```python
from {{ domain_module }} import ResultSetInfo

from {{ base_serializer_module }} import ConfiguredResponseSerializer

__all__ = ["ResultSetSerializer"]

class ResultSetSerializer(ConfiguredResponseSerializer):
    count: int
    total: int

    @classmethod
    def from_domain(cls, result_set: ResultSetInfo) -> "ResultSetSerializer":
        return cls(**result_set)
```

### paginated_result_metadata.py

```python
from pydantic import Field

from {{ domain_module }} import PaginatedResultMetadataInfo

from {{ base_serializer_module }} import ConfiguredResponseSerializer
from .result_set import ResultSetSerializer

__all__ = ["PaginatedResultMetadataSerializer"]

class PaginatedResultMetadataSerializer(ConfiguredResponseSerializer):
    result_set: ResultSetSerializer = Field(..., alias="resultSet")

    @classmethod
    def from_domain(cls, metadata: PaginatedResultMetadataInfo) -> "PaginatedResultMetadataSerializer":
        return cls(
            result_set=ResultSetSerializer.from_domain(result_set=metadata["result_set"]),
        )
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ domain_module }}` | Import path for domain types | `my_service.domain` |
| `{{ base_serializer_module }}` | Import path for base serializer | `.configured_base_serializer` |
