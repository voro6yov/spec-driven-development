---
name: aggregate-fixtures
description: Aggregate Fixtures pattern for DDD Python testing. Use when writing pytest aggregate fixtures, applying state mutations to reach specific lifecycle states, deciding between simple vs. mutated fixture variants, or structuring conftest.py for unit/integration/application test reuse.
user-invocable: false
disable-model-invocation: false
---

# Aggregate Fixtures

## Purpose

- Create fully-constructed domain aggregates ready for use in tests.
- Apply state mutations to create aggregates in specific lifecycle states.
- Provide domain objects that can be persisted or used in unit tests.

## CRITICAL: Placement Rule

**ALL aggregate fixtures MUST be defined in root `tests/conftest.py`.**

This is mandatory because:

- Unit tests use these fixtures for domain logic testing
- Integration tests reuse the same fixtures for persistence testing
- Application tests reuse them for service testing

```
tests/
├── conftest.py          ← ALL aggregate fixtures go here
├── unit/
│   └── domain/
│       └── load/
│           └── test_load.py     ← uses load_1 from root conftest
└── integration/
    └── repositories/
        └── test_load_repository.py  ← reuses same load_1 fixture
```

**VIOLATION**: Creating aggregate fixtures in test modules or subdirectory conftest files.

## When Data Fixtures Are Required vs Optional

For the full data fixture decision rules, see the **aggregate-data-fixtures** skill.

### Data Fixture REQUIRED (Complex Aggregates)

Use a separate data fixture when:

- Aggregate has nested collections (items, line items, child entities)
- Large amount of data is needed (e.g., 100 items)
- Same data structure is reused across multiple aggregate fixtures

```python
# Data fixture needed - complex structure with items
@pytest.fixture
def load_1_data() -> LoadData:
    return {
        "id": "load-001",
        "items": [
            {"item_number": "ITEM-001", "quantity": 50},
            {"item_number": "ITEM-002", "quantity": 50},
        ],
    }

@pytest.fixture
def load_1(load_1_data):
    return Load.from_load_data(DEFAULT_WAREHOUSE_ID, "conveyor-001", load_1_data)
```

### Data Fixture NOT NEEDED (Simple Aggregates)

Skip data fixture when:

- Aggregate has only simple attributes (name, id, status)
- Construction is straightforward with few parameters
- No nested collections

```python
# NO data fixture needed - simple construction
@pytest.fixture
def conveyor_1():
    return Conveyor.new(
        warehouse_id=DEFAULT_WAREHOUSE_ID,
        conveyor_id="conveyor-001",
        name="Main Conveyor",
    )

@pytest.fixture
def user_1():
    return User.new(user_id="user-001", name="John Doe", role="operator")
```

## Structure

- Implemented as `@pytest.fixture` functions.
- Named using pattern `{aggregate}_{n}` (e.g., `load_1`, `conveyor_2`).
- Call aggregate factory methods (`new`, `from_data`, etc.).
- May apply additional mutations to reach desired state.

## Behavior Checklist

- Place in root `tests/conftest.py` (MANDATORY).
- Use data fixture ONLY for complex aggregates with collections.
- Call aggregate's public factory method with appropriate parameters.
- Apply state mutations using public methods only (never set private attributes).
- Add docstring when fixture creates non-obvious state (e.g., "paused receiving").

## Fixture Variants

### Simple Aggregate (No Data Fixture)

```python
@pytest.fixture
def conveyor_1():
    return Conveyor.new(
        warehouse_id=DEFAULT_WAREHOUSE_ID,
        conveyor_id="conveyor-001",
        name="Inbound Conveyor",
    )
```

### Aggregate from Data Fixture (Complex)

```python
@pytest.fixture
def load_1(load_1_data):
    return Load.from_load_data(DEFAULT_WAREHOUSE_ID, "conveyor-002", load_1_data)
```

### Aggregate with Mutations

```python
@pytest.fixture
def load_2(load_1_data):
    """Load in receiving state"""
    load = Load.from_load_data(DEFAULT_WAREHOUSE_ID, "conveyor-002", load_1_data)
    load.start_receiving()
    load.clear_events()
    return load
```

## Scoping Rules

- Use default function scope (new instance per test).
- Each test gets a fresh aggregate to prevent cross-test contamination.
- Session scope should never be used for mutable domain objects.

## Fixture Naming Convention

**Use numbered fixtures for all aggregate states. Document the state in a docstring.**

### Naming Pattern

```
{aggregate}_{n}
```

| Pattern | Use Case | Example |
| --- | --- | --- |
| `{aggregate}_{n}` | Any aggregate fixture (initial or mutated state) | `load_1`, `load_2`, `profile_1`, `profile_2` |

### When to Create Additional Fixtures

```
Do multiple tests need an aggregate in state X?
├── YES → Create {aggregate}_{n} fixture with mutations + docstring
└── NO → Is the setup complex (multiple mutations)?
    ├── YES → Create fixture anyway (clarity)
    └── NO → Consider inline setup (rare)
```

### Fixture Examples

```python
# Initial state
@pytest.fixture
def load_1(load_1_data):
    """Load in initial pending state"""
    load = Load.from_load_data(DEFAULT_WAREHOUSE_ID, "conveyor-001", load_1_data)
    load.clear_events()
    return load

# Different state - use next number, document in docstring
@pytest.fixture
def load_2(load_1_data):
    """Load in receiving state"""
    load = Load.from_load_data(DEFAULT_WAREHOUSE_ID, "conveyor-001", load_1_data)
    load.start_receiving()
    load.clear_events()
    return load

@pytest.fixture
def load_3(load_1_data):
    """Load in completed state"""
    load = Load.from_load_data(DEFAULT_WAREHOUSE_ID, "conveyor-001", load_1_data)
    load.start_receiving()
    load.complete_receiving()
    load.clear_events()
    return load
```

### Fixture Selection Guide

| Test Action | Required Fixture |
| --- | --- |
| `start_receiving()` | `load_1` (pending state) |
| `pause_receiving()` | `load_2` (receiving state) |
| `complete_receiving()` | `load_2` (receiving state) |
| Test "already completed" error | `load_3` (completed state) |

## State Mutation Guidelines

When creating fixtures for specific states:

1. Always use public methods for state transitions.
2. Follow the aggregate's natural lifecycle order.
3. Document the final state in a docstring.
4. **Clear events after setup mutations** (see **aggregate-unit-tests** skill, RULE 5).
5. Name the fixture to indicate the state.

## Template

See [template.md](template.md) for full Python templates with Jinja2 placeholders and a placeholders reference table.
