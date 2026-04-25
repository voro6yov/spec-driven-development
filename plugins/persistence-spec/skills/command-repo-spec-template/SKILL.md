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

| Component | Attribute | Pattern | Template |
| --- | --- | --- | --- |
| `Abstract\{Context\}UnitOfWork` | `\{aggregate_plural\}: Command\{Aggregate\}Repository` | Abstract Unit of Work | `persistence-spec:unit-of-work` |
| `SqlAlchemy\{Context\}UnitOfWork` | `\{aggregate_plural\}: SqlAlchemyCommand\{Aggregate\}Repository` | SQLAlchemy Unit of Work | `persistence-spec:unit-of-work` |

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
    class \{Aggregate\}Table {
        <<Table>>
        -id: String
    }
```

### Table: `\{table_name\}`

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| `id` | String | PK | Primary identifier |
| {column} | {TYPE} | {constraints} | {description} |

### Indexes

| Index | Columns | Purpose |
| --- | --- | --- |
| `idx_\{table\}_\{column\}` | {column} | {Query optimization purpose} |
