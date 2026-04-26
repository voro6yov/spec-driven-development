---
name: query-repo-spec-template
description: Query Repository Spec Template for persistence. Use when writing or filling in a persistence spec for a new aggregate's read side — covers query context analysis and pattern selection only. DTOs come from the source class diagram and method bodies are encoded in the query-repository skill.
user-invocable: false
disable-model-invocation: false
---

# Query Repository Spec Template

## 1. Query Context Analysis

### Purpose

{Brief description of what read operations this query repository supports}

### Schema Reference

| Source | Reference |
| --- | --- |
| Command Persistence Spec | {Link to Command Repository Persistence Spec} |
| Primary Table | `\{table_name\}` |
| Child Tables | {List or None} |

### Query Requirements

| Requirement | Value | Pattern Implication |
| --- | --- | --- |
| Single Entity Lookup | Yes / No | `find_{aggregate}()` method |
| Paginated List | Yes / No | `find_{aggregates}()` method |
| Filtering Support | {List fields or None} | Filtering DTO + `_apply_filtering()` |
| Sorting Support | {List fields or None} | Sorting enum + `_apply_sorting()` |
| Analytics/Aggregations | Yes / No | `get_analytics()` method |
| Multi-tenant | Yes / No | All queries scoped by `tenant_id` |

### Implementation

| Field | Value |
| --- | --- |
| Package | `\{src/path/to/aggregate\}` |
| Import path | `\{import.path.to.aggregate\}` |

---

## 2. Pattern Selection

### DTOs

| DTO | Purpose | Template |
| --- | --- | --- |
| `\{Aggregate\}Info` | Single entity response | `persistence-spec:persistence-dtos` |
| `\{Aggregate\}ListResult` | Paginated list response | `persistence-spec:persistence-dtos` |
| `\{Aggregate\}Filtering` | Filter criteria | `persistence-spec:persistence-dtos` |

### Mappers

| Mapper | Pattern | Template |
| --- | --- | --- |
| `\{Aggregate\}InfoMapper` | DTO Mapper | `persistence-spec:mappers` |

### Repository

| Repository | Pattern | Template |
| --- | --- | --- |
| `Query\{Aggregate\}Repository` | Query Repository | `persistence-spec:query-repository` |

### Context Integration

| Component | Attribute | Pattern | Template |
| --- | --- | --- | --- |
| `Abstract\{Context\}QueryContext` | `\{aggregate_plural\}: Query\{Aggregate\}Repository` | Abstract Query Context | `persistence-spec:query-context` |
| `SqlAlchemy\{Context\}QueryContext` | `\{aggregate_plural\}: SqlAlchemyQuery\{Aggregate\}Repository` | SQLAlchemy Query Context | `persistence-spec:query-context` |
