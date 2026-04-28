---
name: query-repository
description: Query Repository pattern for persistence. Use when implementing read-only SQLAlchemy repositories that return TypedDict DTOs with filtering, sorting, and pagination support.
user-invocable: false
disable-model-invocation: false
---

# Query Repository

**Type:** Supporting

> **Optional Pattern**: This pattern implements the read-side of CQRS (Command Query Responsibility Segregation). Use when you need dedicated query operations separate from command repositories. Skip if your command repositories handle all read needs.

## Purpose

- Implement domain query repository interfaces for read-only aggregate queries.
- Return TypedDict DTOs (constructed inline as `dict` literals) instead of domain aggregates for query operations.
- Handle filtering, sorting, and pagination without transaction overhead and without dedicated DTO mapper classes.

## Structure

- Implements the domain `Query<Aggregate>Repository` ABC.
- Takes SQLAlchemy `Session` in the constructor.
- Constructs result dicts inline (`dict(row)` for single rows, dict literals matching the return TypedDict for paginated results). No `<Aggregate>InfoMapper` is used.
- Exposes a `<aggregate>_columns` property listing the table columns for selection (mirrors the command-side repository).
- Keeps filtering, sorting, and pagination as private helpers (`_apply_filtering`, `_apply_sorting`, `_apply_pagination`).

## Method body templates

Method dispatch is signature-driven from the domain `Query<Aggregate>Repository` ABC. The implementer classifies each `@abstractmethod` into one of the rules below.

### Rule A — Single lookup by id

Return annotation unwraps to `<Aggregate>Info | None` (or `dict[str, Any] | None`); parameter list (after `self`) has exactly one non-`tenant_id` parameter that maps to the aggregate table's PK column via the column-mapping rule.

```python
def find_{{ aggregate_name_lower }}(self, id_: str) -> {{ info_dto }} | None:
    query = select(*self.{{ aggregate_name_lower }}_columns).where(
        {{ table_name }}.c.{{ id_column }} == id_
    )
    row = self._connection.execute(query).mappings().first()
    return dict(row) if row else None
```

### Rule B — Single lookup by alternative field (`find_by_<field>`)

Return annotation unwraps to `<Aggregate>Info | None`; parameter list has at least one non-`tenant_id` parameter, each mapping to a column on the aggregate table; method is **not** the PK lookup. Build the where clause from each parameter using the column-mapping rule.

```python
def find_by_{{ field }}(self, {{ field }}: str) -> {{ info_dto }} | None:
    query = select(*self.{{ aggregate_name_lower }}_columns).where(
        {{ table_name }}.c.{{ field_column }} == {{ field }}
    )
    row = self._connection.execute(query).mappings().first()
    return dict(row) if row else None
```

### Rule C — Paginated list

Return annotation unwraps to `<Aggregate>ListResult` (a TypedDict with one `list[<Brief>]` key plus a `metadata: <Metadata>` key). Parameter list contains some subset of `filtering: <Filtering> | None`, `sorting: <Sorting> | None`, `pagination: Pagination | None`. The dict literal's keys must match the TypedDict definition exactly — typically `<aggregate_plural>` and `metadata` — and the metadata dict must match `PaginatedResultMetadataInfo` (`page`, `per_page`, `total`, `total_pages`).

```python
def find_{{ aggregate_name_lower_plural }}(
    self,
    filtering: {{ filtering_dto }} | None = None,
    sorting: {{ sorting_enum }} | None = None,
    pagination: Pagination | None = None,
) -> {{ info_dto }}:
    query = select(*self.{{ aggregate_name_lower }}_columns)
    total_query = select(func.count()).select_from({{ table_name }})

    if filtering is not None:
        query = self._apply_filtering(query, filtering)
        total_query = self._apply_filtering(total_query, filtering)

    if sorting is not None:
        query = self._apply_sorting(query, sorting)

    if pagination is not None:
        query = self._apply_pagination(query, pagination)

    total = self._connection.execute(total_query).scalar() or 0
    rows = self._connection.execute(query).mappings().fetchall()

    per_page = pagination["per_page"] if pagination is not None else (total or 1)
    page = pagination["page"] if pagination is not None else 1
    total_pages = (total + per_page - 1) // per_page if per_page else 0

    return {
        "{{ aggregate_plural }}": [dict(row) for row in rows],
        "metadata": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
        },
    }
```

### Helper bodies

```python
def _apply_filtering(self, query: Query, filtering: {{ filtering_dto }}) -> Query:
    if filtering.get("{{ filter_field }}") is not None:
        query = query.where(
            {{ table_name }}.c.{{ filter_column }} == filtering["{{ filter_field }}"]
        )
    return query

def _apply_sorting(self, query: Query, sorting: {{ sorting_enum }}) -> Query:
    if sorting is {{ sorting_enum }}.{{ sorting_member }}:
        return query.order_by({{ table_name }}.c.{{ sort_column }}.desc())
    return query

def _apply_pagination(self, query: Query, pagination: Pagination) -> Query:
    return query.limit(pagination["per_page"]).offset(
        (pagination["page"] - 1) * pagination["per_page"]
    )
```

## DTO access conventions

- `Filtering`, `Sorting`, `Pagination`, `<Aggregate>Info`, and `<Aggregate>ListResult` are `TypedDict`s.
- Read TypedDict fields with bracket access (`filtering["status"]`) and presence checks via `.get(...)`.
- Never call attribute access on a TypedDict (`filtering.status` does not work at runtime).
- The Sorting parameter is an `Enum`, not a TypedDict — compare with `is` and reference members as `<Sorting>.<Member>`.

## Field → column mapping

Apply the same column-mapping rule as the command-side repository, in order:

1. Exact match: field name equals a column on the aggregate table.
2. Strip trailing underscore (`id_` → `id`).
3. Strip aggregate prefix (`<aggregate>_<field>` → `<field>`).
4. Append `_id` (`<field>` → `<field>_id`).

A field that resolves to multiple columns is treated as no match — the implementer fails with the offending field rather than guess.

## Module shape

```python
from typing import Any

from sqlalchemy import Column, func, select
from sqlalchemy.orm import Query, Session

from {{ domain_module }} import (
    Pagination,
    {{ query_repository_interface }},
    {{ filtering_dto }},
    {{ sorting_enum }},
)

from ..tables import {{ table_name }}

__all__ = ["{{ query_repository_class }}"]


class {{ query_repository_class }}({{ query_repository_interface }}):
    def __init__(self, connection: Session) -> None:
        self._connection = connection

    @property
    def {{ aggregate_name_lower }}_columns(self) -> list[Column]:
        return [
            {{ table_name }}.c.{{ col_1 }},
            {{ table_name }}.c.{{ col_2 }},
            ...
        ]

    # Method bodies emitted in ABC declaration order — Rules A, B, C above.
    # Helpers (_apply_filtering, _apply_sorting, _apply_pagination) are emitted
    # only when at least one paginated-list method needs them.
```

Imports are emitted only for the symbols actually used by the rendered body (omit `func` when no list method exists, omit `Column` when no `_columns` property is emitted, omit `Sorting` when no method takes a sorting parameter, etc.).

## Testing guidance

- Fake repositories implement the same ABC and return matching TypedDicts from in-memory data.
- Integration tests verify filtering, sorting, and pagination calculations against a real database.
- Test empty result sets — paginated DTOs must return `{"…": [], "metadata": {"total": 0, "total_pages": 0, ...}}`.

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ domain_module }}` | Domain module path | `acme.domain.order` |
| `{{ query_repository_interface }}` | Domain ABC class | `QueryOrderRepository` |
| `{{ query_repository_class }}` | Concrete class | `SqlAlchemyQueryOrderRepository` |
| `{{ info_dto }}` | TypedDict name (return) | `OrderInfo`, `OrderListResult` |
| `{{ filtering_dto }}` | Filtering TypedDict | `OrderFiltering` |
| `{{ sorting_enum }}` | Sorting enum | `OrderSorting` |
| `{{ aggregate_name_lower }}` | snake_case aggregate | `order` |
| `{{ aggregate_name_lower_plural }}` | snake_case plural | `orders` |
| `{{ aggregate_plural }}` | TypedDict list-key | `orders` |
| `{{ table_name }}` | SQLAlchemy table variable | `order_table` |
| `{{ id_column }}` | PK column name | `id`, `order_id` |
| `{{ filter_field }}` / `{{ filter_column }}` | Filtering field & resolved column | `status` |
| `{{ sorting_member }}` / `{{ sort_column }}` | Sorting enum member & resolved column | `NEWEST_FIRST` / `created_at` |
