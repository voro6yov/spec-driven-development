---
name: sorting
description: Sorting pattern for application services. Use when defining type-safe sorting options for query operations using Enum classes.
user-invocable: false
disable-model-invocation: false
---

# Sorting

Purpose: Provide type-safe sorting options for query operations using Enum classes

## Purpose

- Provide type-safe sorting options for query operations.
- Use Enum classes to represent sortable fields and sort orders.
- Enable compile-time checking of sort parameters.

## Structure

- Define `SortOrder` enum with `ASC` and `DESC` values.
- Define domain-specific sorting enum (e.g., `LoadSorting`) with field names as values.
- Use string values that match API or database column names.
- Export both enums in `__all__`.

## Behavior checklist

- Use descriptive enum member names in UPPER_CASE.
- Use string values that match external system expectations (API, database).
- Keep enum values consistent with domain terminology.

## Testing guidance

- Write unit tests that verify enum values.
- Test sorting logic uses enum values correctly.
- Verify enum values match expected external system format.

---

## Template

```python
from enum import Enum

__all__ = ["{{ sorting_class_name }}", "SortOrder"]

class SortOrder(Enum):
    ASC = "asc"
    DESC = "desc"

class {{ sorting_class_name }}(Enum):
{% for field in sort_fields %}
    {{ field.enum_name }} = "{{ field.value }}"
{% endfor %}
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ sorting_class_name }}` | Name of the domain-specific sorting enum | `LoadSorting`, `ProfileSorting` |
| `{{ sort_fields }}` | List of field objects with `enum_name` and `value` | `[{"enum_name": "ESTIMATED_TIME_OF_ARRIVAL", "value": "eta"}, {"enum_name": "STATUS", "value": "status"}]` |
