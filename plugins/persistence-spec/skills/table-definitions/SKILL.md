---
name: table-definitions
description: Table Definitions pattern for persistence. Use when defining SQLAlchemy Table objects with simple, composite PK, or FK constraints for domain aggregate storage.
user-invocable: false
disable-model-invocation: false
---

# Table Definitions

**Type:** Primary

## Purpose

- Define SQLAlchemy Table objects for database schema representation.
- Provide type-safe column definitions with constraints.
- Support JSONB columns for complex nested domain data.

## Table Types

### Simple Table (`table_definition.py.j2`)

Single primary key, no foreign keys.

```python
Table(
    "entity",
    metadata,
    Column("id", String, primary_key=True),
    Column("tenant_id", String, nullable=False),
    ...
)
```

### Composite Primary Key Table (`table_definition_composite_pk.py.j2`)

Multiple columns form the primary key (common for multi-tenant systems).

```python
Table(
    "entity",
    metadata,
    Column("id", String, primary_key=True),
    Column("tenant_id", String, primary_key=True),
    ...
)
```

### Table with Foreign Key (`table_definition_with_fk.py.j2`)

Child table referencing parent with composite FK constraint.

```python
Table(
    "child_entity",
    metadata,
    Column("id", String, primary_key=True),
    Column("parent_id", String, nullable=False),
    Column("tenant_id", String, primary_key=True),
    ...
    ForeignKeyConstraint(
        ["parent_id", "tenant_id"],
        ["parent.id", "parent.tenant_id"],
        ondelete="CASCADE",
    ),
)
```

## Column Types

| Domain Type | SQLAlchemy Type | Notes |
| --- | --- | --- |
| String ID | `String` | Primary keys, foreign keys |
| Enum/Status | `String` | Store enum value as string |
| Timestamp | `DateTime(timezone=True)` | `created_at`, `updated_at` (always timezone-aware to round-trip tz-aware UTC values without losing tzinfo) |
| Value Object | `JSONB` | Nested structures, nullable |
| Collection | `JSONB` | Arrays stored as JSON |

## Constraints

- `primary_key=True` for identity columns (can be multiple for composite PK).
- `nullable=False` for required fields.
- `ForeignKeyConstraint` for composite foreign keys with `ondelete="CASCADE"`.

## Naming Conventions

- Table name: snake_case, matches domain aggregate name.
- Column names: snake_case, match domain attribute names.
- FK constraint: `fk_{child_table}_{parent_table}`.

## Testing guidance

- Table definitions are tested indirectly through repository integration tests.
- Verify table creation in migration tests.
- Check that foreign key constraints work correctly (cascade delete).

---

## Template

### Simple Table

```python
from sqlalchemy import Column, DateTime, String, Table
from sqlalchemy.dialects.postgresql import JSONB

from {{ extras_module }} import metadata

__all__ = ["{{ table_name }}"]

{{ table_name }} = Table(
    "{{ table_name_snake }}",
    metadata,
    Column("{{ id_column }}", String, primary_key=True),
    Column("{{ tenant_id_column }}", String, nullable=False),
    Column("{{ jsonb_column }}", JSONB, nullable=True),
    Column("{{ status_column }}", String, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
```

### Composite Primary Key Table

```python
from sqlalchemy import Column, DateTime, String, Table
from sqlalchemy.dialects.postgresql import JSONB

from {{ extras_module }} import metadata

__all__ = ["{{ table_name }}"]

{{ table_name }} = Table(
    "{{ table_name_snake }}",
    metadata,
    Column("{{ id_column }}", String, primary_key=True),
    Column("{{ tenant_id_column }}", String, primary_key=True),
    Column("{{ additional_column }}", {{ additional_column_type }}, nullable={{ additional_column_nullable }}),
    Column("{{ status_column }}", String, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
```

### Table with Foreign Key

```python
from sqlalchemy import Column, ForeignKeyConstraint, String, Table
from sqlalchemy.dialects.postgresql import JSONB

from {{ extras_module }} import metadata

__all__ = ["{{ table_name }}"]

{{ table_name }} = Table(
    "{{ table_name_snake }}",
    metadata,
    Column("{{ id_column }}", String, primary_key=True),
    Column("{{ parent_id_column }}", String, nullable=False),
    Column("{{ tenant_id_column }}", String, primary_key=True),
    Column("{{ additional_column }}", {{ additional_column_type }}, nullable={{ additional_column_nullable }}),
    Column("{{ status_column }}", String, nullable=False),
    ForeignKeyConstraint(
        ["{{ parent_id_column }}", "{{ tenant_id_column }}"],
        ["{{ parent_table }}.{{ parent_id_column_ref }}", "{{ parent_table }}.{{ tenant_id_column }}"],
        ondelete="CASCADE",
    ),
)
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ extras_module }}` | Infrastructure extras module | `infrastructure.extras`, `persistence.extras` |
| `{{ table_name }}` | Table variable name | `order_table`, `profile_table` |
| `{{ table_name_snake }}` | Database table name (snake_case) | `order`, `profile` |
| `{{ id_column }}` | Primary key column name | `id`, `order_id` |
| `{{ tenant_id_column }}` | Tenant ID column name | `tenant_id` |
| `{{ jsonb_column }}` | JSONB column name | `info`, `metadata` |
| `{{ status_column }}` | Status column name | `status` |
| `{{ additional_column }}` | Additional column name | `name`, `description` |
| `{{ additional_column_type }}` | Additional column SQLAlchemy type | `String`, `Integer`, `JSONB` |
| `{{ additional_column_nullable }}` | Additional column nullable flag | `True`, `False` |
| `{{ parent_id_column }}` | Foreign key to parent | `order_id`, `parent_id` |
| `{{ parent_table }}` | Parent table variable | `order_table` |
| `{{ parent_id_column_ref }}` | Parent table ID column reference | `id` |
