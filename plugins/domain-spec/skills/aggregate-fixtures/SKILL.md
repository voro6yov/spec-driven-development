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

## Aggregate Archetypes

Different aggregates need different fixture strategies. Identify the archetype first.

| Archetype | Characteristics | Fixture strategy |
|-----------|----------------|-----------------|
| **Status-machine** | Has a Status value object; methods transition between named statuses | One fixture per reachable status, built by applying transitions in order |
| **CRUD-collection** | Has multiple independent collection value objects; methods are `add_*`/`update_*`/`delete_*` | One fixture per collection group + fully populated fixture |
| **Hybrid** | Both status transitions and collection CRUD | Status fixtures first, then collection variants within relevant statuses |

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

### Status-Machine Aggregate with Mutations

```python
@pytest.fixture
def load_2(load_1_data):
    """Load in receiving state"""
    load = Load.from_load_data(DEFAULT_WAREHOUSE_ID, "conveyor-002", load_1_data)
    load.start_receiving()
    load.clear_events()
    return load
```

### CRUD-Collection Aggregate — Per-Collection Fixtures

For aggregates with multiple independent collections, create one fixture per collection group so tests can target each area independently:

```python
@pytest.fixture
def profile_type_1():
    """ProfileType in initial state — all collections empty."""
    profile_type = ProfileType.new(
        tenant_id=DEFAULT_TENANT_ID,
        name="Individual Profile",
        description="Profile type for individual clients",
        subject_kind="Individual",
    )
    profile_type.clear_events()
    return profile_type


@pytest.fixture
def profile_type_2():
    """ProfileType with two fields (enough for update/delete testing)."""
    profile_type = ProfileType.new(
        tenant_id=DEFAULT_TENANT_ID,
        name="Individual Profile",
        description="Profile type for individual clients",
        subject_kind="Individual",
    )
    profile_type.add_field(
        name="Full Name",
        description="The full legal name",
        required=True,
        is_collection=False,
    )
    profile_type.add_field(
        name="Date of Birth",
        description="Date of birth",
        required=True,
        is_collection=False,
    )
    profile_type.clear_events()
    return profile_type


@pytest.fixture
def profile_type_3():
    """ProfileType with a document type that has a validation rule (nested operation)."""
    profile_type = ProfileType.new(...)
    profile_type.add_document_type(
        name="Identity Document",
        description="Primary identity document",
        fields=[],
    )
    doc_type_id = profile_type.document_types.document_types[0].id
    profile_type.add_document_type_validation_rule(
        document_type_id=doc_type_id,
        name="Expiry check",
        code="check_expiry",
        field_ids=[],
        description="Validates document is not expired",
    )
    profile_type.clear_events()
    return profile_type
```

### CRUD-Collection Aggregate — Fully Populated Fixture

Create a fixture with items in **every** collection for cross-collection and integration tests:

```python
@pytest.fixture
def profile_type_6():
    """ProfileType fully populated — fields, document types, reconciliation rules, and validation rules."""
    profile_type = ProfileType.new(...)
    profile_type.add_field(name="Full Name", ...)
    profile_type.add_field(name="Date of Birth", ...)
    profile_type.add_document_type(name="Identity Document", ...)
    profile_type.add_reconciliation_rule(name="Name match", description="...")
    profile_type.add_validation_rule(name="Required fields", code="req_fields", field_ids=[], description="...")
    profile_type.clear_events()
    return profile_type
```

### Collection Item Count for Update/Delete Testing

When a collection will be targeted by `update_*` or `delete_*` tests, add **at least 2 items** so that delete can be tested while items remain in the collection.

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

#### Status-machine aggregates

| Test Action | Required Fixture |
| --- | --- |
| `start_receiving()` | `load_1` (pending state) |
| `pause_receiving()` | `load_2` (receiving state) |
| `complete_receiving()` | `load_2` (receiving state) |
| Test "already completed" error | `load_3` (completed state) |

#### CRUD-collection aggregates

| Test Action | Required Fixture |
| --- | --- |
| `add_field()` | `profile_type_1` (empty state) |
| `update_field()` | `profile_type_2` (has fields) |
| `delete_field()` | `profile_type_2` (has ≥ 2 fields) |
| `add_document_type()` | `profile_type_1` (empty state) |
| `add_document_type_validation_rule()` | `profile_type_3` (has document type) or test inline |
| `add_reconciliation_rule()` | `profile_type_1` (empty state) |
| `add_validation_rule()` | `profile_type_1` (empty state) |
| Integration / persistence test | `profile_type_6` (fully populated) |

## State Mutation Guidelines

When creating fixtures for specific states:

1. Always use public methods for state transitions.
2. Follow the aggregate's natural lifecycle order.
3. Document the final state in a docstring.
4. **Clear events after setup mutations** (see **aggregate-unit-tests** skill, RULE 5).
5. Name the fixture to indicate the state.

## Template

See [template.md](template.md) for full Python templates with Jinja2 placeholders and a placeholders reference table.
