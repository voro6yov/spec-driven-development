---
name: query-repository
description: Query Repository pattern for persistence. Use when implementing read-only SQLAlchemy repositories that return DTOs with filtering, pagination, and analytics support.
user-invocable: false
disable-model-invocation: false
---

# Query Repository

**Type:** Supporting

> **Optional Pattern**: This pattern implements the read-side of CQRS (Command Query Responsibility Segregation). Use when you need dedicated query operations separate from command repositories. Skip if your command repositories handle all read needs.
> 

## Purpose

- Implement domain query repository interfaces for read-only aggregate queries.
- Return DTOs (typed dicts) instead of domain aggregates for query operations.
- Handle filtering, pagination, and analytics queries without transaction overhead.

## Structure

- Implements domain `QueryRepository` interface (Protocol or ABC).
- Takes SQLAlchemy `Session` or `DatabaseSession` in constructor.
- Uses mapper classes for DTO conversion (`from_rows`, `from_dict`).
- Exposes query methods that return domain DTOs like `AggregateInfo`, `PaginatedResult`.
- Supports filtering via domain filter objects and pagination via domain `Pagination` type.

## Usage patterns

- `find_aggregate(id_)` returns raw dict or DTO for single aggregate lookup.
- `find_aggregates(filtering, pagination)` returns paginated DTO with metadata.
- `get_analytics(filtering)` returns aggregate analytics DTO with computed metrics.
- Filtering and pagination are applied via private helper methods (`_apply_filtering`, `_apply_pagination`).
- Use SQLAlchemy `func` for aggregations (count, avg, min, max).

## Testing guidance

- Fake repositories should implement the same interface and return DTOs from in-memory data.
- Integration tests verify filtering, pagination, and analytics calculations.
- Test empty result sets return appropriate DTOs with zero counts.

---

## Template

```python
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Query, Session

from {{ domain_module }} import (
    Pagination,
    {{ query_repository_interface }},
    {{ aggregate_info_dto }},
    {{ filtering_dto }},
)

from ..tables import {{ table_name }}
from .mappers import {{ info_mapper_class }}

__all__ = ["{{ query_repository_class }}"]

class {{ query_repository_class }}({{ query_repository_interface }}):
    def __init__(self, connection: Session) -> None:
        self._connection = connection

    def find_{{ aggregate_name_lower }}(self, id_: str) -> dict[str, Any] | None:
        query = select([{{ table_name }}]).where({{ table_name }}.c.{{ id_column }} == id_)

        row = self._connection.execute(query).first()

        if not row:
            return None

        return dict(row)

    def find_{{ aggregate_name_lower }}s(
        self, filtering: {{ filtering_dto }} | None = None, pagination: Pagination | None = None
    ) -> {{ aggregate_info_dto }}:
        query = select([{{ table_name }}]).order_by({{ table_name }}.c.created_at.desc())
        total_query = select([func.count()]).select_from({{ table_name }})

        if filtering:
            query = self._apply_filtering(query, filtering)
            total_query = self._apply_filtering(total_query, filtering)

        if pagination:
            query = self._apply_pagination(query, pagination)

        total = self._connection.execute(total_query).scalar()
        rows = self._connection.execute(query).fetchall()

        return {{ info_mapper_class }}.from_rows([dict(row) for row in rows], total)

    def _apply_filtering(self, query: Query, filtering: {{ filtering_dto }}) -> Query:
        if filtering.{{ filter_field }} is not None:
            query = query.where({{ table_name }}.c.{{ filter_column }} == filtering.{{ filter_field }})

        return query

    def _apply_pagination(self, query: Query, pagination: Pagination) -> Query:
        return query.limit(pagination.limit).offset(pagination.offset)
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ domain_module }}` | Domain module path | `domain.repositories`, `domain.dtos` |
| `{{ query_repository_interface }}` | Query repository interface | `QueryRepository`, `OrderQueryRepository` |
| `{{ aggregate_info_dto }}` | Aggregate info DTO type | `OrderInfo`, `ProfileInfo` |
| `{{ filtering_dto }}` | Filtering DTO type | `OrderFiltering`, `ProfileFiltering` |
| `{{ table_name }}` | SQLAlchemy table variable | `order_table`, `profile_table` |
| `{{ info_mapper_class }}` | Info mapper class | `OrderInfoMapper`, `ProfileInfoMapper` |
| `{{ query_repository_class }}` | Query repository class name | `SqlAlchemyOrderQueryRepository` |
| `{{ aggregate_name_lower }}` | Aggregate name in snake_case | `order`, `profile` |
| `{{ id_column }}` | Primary key column name | `id`, `order_id` |
| `{{ filter_field }}` | Filter field name | `status`, `tenant_id` |
| `{{ filter_column }}` | Filter column name | `status`, `tenant_id` |
