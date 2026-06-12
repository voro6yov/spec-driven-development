---
name: flat-constructor-arguments
description: Flat Constructor Arguments pattern for DDD Python. Use when defining aggregate or entity constructors that accept flat primitives and build value objects internally, or when mapping repository rows to domain objects without leaking construction logic to callers.
user-invocable: false
disable-model-invocation: false
---

# Flat Constructor Arguments Pattern

**Type:** Supporting

## Purpose

Accept flat primitive arguments in constructors and build value objects internally, rather than requiring callers to construct value objects before calling the constructor.

## Problem

When persisting and loading entities from storage, data comes as flat primitives. Requiring callers to construct value objects before calling the entity constructor:
1. Leaks construction logic to callers (repositories, factories)
2. Creates coupling between persistence and domain model construction
3. Complicates reconstitution from database rows

## Rules

### 1. No default values in constructor (except events/commands)
All values are passed explicitly by factory methods or repositories. The exception: `events` and `commands` are keyword-only with defaults since they're infrastructure concerns.

### 2. Value object construction
When a Guard declares a value object type, the constructor accepts the value object's constructor arguments flattened, then builds the value object internally.

### 3. Collection value object construction
Accept lists and use the `or CollectionType.new()` pattern:
```python
self.items = Items(line_items, overages, changes) or Items.new()
```

### 4. Argument ordering
1. Identity fields first (`id_`, `tenant_id`)
2. Value object component args grouped by target (all `ShipmentInfo` args together)
3. Collection value object args grouped by target
4. Simple primitive fields (`bypass_mode`)
5. Timestamps (`created_at`, `updated_at`)
6. Optional keyword-only args (`events`, `commands`)

### 5. When to use pre-built value objects
Accept pre-built value objects when the value object is provided by external sources (a DTO that maps directly) or is truly atomic (single-field wrappers).

## Testing guidance

- Verify that repositories can pass database columns directly to constructors without knowing value object construction details.
- Test factory methods provide all values explicitly.

## Template

See [template.md](template.md) for a full annotated example.
