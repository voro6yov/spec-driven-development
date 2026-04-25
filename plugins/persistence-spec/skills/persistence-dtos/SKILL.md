---
name: persistence-dtos
description: DTOs pattern for persistence. Use when defining TypedDict query result classes and paginated read models separate from domain aggregates.
user-invocable: false
disable-model-invocation: false
---

# DTOs

Purpose: Provide TypedDict classes for query results and data transfer, separating read models from domain aggregates

## Purpose

- Provide TypedDict classes for query results and data transfer.
- Separate read models from domain aggregates.
- Include metadata for paginated results.

## Structure

- Use `TypedDict` from `typing` module.
- Define brief info TypedDicts for list items.
- Define metadata TypedDicts that extend domain pagination metadata.
- Define main info TypedDicts that combine brief info lists with metadata.
- Export all DTOs in `__all__`.

## Behavior checklist

- Use descriptive names ending with `Info` (e.g., `LoadsDetailsInfo`, `BriefLoadDetailsInfo`).
- Include only necessary fields for the use case.
- Use domain value objects or primitives as field types.
- Extend domain pagination metadata types when applicable.

## Testing guidance

- Write unit tests that verify DTO structure matches expected shape.
- Test DTO creation from domain objects or query results.
- Verify pagination metadata is correctly included.

---

## Template

```python
from typing import TypedDict

{% if pagination_metadata_module %}
from {{ pagination_metadata_module }} import PaginatedResultMetadataInfo
{% else %}
class PaginatedResultMetadataInfo(TypedDict):
    page: int
    per_page: int
    total: int
    total_pages: int
{% endif %}

__all__ = ["{{ info_class_name }}", "{{ brief_info_class_name }}", "{{ metadata_class_name }}"]

class {{ brief_info_class_name }}(TypedDict):
{% for field in brief_fields %}
    {{ field.name }}: {{ field.type }}
{% endfor %}

class {{ metadata_class_name }}(PaginatedResultMetadataInfo):
    pass

class {{ info_class_name }}(TypedDict):
    {{ aggregate_plural }}: list[{{ brief_info_class_name }}]
    metadata: {{ metadata_class_name }}
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ info_class_name }}` | Main info TypedDict name | `LoadsDetailsInfo`, `ProfilesDetailsInfo` |
| `{{ brief_info_class_name }}` | Brief info TypedDict name | `BriefLoadDetailsInfo`, `BriefProfileDetailsInfo` |
| `{{ metadata_class_name }}` | Metadata TypedDict name | `LoadsDetailsMetadataInfo`, `ProfilesDetailsMetadataInfo` |
| `{{ aggregate_plural }}` | Plural form for list field | `loads`, `profiles` |
| `{{ brief_fields }}` | List of field objects with `name` and `type` | `[{"name": "id", "type": "str"}, {"name": "status", "type": "str"}]` |
| `{{ pagination_metadata_module }}` | Optional module path for pagination metadata | `tss_load_processing.domain` |

If `pagination_metadata_module` is not provided, a basic `PaginatedResultMetadataInfo` TypedDict will be included in the template.
