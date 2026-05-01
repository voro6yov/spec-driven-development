---
name: base-serializers
description: Base Serializers pattern for REST API request/response models. Use when scaffolding configured Pydantic base classes that enforce camelCase JSON aliasing and shared validation/serialization settings.
user-invocable: false
disable-model-invocation: false
---

# Base Serializers

## Purpose

- Provide configured base classes for request and response serializers.
- Ensure consistent camelCase JSON field naming.
- Share validation and serialization settings across all serializers.

## Structure

- Two base classes: `ConfiguredRequestSerializer` and `ConfiguredResponseSerializer`.
- Pydantic `ConfigDict` for configuration.
- Use `to_camel` function for alias generation.

## Template Parameters

- `{{ json_utils_module }}` - Import path for json_utils module

## Configuration Options

### ConfiguredRequestSerializer

| Setting | Value | Purpose |
| --- | --- | --- |
| `alias_generator` | `to_camel` | Convert field names to camelCase |
| `serialize_by_alias` | `True` | Output uses aliases |
| `validate_by_name` | `True` | Accept original field names |
| `validate_by_alias` | `True` | Accept alias field names |
| `use_enum_values` | `True` | Use enum values instead of enum objects |
| `str_strip_whitespace` | `True` | Strip whitespace from strings |

### ConfiguredResponseSerializer

| Setting | Value | Purpose |
| --- | --- | --- |
| `validate_by_name` | `True` | Accept original field names |
| `alias_generator` | `to_camel` | Convert field names to camelCase |
| `validate_by_alias` | `True` | Accept alias field names |
| `serialize_by_alias` | `True` | Output uses aliases |
| `use_enum_values` | `True` | Use enum values instead of enum objects |

## Example

```python
from pydantic import BaseModel, ConfigDict

from .json_utils import to_camel

__all__ = ["ConfiguredResponseSerializer", "ConfiguredRequestSerializer"]

class ConfiguredRequestSerializer(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        serialize_by_alias=True,
        validate_by_name=True,
        validate_by_alias=True,
        use_enum_values=True,
        str_strip_whitespace=True,
    )

class ConfiguredResponseSerializer(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
        validate_by_alias=True,
        serialize_by_alias=True,
        use_enum_values=True,
    )
```

## Usage

### Request Serializer

```python
from .configured_base_serializer import ConfiguredRequestSerializer

class CreateResourceRequest(ConfiguredRequestSerializer):
    resource_id: str  # Accepts "resourceId" from JSON
    name: str
```

### Response Serializer

```python
from .configured_base_serializer import ConfiguredResponseSerializer

class GetResourceResponse(ConfiguredResponseSerializer):
    resource_id: str  # Serializes as "resourceId" in JSON
    created_at: datetime  # Serializes as "createdAt"
```

## Field Name Transformation

| Python Field | JSON Field |
| --- | --- |
| `resource_id` | `resourceId` |
| `created_at` | `createdAt` |
| `warehouse_id` | `warehouseId` |
| `is_active` | `isActive` |

## Testing Guidance

- Test that snake_case fields serialize to camelCase.
- Test that camelCase input is accepted for request serializers.
- Test enum values are serialized correctly.
- Test whitespace stripping on request serializers.

---

## Template

```python
from pydantic import BaseModel, ConfigDict

from {{ json_utils_module }} import to_camel

__all__ = ["ConfiguredResponseSerializer", "ConfiguredRequestSerializer"]

class ConfiguredRequestSerializer(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        serialize_by_alias=True,
        validate_by_name=True,
        validate_by_alias=True,
        use_enum_values=True,
        str_strip_whitespace=True,
    )

class ConfiguredResponseSerializer(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        alias_generator=to_camel,
        validate_by_alias=True,
        serialize_by_alias=True,
        use_enum_values=True,
    )
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ json_utils_module }}` | Import path for to_camel function | `.json_utils` |
