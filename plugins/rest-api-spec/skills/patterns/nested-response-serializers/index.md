---
name: nested-response-serializers
description: Nested Response Serializers pattern for REST API responses. Use when structuring complex hierarchical responses with child serializers, polymorphic union types, or deeply nested domain-to-DTO transformations.
user-invocable: false
disable-model-invocation: false
---

# Nested Response Serializers

## Purpose

- Structure complex API responses with hierarchical data.
- Delegate serialization logic to child serializers.
- Maintain separation of concerns in large response models.

## Structure

- Parent serializer contains child serializer fields.
- Each serializer has its own `from_domain()` method.
- Parent's `from_domain()` orchestrates child serialization.
- Use type aliases for union types (polymorphic responses).

## When to Use

Use nested serializers when:

- Response has 2+ levels of nested objects
- Child objects are reused across multiple responses
- Complex domain objects need transformation
- Response includes collections of typed objects

## Example

### Basic Nested Structure

```python
from pydantic import Field

from ...configured_base_serializer import ConfiguredResponseSerializer

__all__ = ["GetLoadResponse", "LineItemSerializer", "TiresSerializer"]

class LineItemSerializer(ConfiguredResponseSerializer):
    item_number: str = Field(..., alias="itemNumber")
    product_name: str = Field(..., alias="productName")
    total_quantity: int = Field(..., alias="totalQuantity")
    status: str

    @classmethod
    def from_domain(cls, line_item) -> "LineItemSerializer":
        return cls(
            item_number=line_item.item_number,
            product_name=line_item.product_name,
            total_quantity=line_item.total_quantity,
            status=line_item.status,
        )

class TiresSerializer(ConfiguredResponseSerializer):
    unexpected_tires: list[UnexpectedTireSerializer] = Field(..., alias="unexpectedTires")
    failed_tires: list[FailedTireSerializer] = Field(..., alias="failedTires")

class GetLoadResponse(ConfiguredResponseSerializer):
    id: str
    status: str
    line_items: list[LineItemSerializer] = Field(..., alias="lineItems")
    tires: TiresSerializer

    @classmethod
    def from_domain(cls, load: Load) -> "GetLoadResponse":
        return cls(
            id=load.id,
            status=load.status,
            line_items=[LineItemSerializer.from_domain(item) for item in load.items],
            tires=TiresSerializer(
                unexpected_tires=[
                    UnexpectedTireSerializer.from_domain(t) 
                    for t in load.tires.unexpected_tires
                ],
                failed_tires=[
                    FailedTireSerializer.from_domain(t) 
                    for t in load.tires.failed_tires
                ],
            ),
        )
```

### Polymorphic Responses (Union Types)

When a field can contain different types of objects:

```python
from typing import Literal

from pydantic import Field

from ...configured_base_serializer import ConfiguredResponseSerializer

class RecognizedTireSerializer(ConfiguredResponseSerializer):
    tire_id: str = Field(..., alias="tireId")
    extraction_info: ExtractionInfoSerializer | None = Field(None, alias="extractionInfo")

    @classmethod
    def from_domain(cls, recognized_tire: dict) -> "RecognizedTireSerializer":
        extraction_info = None
        if recognized_tire.get("extraction_info"):
            extraction_info = ExtractionInfoSerializer.from_domain(recognized_tire["extraction_info"])
        return cls(
            tire_id=recognized_tire["tire_id"],
            extraction_info=extraction_info,
        )

class FailedTireSerializer(ConfiguredResponseSerializer):
    tire_id: str = Field(..., alias="tireId")
    error_message: str = Field(..., alias="errorMessage")
    status: Literal["waiting", "retried", "deferred", "confirmed"]

    @classmethod
    def from_domain(cls, failed_tire: dict) -> "FailedTireSerializer":
        return cls(
            tire_id=failed_tire["tire_id"],
            error_message=failed_tire["error_message"],
            status=failed_tire["status"],
        )

class UnexpectedTireSerializer(ConfiguredResponseSerializer):
    tire_id: str = Field(..., alias="tireId")
    extraction_info: ExtractionInfoSerializer = Field(..., alias="extractionInfo")
    status: Literal["waiting", "confirmed", "deferred"]

    @classmethod
    def from_domain(cls, unexpected_tire: dict) -> "UnexpectedTireSerializer":
        return cls(
            tire_id=unexpected_tire["tire_id"],
            extraction_info=ExtractionInfoSerializer.from_domain(unexpected_tire["extraction_info"]),
            status=unexpected_tire["status"],
        )

# Type alias for union type
BypassedTireSerializer = (
    RecognizedTireSerializer 
    | UnexpectedTireSerializer 
    | UnrecognizedTireSerializer 
    | FailedTireSerializer
)
BypassedTiresSerializer = list[BypassedTireSerializer]

class TiresSerializer(ConfiguredResponseSerializer):
    bypassed_tires: BypassedTiresSerializer = Field(..., alias="bypassedTires")
```

### Discriminated Serialization

When you need to choose serializer based on data content:

```python
class GetLoadResponse(ConfiguredResponseSerializer):
    tires: TiresSerializer

    @classmethod
    def from_domain(cls, load: Load) -> "GetLoadResponse":
        return cls(
            tires=TiresSerializer(
                bypassed_tires=[
                    cls._serialize_bypassed_tire(tire) 
                    for tire in load.tires.bypassed_tires
                ],
            ),
        )

    @staticmethod
    def _serialize_bypassed_tire(
        bypassed_tire: dict,
    ) -> RecognizedTireSerializer | FailedTireSerializer | UnexpectedTireSerializer:
        # Discriminate based on data structure
        if "error_message" in bypassed_tire:
            return FailedTireSerializer.from_domain(bypassed_tire)

        if "line_items" in bypassed_tire:
            return UnrecognizedTireSerializer.from_domain(bypassed_tire)

        if "status" in bypassed_tire and "extraction_info" in bypassed_tire:
            return UnexpectedTireSerializer.from_domain(bypassed_tire)

        return RecognizedTireSerializer.from_domain(bypassed_tire)
```

### Deeply Nested Structures

```python
class ProductDataSerializer(ConfiguredResponseSerializer):
    product_number: str = Field(..., alias="productNumber")
    product_name: str = Field(..., alias="productName")
    confidence: float

    @classmethod
    def from_domain(cls, product_data: dict) -> "ProductDataSerializer":
        return cls(
            product_number=product_data["product_number"],
            product_name=product_data["product_name"],
            confidence=product_data["confidence"],
        )

class ExtractionInfoSerializer(ConfiguredResponseSerializer):
    tire_size: str = Field(..., alias="tireSize")
    manufacturer: str
    search_results: list[ProductDataSerializer] = Field(..., alias="searchResults")

    @classmethod
    def from_domain(cls, extraction_info: dict) -> "ExtractionInfoSerializer":
        return cls(
            tire_size=extraction_info["tire_size"],
            manufacturer=extraction_info["manufacturer"],
            search_results=[
                ProductDataSerializer.from_domain(result) 
                for result in extraction_info["search_results"]
            ],
        )

class TireSerializer(ConfiguredResponseSerializer):
    id: str
    extraction_info: ExtractionInfoSerializer | None

    @classmethod
    def from_domain(cls, tire: dict) -> "TireSerializer":
        return cls(
            id=tire["tire_id"],
            extraction_info=ExtractionInfoSerializer.from_domain(tire["extraction_info"])
            if tire["extraction_info"] else None,
        )
```

## Patterns

### 1. Collection Delegation

```python
line_items=[LineItemSerializer.from_domain(item) for item in domain.items]
```

### 2. Optional Field Handling

```python
extraction_info=ExtractionInfoSerializer.from_domain(data["extraction_info"])
    if data.get("extraction_info") else None
```

### 3. Inline Child Construction

When child serializer doesn't have `from_domain()`:

```python
tires=TiresSerializer(
    unexpected_tires=[...],
    failed_tires=[...],
)
```

### 4. Type-Safe Status Fields

```python
status: Literal["waiting", "confirmed", "deferred"]
```

## File Organization

For complex responses, keep serializers in the same file or split logically:

```
serializers/v2/loads/
├── __init__.py
├── get_load_response.py      # Main response + all nested serializers
├── line_item.py              # If reused elsewhere
└── tire_serializers.py       # If tire serializers are complex
```

## Testing Guidance

- Test each nested serializer's `from_domain()` independently.
- Test parent serializer correctly delegates to children.
- Test polymorphic discrimination logic with all variants.
- Test optional field handling (null vs missing).
- Verify camelCase aliases in nested JSON output.

## Common Pitfalls

### Circular Imports

Avoid by keeping related serializers in the same file or using forward references:

```python
from __future__ import annotations  # Enable forward references
```

### Missing `from_domain()` on Children

Ensure all nested serializers have `from_domain()` for consistency.

### Deep Nesting Performance

For very deep structures, consider flattening or pagination.
