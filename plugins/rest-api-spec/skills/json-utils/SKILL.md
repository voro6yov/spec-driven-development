---
name: json-utils
description: JSON Utils pattern for REST API field name transformation. Use when converting snake_case Python field names to camelCase JSON keys for API responses, either via Pydantic alias_generator or direct dictionary transformation.
user-invocable: false
disable-model-invocation: false
---

# JSON Utils

## Purpose

- Provide utility functions for JSON field name transformation.
- Convert snake_case to camelCase for API responses.
- Support recursive object transformation.

## Structure

- `to_camel` - Convert single string from snake_case to camelCase.
- `camelize` - Recursively convert dictionary keys to camelCase.

## Example

```python
__all__ = ["camelize", "to_camel"]

def to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])

def camelize(obj):
    if isinstance(obj, list):
        return [camelize(item) for item in obj]
    elif isinstance(obj, dict):
        return {to_camel(k): camelize(v) for k, v in obj.items()}
    else:
        return obj
```

## Function Details

### to_camel

Converts a single snake_case string to camelCase:

```python
to_camel("resource_id")      # "resourceId"
to_camel("created_at")       # "createdAt"
to_camel("warehouse_id")     # "warehouseId"
to_camel("is_active")        # "isActive"
to_camel("id")               # "id" (no change)
```

### camelize

Recursively transforms dictionary keys and list items:

```python
data = {
    "resource_id": "123",
    "created_at": "2024-01-01",
    "nested_object": {
        "inner_field": "value"
    },
    "list_items": [
        {"item_name": "first"},
        {"item_name": "second"}
    ]
}

camelize(data)
# {
#     "resourceId": "123",
#     "createdAt": "2024-01-01",
#     "nestedObject": {
#         "innerField": "value"
#     },
#     "listItems": [
#         {"itemName": "first"},
#         {"itemName": "second"}
#     ]
# }
```

## Usage

### With Pydantic Base Class

The `to_camel` function is used as the `alias_generator` in base serializer configuration:

```python
from pydantic import BaseModel, ConfigDict
from .json_utils import to_camel

class ConfiguredResponseSerializer(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        serialize_by_alias=True,
    )
```

### Direct Dictionary Transformation

For cases where Pydantic serialization isn't used:

```python
from .json_utils import camelize

result = some_query_function()
response_data = camelize(result)
```

## Testing Guidance

- Test `to_camel` with various snake_case inputs.
- Test single-word strings remain unchanged.
- Test `camelize` with nested dictionaries.
- Test `camelize` with lists of dictionaries.
- Test `camelize` with primitive values (should pass through).

---

## Template

```python
__all__ = ["camelize", "to_camel"]

def to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])

def camelize(obj):
    if isinstance(obj, list):
        return [camelize(item) for item in obj]
    elif isinstance(obj, dict):
        return {to_camel(k): camelize(v) for k, v in obj.items()}
    else:
        return obj
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| (None) | This template has no required placeholders | - |

Note: This pattern is typically used as-is without modification.
