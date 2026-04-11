---
name: aggregate-unit-tests
description: Unit test rules for DDD Python aggregates. Use when writing, reviewing, or fixing pytest tests for aggregate roots — covers fixture setup, encapsulation, assertions, events, naming.
user-invocable: false
disable-model-invocation: false
---

# Aggregate Unit Tests

## Purpose

- Enforce correct GIVEN/WHEN/THEN structure in pytest tests for domain aggregates.
- Prevent encapsulation violations (private attribute access/mutation).
- Ensure fixtures are reusable, correctly placed, and free of event leaks.
- Guide assertion strategy by test type (factory, state transition, query, event, validation).

---

## RULE 1: Test Setup MUST Be Done in Fixtures

**Test preconditions (GIVEN) MUST be set up via fixtures. The test function contains only the action (WHEN) and assertions (THEN).**

### Decision: Setup or Action?

```
Is this mutation/creation the thing I'm testing?
├── YES → Do it in the test function (WHEN)
└── NO → Do it in a fixture (GIVEN)
```

### Allowed in Test Functions

| In Test Function | Allowed? | Reason |
| --- | --- | --- |
| Object mutation (action under test) | ✓ YES | This is WHEN — the action being tested |
| Object creation (factory method test) | ✓ YES | When testing `Load.new()` or `Load.from_data()` |
| Object mutation for setup | ✗ NO | This is GIVEN — belongs in fixture |
| Object creation for setup | ✗ NO | This is GIVEN — belongs in fixture |

### VIOLATION: Inline State Mutation for Setup

```python
# WRONG - mutating fixture to set up test precondition
def test_load_pause_receiving(load_1):
    load_1.start_receiving()  # ❌ VIOLATION - this is SETUP, not the action under test
    load_1.pause_receiving()  # This is the actual action
    assert load_1.status == "paused"
```

### CORRECT: Fixture Provides Ready State

```python
# conftest.py
@pytest.fixture
def load_2(load_1_data):
    """Load in receiving state, ready for pause/complete actions"""
    load = Load.from_load_data(DEFAULT_WAREHOUSE_ID, "conveyor-001", load_1_data)
    load.start_receiving()
    load.clear_events()
    return load

# test_load.py
def test_load_pause_receiving(load_2):
    # GIVEN a load in receiving state (via fixture)
    # WHEN pausing
    load_2.pause_receiving()
    # THEN status is paused
    assert load_2.status == "paused"
```

---

## RULE 2: No Encapsulation Violation

**Tests MUST interact with aggregates only through public methods. Never access or set private attributes.**

### VIOLATION: Accessing or Setting Private Attributes

```python
# WRONG - reading private attribute
assert len(load_1._items) == 2  # ❌ accessing _items

# WRONG - setting private attribute to force state
load_1._status = "receiving"  # ❌ bypassing domain logic
assert load_1._status == "completed"  # ❌ again
```

### Encapsulation Checklist

- ✓ Call public methods only (`start_receiving()`, `pause()`, `complete()`)
- ✓ Assert on public properties only (`status`, `id`, `items`)
- ✓ Use `.equals()` for entity/value object comparison
- ✗ Never access attributes starting with `_`
- ✗ Never set internal state directly

---

## RULE 3: Fixture Placement

**All aggregate fixtures MUST be in root `tests/conftest.py`.**

```
tests/
├── conftest.py          ← ALL aggregate fixtures here
│   ├── load_1, load_2, load_3
│   ├── conveyor_1, conveyor_2
│   └── user_1, user_admin
├── unit/
│   └── domain/
│       └── load/
│           └── test_load.py  ← Uses fixtures from root conftest
└── integration/
    └── ...                   ← Reuses same fixtures
```

### VIOLATION: Fixtures in Test Module

```python
# tests/unit/domain/load/test_load.py
@pytest.fixture  # ❌ VIOLATION - fixture in test module
def load_for_this_test():
    return Load.new(...)
```

---

## RULE 4: Assertion Guidance

**What to assert depends on the test type. Don't over-assert or under-assert.**

### Assertion Matrix by Test Type

| Test Type | Assert State? | Assert Events? | Assert Return Value? |
| --- | --- | --- | --- |
| Factory method | ✓ YES | ✗ Usually NO | ✗ NO (returns self) |
| State transition | ✓ YES | ✓ YES (if emits) | ✗ Usually NO |
| Query method | ✗ NO | ✗ NO | ✓ YES |
| Command returning value | ✓ Maybe | ✓ YES (if emits) | ✓ YES |
| Validation (raises) | ✗ NO | ✗ NO | N/A (check exception) |

### Don't Over-Assert

```python
# WRONG - asserting unrelated state
def test_load_start_receiving(load_1):
    load_1.start_receiving()
    assert load_1.status == "receiving"
    assert load_1.id == "load-001"           # ❌ Unrelated to action
    assert load_1.warehouse_id == "wh-001"   # ❌ Unrelated

# CORRECT - assert only what changed
def test_load_start_receiving(load_1):
    load_1.start_receiving()
    assert load_1.status == "receiving"
```

---

## RULE 5: Events Cleanup in Fixtures

**Fixtures that mutate aggregates accumulate setup events. Clear events when the test should only see events from the action under test.**

### Problem: Fixture Events Leak into Test

```python
@pytest.fixture
def load_2(load_1_data):
    """Load in receiving state"""
    load = Load.from_load_data(DEFAULT_WAREHOUSE_ID, "conveyor-001", load_1_data)
    load.start_receiving()  # Emits LoadReceivingStarted — leaks into test!
    return load
```

### Solution: Clear Events After Setup

```python
@pytest.fixture
def load_2(load_1_data):
    """Load in receiving state"""
    load = Load.from_load_data(DEFAULT_WAREHOUSE_ID, "conveyor-001", load_1_data)
    load.start_receiving()
    load.clear_events()  # ✓ Clear setup events
    return load
```

### When to Clear Events

| Scenario | Clear Events? |
| --- | --- |
| Fixture reaches state via mutations | ✓ YES |
| Fixture creates aggregate via factory (no mutations) | ✗ NO |
| Test needs to verify ALL events including setup | ✗ NO (document in test) |

---

## Test Naming Convention

```
test_{aggregate}_{method}__{scenario}__{expected_outcome}
```

| Part | Description | Example |
| --- | --- | --- |
| `{aggregate}` | Domain object being tested | `load`, `conveyor`, `money` |
| `{method}` | Public method under test | `start_receiving`, `add`, `new` |
| `{scenario}` | Precondition or input variation | `already_completed`, `negative_amount` |
| `{expected_outcome}` | What should happen | `success`, `raises`, `emits_event` |

### Examples

```python
# Success
test_load_start_receiving__success
test_money_add__same_currency__returns_sum

# Error
test_load_start_receiving__already_completed__raises
test_money_new__negative_amount__raises

# Events
test_load_complete_receiving__emits_sync_event

# Query
test_load_items_count__returns_count
```

---

## Test Structure Template

```python
def test_{aggregate}_{action}__{expected_outcome}({fixture_providing_ready_state}):
    # GIVEN {precondition from fixture}

    # WHEN {single action under test}
    {fixture}.{public_method}({args})

    # THEN {expected outcome}
    assert {fixture}.{public_property} == {expected_value}
```

---

## Domain Event Assertions

Domain event tests must verify **both event type AND payload**. Checking only `isinstance()` is insufficient.

### VIOLATION: Type-Only Check

```python
# WRONG - only checks event type, ignores payload
assert any(isinstance(e, LoadReceivingStarted) for e in load_1.events)  # ❌ Incomplete
```

### CORRECT: Type + Payload Check

```python
def test_load_start_receiving__emits_event(load_1):
    # GIVEN a load in pending state (load_1)
    load_1.start_receiving()

    event = next(e for e in load_1.events if isinstance(e, LoadReceivingStarted))
    assert event.load_id == load_1.id
    assert event.warehouse_id == load_1.warehouse_id
```

### Multiple Events

```python
def test_load_complete_receiving__emits_events(load_2):
    # GIVEN a load in receiving state (load_2)
    load_2.complete_receiving()

    completion_event = next(
        e for e in load_2.events if isinstance(e, LoadReceivingCompleted)
    )
    assert completion_event.load_id == load_2.id

    sync_event = next(
        e for e in load_2.events if isinstance(e, LoadSyncRequested)
    )
    assert sync_event.load_id == load_2.id
```

### Event Ordering

```python
def test_load_workflow__events_in_order(load_1):
    # GIVEN a load in pending state (load_1)
    load_1.start_receiving()
    load_1.complete_receiving()

    event_types = [type(e) for e in load_1.events]
    assert event_types == [LoadReceivingStarted, LoadReceivingCompleted, LoadSyncRequested]
```

### No Event Emitted

```python
def test_load_pause__no_sync_event(load_2):
    # GIVEN a load in receiving state (load_2)
    load_2.pause_receiving()
    assert not any(isinstance(e, LoadSyncRequested) for e in load_2.events)
```

---

## Summary of Violations

| Violation | Example | Fix |
| --- | --- | --- |
| Object creation for SETUP | `load = Load.new()` then test something else | Create fixture |
| State mutation for SETUP | `load.start()` before the actual action | Create fixture with ready state |
| Private attribute access | `load._status` | Use `load.status` |
| Private attribute mutation | `load._items = []` | Use public methods |
| Fixture in test module | `@pytest.fixture` in test file | Move to root conftest |
| Type-only event assertion | `isinstance(e, Event)` without payload | Assert `event.load_id == load.id` |
| Fixture leaks setup events | No `clear_events()` after mutations | Add `load.clear_events()` in fixture |
| Over-assertion | Assert unrelated properties | Assert only what action changed |

## What's NOT a Violation

| Action | Example | Why It's OK |
| --- | --- | --- |
| Object creation as ACTION | `load = Load.new()` when testing factory | Factory method IS the action under test |
| State mutation as ACTION | `load.start_receiving()` | Method call IS the action under test |
| Multiple asserts per test | Assert state + event + return value | When all relate to the action |

## Templates

See [template.md](template.md) for reusable Jinja2-style test templates with placeholders reference.
