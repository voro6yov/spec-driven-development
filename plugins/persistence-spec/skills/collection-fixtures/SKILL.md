---
name: collection-fixtures
description: Collection Fixtures pattern for aggregating multiple individual aggregate fixtures into a list for bulk persistence operations and integration tests. Use when defining project-wide test data collections in tests/conftest.py that bundle per-aggregate fixtures.
user-invocable: false
disable-model-invocation: false
---

# Collection Fixtures

## Purpose

- Aggregate multiple individual fixtures into a list for bulk operations.
- Enable persistence fixtures to store all test aggregates in a single operation.
- Provide a canonical set of test data for comprehensive integration tests.

## Structure

- Implemented as `@pytest.fixture` functions that depend on multiple aggregate fixtures.
- Named using pattern `test_{aggregates}` (plural form of aggregate name).
- Return a list containing all requested fixture instances.
- Defined in root `tests/conftest.py` for project-wide availability.

## Behavior Checklist

- List all individual fixtures as function parameters (explicit dependencies).
- Return aggregates as a simple Python list.
- Include aggregates covering different states and scenarios.
- Order may be significant if tests rely on iteration order.

## Scoping Rules

- Use default function scope (new list per test).
- Collection is recreated for each test, containing fresh aggregate instances.
- Never use session scope since contained aggregates are function-scoped.

## Dependencies

- Depends on all individual aggregate fixtures listed in parameters.
- Pytest resolves the dependency graph and creates each aggregate first.

## Example

```python
@pytest.fixture
def test_loads(
    load_1,
    load_2,
    load_3,
    load_4,
    load_5,
    load_6,
    load_7,
    load_9,
    load_10,
    load_11,
    load_12,
    load_13,
):
    return [
        load_1,
        load_2,
        load_3,
        load_4,
        load_5,
        load_6,
        load_7,
        load_9,
        load_10,
        load_11,
        load_12,
        load_13,
    ]

@pytest.fixture
def test_conveyors(conveyor_1, conveyor_2, conveyor_4, conveyor_5):
    return [conveyor_1, conveyor_2, conveyor_4, conveyor_5]
```

## Adding New Aggregates

When adding a new aggregate fixture:

1. Create the aggregate fixture (`load_N`).
2. Add the aggregate fixture to the collection's parameters.
3. Add the aggregate to the returned list.

```python
# Before: 12 loads
@pytest.fixture
def test_loads(load_1, load_2, ..., load_12):
    return [load_1, load_2, ..., load_12]

# After: 13 loads
@pytest.fixture
def test_loads(load_1, load_2, ..., load_12, load_13):
    return [load_1, load_2, ..., load_12, load_13]
```

---

## Template

```python
import pytest

@pytest.fixture
def test_{{ aggregate_name_plural }}(
    {% for fixture in fixtures -%}
    {{ fixture }},
    {% endfor -%}
):
    return [
        {% for fixture in fixtures -%}
        {{ fixture }},
        {% endfor -%}
    ]
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ aggregate_name_plural }}` | Plural form of aggregate name | `documents`, `loads`, `conveyors` |
| `{{ fixtures }}` | List of individual fixture names | `["load_1", "load_2", "load_3"]` |
