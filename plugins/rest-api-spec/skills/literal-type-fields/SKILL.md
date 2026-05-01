---
name: literal-type-fields
description: Literal Type Fields pattern for REST API response serializers. Use when constraining response fields to a small set of fixed values, generating accurate OpenAPI enum schemas, or defining discriminator fields.
user-invocable: false
disable-model-invocation: false
---

# Literal Type Fields

## Purpose

- Constrain response fields to specific allowed values.
- Generate accurate OpenAPI enum schemas.
- Provide compile-time type checking for status and category fields.

## Structure

- Use `typing.Literal` for fields with known fixed values.
- Define allowed values inline in the field type.
- Apply to status fields, categories, and discriminator fields.

## When to Use

Use Literal types when:

- Field has a small set of known, stable values
- Values represent states or categories (not domain enums)
- OpenAPI schema should show exact allowed values
- Type checker should validate value assignments

Use Enum instead when:

- Values are used throughout the domain layer
- Need enum methods (`.value`, iteration)
- Values may expand and need centralized definition

## Example

### Status Field with Literal

```python
from typing import Literal

from pydantic import Field

from ...configured_base_serializer import ConfiguredResponseSerializer

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
```

### Multiple Literal Fields

```python
from typing import Literal

from pydantic import Field

from ...configured_base_serializer import ConfiguredResponseSerializer

class LineItemSerializer(ConfiguredResponseSerializer):
    item_number: str = Field(..., alias="itemNumber")
    status: Literal["pending", "partial", "complete", "cancelled"]
    priority: Literal["low", "medium", "high", "urgent"]
    category: Literal["standard", "express", "bulk"]

    @classmethod
    def from_domain(cls, line_item: dict) -> "LineItemSerializer":
        return cls(
            item_number=line_item["item_number"],
            status=line_item["status"],
            priority=line_item["priority"],
            category=line_item["category"],
        )
```

### Discriminator Field

```python
from typing import Literal

from ...configured_base_serializer import ConfiguredResponseSerializer

class RecognizedTireSerializer(ConfiguredResponseSerializer):
    type: Literal["recognized"] = "recognized"
    tire_id: str

class FailedTireSerializer(ConfiguredResponseSerializer):
    type: Literal["failed"] = "failed"
    tire_id: str
    error_message: str
```

## OpenAPI Schema Generation

Literal types generate accurate OpenAPI enum schemas:

```yaml
# Generated OpenAPI schema
components:
  schemas:
    FailedTireSerializer:
      properties:
        status:
          type: string
          enum:
            - waiting
            - retried
            - deferred
            - confirmed
```

## Comparison with Enum

| Aspect | Literal | Enum |
| --- | --- | --- |
| Definition location | Inline in serializer | Separate domain file |
| OpenAPI generation | Direct enum values | Via `.value` conversion |
| Type checking | Built-in | Requires enum import |
| Extensibility | Edit inline | Edit enum class |
| Domain reuse | No | Yes |
| Default value | Can specify | Requires explicit handling |

### When Enum is Better

```python
# domain/tire_status.py
from enum import Enum

class TireStatus(Enum):
    WAITING = "waiting"
    RETRIED = "retried"
    DEFERRED = "deferred"
    CONFIRMED = "confirmed"

# serializer - using enum
class TireSerializer(ConfiguredResponseSerializer):
    status: str

    @classmethod
    def from_domain(cls, tire: Tire) -> "TireSerializer":
        return cls(status=tire.status.value)
```

Use Enum when status is used in domain logic, not just serialization.

## Type Aliases for Reuse

Create type aliases for repeated Literal types:

```python
from typing import Literal, TypeAlias

TireStatusLiteral: TypeAlias = Literal["waiting", "retried", "deferred", "confirmed"]
PriorityLiteral: TypeAlias = Literal["low", "medium", "high", "urgent"]

class TireSerializer(ConfiguredResponseSerializer):
    status: TireStatusLiteral
    priority: PriorityLiteral
```

## Validation Behavior

Pydantic validates Literal values at runtime:

```python
# This will raise ValidationError
serializer = FailedTireSerializer(
    tire_id="123",
    error_message="Error",
    status="invalid_status"  # ValidationError: status must be one of: waiting, retried, deferred, confirmed
)
```

## Testing Guidance

- Test serialization with each allowed Literal value.
- Verify ValidationError for invalid values.
- Check OpenAPI schema includes all enum values.
- Test default values for discriminator fields.

### Test Example

```python
import pytest
from pydantic import ValidationError

def test_valid_status_values():
    for status in ["waiting", "retried", "deferred", "confirmed"]:
        serializer = FailedTireSerializer(
            tire_id="123",
            error_message="Error",
            status=status,
        )
        assert serializer.status == status

def test_invalid_status_raises_error():
    with pytest.raises(ValidationError) as exc_info:
        FailedTireSerializer(
            tire_id="123",
            error_message="Error",
            status="invalid",
        )
    assert "status" in str(exc_info.value)
```

---

## Template

```python
from typing import Literal

from pydantic import Field

from {{ base_serializer_module }} import ConfiguredResponseSerializer

__all__ = ["{{ serializer_name }}"]

{% if type_aliases %}
{% for alias in type_aliases %}
{{ alias.name }}: TypeAlias = Literal[{{ alias.values | map('tojson') | join(', ') }}]
{% endfor %}
{% endif %}

class {{ serializer_name }}(ConfiguredResponseSerializer):
{% for field in fields %}
{% if field.literal_values %}
    {{ field.name }}: Literal[{{ field.literal_values | map('tojson') | join(', ') }}]{% if field.default %} = {{ field.default | tojson }}{% endif %}

{% else %}
    {{ field.name }}: {{ field.type }}{% if field.alias %} = Field(..., alias="{{ field.alias }}"){% endif %}

{% endif %}
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
| `{{ serializer_name }}` | Name of the serializer class | `FailedTireSerializer` |
| `{{ base_serializer_module }}` | Import path for base serializer | `...configured_base_serializer` |
| `{{ fields }}` | List of field definitions | See below |
| `{{ type_aliases }}` | Optional type aliases for reuse | `[{"name": "StatusLiteral", "values": ["a", "b"]}]` |
| `{{ domain_param }}` | Parameter name in from_domain | `data` |
| `{{ domain_type }}` | Type of domain parameter | `dict` |
| `{{ field_mappings }}` | Field to domain mappings | `[{"field": "status", "value": "data['status']"}]` |

### Field Definition with Literal

```python
{
    "name": "status",
    "literal_values": ["waiting", "retried", "deferred", "confirmed"],
    "default": None  # Optional default value
}
```
