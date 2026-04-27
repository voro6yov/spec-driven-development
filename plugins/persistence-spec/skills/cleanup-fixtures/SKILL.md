---
name: cleanup-fixtures
description: Cleanup Fixtures pattern for integration test database isolation. Use when authoring autouse pytest fixtures that truncate repository tables before and after each test to guarantee clean state.
user-invocable: false
disable-model-invocation: false
---

# Cleanup Fixtures

## Purpose

- Ensure database state is clean before and after each test.
- Prevent test pollution from leftover data in previous tests.
- Provide isolation guarantees for integration tests.

## Structure

- Implemented as `@pytest.fixture(autouse=True)` to run automatically.
- Named using pattern `empty_{resource}` (e.g., `empty_unit_of_work`).
- Truncate relevant tables before yielding to test.
- Truncate again after test completes (in finally/teardown block).
- Defined in `tests/integration/conftest.py`.

## Behavior Checklist

- Use `autouse=True` to run for every test in scope.
- Depend on `unit_of_work` fixture for database access.
- Clear all tables that tests might populate.
- Handle exceptions gracefully to avoid masking test failures.
- Use try/except to ensure cleanup doesn't break test reporting.

## Scoping Rules

- Use default function scope for per-test cleanup.
- Cleanup runs before and after each test function.
- Order of operations: cleanup → fixtures → test → cleanup.

## Dependencies

- Depends on `unit_of_work` fixture for transactional access.
- Should be one of the first fixtures resolved due to autouse.

## Example

```python
@pytest.fixture(autouse=True)
def empty_unit_of_work(unit_of_work):
    try:
        with unit_of_work:
            unit_of_work.loads.erase_all()
            unit_of_work.conveyors.erase_all()
            unit_of_work.commit()
    except Exception:
        pass

    yield

    try:
        with unit_of_work:
            unit_of_work.loads.erase_all()
            unit_of_work.conveyors.erase_all()
            unit_of_work.commit()
    except Exception:
        pass
```

The `yield` MUST sit between two independent `try/except` blocks. Wrapping the `yield` inside a single `try/except Exception: pass` would silently swallow exceptions raised by the test body itself.

## Repository Method Requirements

Command repositories should implement an `erase_all()` method:

```python
class UowCommandLoadRepository(ICommandLoadRepository):
    def erase_all(self) -> None:
        self._session.execute(delete(LoadOrm))
```

---

## Template

```python
import pytest

@pytest.fixture(autouse=True)
def empty_unit_of_work(unit_of_work):
    try:
        with unit_of_work:
            {% for repository in repositories -%}
            unit_of_work.{{ repository }}.erase_all()
            {% endfor -%}
            unit_of_work.commit()
    except Exception:
        pass

    yield

    try:
        with unit_of_work:
            {% for repository in repositories -%}
            unit_of_work.{{ repository }}.erase_all()
            {% endfor -%}
            unit_of_work.commit()
    except Exception:
        pass
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ repositories }}` | List of repository property names | `["loads", "conveyors", "documents"]` |
