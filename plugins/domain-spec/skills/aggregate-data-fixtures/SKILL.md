---
name: aggregate-data-fixtures
description: Aggregate Data Fixtures pattern for DDD Python testing. Use when writing pytest fixtures for complex aggregates with nested collections, or when deciding whether to create a data fixture vs. a direct aggregate fixture.
user-invocable: false
disable-model-invocation: false
---
## Purpose

- Provide raw data (TypedDict) for **complex** aggregate factory methods.
- Separate large data structures from aggregate construction.
- Enable tests to access expected values without reconstructing domain objects.

## CRITICAL: When to Use Data Fixtures

### USE Data Fixtures When:

- Aggregate has **nested collections** (items, line items, child entities)
- **Large amount of data** is needed (many items, complex structures)
- Same data structure is **reused across multiple aggregate fixtures**
- Testing **factory method validation** that requires specific data

### DO NOT USE Data Fixtures When:

- Aggregate has **only simple attributes** (name, id, status, single values)
- Construction is **straightforward** with few parameters
- **No nested collections** exist

**VIOLATION**: Creating a `{aggregate}_data` fixture for simple aggregates that can be constructed directly.

## Structure

- Implemented as `@pytest.fixture` functions returning a TypedDict.
- Named using pattern `{aggregate}_{n}_data` where `n` is a sequential identifier.
- Contain all required fields for the aggregate's factory method.
- Defined in root `tests/conftest.py` for project-wide availability.

## Behavior Checklist

- Use ONLY for complex aggregates with nested collections.
- Return a complete TypedDict with all required fields populated.
- Use realistic but deterministic values (fixed dates, sequential IDs).
- Include nested collections (items, line items) when present.
- Avoid side effects — data fixtures are pure functions returning dictionaries.

## Scoping Rules

- Use default function scope (new instance per test).
- Never mutate returned data in tests — create a copy if modification is needed.

## Dependencies

- Data fixtures should have no dependencies on other fixtures.
- They represent the "ground truth" for aggregate creation.

## Decision Flowchart

```
Does aggregate have nested collections (items, children)?
├── YES → Create data fixture
└── NO → Does aggregate have many attributes (>5)?
    ├── YES → Consider data fixture for readability
    └── NO → Create aggregate directly in fixture (NO data fixture)
```

## Template

See [template.md](template.md) for the full Python template with Jinja2 placeholders and a placeholders reference table.
