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

**Single-value coercion (query-param models only).** When a `list[...]` field is bound from the **query string** (a query-params model, per § Query Parameters), a single occurrence (`?ids=A`) arrives as a scalar and Pydantic v2 rejects it with `list_type` (two or more values bind fine). Add a `mode="before"` validator that wraps a lone scalar into a one-element list:

```python
from pydantic import Field, field_validator


class GetThingsRequest(ConfiguredRequestSerializer):
    ids: list[str] | None = Field(default=None)
    tags: list[str] | None = Field(default=None)

    @field_validator("ids", "tags", mode="before")
    @classmethod
    def _wrap_scalar_in_list(cls, value):
        if value is None or isinstance(value, list):
            return value
        return [value]
```

List **body** fields (a JSON array in a request body) do not need this — the JSON parser already delivers a list. Emit the validator only for query-param models.

## `to_domain()` method for nested TypedDict targets

When a nested request sub-serializer mirrors the shape of a domain `<<Domain TypedDict>>` / `<<Query DTO>>` that the application service consumes, the sub-serializer exposes a `to_domain(self) -> <TypedDictName>` method. This is the canonical request→domain conversion site; the endpoint layer calls it (or list-comprehends over it for `list[T]` parameters) instead of using Pydantic's generic `model_dump()` — `to_domain()` is typed, robust to Pydantic config changes (e.g. `by_alias=True` flipping global key casing), and a single colocated place to evolve the conversion if the TypedDict diverges from the serializer's shape.

The pattern is symmetric with the response-side `from_domain` classmethod: `from_domain(cls, dto)` constructs the serializer from a domain object; `to_domain(self)` constructs the domain object (TypedDict) from the serializer.

### Scope

- Emit `to_domain()` **only** on nested sub-serializers whose target application-service parameter type is `<<Domain TypedDict>>` / `<<Query DTO>>` (directly, as `list[T]`, or as `T | None` / `list[T] | None`).
- **Do not** emit `to_domain()` on the top-level `<Operation>Request` — the endpoint accesses primitive fields directly via `request.<field>` and only invokes `to_domain()` on the nested sub-serializer instances passed for TypedDict-shaped fields.
- **Do not** emit `to_domain()` on sub-serializers whose target type is a `<<Value Object>>` or `<<Aggregate Root>>` — those have their own construction patterns at the application or domain layer.

### Body shape

```python
class LookupArgumentDataSerializer(ConfiguredRequestSerializer):
    code: str
    name: str
    arguments: list[ArgumentDataSerializer]
    response: list[ResponseDataSerializer]
    note: str | None = None

    def to_domain(self) -> LookupArgumentData:
        return {
            "code": self.code,
            "name": self.name,
            "arguments": [item.to_domain() for item in self.arguments],
            "response": [item.to_domain() for item in self.response],
            "note": self.note,
        }
```

Per-field rendering rules:

| Field type | Body expression |
| --- | --- |
| Primitive (`str`, `int`, `bool`, …) | `self.<field>` |
| `<SubSerializer>` (scalar nested TypedDict) | `self.<field>.to_domain()` |
| `list[<SubSerializer>]` | `[item.to_domain() for item in self.<field>]` |
| `<SubSerializer> \| None` | `self.<field>.to_domain() if self.<field> else None` |
| `list[<SubSerializer>] \| None` | `[i.to_domain() for i in self.<field>] if self.<field> else None` |
| Anything else | `self.<field>` (and emit `# TODO: verify conversion for <field>`) |

The return annotation names the target TypedDict — imported from `<pkg>.domain.<aggregate>` (or `<pkg>.domain.shared` when shared).

### Worked example

```python
from my_service.domain.cache_type import ArgumentData, LookupArgumentData, ResponseData

from ...configured_base_serializer import ConfiguredRequestSerializer, ConfiguredResponseSerializer

__all__ = [
    "ArgumentDataSerializer",
    "ResponseDataSerializer",
    "LookupArgumentDataSerializer",
    "CreateRequest",
    "CreateResponse",
]


class ArgumentDataSerializer(ConfiguredRequestSerializer):
    name: str
    type: str

    def to_domain(self) -> ArgumentData:
        return {
            "name": self.name,
            "type": self.type,
        }


class ResponseDataSerializer(ConfiguredRequestSerializer):
    name: str
    type: str

    def to_domain(self) -> ResponseData:
        return {
            "name": self.name,
            "type": self.type,
        }


class LookupArgumentDataSerializer(ConfiguredRequestSerializer):
    code: str
    name: str
    arguments: list[ArgumentDataSerializer]
    response: list[ResponseDataSerializer]

    def to_domain(self) -> LookupArgumentData:
        return {
            "code": self.code,
            "name": self.name,
            "arguments": [item.to_domain() for item in self.arguments],
            "response": [item.to_domain() for item in self.response],
        }


class CreateRequest(ConfiguredRequestSerializer):
    code: str
    name: str
    lookups: list[LookupArgumentDataSerializer]
```

The endpoint then delegates:

```python
def create(request: CreateRequest, ...):
    cache_type_commands.create(
        code=request.code,
        name=request.name,
        lookups=[item.to_domain() for item in request.lookups],
        tenant_id=tenant_id,
    )
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

### Query Parameters via `Annotated[..., Query()]`

A `ConfiguredRequestSerializer` (a `BaseModel`) used for query parameters is bound with `Annotated[<Model>, Query()]` — **not** `Depends()`. In this FastAPI / Pydantic-v2 stack a `BaseModel` consumed via `Depends()` is parsed as a request **body** (`422 {loc: ["body"]}` on every call); `Annotated[<Model>, Query()]` is FastAPI's supported "Pydantic model as query parameters" binding (FastAPI ≥ 0.115). The model's camelCase aliases (`alias_generator=to_camel`) are honored as the query-param names.

```python
from typing import Annotated

from fastapi import Query


@router.get("")
def get_resources(request: Annotated[GetResourcesRequest, Query()]):
    # request.page, request.per_page
```

When a query-params model has any `list[...]` field, it must also coerce a single occurrence into a one-element list — see [§ List Fields](#list-fields).

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
