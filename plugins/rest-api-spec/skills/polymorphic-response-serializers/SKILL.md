---
name: polymorphic-response-serializers
description: Polymorphic Response Serializers pattern for REST API responses. Use when an endpoint returns items with different shapes, when entity states have different fields, or when aggregating heterogeneous collections in a single response.
user-invocable: false
disable-model-invocation: false
---

# Polymorphic Response Serializers

## Purpose

- Handle responses that can return different shapes based on data type.
- Use Union types to represent multiple possible response structures.
- Implement discriminator logic to select correct serializer at runtime.

## Structure

- Define multiple serializer classes for different response variants.
- Create Union type alias combining all variants.
- Implement static helper method with discrimination logic.
- Use in parent serializer's `from_domain()` method.

## Template Parameters

- `{{ serializer_variants }}` - List of serializer class definitions
- `{{ union_type_name }}` - Name for the Union type alias
- `{{ discriminator_method }}` - Name of helper method for type selection

## When to Use

Use polymorphic response serializers when:

- API returns items that can have different structures
- Different states of an entity have different fields
- Aggregating heterogeneous collections in a single response

## Example

### Variant Serializers

Define each variant with its specific fields:

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
```

### Union Type Definition

```python
BypassedTireSerializer = (
    RecognizedTireSerializer | UnexpectedTireSerializer | UnrecognizedTireSerializer | FailedTireSerializer
)
BypassedTiresSerializer = list[BypassedTireSerializer]
```

### Discriminator Method

Implement static method to select correct serializer based on data shape:

```python
class GetLoadResponse(ConfiguredResponseSerializer):
    # ... fields
    
    @staticmethod
    def _serialize_bypassed_tire(
        bypassed_tire: dict,
    ) -> RecognizedTireSerializer | UnexpectedTireSerializer | UnrecognizedTireSerializer | FailedTireSerializer:
        # Discriminate by unique field presence
        if "error_message" in bypassed_tire:
            return FailedTireSerializer.from_domain(bypassed_tire)

        if "line_items" in bypassed_tire:
            return UnrecognizedTireSerializer.from_domain(bypassed_tire)

        if "status" in bypassed_tire and "extraction_info" in bypassed_tire:
            return UnexpectedTireSerializer.from_domain(bypassed_tire)

        return RecognizedTireSerializer.from_domain(bypassed_tire)
```

### Usage in Parent Serializer

```python
class GetLoadResponse(ConfiguredResponseSerializer):
    id: str
    tires: TiresSerializer
    # ... other fields

    @classmethod
    def from_domain(cls, load: Load) -> "GetLoadResponse":
        return cls(
            id=load.id,
            tires=TiresSerializer(
                unexpected_tires=[UnexpectedTireSerializer.from_domain(t) for t in load.tires.unexpected_tires],
                failed_tires=[FailedTireSerializer.from_domain(t) for t in load.tires.failed_tires],
                bypassed_tires=[GetLoadResponse._serialize_bypassed_tire(t) for t in load.tires.bypassed_tires],
            ),
        )
```

## Discrimination Strategies

### By Unique Field Presence

```python
if "error_message" in data:
    return ErrorVariantSerializer.from_domain(data)
if "success_data" in data:
    return SuccessVariantSerializer.from_domain(data)
```

### By Type Field Value

```python
type_map = {
    "error": ErrorVariantSerializer,
    "success": SuccessVariantSerializer,
    "pending": PendingVariantSerializer,
}
serializer_class = type_map[data["type"]]
return serializer_class.from_domain(data)
```

### By Status Field

```python
if data["status"] == "failed":
    return FailedSerializer.from_domain(data)
elif data["status"] in ["waiting", "processing"]:
    return PendingSerializer.from_domain(data)
else:
    return CompletedSerializer.from_domain(data)
```

## Literal Types for Status Fields

Use `Literal` to constrain status values in OpenAPI schema:

```python
from typing import Literal

class UnexpectedTireSerializer(ConfiguredResponseSerializer):
    status: Literal["waiting", "confirmed", "deferred"]
```

Benefits:

- OpenAPI schema shows exact allowed values
- Type checker validates status assignments
- Self-documenting API contract

## Container Serializer Pattern

Wrap polymorphic collection in a container serializer:

```python
class TiresSerializer(ConfiguredResponseSerializer):
    unexpected_tires: list[UnexpectedTireSerializer] = Field(..., alias="unexpectedTires")
    unrecognized_tires: list[UnrecognizedTireSerializer] = Field(..., alias="unrecognizedTires")
    failed_tires: list[FailedTireSerializer] = Field(..., alias="failedTires")
    bypassed_tires: BypassedTiresSerializer = Field(..., alias="bypassedTires")
```

## Testing Guidance

- Test each variant serializer independently.
- Test discriminator method with data for each variant type.
- Test edge cases where discrimination fields are missing.
- Verify OpenAPI schema includes all Union variants.
- Test list responses with mixed variant types.

### Test Example

```python
def test_serialize_failed_tire():
    data = {"tire_id": "123", "error_message": "Processing failed", "status": "waiting"}
    
    result = GetLoadResponse._serialize_bypassed_tire(data)
    
    assert isinstance(result, FailedTireSerializer)
    assert result.tire_id == "123"
    assert result.error_message == "Processing failed"

def test_serialize_recognized_tire():
    data = {"tire_id": "456", "extraction_info": None}
    
    result = GetLoadResponse._serialize_bypassed_tire(data)
    
    assert isinstance(result, RecognizedTireSerializer)

def test_bypassed_tires_mixed_types():
    tires_data = [
        {"tire_id": "1", "error_message": "Failed", "status": "waiting"},
        {"tire_id": "2", "extraction_info": None},
    ]
    
    results = [GetLoadResponse._serialize_bypassed_tire(t) for t in tires_data]
    
    assert isinstance(results[0], FailedTireSerializer)
    assert isinstance(results[1], RecognizedTireSerializer)
```

---

## Template

```python
from typing import Literal

from pydantic import Field

from {{ base_serializer_module }} import ConfiguredResponseSerializer

__all__ = [
{% for variant in serializer_variants %}
    "{{ variant.class_name }}",
{% endfor %}
    "{{ union_type_name }}",
]

{% for variant in serializer_variants %}

class {{ variant.class_name }}(ConfiguredResponseSerializer):
{% for field in variant.fields %}
    {{ field.name }}: {{ field.type }}{% if field.alias %} = Field(..., alias="{{ field.alias }}"){% endif %}

{% endfor %}

    @classmethod
    def from_domain(cls, data: dict) -> "{{ variant.class_name }}":
        return cls(
{% for field in variant.fields %}
            {{ field.name }}=data["{{ field.domain_key }}"],
{% endfor %}
        )
{% endfor %}

{{ union_type_name }} = {% for variant in serializer_variants %}{{ variant.class_name }}{% if not loop.last %} | {% endif %}{% endfor %}
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ base_serializer_module }}` | Import path for base serializer | `...configured_base_serializer` |
| `{{ serializer_variants }}` | List of variant definitions | See below |
| `{{ union_type_name }}` | Name for Union type alias | `BypassedTireSerializer` |

### Variant Definition Structure

```python
{
    "class_name": "FailedTireSerializer",
    "fields": [
        {"name": "tire_id", "type": "str", "alias": "tireId", "domain_key": "tire_id"},
        {"name": "error_message", "type": "str", "alias": "errorMessage", "domain_key": "error_message"},
        {"name": "status", "type": "Literal[\"waiting\", \"retried\"]", "alias": None, "domain_key": "status"}
    ]
}
```
