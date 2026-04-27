---
name: persistence-fixtures
description: Persistence Fixtures pattern for integration tests. Use when authoring pytest fixtures that persist aggregates to the database via Unit of Work, including dependency ordering and cleanup.
user-invocable: false
disable-model-invocation: false
---

# Persistence Fixtures

## Purpose

- Store aggregate fixtures in the database for integration tests.
- Establish pre-existing state before test execution.
- Handle dependency ordering (e.g., conveyors before loads with foreign keys).

## Structure

- Implemented as `@pytest.fixture` functions that use Unit of Work.
- Named using pattern `add_{aggregates}` (e.g., `add_loads`, `add_conveyors`).
- Iterate over collection fixtures and save each aggregate.
- Commit transaction after all saves.
- Defined in `tests/integration/conftest.py`.

## Behavior Checklist

- Depend on `unit_of_work` fixture for transactional access.
- Depend on collection fixture for aggregates to persist.
- Depend on related persistence fixtures when foreign keys exist.
- Use `with unit_of_work:` context manager for transaction scope.
- Call `unit_of_work.commit()` after saving all aggregates.
- Use `yield` if cleanup is needed (often delegated to cleanup fixture).

## Scoping Rules

- Use default function scope (fresh data per test).
- Persistence happens within the test's transaction scope.
- Cleanup fixtures handle table truncation before/after tests.

## Dependency Ordering

When aggregates have foreign key relationships:

```python
@pytest.fixture()
def add_conveyors(unit_of_work, test_conveyors):
    with unit_of_work:
        for conveyor in test_conveyors:
            unit_of_work.conveyors.save(conveyor)
        unit_of_work.commit()

@pytest.fixture()
def add_loads(unit_of_work, test_loads, add_conveyors):  # Depends on add_conveyors
    with unit_of_work:
        for load in test_loads:
            unit_of_work.loads.save(load)
        unit_of_work.commit()
        yield
```

## Unit of Work Fixture

Provides access to the transactional boundary:

```python
@pytest.fixture
def unit_of_work(containers):
    return containers.unit_of_work()
```

## Query Repository Fixtures

For read-only queries outside Unit of Work scope:

```python
@pytest.fixture
def query_load_repository(repositories):
    return repositories.query_load()

@pytest.fixture
def query_conveyor_repository(repositories):
    return repositories.query_conveyor()
```

## Cleanup Fixture

Autouse fixture that truncates tables before and after each test:

```python
@pytest.fixture(autouse=True)
def empty_unit_of_work(unit_of_work):
    try:
        with unit_of_work:
            unit_of_work.loads.erase_all()
            unit_of_work.conveyors.erase_all()
            unit_of_work.commit()

        yield

        with unit_of_work:
            unit_of_work.loads.erase_all()
            unit_of_work.conveyors.erase_all()
            unit_of_work.commit()
    except Exception:
        pass
```

---

## Templates

### Persistence Fixture

```python
import pytest

@pytest.fixture()
def add_{{ aggregate_name_plural }}(unit_of_work, test_{{ aggregate_name_plural }}{% if depends_on %}, {{ depends_on }}{% endif %}):
    with unit_of_work:
        for {{ aggregate_name }} in test_{{ aggregate_name_plural }}:
            unit_of_work.{{ repository_name }}.save({{ aggregate_name }})

        unit_of_work.commit()

        yield
```

### Unit of Work Fixture

```python
import pytest

@pytest.fixture
def unit_of_work(containers):
    return containers.unit_of_work()
```

### Query Repository Fixture

```python
import pytest

@pytest.fixture
def query_{{ aggregate_name }}_repository(repositories):
    return repositories.query_{{ aggregate_name }}()
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ aggregate_name_plural }}` | Plural form of aggregate name | `documents`, `loads`, `conveyors` |
| `{{ aggregate_name }}` | Singular form of aggregate name | `document`, `load`, `conveyor` |
| `{{ repository_name }}` | Repository property name on UoW | `documents`, `loads`, `conveyors` |
| `{{ depends_on }}` | Optional dependency fixture name | `add_conveyors` |
