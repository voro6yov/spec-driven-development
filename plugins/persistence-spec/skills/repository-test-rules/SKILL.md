---
name: repository-test-rules
description: Repository Integration Test Rules pattern for persistence-layer testing. Use when writing or reviewing repository integration tests that rely on collection and persistence fixtures.
user-invocable: false
disable-model-invocation: false
---

# Repository Integration Test Rules

## Purpose

Explicit rules for writing repository integration tests using existing collection and persistence fixtures. These rules ensure tests are maintainable, use fixtures correctly, and don't create objects inline.

## RULE 1: Use Fixtures for Test Data

**All test data MUST come from fixtures. Never create or persist objects inside test functions.**

### VIOLATION: Creating and Persisting in Test

```python
# WRONG - creating and storing object in test
def test_load_of_id__success(unit_of_work):
    load = Load.from_load_data(  # ❌ VIOLATION - creating in test
        DEFAULT_WAREHOUSE_ID,
        "conveyor-001",
        {"id": "load-001", "items": [...]},
    )
    with unit_of_work:
        unit_of_work.loads.save(load)  # ❌ VIOLATION - persisting in test
        unit_of_work.commit()

    result = unit_of_work.loads.load_of_id(load.id, load.warehouse_id)
    assert result is not None
```

### CORRECT: Use Persistence Fixtures

```python
# CORRECT - fixtures handle creation and persistence
def test_load_of_id__success(unit_of_work, load_1, add_loads):
    # GIVEN load exists in DB (via add_loads fixture)
    # WHEN querying by ID
    result = unit_of_work.loads.load_of_id(load_1.id, load_1.warehouse_id)

    # THEN load is returned
    assert result.equals(load_1)
```

## RULE 2: No Unnecessary UoW Context Manager

**Don't wrap repository calls in `with unit_of_work:` unless you need a transaction.**

### When UoW Context IS Needed

| Operation | Context Needed? |
| --- | --- |
| Read-only query (single call) | ✗ NO |
| Multiple reads in sequence | ✗ NO |
| Save/update operation | ✓ YES |
| Delete operation | ✓ YES |
| Multiple writes (transaction) | ✓ YES |

### VIOLATION: Wrapping Read Operations

```python
# WRONG - unnecessary context manager for read
def test_load_of_id__success(unit_of_work, load_1, add_loads):
    with unit_of_work:  # ❌ VIOLATION - not needed for read
        result = unit_of_work.loads.load_of_id(load_1.id, load_1.warehouse_id)
    assert result.equals(load_1)
```

### CORRECT: Direct Read

```python
# CORRECT - no context manager for read operations
def test_load_of_id__success(unit_of_work, load_1, add_loads):
    # GIVEN load exists in DB
    # WHEN querying
    result = unit_of_work.loads.load_of_id(load_1.id, load_1.warehouse_id)

    # THEN returns load
    assert result.equals(load_1)
```

### CORRECT: Context Manager for Write Operations

```python
# CORRECT - context manager needed for save
def test_save_load__persists_load(unit_of_work, load_1):
    # GIVEN a load not in DB
    # WHEN saving
    with unit_of_work:
        unit_of_work.loads.save(load_1)
        unit_of_work.commit()

    # THEN load is persisted
    result = unit_of_work.loads.load_of_id(load_1.id, load_1.warehouse_id)
    assert result.equals(load_1)
```

## RULE 3: Use `.equals()` for Entity Comparison

**Always use `.equals()` method to compare domain entities, never `==`.**

### VIOLATION: Direct Equality

```python
# WRONG - using == for entity comparison
def test_load_of_id__success(unit_of_work, load_1, add_loads):
    result = unit_of_work.loads.load_of_id(load_1.id, load_1.warehouse_id)
    assert result == load_1  # ❌ VIOLATION - may fail due to object identity
```

### CORRECT: Use `.equals()`

```python
# CORRECT - using .equals() for comparison
def test_load_of_id__success(unit_of_work, load_1, add_loads):
    result = unit_of_work.loads.load_of_id(load_1.id, load_1.warehouse_id)
    assert result.equals(load_1)  # ✓ Compares by value/identity
```

### Comparison Methods

| Comparison | Use Case |
| --- | --- |
| `.equals(other)` | Entities and value objects |
| `== None` or `is None` | Checking for not found |
| `len(results) == N` | Counting results |

## RULE 4: No Encapsulation Violation

**Same rules as unit tests: use public methods/properties only.**

### VIOLATION: Asserting on Private Attributes

```python
# WRONG - accessing private attribute
def test_load_of_id__success(unit_of_work, load_1, add_loads):
    result = unit_of_work.loads.load_of_id(load_1.id, load_1.warehouse_id)
    assert result._status == "pending"  # ❌ VIOLATION
    assert len(result._items) == 2  # ❌ VIOLATION
```

### CORRECT: Use Public Properties

```python
# CORRECT - using public properties
def test_load_of_id__success(unit_of_work, load_1, add_loads):
    result = unit_of_work.loads.load_of_id(load_1.id, load_1.warehouse_id)
    assert result.status == "pending"  # ✓ Public property
    assert result.items_count == 2  # ✓ Public property
```

## RULE 5: Choosing Fixtures

### Individual vs Collection Fixture

| Scenario | Use |
| --- | --- |
| Test single entity query (found) | Individual fixture (`load_1`) |
| Test "not found" scenario | Individual fixture (no `add_*`) |
| Test bulk operations | Collection (`test_loads`) |
| Test queries returning multiple | Collection + iteration |

Note: tests targeting a single entity may still depend on `add_loads` even though it persists the whole collection. Cleanup fixtures clear data between tests, the collection approach keeps fixture structure simple, and the performance impact is minimal.

### When to Use `add_*` Fixture

| Scenario | Use `add_*`? |
| --- | --- |
| Test "found" query | ✓ YES |
| Test "not found" query | ✗ NO |
| Test update operation | ✓ YES |
| Test save new entity | ✗ NO |
| Test delete operation | ✓ YES |

## Test Patterns by Repository Method

### Query by ID (Found)

```python
def test_load_of_id__found(unit_of_work, load_1, add_loads):
    # GIVEN load exists (add_loads persists test_loads which includes load_1)
    # WHEN querying by ID
    result = unit_of_work.loads.load_of_id(load_1.id, load_1.warehouse_id)

    # THEN returns the load
    assert result is not None
    assert result.equals(load_1)
```

### Query by ID (Not Found)

```python
def test_load_of_id__not_found(unit_of_work, load_1):
    # GIVEN load does NOT exist (no add_loads fixture!)
    # WHEN querying by ID
    result = unit_of_work.loads.load_of_id(load_1.id, load_1.warehouse_id)

    # THEN returns None
    assert result is None
```

### Query All / Query by Criteria

```python
def test_loads_by_warehouse__returns_all(unit_of_work, test_loads, add_loads):
    # GIVEN multiple loads exist
    # WHEN querying by warehouse
    results = unit_of_work.loads.loads_by_warehouse(DEFAULT_WAREHOUSE_ID)

    # THEN returns all loads
    assert len(results) == len(test_loads)
    for load in test_loads:
        assert any(r.equals(load) for r in results)
```

### Save Operation

```python
def test_save__persists_new_load(unit_of_work, load_1):
    # GIVEN a new load (not persisted)
    # WHEN saving
    with unit_of_work:
        unit_of_work.loads.save(load_1)
        unit_of_work.commit()

    # THEN load exists in DB
    result = unit_of_work.loads.load_of_id(load_1.id, load_1.warehouse_id)
    assert result.equals(load_1)
```

### Update Operation

```python
def test_save__updates_existing_load(unit_of_work, load_1, add_loads):
    # GIVEN load exists in DB
    # AND load is modified
    load_1.start_receiving()

    # WHEN saving
    with unit_of_work:
        unit_of_work.loads.save(load_1)
        unit_of_work.commit()

    # THEN changes are persisted
    result = unit_of_work.loads.load_of_id(load_1.id, load_1.warehouse_id)
    assert result.status == "receiving"
```

### Delete Operation

```python
def test_delete__removes_load(unit_of_work, load_1, add_loads):
    # GIVEN load exists in DB
    # WHEN deleting
    with unit_of_work:
        unit_of_work.loads.delete(load_1)
        unit_of_work.commit()

    # THEN load no longer exists
    result = unit_of_work.loads.load_of_id(load_1.id, load_1.warehouse_id)
    assert result is None
```

## Test Naming Convention

```
test_{repository_method}__{scenario}__{expected_outcome}
```

### Examples

```python
# Query tests
test_load_of_id__found__returns_load
test_load_of_id__not_found__returns_none
test_loads_by_warehouse__multiple_exist__returns_all
test_loads_by_status__none_match__returns_empty_list

# Command tests
test_save__new_load__persists
test_save__existing_load__updates
test_delete__existing_load__removes
```

## Summary of Violations

| Violation | Example | Fix |
| --- | --- | --- |
| Create object in test | `load = Load.new()` in test | Use fixture |
| Persist in test | `unit_of_work.save(load)` for setup | Use `add_*` fixture |
| Unnecessary UoW context | `with unit_of_work:` for reads | Remove context manager |
| Direct equality | `result == load_1` | Use `result.equals(load_1)` |
| Private attribute access | `result._status` | Use `result.status` |
| Missing persistence fixture | Test assumes data exists | Add `add_loads` to parameters |

## What's NOT a Violation

| Action | Example | Why It's OK |
| --- | --- | --- |
| UoW context for writes | `with unit_of_work:` for save | Needed for transaction |
| Modifying fixture before save | `load_1.start_receiving()` then save | Testing update behavior |
| Querying without add_* | Test "not found" scenario | Intentional empty DB |
