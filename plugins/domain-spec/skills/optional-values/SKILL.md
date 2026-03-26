---
name: optional-values
description: Optional Values pattern for DDD Python. Use when handling optional attributes in entities or value objects, choosing between conditional assignment and default values, or implementing state-checking properties based on None presence.
user-invocable: false
disable-model-invocation: false
---

# Optional Values Pattern

**Type:** Supporting

## Purpose

- Define and initialize optional attributes in domain entities and value objects consistently.
- Distinguish between attributes that may be absent versus those that have default values.
- Enable clear state checking through `None` presence or absence.

## Structure

- Type optional parameters as `Type | None` in method signatures.
- Conditionally assign optional values in `__init__` based on their presence.
- Declare `Guard` descriptors for optional attributes even when they may not be assigned.

## Behavior checklist

- Use `if value:` for optional strings, objects, or collections that should only be assigned when truthy.
- Use `if value is not None:` for numeric values, floats, or booleans where `0` or `False` are valid values.
- Use default value assignment: `self.attr = value if value is not None else default` when a default is required.
- Use factory methods: `FactoryClass(value) or FactoryClass.new()` when the attribute should always have a value object instance.
- Leave attributes unassigned when `None` if they represent truly optional state (e.g., `extraction_info`, `product_info`).
- Create properties that check for `None` to determine entity state (e.g., `is_in_progress`, `is_processed`).
- In factory methods like `new()`, pass `None` explicitly for optional parameters to make initialization clear.

## Patterns

```python
# Conditional assignment for datetime / value objects
if started_at is not None:
    self.started_at = started_at

# Default to empty for lists
self.items = items or []

# Factory fallback for collection value objects
self.collection = CollectionType(raw_items, changes) or CollectionType.new()

# State property
@property
def is_started(self) -> bool:
    return hasattr(self, "started_at")
```

## Testing guidance

- Verify that optional attributes are not assigned when `None` is passed.
- Assert that default values are used when appropriate.
- Test that truthy checks work correctly for strings and objects.
- Test that `is not None` checks work correctly for numeric values including `0`.
- Verify state properties correctly detect presence or absence of optional attributes.
