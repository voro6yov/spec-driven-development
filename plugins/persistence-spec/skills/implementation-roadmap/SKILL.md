---
name: implementation-roadmap
description: Persistence Implementation Roadmap — pattern catalog and selection guide for tables, migrations, mappers, command repositories, and context integration. Use when filling Aggregate Analysis or Pattern Selection sections of a command repository spec, or when deciding which persistence pattern fits an aggregate's structure.
user-invocable: false
disable-model-invocation: false
---

# Persistence Implementation Roadmap

Conventions for infrastructure artifacts (unit of work, repositories, mappers, tables, migrations). Assumes the domain model (aggregates, value objects, entities, repository interfaces) is already defined.

## Implementation Order

```
Tables → Migrations → Mappers → Repository → Context Integration
```

Each step depends only on previous steps. When an aggregate owns child entities, maintain **parent → child** order within each step. Testing patterns are out of scope for this roadmap.

---

## Pattern Catalog

### 1. Tables

Define SQLAlchemy Table objects for database schema representation. Order: parent → children.

| Pattern | When to Use |
| --- | --- |
| Simple Table | Single primary key, no children |
| Composite PK Table | Multi-tenant (`id + tenant_id` as PK) |
| Table with FK | Child table referencing parent |

Template skill: `persistence-spec:table-definitions`

### 2. Migrations

Liquibase YAML changesets. Order: parent → child → indexes.

| Pattern | When to Use |
| --- | --- |
| Create Table | New parent table |
| Create Table (Composite PK) | Multi-tenant parent table |
| Add Foreign Key | Child table with FK constraint |
| Add Index | Query optimization |
| Add JSONB Index | JSONB column search optimization |
| Add Column | Extend existing table |
| Add Not Null Constraint | Enforce non-null values |

Template skill: `persistence-spec:migration`

### 3. Mappers

Convert between domain aggregates/value objects and database rows. Order: value objects → child entities → aggregate.

| Pattern | When to Use |
| --- | --- |
| Simple Value Object Mapper | JSONB value objects with datetime |
| Complex Value Object Mapper | Value objects with nested optional fields |
| Value Object with Collection Mapper | Value objects containing collections |
| Child Entity Mapper | Entities in child tables |
| Polymorphic Mapper | Type hierarchies with discriminator |
| Full Aggregate Mapper | Aggregate with status, timestamps, nested data |
| Minimal Aggregate Mapper | Simple aggregate without status/timestamps |
| Aggregate Mapper with Children | Aggregate owning child entities |

Template skill: `persistence-spec:mappers`

### 4. Repository

Implement the domain command repository interface.

| Pattern | When to Use |
| --- | --- |
| Simple Command Repository | Aggregate without children |
| Command Repository with Children | Aggregate with child entities, orphan cleanup |

Alternative lookups: by non-PK field, by JSONB array contains, via child entity.

Template skill: `persistence-spec:command-repository`

### 5. Context Integration (Unit of Work)

| Pattern | When to Use |
| --- | --- |
| Abstract Unit of Work | Define repository attributes, commit/rollback contract |
| SQLAlchemy Unit of Work | Concrete implementation with `DatabaseSession` |

Template skill: `persistence-spec:unit-of-work`

---

## Pattern Selection Guide

Determine the four characteristics of the aggregate, then look up the patterns:

| Characteristic | Detect from package spec | Pattern Implication |
| --- | --- | --- |
| Has child entities? | Aggregate root has `<<Entity>>` collaborators or owns a collection of entities | Table with FK · Aggregate Mapper with Children · Command Repository with Children |
| Multi-tenant? | Aggregate carries `tenant_id` (or equivalent tenant scope field) | Composite PK Table · Create Table (Composite PK) |
| Has JSONB value objects? | Aggregate or entity has non-trivial `<<Value Object>>` collaborators stored inline | Simple / Complex / Collection Value Object Mapper (one per VO) |
| Polymorphic nested data? | Type hierarchy with discriminator among value objects or entities | Polymorphic Mapper |

Defaults when characteristic is absent: Simple Table · Create Table · Minimal or Full Aggregate Mapper · Simple Command Repository.

---

## Pattern Selection Table (per artifact)

Use these rules to fill Section 2 of the command repository spec:

**Tables**
- Parent table → `Composite PK Table` if multi-tenant, else `Simple Table`.
- One `Table with FK` per child entity collection.

**Migrations**
- Parent → `Create Table (Composite PK)` if multi-tenant, else `Create Table`.
- One `Add Foreign Key` per child table.
- `Add Index` per non-PK lookup field implied by the domain repository interface. Identify these by scanning the repository interface for finder methods that are **not** `*_of_id` — e.g. `*_with_*`, `*_by_*`, `find_*` — and indexing the column the lookup parameter maps to.
- `Add JSONB Index` per JSONB column queried by one of those finders.

**Mappers**
- One value object mapper per JSONB value object. Pick the variant by VO shape:
  - `Simple Value Object Mapper` — flat fields, optionally including a datetime.
  - `Complex Value Object Mapper` — has nested optional sub-objects.
  - `Value Object with Collection Mapper` — contains a list/set of inner items.
- One Child Entity Mapper per child entity table.
- Aggregate mapper: `Aggregate Mapper with Children` if children exist, else `Full` (status + timestamps) or `Minimal` (neither).
- Add `Polymorphic Mapper` if a type hierarchy with discriminator is present.

**Repository**
- `Command Repository with Children` if children exist, else `Simple Command Repository`.
- Add Alternative Lookups for each non-`*_of_id` finder declared on the domain interface.

**Context Integration**
- Always pair `Abstract Unit of Work` + `SQLAlchemy Unit of Work`.
- Repository attribute on UoW: `{aggregate_plural}: Command{Aggregate}Repository`. Derive `{aggregate_plural}` from the package spec — prefer an explicit collection name used by the domain (e.g. a repository docstring or aggregate-collection value object); fall back to naive snake_case pluralisation of the aggregate name only when no domain term exists.

---

## Child Entity Ordering

When the aggregate owns child entities, maintain **parent → child** order within each step:

| Step | Without Children | With Children |
| --- | --- | --- |
| Tables | Parent table | Parent table → Child table (FK) |
| Migrations | Single migration | Parent first → Child with FK |
| Mappers | Aggregate mapper | Child mapper → Aggregate mapper |
| Repository | Simple template | With-children template |
