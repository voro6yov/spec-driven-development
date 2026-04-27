---
name: command-repository
description: Command Repository pattern for persistence. Use when implementing SQLAlchemy repositories that handle aggregate saves, lookups, and deletes within unit of work transactions.
user-invocable: false
disable-model-invocation: false
---

# Command Repository

**Type:** Primary

## Purpose

- Implement domain command repository interfaces for aggregate persistence.
- Handle aggregate lookups and saves within unit of work transactions.
- Convert between domain aggregates and database representations using mappers.

## Structure

- Implements domain `CommandRepository` interface (ABC or Protocol).
- Takes SQLAlchemy `Session` in constructor (provided by unit of work).
- Uses static mapper classes for bidirectional conversion (`to_dict`, `from_row`, `from_rows`).
- Defines `aggregate_columns` property listing all columns needed for aggregate reconstruction.
- Two variants: simple (single table) and with-children (parent + child tables).

## Usage patterns

- `aggregate_of_id(id_, tenant_id)` returns aggregate instance or `None` using mapper `from_row` or `from_rows`.
- `save(aggregate)` uses SQLAlchemy `insert().on_conflict_do_update()` for upsert pattern.
- `save_all(aggregates)` uses batch insert with upsert for multiple aggregates in a single database round-trip.
- `delete(aggregate)` removes the aggregate (and children if applicable) from the database.
- Use `erase_all()` for test cleanup (deletes all records).

## Alternative lookup patterns

Beyond the primary `aggregate_of_id()` lookup, repositories often need additional query methods:

### Lookup by non-PK field (returns list)

```python
def aggregates_of_file(self, file_id: str, tenant_id: str) -> list[Aggregate]:
    query = select(table).where(
        and_(
            table.c.file_id == file_id,
            table.c.tenant_id == tenant_id,
        ),
    )
    rows = self._connection.execute(query).fetchall()
    return [Mapper.from_row(row._mapping) for row in rows]
```

### Lookup by JSONB array contains

```python
def aggregate_with_item(self, item_id: str, tenant_id: str) -> Aggregate | None:
    query = select([table.c.id]).where(
        and_(
            table.c.tenant_id == tenant_id,
            table.c.items.contains([item_id]),  # JSONB array contains
        ),
    )
    row = self._connection.execute(query).fetchone()
    if not row:
        return None
    return self.aggregate_of_id(row.id, tenant_id)
```

### Existence check (returns bool)

```python
def has_aggregate_with_field(self, field: str, tenant_id: str) -> bool:
    query = (
        select(table.c.id)
        .where(
            and_(
                table.c.tenant_id == tenant_id,
                table.c.field == field,
            ),
        )
        .limit(1)
    )
    return self._connection.execute(query).fetchone() is not None
```

For JSONB sub-key existence (e.g. `details->>'name' == name`):

```python
def has_aggregate_with_name(self, name: str, tenant_id: str) -> bool:
    query = (
        select(table.c.id)
        .where(
            and_(
                table.c.tenant_id == tenant_id,
                table.c.details["name"].astext == name,
            ),
        )
        .limit(1)
    )
    return self._connection.execute(query).fetchone() is not None
```

### Lookup via child entity

```python
def aggregate_with_child(self, child_id: str, tenant_id: str) -> Aggregate | None:
    query = select(child_table.c.parent_id).where(
        and_(
            child_table.c.id == child_id,
            child_table.c.tenant_id == tenant_id,
        ),
    )
    row = self._connection.execute(query).fetchone()
    if not row:
        return None
    return self.aggregate_of_id(row.parent_id, tenant_id)
```

## Child entity handling

For aggregates with child entities, use the `uow_command_repository_with_children.py.j2` template:

- **Orphan cleanup pattern**: Compare existing child IDs with current child IDs, delete only orphaned children.
- This is more efficient than delete-all-then-insert when most children remain unchanged.
- `_sync_children()` method handles the orphan detection and batch upsert.
- Delete order: children first, then parent (respects FK constraints).
- Child mappers receive parent context (`parent_id`, `tenant_id`) in `to_dict()`.

## Testing guidance

- Fake repositories should implement the same interface and store aggregates in memory.
- Integration tests verify mapper conversion, upsert behavior, and child entity handling.
- Test aggregate lookup returns `None` when not found.
- Test orphan cleanup: add children, remove some, save, verify only removed ones are deleted.

---

## Template

### Simple Command Repository

```python
from sqlalchemy import Column, and_, delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from {{ domain_module }} import {{ command_repository_interface }}, {{ aggregate_name }}

from ..tables import {{ table_name }}
from .mappers import {{ mapper_class }}

__all__ = ["{{ uow_repository_class }}"]

class {{ uow_repository_class }}({{ command_repository_interface }}):
    def __init__(self, connection: Session) -> None:
        self._connection = connection

    @property
    def {{ aggregate_name_lower }}_columns(self) -> list[Column]:
        return [
            {{ table_name }}.c.{{ id_column }},
            {{ table_name }}.c.{{ tenant_id_column }},
            {{ table_name }}.c.{{ additional_columns }},
        ]

    def {{ lookup_method }}(self, id_: str, tenant_id: str) -> {{ aggregate_name }} | None:
        query = (
            select(self.{{ aggregate_name_lower }}_columns)
            .select_from({{ table_name }})
            .where(
                and_(
                    {{ table_name }}.c.{{ id_column }} == id_,
                    {{ table_name }}.c.{{ tenant_id_column }} == tenant_id,
                ),
            )
        )

        row = self._connection.execute(query).fetchone()

        if not row:
            return None

        return {{ mapper_class }}.from_row(row)

    def save(self, {{ aggregate_name_lower }}: {{ aggregate_name }}) -> None:
        insert_command = insert({{ table_name }})
        save_{{ aggregate_name_lower }}_command = insert_command.on_conflict_do_update(
            constraint={{ table_name }}.primary_key,
            set_=dict(insert_command.excluded),
        ).values(**{{ mapper_class }}.to_dict({{ aggregate_name_lower }}))

        self._connection.execute(save_{{ aggregate_name_lower }}_command)

    def save_all(self, {{ aggregate_name_lower }}s: list[{{ aggregate_name }}]) -> None:
        if not {{ aggregate_name_lower }}s:
            return

        values = [{{ mapper_class }}.to_dict(item) for item in {{ aggregate_name_lower }}s]
        insert_command = insert({{ table_name }})
        save_command = insert_command.on_conflict_do_update(
            constraint={{ table_name }}.primary_key,
            set_=dict(insert_command.excluded),
        )

        self._connection.execute(save_command, values)

    def delete(self, {{ aggregate_name_lower }}: {{ aggregate_name }}) -> None:
        delete_statement = delete({{ table_name }}).where(
            and_(
                {{ table_name }}.c.{{ id_column }} == {{ aggregate_name_lower }}.id,
                {{ table_name }}.c.{{ tenant_id_column }} == {{ aggregate_name_lower }}.tenant_id,
            ),
        )

        self._connection.execute(delete_statement)

    def erase_all(self) -> None:
        self._connection.execute(delete({{ table_name }}))
```

### Command Repository with Children

```python
from sqlalchemy import Column, and_, delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from {{ domain_module }} import {{ command_repository_interface }}, {{ aggregate_name }}

from ..tables import {{ table_name }}
from ..tables import {{ child_table_name }}
from .mappers import {{ mapper_class }}
from .mappers import {{ child_mapper_class }}

__all__ = ["{{ uow_repository_class }}"]

class {{ uow_repository_class }}({{ command_repository_interface }}):
    def __init__(self, connection: Session) -> None:
        self._connection = connection

    @property
    def {{ aggregate_name_lower }}_columns(self) -> list[Column]:
        return [
            {{ table_name }}.c.{{ id_column }},
            {{ table_name }}.c.{{ tenant_id_column }},
            {{ table_name }}.c.{{ additional_columns }},
        ]

    @property
    def {{ child_name_lower }}_columns(self) -> list[Column]:
        return [
            {{ child_table_name }}.c.{{ child_id_column }},
            {{ child_table_name }}.c.{{ parent_id_column }},
            {{ child_table_name }}.c.{{ tenant_id_column }},
            {{ child_table_name }}.c.{{ child_additional_columns }},
        ]

    def {{ lookup_method }}(self, id_: str, tenant_id: str) -> {{ aggregate_name }} | None:
        aggregate_query = select(*self.{{ aggregate_name_lower }}_columns).where(
            and_(
                {{ table_name }}.c.{{ id_column }} == id_,
                {{ table_name }}.c.{{ tenant_id_column }} == tenant_id,
            ),
        )

        aggregate_row = self._connection.execute(aggregate_query).fetchone()

        if not aggregate_row:
            return None

        children_query = select(*self.{{ child_name_lower }}_columns).where(
            and_(
                {{ child_table_name }}.c.{{ parent_id_column }} == id_,
                {{ child_table_name }}.c.{{ tenant_id_column }} == tenant_id,
            ),
        )

        child_rows = self._connection.execute(children_query).fetchall()

        return {{ mapper_class }}.from_rows(aggregate_row._mapping, [row._mapping for row in child_rows])

    def save(self, {{ aggregate_name_lower }}: {{ aggregate_name }}) -> None:
        aggregate_dict = {{ mapper_class }}.to_dict({{ aggregate_name_lower }})

        insert_aggregate_command = insert({{ table_name }})
        save_aggregate_command = insert_aggregate_command.on_conflict_do_update(
            constraint={{ table_name }}.primary_key,
            set_=dict(insert_aggregate_command.excluded),
        ).values(**aggregate_dict)

        self._connection.execute(save_aggregate_command)

        self._sync_children({{ aggregate_name_lower }})

    def _sync_children(self, {{ aggregate_name_lower }}: {{ aggregate_name }}) -> None:
        existing_ids_query = select({{ child_table_name }}.c.{{ child_id_column }}).where(
            and_(
                {{ child_table_name }}.c.{{ parent_id_column }} == {{ aggregate_name_lower }}.id,
                {{ child_table_name }}.c.{{ tenant_id_column }} == {{ aggregate_name_lower }}.tenant_id,
            ),
        )
        existing_ids = {row.{{ child_id_column }} for row in self._connection.execute(existing_ids_query).fetchall()}

        current_ids = {child.id for child in {{ aggregate_name_lower }}.{{ children_attribute }}}

        orphaned_ids = existing_ids - current_ids

        if orphaned_ids:
            delete_statement = delete({{ child_table_name }}).where(
                and_(
                    {{ child_table_name }}.c.{{ parent_id_column }} == {{ aggregate_name_lower }}.id,
                    {{ child_table_name }}.c.{{ tenant_id_column }} == {{ aggregate_name_lower }}.tenant_id,
                    {{ child_table_name }}.c.{{ child_id_column }}.in_(orphaned_ids),
                ),
            )
            self._connection.execute(delete_statement)

        if {{ aggregate_name_lower }}.{{ children_attribute }}:
            child_dicts = [
                {{ child_mapper_class }}.to_dict(child, {{ aggregate_name_lower }}.id, {{ aggregate_name_lower }}.tenant_id)
                for child in {{ aggregate_name_lower }}.{{ children_attribute }}
            ]

            insert_child_command = insert({{ child_table_name }})

            # Option 1: Update all columns (simpler)
            # set_=dict(insert_child_command.excluded)
            #
            # Option 2: Explicit columns (excludes PK columns from update)
            # set_={
            #     "{{ parent_id_column }}": insert_child_command.excluded.{{ parent_id_column }},
            #     "{{ child_additional_column }}": insert_child_command.excluded.{{ child_additional_column }},
            # }
            save_children_command = insert_child_command.on_conflict_do_update(
                constraint={{ child_table_name }}.primary_key,
                set_=dict(insert_child_command.excluded),
            )

            self._connection.execute(save_children_command, child_dicts)

    def delete(self, {{ aggregate_name_lower }}: {{ aggregate_name }}) -> None:
        delete_children_statement = delete({{ child_table_name }}).where(
            and_(
                {{ child_table_name }}.c.{{ parent_id_column }} == {{ aggregate_name_lower }}.id,
                {{ child_table_name }}.c.{{ tenant_id_column }} == {{ aggregate_name_lower }}.tenant_id,
            ),
        )

        self._connection.execute(delete_children_statement)

        delete_aggregate_statement = delete({{ table_name }}).where(
            and_(
                {{ table_name }}.c.{{ id_column }} == {{ aggregate_name_lower }}.id,
                {{ table_name }}.c.{{ tenant_id_column }} == {{ aggregate_name_lower }}.tenant_id,
            ),
        )

        self._connection.execute(delete_aggregate_statement)

    def erase_all(self) -> None:
        self._connection.execute(delete({{ child_table_name }}))
        self._connection.execute(delete({{ table_name }}))
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ domain_module }}` | Domain module path | `domain.repositories`, `domain.aggregates` |
| `{{ command_repository_interface }}` | Command repository interface | `CommandRepository`, `OrderRepository` |
| `{{ aggregate_name }}` | Aggregate class name | `Order`, `Profile` |
| `{{ aggregate_name_lower }}` | Aggregate name in snake_case | `order`, `profile` |
| `{{ table_name }}` | SQLAlchemy table variable | `order_table`, `profile_table` |
| `{{ mapper_class }}` | Mapper class name | `OrderMapper`, `ProfileMapper` |
| `{{ uow_repository_class }}` | Repository class name | `SqlAlchemyOrderRepository` |
| `{{ id_column }}` | Primary key column name | `id`, `order_id` |
| `{{ tenant_id_column }}` | Tenant ID column name | `tenant_id` |
| `{{ additional_columns }}` | Additional column names (comma-separated) | `status, created_at` |
| `{{ lookup_method }}` | Lookup method name | `order_of_id`, `profile_of_id` |
| `{{ child_table_name }}` | Child table variable | `order_item_table` |
| `{{ child_mapper_class }}` | Child mapper class | `OrderItemMapper` |
| `{{ child_name_lower }}` | Child entity name in snake_case | `order_item` |
| `{{ child_id_column }}` | Child primary key column | `id` |
| `{{ parent_id_column }}` | Foreign key to parent | `order_id` |
| `{{ child_additional_columns }}` | Child additional columns | `quantity, price` |
| `{{ children_attribute }}` | Aggregate children attribute | `items`, `addresses` |
