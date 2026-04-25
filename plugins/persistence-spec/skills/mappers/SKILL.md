---
name: mappers
description: Mappers pattern for persistence. Use when converting between domain aggregates and database rows, handling nested value objects, child entities, and polymorphic types.
user-invocable: false
disable-model-invocation: false
---

# Mappers

**Type:** Primary

## Purpose

- Convert between domain aggregates/value objects and database representations.
- Handle nested value objects and entities through nested mapper delegation.
- Normalize data during conversion when needed (e.g., datetime serialization).

## Aggregate Mappers

### Full Aggregate Mapper (`mapper.py.j2`)

Converts root aggregates with status, timestamps, and optional nested polymorphic data.

- `to_dict(aggregate)` converts domain aggregate to dictionary for database insertion.
- `from_row(row)` converts single database row to domain aggregate.
- Handles optional nested polymorphic fields (kind + entity pattern).

### Minimal Aggregate Mapper (`mapper_minimal.py.j2`)

For simple aggregates without status or timestamps.

- `to_dict(aggregate)` converts only id, tenant_id, and additional fields.
- `from_row(row)` reconstructs aggregate with default value handling.
- Use when aggregate has no status tracking or audit timestamps.

### Aggregate Mapper with Children (`mapper_with_children.py.j2`)

For aggregates that own child entities stored in separate tables.

- `to_dict(aggregate)` converts only the aggregate's own fields (not children).
- `from_row(row)` reconstructs aggregate without children (for simple lookups).
- `from_rows(aggregate_row, child_rows)` reconstructs full aggregate with children.

## Value Object Mappers

### Simple Value Object Mapper (`value_object_mapper.py.j2`)

For value objects stored in JSONB columns with datetime handling.

- `to_json(value_object)` converts to JSON-compatible dict, handles datetime serialization.
- `from_json(data)` reconstructs value object, handles datetime parsing with `contextlib.suppress`.
- Returns `None` for `None` inputs.

### Complex Value Object Mapper (`complex_value_object_mapper.py.j2`)

For value objects containing multiple optional nested value objects.

- Uses `getattr(obj, "attr", None)` pattern for optional fields.
- Delegates to nested field mapper for each optional field.
- Handles `None` checks on deserialization with `data.get("field")`.

### Value Object with Collection Mapper (`value_object_with_collection_mapper.py.j2`)

For value objects containing a collection of nested value objects.

- Handles both scalar fields and collection fields.
- Iterates over collection for serialization/deserialization.
- Uses `hasattr()` check for optional collections.

## Entity Mappers

### Child Entity Mapper (`child_entity_mapper.py.j2`)

For entities owned by an aggregate, stored in child tables.

- `to_dict(entity, parent_id, tenant_id)` includes parent context in output.
- `from_row(row)` reconstructs entity without parent reference.

### Polymorphic Mapper (`polymorphic_mapper.py.j2`)

For type hierarchies stored in JSONB with a discriminator field.

- `to_json(kind, entity)` dispatches to type-specific mapper based on discriminator.
- `from_json(kind, data)` reconstructs correct type based on discriminator.
- Returns `None` when kind or data is missing.

## Datetime Handling

JSONB columns require explicit datetime serialization:

```python
import contextlib
from datetime import datetime

# Serialization
if isinstance(value, datetime):
    value = value.isoformat()

# Deserialization (preferred pattern)
if isinstance(value, str) and "T" in value:
    with contextlib.suppress(ValueError, TypeError):
        value = datetime.fromisoformat(value)
```

## Testing guidance

- Write unit tests that verify round-trip conversion: aggregate → dict → aggregate.
- Test optional attribute handling (None values, missing attributes).
- Test nested mapper delegation for child entities and value objects.
- Verify datetime serialization produces ISO format strings.
- Test collection mappers with empty, single, and multiple items.

---

## Template

### Full Aggregate Mapper

```python
from collections.abc import Mapping
from typing import Any

from {{ domain_module }} import {{ aggregate_name }}

from .{{ nested_mapper }} import {{ nested_mapper_class }}

__all__ = ["{{ mapper_class }}"]

class {{ mapper_class }}:
    @staticmethod
    def to_dict({{ aggregate_name_lower }}: {{ aggregate_name }}) -> dict[str, Any]:
        result = {
            "{{ id_column }}": {{ aggregate_name_lower }}.id,
            "{{ tenant_id_column }}": {{ aggregate_name_lower }}.tenant_id,
            "{{ status_column }}": {{ aggregate_name_lower }}.status.status,
            "{{ status_error_column }}": {{ aggregate_name_lower }}.status.error if {{ aggregate_name_lower }}.status.error else None,
            "created_at": {{ aggregate_name_lower }}.created_at,
            "updated_at": {{ aggregate_name_lower }}.updated_at,
        }

        if {{ aggregate_name_lower }}.{{ nested_field }}:
            result["{{ nested_kind_column }}"] = {{ aggregate_name_lower }}.{{ nested_field }}.kind
            result["{{ nested_data_column }}"] = {{ nested_mapper_class }}.to_json(
                {{ aggregate_name_lower }}.{{ nested_field }}.kind,
                {{ aggregate_name_lower }}.{{ nested_field }}.entity,
            )
        else:
            result["{{ nested_kind_column }}"] = None
            result["{{ nested_data_column }}"] = None

        return result

    @staticmethod
    def from_row(row: Mapping[str, Any]) -> {{ aggregate_name }}:
        {{ nested_field }}_entity = {{ nested_mapper_class }}.from_json(
            row.get("{{ nested_kind_column }}"),
            row.get("{{ nested_data_column }}"),
        )
        {{ nested_field }}_kind = row.get("{{ nested_kind_column }}")

        status_error = row.get("{{ status_error_column }}")

        return {{ aggregate_name }}(
            id_=row["{{ id_column }}"],
            tenant_id=row["{{ tenant_id_column }}"],
            {{ nested_kind_param }}={{ nested_field }}_kind,
            {{ nested_entity_param }}={{ nested_field }}_entity,
            status_value=row["{{ status_column }}"],
            status_error=status_error,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
```

### Minimal Aggregate Mapper

```python
from collections.abc import Mapping
from typing import Any

from {{ domain_module }} import {{ aggregate_name }}

__all__ = ["{{ mapper_class }}"]

class {{ mapper_class }}:
    @staticmethod
    def to_dict({{ aggregate_name_lower }}: {{ aggregate_name }}) -> dict[str, Any]:
        return {
            "{{ id_column }}": {{ aggregate_name_lower }}.id,
            "{{ tenant_id_column }}": {{ aggregate_name_lower }}.tenant_id,
            "{{ additional_column }}": {{ aggregate_name_lower }}.{{ additional_attribute }},
        }

    @staticmethod
    def from_row(row: Mapping[str, Any]) -> {{ aggregate_name }}:
        {{ additional_attribute }} = row.get("{{ additional_column }}")
        if {{ additional_attribute }} is None:
            {{ additional_attribute }} = {{ additional_default }}

        return {{ aggregate_name }}(
            id_=row["{{ id_column }}"],
            tenant_id=row["{{ tenant_id_column }}"],
            {{ additional_attribute }}={{ additional_attribute }},
        )
```

### Aggregate Mapper with Children

```python
from collections.abc import Mapping
from typing import Any

from {{ domain_module }} import {{ aggregate_name }}

from .{{ child_mapper_module }} import {{ child_mapper_class }}

__all__ = ["{{ mapper_class }}"]

class {{ mapper_class }}:
    @staticmethod
    def to_dict({{ aggregate_name_lower }}: {{ aggregate_name }}) -> dict[str, Any]:
        return {
            "{{ id_column }}": {{ aggregate_name_lower }}.id,
            "{{ tenant_id_column }}": {{ aggregate_name_lower }}.tenant_id,
            "{{ additional_column }}": {{ aggregate_name_lower }}.{{ additional_attribute }},
        }

    @staticmethod
    def from_row(row: Mapping[str, Any]) -> {{ aggregate_name }}:
        {{ additional_attribute }} = row.get("{{ additional_column }}")
        if {{ additional_attribute }} is None:
            {{ additional_attribute }} = {{ additional_default }}

        return {{ aggregate_name }}(
            id_=row["{{ id_column }}"],
            tenant_id=row["{{ tenant_id_column }}"],
            {{ additional_attribute }}={{ additional_attribute }},
            {{ children_attribute }}=None,
        )

    @staticmethod
    def from_rows(aggregate_row: Mapping[str, Any], child_rows: list[Mapping[str, Any]]) -> {{ aggregate_name }}:
        children = [{{ child_mapper_class }}.from_row(row) for row in child_rows]

        {{ additional_attribute }} = aggregate_row.get("{{ additional_column }}")
        if {{ additional_attribute }} is None:
            {{ additional_attribute }} = {{ additional_default }}

        return {{ aggregate_name }}(
            id_=aggregate_row["{{ id_column }}"],
            tenant_id=aggregate_row["{{ tenant_id_column }}"],
            {{ additional_attribute }}={{ additional_attribute }},
            {{ children_attribute }}=children,
        )
```

### Simple Value Object Mapper

```python
import contextlib
from datetime import datetime
from typing import Any

from {{ domain_module }} import {{ value_object_name }}

__all__ = ["{{ mapper_class }}"]

class {{ mapper_class }}:
    @staticmethod
    def to_json({{ value_object_name_lower }}: {{ value_object_name }} | None) -> dict[str, Any] | None:
        if {{ value_object_name_lower }} is None:
            return None

        value = {{ value_object_name_lower }}.{{ value_attribute }}
        if isinstance(value, datetime):
            value = value.isoformat()

        return {
            "{{ value_attribute }}": value,
            "{{ source_attribute }}": {{ value_object_name_lower }}.{{ source_attribute }},
            "{{ confidence_attribute }}": {{ value_object_name_lower }}.{{ confidence_attribute }},
        }

    @staticmethod
    def from_json(data: dict[str, Any]) -> {{ value_object_name }}:
        value = data["{{ value_attribute }}"]
        if isinstance(value, str) and "T" in value:
            with contextlib.suppress(ValueError, TypeError):
                value = datetime.fromisoformat(value)

        return {{ value_object_name }}(
            {{ value_attribute }}=value,
            {{ source_attribute }}=data["{{ source_attribute }}"],
            {{ confidence_attribute }}=data["{{ confidence_attribute }}"],
        )
```

### Complex Value Object Mapper

```python
from typing import Any

from {{ domain_module }} import {{ value_object_name }}

from .{{ field_mapper_module }} import {{ field_mapper_class }}

__all__ = ["{{ mapper_class }}"]

class {{ mapper_class }}:
    @staticmethod
    def to_json({{ value_object_name_lower }}: {{ value_object_name }}) -> dict[str, Any]:
        return {
            "{{ type_field }}": {{ value_object_name_lower }}.{{ type_field }},
            "{{ field_1 }}": {{ field_mapper_class }}.to_json(getattr({{ value_object_name_lower }}, "{{ field_1 }}", None)),
            "{{ field_2 }}": {{ field_mapper_class }}.to_json(getattr({{ value_object_name_lower }}, "{{ field_2 }}", None)),
            "{{ field_3 }}": {{ field_mapper_class }}.to_json(getattr({{ value_object_name_lower }}, "{{ field_3 }}", None)),
            "{{ field_4 }}": {{ field_mapper_class }}.to_json(getattr({{ value_object_name_lower }}, "{{ field_4 }}", None)),
            "{{ field_5 }}": {{ field_mapper_class }}.to_json(getattr({{ value_object_name_lower }}, "{{ field_5 }}", None)),
        }

    @staticmethod
    def from_json(data: dict[str, Any]) -> {{ value_object_name }}:
        return {{ value_object_name }}(
            {{ type_field }}=data["{{ type_field }}"],
            {{ field_1 }}={{ field_mapper_class }}.from_json(data["{{ field_1 }}"]) if data.get("{{ field_1 }}") else None,
            {{ field_2 }}={{ field_mapper_class }}.from_json(data["{{ field_2 }}"]) if data.get("{{ field_2 }}") else None,
            {{ field_3 }}={{ field_mapper_class }}.from_json(data["{{ field_3 }}"]) if data.get("{{ field_3 }}") else None,
            {{ field_4 }}={{ field_mapper_class }}.from_json(data["{{ field_4 }}"]) if data.get("{{ field_4 }}") else None,
            {{ field_5 }}={{ field_mapper_class }}.from_json(data["{{ field_5 }}"]) if data.get("{{ field_5 }}") else None,
        )
```

### Value Object with Collection Mapper

```python
from typing import Any

from {{ domain_module }} import {{ value_object_name }}, {{ nested_item_name }}

from .{{ field_mapper_module }} import {{ field_mapper_class }}

__all__ = ["{{ mapper_class }}"]

class {{ mapper_class }}:
    @staticmethod
    def to_json({{ value_object_name_lower }}: {{ value_object_name }}) -> dict[str, Any]:
        {{ collection_field }}_data = []
        if hasattr({{ value_object_name_lower }}, "{{ collection_field }}") and {{ value_object_name_lower }}.{{ collection_field }}:
            for item in {{ value_object_name_lower }}.{{ collection_field }}:
                {{ collection_field }}_data.append({
                    "{{ item_field_1 }}": {{ field_mapper_class }}.to_json(getattr(item, "{{ item_field_1 }}", None)),
                    "{{ item_field_2 }}": {{ field_mapper_class }}.to_json(getattr(item, "{{ item_field_2 }}", None)),
                    "{{ item_field_3 }}": {{ field_mapper_class }}.to_json(getattr(item, "{{ item_field_3 }}", None)),
                })

        return {
            "{{ type_field }}": {{ value_object_name_lower }}.{{ type_field }},
            "{{ scalar_field_1 }}": {{ field_mapper_class }}.to_json(getattr({{ value_object_name_lower }}, "{{ scalar_field_1 }}", None)),
            "{{ scalar_field_2 }}": {{ field_mapper_class }}.to_json(getattr({{ value_object_name_lower }}, "{{ scalar_field_2 }}", None)),
            "{{ collection_field }}": {{ collection_field }}_data,
        }

    @staticmethod
    def from_json(data: dict[str, Any]) -> {{ value_object_name }}:
        {{ collection_field }}_list = []
        if data.get("{{ collection_field }}"):
            for item_data in data["{{ collection_field }}"]:
                {{ collection_field }}_list.append(
                    {{ nested_item_name }}(
                        {{ item_field_1 }}={{ field_mapper_class }}.from_json(item_data["{{ item_field_1 }}"]) if item_data.get("{{ item_field_1 }}") else None,
                        {{ item_field_2 }}={{ field_mapper_class }}.from_json(item_data["{{ item_field_2 }}"]) if item_data.get("{{ item_field_2 }}") else None,
                        {{ item_field_3 }}={{ field_mapper_class }}.from_json(item_data["{{ item_field_3 }}"]) if item_data.get("{{ item_field_3 }}") else None,
                    )
                )

        return {{ value_object_name }}(
            {{ type_field }}=data["{{ type_field }}"],
            {{ scalar_field_1 }}={{ field_mapper_class }}.from_json(data["{{ scalar_field_1 }}"]) if data.get("{{ scalar_field_1 }}") else None,
            {{ scalar_field_2 }}={{ field_mapper_class }}.from_json(data["{{ scalar_field_2 }}"]) if data.get("{{ scalar_field_2 }}") else None,
            {{ collection_field }}={{ collection_field }}_list,
        )
```

### Child Entity Mapper

```python
from collections.abc import Mapping
from typing import Any

from {{ domain_module }} import {{ entity_name }}

__all__ = ["{{ mapper_class }}"]

class {{ mapper_class }}:
    @staticmethod
    def to_dict({{ entity_name_lower }}: {{ entity_name }}, {{ parent_id_param }}: str, tenant_id: str) -> dict[str, Any]:
        return {
            "{{ id_column }}": {{ entity_name_lower }}.id,
            "{{ parent_id_column }}": {{ parent_id_param }},
            "{{ tenant_id_column }}": tenant_id,
            "{{ additional_column }}": {{ entity_name_lower }}.{{ additional_attribute }},
            "{{ status_column }}": {{ entity_name_lower }}.status.status,
            "{{ status_error_column }}": {{ entity_name_lower }}.status.error if {{ entity_name_lower }}.status.error else None,
        }

    @staticmethod
    def from_row(row: Mapping[str, Any]) -> {{ entity_name }}:
        status_error = row.get("{{ status_error_column }}")

        return {{ entity_name }}(
            id_=row["{{ id_column }}"],
            {{ additional_attribute }}=row["{{ additional_column }}"],
            status_value=row["{{ status_column }}"],
            status_error=status_error,
        )
```

### Polymorphic Mapper

```python
from typing import Any

from {{ domain_module }} import {{ type_a_name }}, {{ type_b_name }}

from .{{ type_a_mapper_module }} import {{ type_a_mapper_class }}
from .{{ type_b_mapper_module }} import {{ type_b_mapper_class }}

__all__ = ["{{ mapper_class }}"]

class {{ mapper_class }}:
    @staticmethod
    def to_json(kind: str, entity: {{ type_a_name }} | {{ type_b_name }}) -> dict[str, Any]:
        if kind == "{{ type_a_discriminator }}":
            return {{ type_a_mapper_class }}.to_json(entity)
        else:
            return {{ type_b_mapper_class }}.to_json(entity)

    @staticmethod
    def from_json(kind: str | None, data: dict[str, Any] | None) -> {{ type_a_name }} | {{ type_b_name }} | None:
        if not kind or not data:
            return None

        if kind == "{{ type_a_discriminator }}":
            return {{ type_a_mapper_class }}.from_json(data)
        else:
            return {{ type_b_mapper_class }}.from_json(data)
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ domain_module }}` | Domain module path | `domain.aggregates`, `domain.value_objects` |
| `{{ aggregate_name }}` | Aggregate class name | `Order`, `Profile` |
| `{{ aggregate_name_lower }}` | Aggregate name in snake_case | `order`, `profile` |
| `{{ mapper_class }}` | Mapper class name | `OrderMapper`, `ProfileMapper` |
| `{{ id_column }}` | Primary key column name | `id`, `order_id` |
| `{{ tenant_id_column }}` | Tenant ID column name | `tenant_id` |
| `{{ status_column }}` | Status column name | `status` |
| `{{ status_error_column }}` | Status error column name | `status_error` |
| `{{ nested_field }}` | Nested polymorphic field name | `info`, `metadata` |
| `{{ nested_kind_column }}` | Nested kind column name | `info_kind` |
| `{{ nested_data_column }}` | Nested data column name | `info_data` |
| `{{ nested_mapper_class }}` | Nested mapper class | `InfoMapper` |
| `{{ nested_kind_param }}` | Constructor parameter for kind | `info_kind` |
| `{{ nested_entity_param }}` | Constructor parameter for entity | `info_entity` |
| `{{ additional_column }}` | Additional column name | `name`, `description` |
| `{{ additional_attribute }}` | Additional attribute name | `name`, `description` |
| `{{ additional_default }}` | Default value for optional attribute | `""`, `[]`, `None` |
| `{{ child_mapper_module }}` | Child mapper module path | `mappers.order_item_mapper` |
| `{{ child_mapper_class }}` | Child mapper class | `OrderItemMapper` |
| `{{ children_attribute }}` | Children collection attribute | `items`, `addresses` |
| `{{ value_object_name }}` | Value object class name | `OrderInfo`, `Address` |
| `{{ value_object_name_lower }}` | Value object name in snake_case | `order_info`, `address` |
| `{{ value_attribute }}` | Value attribute name | `value`, `amount` |
| `{{ source_attribute }}` | Source attribute name | `source`, `provider` |
| `{{ confidence_attribute }}` | Confidence attribute name | `confidence`, `score` |
| `{{ field_mapper_module }}` | Field mapper module | `mappers.field_mapper` |
| `{{ field_mapper_class }}` | Field mapper class | `FieldMapper` |
| `{{ type_field }}` | Type discriminator field | `type`, `kind` |
| `{{ field_1 }}` through `{{ field_5 }}` | Optional field names | `field1`, `field2` |
| `{{ collection_field }}` | Collection field name | `items`, `tags` |
| `{{ nested_item_name }}` | Nested item class name | `OrderItem`, `Tag` |
| `{{ item_field_1 }}` through `{{ item_field_3 }}` | Item field names | `name`, `value` |
| `{{ scalar_field_1 }}`, `{{ scalar_field_2 }}` | Scalar field names | `name`, `description` |
| `{{ entity_name }}` | Entity class name | `OrderItem`, `Address` |
| `{{ entity_name_lower }}` | Entity name in snake_case | `order_item`, `address` |
| `{{ parent_id_param }}` | Parent ID parameter name | `order_id`, `parent_id` |
| `{{ parent_id_column }}` | Parent ID column name | `order_id`, `parent_id` |
| `{{ type_a_name }}`, `{{ type_b_name }}` | Polymorphic type names | `TypeA`, `TypeB` |
| `{{ type_a_mapper_module }}` | Type A mapper module | `mappers.type_a_mapper` |
| `{{ type_a_mapper_class }}` | Type A mapper class | `TypeAMapper` |
| `{{ type_b_mapper_module }}` | Type B mapper module | `mappers.type_b_mapper` |
| `{{ type_b_mapper_class }}` | Type B mapper class | `TypeBMapper` |
| `{{ type_a_discriminator }}` | Type A discriminator value | `"type_a"`, `"standard"` |
