---
name: value-object
description: Value Object pattern for DDD Python. Use when implementing value objects, descriptive concepts without identity, immutable domain data holders, or when the spec contains <<Value Object>> stereotype.
user-invocable: false
disable-model-invocation: false
---

# Value Object Pattern

**Type:** Primary

## Purpose

- Model descriptive concepts without identity, emphasizing immutability and equality-by-value.
- Encapsulate computations and validation around a cohesive set of attributes (status transitions, timestamps).

## Structure

- Use the shared `ValueObject` metaclass to inherit guard-based equality and repr behavior.
- Declare guards with `ImmutableCheck` for attributes that must not change after initialization.
- Provide factory or helper methods that update state yet still enforce invariants.

## Behavior checklist

- Favor pure functions; when a mutation is required (e.g., storing a timestamp), emit events through the aggregate passed into the method.
- Avoid referencing infrastructure concerns; rely on primitives and other value objects only.
- Keep method signatures explicit about required collaborators (aggregate instance, dependent collections).

## Testing guidance

- Assert equality semantics (`ValueObject.equals`) and invariants enforced by guards.
- Verify that behavioral helpers append the correct events and update any tracked timestamps.

## Template

See [template.md](template.md) for the full Python template with Jinja2 placeholders and a placeholders reference table.
