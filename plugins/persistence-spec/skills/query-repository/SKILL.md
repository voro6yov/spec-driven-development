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
- Return TypedDict DTOs **constructed explicitly** (`<Info>(key=row["key"], …)`), not via `dict(row)` casts — the TypedDict drives both what is SELECTed and what shape the return value takes.
- Handle filtering, sorting, and pagination without transaction overhead and without dedicated DTO mapper classes.

## Structure

- Implements the domain `Query<Aggregate>Repository` ABC.
- Takes SQLAlchemy `Session` in the constructor.
- Each method **inlines its projection** — `select(<col_1>, <col_2>, …)` lists exactly the columns the method's return TypedDict declares as keys. There is no shared `<aggregate>_columns` property; per-method projections diverge naturally when `<Info>` and `<BriefInfo>` differ.
- Each method **constructs the return TypedDict explicitly** with keyword arguments (`<Info>(id=row["id"], …)` for single-result methods; `[<BriefInfo>(id=row["id"], …) for row in rows]` for the list inside paginated results).
- Keeps filtering, sorting, and pagination as private helpers (`_apply_filtering`, `_apply_sorting`, `_apply_pagination`).

## Method body templates

Method dispatch is signature-driven from the domain `Query<Aggregate>Repository` ABC. The implementer classifies each `@abstractmethod` into one of the rules below.

### Rule A — Single lookup by id

Return annotation unwraps to `<Info> | None`; parameter list (after `self`) has exactly one non-`tenant_id` parameter that maps to the aggregate table's PK column via the column-mapping rule. The projection lists every key of `<Info>` resolved through the column-expression resolver (bare column or JSONB sub-field). The return is an explicit `<Info>(…)` constructor.

```python
def find_{{ aggregate_name_lower }}(self, id_: str) -> {{ info_dto }} | None:
    query = select(
        {{ table_name }}.c.id,
        {{ table_name }}.c.{{ jsonb_col }}["name"].astext.label("name"),
        {{ table_name }}.c.enabled,
        {{ table_name }}.c.created_at,
        {{ table_name }}.c.updated_at,
    ).where({{ table_name }}.c.{{ id_column }} == id_)
    row = self._connection.execute(query).mappings().first()
    return {{ info_dto }}(
        id=row["id"],
        name=row["name"],
        enabled=row["enabled"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    ) if row else None
```

### Rule B — Single lookup by alternative field (`find_by_<field>`)

Return annotation unwraps to `<Info> | None`; parameter list has at least one non-`tenant_id` parameter, each mapping to a column on the aggregate table; method is **not** the PK lookup. The projection and explicit constructor are identical to Rule A; the where clause is built from each parameter using the column-mapping rule.

```python
def find_by_{{ field }}(self, {{ field }}: str) -> {{ info_dto }} | None:
    query = select(
        {{ table_name }}.c.id,
        {{ table_name }}.c.{{ jsonb_col }}["name"].astext.label("name"),
        ...
    ).where({{ table_name }}.c.{{ field_column }} == {{ field }})
    row = self._connection.execute(query).mappings().first()
    return {{ info_dto }}(
        id=row["id"],
        name=row["name"],
        ...
    ) if row else None
```

### Rule C — Paginated list

Return annotation unwraps to `<ListResult>` — a flat TypedDict with exactly one `list[<BriefInfo>]` key plus zero or more scalar keys (`total`, `page`, `per_page`, `total_pages`, …). Parameter list contains some subset of `filtering: <Filtering> | None`, `sorting: <Sorting> | None`, `pagination: Pagination | None`. The projection lists every key of `<BriefInfo>` resolved through the column-expression resolver. The return is an explicit `<ListResult>(…)` constructor whose `<list_key>` field is a list of explicit `<BriefInfo>(…)` constructors and whose scalar fields come from the **scalar-key registry** (`total` from the SQL count; `page` / `per_page` / `total_pages` from the pagination parameter and integer arithmetic).

```python
def find_{{ aggregate_name_lower_plural }}(
    self,
    filtering: {{ filtering_dto }} | None = None,
    sorting: {{ sorting_enum }} | None = None,
    pagination: Pagination | None = None,
) -> {{ list_result_dto }}:
    query = select(
        {{ table_name }}.c.id,
        {{ table_name }}.c.{{ jsonb_col }}["name"].astext.label("name"),
        {{ table_name }}.c.enabled,
        {{ table_name }}.c.created_at,
        {{ table_name }}.c.updated_at,
    )
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

    per_page = pagination.per_page if pagination is not None else (total or 1)
    page = pagination.page if pagination is not None else 0
    total_pages = (total + per_page - 1) // per_page if per_page else 0

    return {{ list_result_dto }}(
        {{ aggregate_plural }}=[
            {{ brief_info_dto }}(
                id=row["id"],
                name=row["name"],
                enabled=row["enabled"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )
```

The `<scalar_local_assignments>` (`per_page`, `page`, `total_pages`) are emitted only when the corresponding scalar keys are referenced in the resolved scalar values. When the `<ListResult>` declares only `<list_key>` and `total` (the simplest flat shape), drop the `per_page` / `page` / `total_pages` locals entirely — the constructor receives just `<list_key>=…` and `total=total`.

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
    return query.limit(pagination.per_page).offset(pagination.first_element_index)
```

## DTO access conventions

- `Filtering`, `<Aggregate>Info`, and `<Aggregate>ListResult` are `TypedDict`s.
- Read TypedDict fields with bracket access (`filtering["status"]`) and presence checks via `.get(...)`.
- Never call attribute access on a TypedDict (`filtering.status` does not work at runtime).
- `Pagination` is a `@dataclass` (defined in `<pkg>/domain/shared/pagination.py`) with fields `page` (0-indexed) and `per_page`, plus the property `first_element_index = page * per_page`. Use attribute access (`pagination.per_page`, `pagination.first_element_index`) — bracket access raises `TypeError`.
- The Sorting parameter is an `Enum` — compare with `is` and reference members as `<Sorting>.<Member>`.

## Two distinct mapping rules

The query repository uses two related but **distinct** mapping rules:

### 1. Column-mapping rule (parameter → table column)

Used to build WHERE clauses from method parameters. Apply in order against the on-disk table column list:

1. Exact match: parameter name equals a column on the aggregate table.
2. Strip trailing underscore (`id_` → `id`).
3. Strip aggregate prefix (`<aggregate>_<field>` → `<field>`).
4. Append `_id` (`<field>` → `<field>_id`).
5. Otherwise: no match (and the implementer fails with the offending parameter).

### 2. Column-expression resolver (TypedDict key → SQL expression)

Used to build per-method projection lists from the return TypedDict's keys, and to resolve filter and sort fields. Apply in order:

1. **Bare column.** TypedDict key matches a column name in `<on_disk_columns>` → `<table>.c.<key>`.
2. **JSONB sub-field.** TypedDict key matches a key declared by a value-object mapper (`<X>Mapper.to_json` return-dict) linked to a JSONB column on the table → `<table>.c.<jsonb_col>["<key>"].astext.label("<key>")` for primitive types (`str`, `int`, `float`, `bool`, `Enum`); drop `.astext` for nested `dict[…]`/`list[…]`/TypedDict types so the value remains JSON.
3. **No match or multiple matches** → fail with a precise error citing the inspected sources.

The link `JSONB column → value-object mapper` is read from the aggregate's command-side `<Aggregate>Mapper.to_dict` body — entries of the form `"<jsonb_col>": <X>Mapper.to_json(<expr>)` are detected and used to learn which JSONB column holds which value-object's keys.

### JSONB sub-field projection — example

Query DTOs (`<Info>`, `<BriefInfo>`) are intentionally flat — they expose value-object attributes as top-level keys (`name`, `description`, …) even when the underlying schema stores them inside a JSONB column (`details`, `info`, `metadata`, …). Each method's inline projection lists each TypedDict key as the resolved expression:

```python
query = select(
    {{ table_name }}.c.id,
    # Flat columns map 1:1 to TypedDict keys
    {{ table_name }}.c.enabled,
    {{ table_name }}.c.created_at,
    {{ table_name }}.c.updated_at,
    # JSONB sub-fields are projected as labelled top-level columns
    {{ table_name }}.c.{{ jsonb_col }}["name"].astext.label("name"),
    {{ table_name }}.c.{{ jsonb_col }}["description"].astext.label("description"),
).where(...)
```

Apply the same JSONB sub-field projection in `_apply_filtering` and `_apply_sorting` — compare against `<table>.c.<jsonb_col>["<field>"].astext` rather than a non-existent top-level column. (Filtering and sorting use the **bare** SQL expression — strip the trailing `.label("<field>")` from the resolver's output before composing the where/order_by clause.)

Use `.astext` for scalar string/number/bool sub-fields. For nested object or array sub-fields preserve them as JSON (drop `.astext`); the DTO key is then a `dict` / `list` rather than a string.

## Module shape

```python
from sqlalchemy import func, select
from sqlalchemy.orm import Query, Session

from {{ domain_module }} import (
    {{ brief_info_dto }},
    {{ filtering_dto }},
    {{ info_dto }},
    {{ list_result_dto }},
    {{ query_repository_interface }},
    {{ sorting_enum }},
)
from {{ shared_module }} import Pagination

from ..tables import {{ table_name }}

__all__ = ["{{ query_repository_class }}"]


class {{ query_repository_class }}({{ query_repository_interface }}):
    def __init__(self, connection: Session) -> None:
        self._connection = connection

    # Method bodies emitted in ABC declaration order — Rules A, B, C above.
    # Each method inlines its projection (driven by its return TypedDict's keys)
    # and constructs its return value with an explicit TypedDict constructor.
    # Helpers (_apply_filtering, _apply_sorting, _apply_pagination) are emitted
    # only when at least one paginated-list method needs them.
```

Imports are emitted only for the symbols actually used by the rendered body. Notable rules:

- `Column` is **never** imported — there is no shared `<aggregate>_columns` property.
- `typing.Any` is **never** imported — every return is an explicit TypedDict constructor, not a `dict[str, Any]`.
- `math` is **never** imported — `total_pages` uses integer arithmetic (`(total + per_page - 1) // per_page`).
- `func` is omitted when no Rule C body is present (no list method).
- `Query` is omitted when no helper is emitted.
- `and_` is added only when a compound where clause is needed (multi-tenant Rule A; multi-parameter or multi-tenant Rule B).
- The ABC, every per-method return TypedDict (`<Info>`, `<BriefInfo>`, `<ListResult>`), `<Filtering>`, and `<Sorting>` are imported from their on-disk modules; `Pagination` typically lands on its own line because it lives in a shared kernel module.

## Testing guidance

- Fake repositories implement the same ABC and return matching TypedDicts from in-memory data.
- Integration tests verify filtering, sorting, and pagination calculations against a real database.
- Test empty result sets — paginated DTOs must return `<ListResult>(<list_key>=[], total=0, …)` with the scalar keys populated to their zero/default values.

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ domain_module }}` | Domain module path | `acme.domain.order` |
| `{{ shared_module }}` | Dotted module that defines `Pagination` (the `from … import Pagination` source) | `acme.domain.shared.pagination` |
| `{{ query_repository_interface }}` | Domain ABC class | `QueryOrderRepository` |
| `{{ query_repository_class }}` | Concrete class | `SqlAlchemyQueryOrderRepository` |
| `{{ info_dto }}` | Single-result TypedDict | `OrderInfo` |
| `{{ brief_info_dto }}` | List-item TypedDict | `BriefOrderInfo` |
| `{{ list_result_dto }}` | List-result TypedDict | `OrderListResult` |
| `{{ filtering_dto }}` | Filtering TypedDict | `OrderFiltering` |
| `{{ sorting_enum }}` | Sorting enum | `OrderSorting` |
| `{{ aggregate_name_lower }}` | snake_case aggregate | `order` |
| `{{ aggregate_name_lower_plural }}` | snake_case plural | `orders` |
| `{{ aggregate_plural }}` | TypedDict list-key (the field on `<ListResult>` that holds the list) | `orders` |
| `{{ table_name }}` | SQLAlchemy table variable | `order_table` |
| `{{ jsonb_col }}` | JSONB column hosting a value-object's serialized fields | `details` |
| `{{ id_column }}` | PK column name | `id`, `order_id` |
| `{{ filter_field }}` / `{{ filter_column }}` | Filtering field & resolved column | `status` |
| `{{ sorting_member }}` / `{{ sort_column }}` | Sorting enum member & resolved column | `NEWEST_FIRST` / `created_at` |
