---
name: queries-specification-template
description: Queries Specification Template pattern for application-layer query services. Use when documenting a Queries application service (read-side) with DTOs, settings, sorting, optional external interfaces, and method specifications.
user-invocable: false
disable-model-invocation: false
---

# Queries Specification Template

This template provides a standardized structure for documenting Queries Application Service specifications. Generate specifications section-by-section by applying the referenced pattern skills.

---

## Section 1: Service Architecture

**Pattern Reference**: `application-spec:queries-pattern`

### Diagram

```mermaid
---
title: {ServiceName} Domain Model (Application - Queries)
config:
    class:
        hideEmptyMembersBox: true
---

classDiagram
	class {ServiceName}Queries {
			<<Application>>
			-query_repository: Query{Aggregate}Repository
			-settings: {Aggregate}QueriesSettings
			+find_{aggregate}(id, tenant_id) dict
			+find_{aggregates}(pagination, filters, sorting) dict
	}
	
	{ServiceName}Queries --() Query{Aggregate}Repository : uses
	{ServiceName}Queries --() {Aggregate}QueriesSettings : uses
```

## {ServiceName}Queries Application Service Specification

The `{ServiceName}Queries` application service handles read operations for the `{Aggregate}` domain by coordinating between query repositories, optional external interfaces, and settings. It returns TypedDict DTOs rather than domain aggregates, maintaining separation between read models and domain objects.

**Responsibilities**:

- Single entity retrieval via `find_{aggregate}()`
- Paginated list retrieval via `find_{aggregates}()`
- Apply default pagination/sorting from settings when parameters are None
- Raise domain exceptions when entities are not found

---

## Section 2: DTOs (Optional)

**Pattern Reference**: `application-spec:queries-pattern`

**When to include**: DTOs not already defined in domain layer

**Skip if**: Domain layer already provides the required DTOs

### Brief Info DTO: `Brief{Aggregate}Info`

**Purpose**: Represents a single item in list results

```python
class Brief{Aggregate}Info(TypedDict):
    id: str
    tenant_id: str
    # Add domain-specific fields
    status: str
    created_at: str
```

### Metadata DTO: `{Aggregate}sMetadataInfo`

**Purpose**: Pagination metadata for list results

```python
class {Aggregate}sMetadataInfo(TypedDict):
    page: int
    per_page: int
    total: int
    total_pages: int
```

### Main Info DTO: `{Aggregate}sInfo`

**Purpose**: Combined list + metadata for paginated results

```python
class {Aggregate}sInfo(TypedDict):
    {aggregates}: list[Brief{Aggregate}Info]
    metadata: {Aggregate}sMetadataInfo
```

### Detail DTO: `{Aggregate}Info` (Optional)

**Purpose**: Full detail for single entity retrieval (if different from Brief)

```python
class {Aggregate}Info(TypedDict):
    id: str
    tenant_id: str
    # All fields needed for detail view
```

**Implementation Location**: `application/{context}/{aggregate}_dtos.py` or `domain/{aggregate}/dtos.py`

---

## Section 3: Settings

**Pattern Reference**: `application-spec:settings`

**Always required** - Provides defaults for pagination and other query parameters.

### Settings Class: `{Aggregate}QueriesSettings`

```python
from pydantic_settings import BaseSettings

class PaginationSettings(BaseSettings):
    default_per_page: int = 10
    default_page: int = 0

class {Aggregate}QueriesSettings(BaseSettings):
    pagination: PaginationSettings = PaginationSettings()
```

**Implementation Location**: `application/{context}/{aggregate}_queries_settings.py`

**Configuration Notes**:

- Default values should work for development environment
- Can be overridden via environment variables

---

## Section 4: Sorting (Optional)

**Pattern Reference**: `application-spec:sorting`

**When to include**: Query results need sorting options

**Skip if**: No sorting requirements

### Sorting Enums

```python
from enum import Enum

class SortOrder(Enum):
    ASC = "asc"
    DESC = "desc"

class {Aggregate}Sorting(Enum):
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    # Add domain-specific sortable fields
```

**Implementation Location**: `application/{context}/{aggregate}_sorting.py`

**Notes**:

- Enum values must match database/API field names
- Keep enum member names in UPPER_CASE

---

## Section 5: External Interfaces (Optional)

**Pattern Reference**: `application-spec:interfaces`

**When to include**: Complex queries spanning multiple data sources

**Skip if**: Simple queries using single repository

### Interface: `ICanQuery{Aggregates}`

**Purpose**: [Protocol interface for complex query operations]

**Methods**:

```python
class ICanQuery{Aggregates}(Protocol):
    def find_with_details(self, id: str, tenant_id: str) -> {Aggregate}DetailInfo:
        """[Method description]"""
        ...
```

**Implementation Location**: `application/{context}/i_can_query_{aggregates}.py`

**Notes**:

- [When this interface is needed]
- [Expected implementations]

---

## Section 6: Method Specifications

**Pattern Reference**: `application-spec:queries-pattern`

### Method: `find_{aggregate}(id: str, tenant_id: str) -> dict[str, Any]`

**Purpose**: Retrieve a single {Aggregate} by ID

**Preconditions**:

- `id` must be a valid UUID string (non-empty)
- `tenant_id` must be a valid UUID string (non-empty)

**Dependencies**:

- `query_repository: Query{Aggregate}Repository`

**Method Flow**:

1. Call `query_repository.find_one(id, tenant_id)` to retrieve entity
2. If not found, raise `{Aggregate}NotFound` exception
3. Return the DTO result

**Postconditions**:

- Returns `{Aggregate}Info` TypedDict with entity data
- Raises `{Aggregate}NotFound` if entity does not exist

**Error Handling**:

- If entity not found: raise `{Aggregate}NotFoundError`
- Infrastructure errors propagated to caller

---

### Method: `find_{aggregates}(pagination: Pagination | None, filters: Filters | None, sorting: Sorting | None) -> dict[str, Any]`

**Purpose**: Retrieve paginated list of {Aggregates} with optional filtering and sorting

**Preconditions**:

- `pagination` can be None (defaults applied from settings)
- `filters` can be None (no filtering)
- `sorting` can be None (default sort order)

**Dependencies**:

- `query_repository: Query{Aggregate}Repository`
- `settings: {Aggregate}QueriesSettings`

**Method Flow**:

1. Apply default pagination from settings if `pagination` is None
2. Apply default sorting if `sorting` is None (if applicable)
3. Call `query_repository.find_many(pagination, filters, sorting)`
4. Return the `{Aggregates}Info` DTO with items and metadata

**Postconditions**:

- Returns `{Aggregates}Info` TypedDict with list and pagination metadata
- Empty list returned if no matches (not an error)

**Error Handling**:

- Invalid filter values: raise appropriate validation error
- Infrastructure errors propagated to caller

**Implementation Notes**:

- Always apply settings defaults for None parameters
- Log query parameters for debugging

---

## Section 7: Dependency Injection

**Pattern Reference**: `application-spec:dependency-injection-patterns` → Container Provider Template

**Dependencies to wire**:

- `query_repository: Query{Aggregate}Repository`
- `settings: {Aggregate}QueriesSettings`
- [External interfaces from Section 5, if any]

---

## General Implementation Guidelines

### DTO vs Domain Aggregate

| Aspect | Domain Aggregate | Query DTO |
| --- | --- | --- |
| Used by | Commands (write operations) | Queries (read operations) |
| Contains | Business logic, invariants | Data only, no behavior |
| Structure | Domain model classes | TypedDict |
| Purpose | Enforce domain rules | Transfer data to API layer |

### Settings Application

- Always check if parameter is None before using
- Apply defaults from settings, not hardcoded values
- Log when defaults are applied for debugging

### Query Repository vs Command Repository

| Aspect | Command Repository | Query Repository |
| --- | --- | --- |
| Returns | Domain aggregates | TypedDict DTOs |
| Operations | save, delete, lookup by ID | find_one, find_many with filters |
| Used by | Commands service | Queries service |

### Testing Considerations

- Integration tests for query results matching expected DTO shapes
- Test pagination with various page sizes and page numbers
- Test sorting in both ASC and DESC orders
- Test filter combinations
- Test empty result sets (should not throw)
- Test not found scenarios (should throw)
- Use fakes for query repositories

---

> **Note**: [Add any domain-specific notes or cross-references to related bounded contexts here]
>
