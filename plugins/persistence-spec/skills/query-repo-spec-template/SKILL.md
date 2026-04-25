---
name: query-repo-spec-template
description: Query Repository Spec Template for persistence. Use when writing or filling in a persistence spec for a new aggregate's read side — covers DTO definitions, mapper selection, and query repository method specifications.
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

---

## 3. DTO Specifications

### `\{Aggregate\}Info`

**Purpose**: Single entity read model for API responses

```python
class {Aggregate}Info(TypedDict):
    id: str
    tenant_id: str
    # {additional fields from schema}
    created_at: str
    updated_at: str
```

**Field Mapping** *(from Command Persistence Spec schema)*:

| DTO Field | Table Column | Transformation |
| --- | --- | --- |
| `id` | `id` | Direct |
| `tenant_id` | `tenant_id` | Direct |
| {field} | {column} | {transformation or Direct} |

### `\{Aggregate\}ListResult`

**Purpose**: Paginated list response with metadata

```python
class {Aggregate}ListResult(TypedDict):
    items: list[{Aggregate}Info]
    total: int
    page: int
    per_page: int
```

### `\{Aggregate\}Filtering` *(if filtering required)*

**Purpose**: Filter criteria for list queries

```python
@dataclass
class {Aggregate}Filtering:
    {filter_field}: {type} | None = None
    # {additional filter fields}
```

**Supported Filters**:

| Filter Field | Column | Operator | Notes |
| --- | --- | --- | --- |
| {field} | {column} | `=` / `LIKE` / `IN` | {notes} |

---

## 4. Repository Method Specifications

### `find_{aggregate}(id: str, tenant_id: str) -> {Aggregate}Info | None`

**Purpose**: Retrieve single {Aggregate} as DTO by ID

**Preconditions**:

- `id` and `tenant_id` must be valid UUID strings

**Method Flow**:

1. Query {table} by `id` and `tenant_id`
2. If not found, return `None`
3. Map row to `\{Aggregate\}Info` DTO using mapper
4. Return DTO

**Postconditions**:

- If found: `\{Aggregate\}Info` DTO returned
- If not found: `None` returned

**Index Used**: Primary key index

---

### `find_{aggregates}(tenant_id: str, filtering: {Aggregate}Filtering | None, pagination: Pagination | None) -> {Aggregate}ListResult`

**Purpose**: Retrieve paginated list of {Aggregate} DTOs with optional filtering

**Preconditions**:

- `tenant_id` must be valid UUID string
- `pagination.page` >= 1 if provided
- `pagination.per_page` >= 1 if provided

**Method Flow**:

1. Build base query selecting from {table} where `tenant_id` matches
2. Apply filtering via `_apply_filtering()` if provided
3. Apply sorting via `_apply_sorting()` if provided
4. Execute count query for total
5. Apply pagination via `_apply_pagination()` if provided
6. Execute query and map rows to `\{Aggregate\}Info` DTOs
7. Return `\{Aggregate\}ListResult` with items, total, page, per_page

**Postconditions**:

- Returns `\{Aggregate\}ListResult` (may have empty `items` list)
- `total` reflects count before pagination

**Indexes Used**: {list relevant indexes from Command Persistence Spec}

---

### Helper Methods

#### `_apply_filtering(query: Query, filtering: {Aggregate}Filtering) -> Query`

**Logic**:

```python
if filtering.{field} is not None:
    query = query.where(table.c.{column} == filtering.{field})
# ... additional filters
return query
```

#### `_apply_sorting(query: Query, sorting: {Aggregate}Sorting) -> Query`

**Logic**:

```python
column = {
    {Aggregate}Sorting.CREATED_AT: table.c.created_at,
    # ... additional sort fields
}[sorting.field]
order = column.desc() if sorting.order == SortOrder.DESC else column.asc()
return query.order_by(order)
```

#### `_apply_pagination(query: Query, pagination: Pagination) -> Query`

**Logic**:

```python
offset = (pagination.page - 1) * pagination.per_page
return query.limit(pagination.per_page).offset(offset)
```

---

## 5. Deferred Decisions

| Decision | Status | Depends On |
| --- | --- | --- |
| {Decision topic} | ⏸️ Deferred | {Dependency} |

---

## 6. References

- **Command Persistence Spec**: {link to Command Repository Persistence Spec}
- **Domain Model**: {link to bounded context}
- **Aggregate Spec**: {link to package spec}
- **Pattern Library**: `persistence-spec:query-repository`
