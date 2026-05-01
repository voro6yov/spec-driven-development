---
name: request-serializers
description: Request Serializers pattern for REST API request validation. Use when defining Pydantic-based request bodies or query parameter models with camelCase aliases and validation constraints.
user-invocable: false
disable-model-invocation: false
---

# Request Serializers

## Purpose

- Validate incoming request bodies with Pydantic.
- Provide type-safe access to request data.
- Support camelCase input from API consumers.

## Structure

- Extend `ConfiguredRequestSerializer` base class.
- Define fields matching the expected request format.
- Use `Field()` for validation constraints and aliases.
- Export via `__all__`.

## Template Parameters

- `{{ serializer_name }}` - Name of the serializer class
- `{{ fields }}` - List of field definitions with name, type, default, and validation

## Request Types

### Create Request

```python
from my_service.api.serializers.configured_base_serializer import ConfiguredRequestSerializer

__all__ = ["CreateConveyorRequest"]

class CreateConveyorRequest(ConfiguredRequestSerializer):
    id: str
    name: str
    warehouse_id: str | None = None
```

### Request with Validation

```python
from pydantic import Field

from my_service.api.serializers.configured_base_serializer import ConfiguredRequestSerializer

__all__ = ["GetConveyorsRequest"]

class GetConveyorsRequest(ConfiguredRequestSerializer):
    page: int = Field(default=0, ge=0)
    per_page: int = Field(default=10, ge=1, le=100)
```

### Request with Custom Alias

```python
from pydantic import Field

from my_service.api.serializers.configured_base_serializer import ConfiguredRequestSerializer

__all__ = ["QueryLoadsRequest"]

class QueryLoadsRequest(ConfiguredRequestSerializer):
    search: str | None = Field(default=None)
    load_ids: list[str] | None = Field(default=None, alias="loadIds")
    eta_from: str | None = Field(default=None, alias="etaFrom")
    eta_to: str | None = Field(default=None, alias="etaTo")
    statuses: list[str] | None = Field(default=None)
    warehouse_ids: list[str] | None = Field(default=None, alias="warehouseIds")
    page: int | None = Field(default=None, ge=1)
    per_page: int | None = Field(default=None, ge=1, alias="perPage")
```

## Validation Patterns

### Range Constraints

```python
page: int = Field(default=0, ge=0)          # >= 0
per_page: int = Field(default=10, ge=1, le=100)  # 1 <= x <= 100
```

### String Constraints

```python
name: str = Field(..., min_length=1, max_length=255)
email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
```

### Optional Fields

```python
description: str | None = None
warehouse_id: str | None = Field(default=None, alias="warehouseId")
```

### List Fields

```python
tags: list[str] = Field(default_factory=list)
ids: list[str] | None = Field(default=None)
```

## Base Class Configuration

The `ConfiguredRequestSerializer` includes:

```python
class ConfiguredRequestSerializer(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        serialize_by_alias=True,
        validate_by_name=True,
        validate_by_alias=True,
        use_enum_values=True,
        str_strip_whitespace=True,
    )
```

This enables:

- Automatic camelCase alias generation
- Validation by both field name and alias
- Enum values converted to their underlying type
- Automatic whitespace stripping on strings

## Usage in Endpoints

### Body Request

```python
@router.post("")
def create_resource(request: CreateResourceRequest):
    # request.id, request.name, etc.
```

### Query Parameters via Depends

```python
@router.get("")
def get_resources(request: GetResourcesRequest = Depends()):
    # request.page, request.per_page
```

## Testing Guidance

- Test validation with valid input data.
- Test validation errors with invalid data (missing required, out of range).
- Verify camelCase aliases work correctly.
- Test default values are applied.

---

## Template

```python
from pydantic import Field

from {{ base_serializer_module }} import ConfiguredRequestSerializer

__all__ = ["{{ serializer_name }}"]

class {{ serializer_name }}(ConfiguredRequestSerializer):
{% for field in fields %}
{% if field.validation %}
    {{ field.name }}: {{ field.type }} = Field({{ field.validation }})
{% else %}
    {{ field.name }}: {{ field.type }}{% if field.default is defined %} = {{ field.default }}{% endif %}

{% endif %}
{% endfor %}
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ serializer_name }}` | Name of the serializer class | `CreateConveyorRequest` |
| `{{ base_serializer_module }}` | Import path for base serializer | `...configured_base_serializer` |
| `{{ fields }}` | List of field definitions | See below |

### Field Definition Structure

```python
{
    "name": "page",
    "type": "int",
    "default": "0",
    "validation": "default=0, ge=0"
}
```
