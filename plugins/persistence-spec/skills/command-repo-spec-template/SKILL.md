---
name: command-repo-spec-template
description: Command Repository Spec Template for persistence. Use when writing or filling in a persistence spec for a new aggregate — covers pattern selection, schema, and repository method specifications.
user-invocable: false
disable-model-invocation: false
---

# Command Repository Spec Template

## 1. Aggregate Analysis

### Purpose

{Brief description of what this persistence spec covers}

### Aggregate Summary

| Characteristic | Value | Pattern Implication |
| --- | --- | --- |
| Aggregate Root | {AggregateName} | — |
| Has Child Entities? | Yes / No | {e.g., Table with FK, Repository with Children} |
| Multi-tenant? | Yes / No | {e.g., Composite PK Table} |
| JSONB Value Objects | {List or None} | {e.g., Value Object Mapper for each} |
| Polymorphic Data? | Yes / No | {e.g., Polymorphic Mapper} |

---

## 2. Pattern Selection

### Tables

| Table | Pattern | Template |
| --- | --- | --- |
| `\{table_name\}` | {Simple Table / Composite PK Table} | `persistence-spec:table-definitions` |
| `\{child_table_name\}` | Table with FK | `persistence-spec:table-definitions` |

### Migrations

| Changeset | Pattern | Template |
| --- | --- | --- |
| Create `\{table_name\}` | {Create Table / Create Table (Composite PK)} | `persistence-spec:migration` |
| Create `\{child_table_name\}` | Add Foreign Key | `persistence-spec:migration` |
| Indexes | {Add Index / Add JSONB Index} | `persistence-spec:migration` |

### Mappers

| Mapper | Pattern | Template |
| --- | --- | --- |
| `\{ValueObject\}Mapper` | {Simple / Complex / Collection} Value Object Mapper | `persistence-spec:mappers` |
| `\{ChildEntity\}Mapper` | Child Entity Mapper | `persistence-spec:mappers` |
| `\{Aggregate\}Mapper` | {Full / Minimal / With Children} Aggregate Mapper | `persistence-spec:mappers` |

### Repository

| Repository | Pattern | Template |
| --- | --- | --- |
| `Command\{Aggregate\}Repository` | {Simple / With Children} Command Repository | `persistence-spec:command-repository` |

**Alternative Lookups** *(if needed)*:

- {e.g., Lookup by JSONB array contains}
- {e.g., Lookup via child entity}

### Context Integration

| Component | Pattern | Template |
| --- | --- | --- |
| `Abstract\{Context\}UnitOfWork` | Abstract Unit of Work | `persistence-spec:unit-of-work` |
| `SqlAlchemy\{Context\}UnitOfWork` | SQLAlchemy Unit of Work | `persistence-spec:unit-of-work` |

---

## 3. Schema Specification

### Entity Relationship

```mermaid
---
title: {Domain} Storage Model
config:
    class:
        hideEmptyMembersBox: true
---

classDiagram
    class AggregateTable {
        <<Table>>
        -id: UUID
        -tenant_id: UUID
    }
    
    class ChildTable {
        <<Table>>
        -id: UUID
        -parent_id: UUID
    }
    
    AggregateTable "1" --* "0..n" ChildTable : owns
```

### Table: `\{table_name\}`

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | UUID | PK | Primary identifier |
| `tenant_id` | UUID | NOT NULL | Tenant scope |
| {column} | {TYPE} | {constraints} | {description} |

### Table: `\{child_table_name\}` *(if applicable)*

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | UUID | PK | Child identifier |
| `\{parent\}_id` | UUID | FK, NOT NULL | Parent reference |
| `tenant_id` | UUID | NOT NULL | Tenant scope (denormalized) |

### Indexes

| Index | Columns | Purpose |
| --- | --- | --- |
| `idx_\{table\}_\{column\}` | {column}, tenant_id | {Query optimization purpose} |

---

## 4. Repository Method Specifications

### `\{aggregate\}_of_id(id: str, tenant_id: str) -> \{Aggregate\} | None`

**Purpose**: Retrieve {Aggregate} aggregate by ID {with/without loading related data}

**Preconditions**:

- `id` and `tenant_id` must be valid UUID strings

**Method Flow**:

1. Query {Aggregate} record by `id` and `tenant_id`
2. If not found, return `None`
3. {Additional loading steps if needed}
4. Map row data to {Aggregate} aggregate using mapper
5. Return {Aggregate} aggregate

**Postconditions**:

- If found: {Aggregate} returned {with specific state}
- If not found: `None` returned

**Error Handling**:

- Database error → `PersistenceError`

---

### `\{aggregate\}_with_\{lookup\}(\{lookup\}_id: str, tenant_id: str) -> \{Aggregate\} | None` *(if needed)*

**Purpose**: Retrieve {Aggregate} aggregate by {lookup} reference

**Preconditions**:

- `\{lookup\}_id` and `tenant_id` must be valid UUID strings

**Method Flow**:

1. Query {child/related} record by `\{lookup\}_id` and `tenant_id`
2. If not found, return `None`
3. Extract `\{aggregate\}_id` from found record
4. Delegate to `\{aggregate\}_of_id(\{aggregate\}_id, tenant_id)`
5. Return {Aggregate} aggregate

**Postconditions**:

- If found: {Aggregate} returned with fully hydrated state
- If not found: `None` returned

**Implementation Notes**:

- Uses index `idx_\{table\}_\{lookup\}_id` for efficient lookup
- Useful for event handlers receiving `\{lookup\}_id` from domain events

---

### `save(\{aggregate\}: \{Aggregate\}) -> None`

**Purpose**: Persist {Aggregate} aggregate {with child entities}

**Preconditions**:

- `\{aggregate\}` must be a valid {Aggregate} aggregate with `id` and `tenant_id`

**Method Flow**:

1. Map {Aggregate} aggregate to persistence format using mapper
2. Upsert {Aggregate} record
3. {Handle child entities if applicable}
4. {Handle orphan removal if applicable}
5. Commit transaction

**Postconditions**:

- {Aggregate} record persisted
- {Child records persisted/updated}
- {Orphaned records removed if applicable}

**Error Handling**:

- Unique constraint violation → `Duplicate\{Aggregate\}Error`
- Database error → `PersistenceError`

---

### `save_all(\{aggregates\}: list[\{Aggregate\}]) -> None` *(if batch operations needed)*

**Purpose**: Batch persist multiple {Aggregate} aggregates in a single transaction

**Preconditions**:

- All aggregates must have valid `id` and `tenant_id`
- List should not exceed batch size limit (configurable, default 100)

**Method Flow**:

1. Begin transaction
2. For each aggregate:
    - Serialize to persistence format
    - Add to batch upsert operation
3. Execute batch upsert
4. Commit transaction

**Postconditions**:

- All {Aggregate} records persisted atomically
- `updated_at` timestamps refreshed

---

### `delete(\{aggregate\}: \{Aggregate\}) -> None`

**Purpose**: Hard delete a persisted {Aggregate} aggregate

**Preconditions**:

- `\{aggregate\}.id` and `\{aggregate\}.tenant_id` are valid UUID strings

**Method Flow**:

1. Delete {Aggregate} record
2. {Child records cascade-deleted automatically / explicit child deletion}
3. Do not create tombstones or soft-delete flags

**Postconditions**:

- {Aggregate} record removed
- Associated child records removed

**Error Handling**:

- Database error → `PersistenceError`

**Notes**:

- {External cleanup notes, e.g., S3 files handled separately}

---

## 5. Deferred Decisions

| Decision | Status | Depends On |
| --- | --- | --- |
| {Decision topic} | ⏸️ Deferred | {Dependency} |

---

## 6. References

- **Domain Model**: {link to bounded context}
- **Aggregate Spec**: {link to package spec}
