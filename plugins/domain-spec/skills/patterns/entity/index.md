---
name: entity
description: Entity pattern for DDD Python. Use when implementing entity classes with identity managed by their aggregate root, mutable attributes guarded over time, or when the spec contains <<Entity>> stereotype.
user-invocable: false
disable-model-invocation: false
---

# Entity Pattern

**Type:** Primary

## Purpose

- Represent objects with identity managed by their aggregate root.
- Own mutable attributes that change over time but remain guarded through the shared `Entity` metaclass.

## Structure

- Define `Guard` descriptors for each attribute plus any helper constants (statuses, thresholds).
- Assign a deterministic identifier inside `__init__` (e.g., a natural key like `reference`).
- Provide behavior methods that change internal state and notify parent collections via callbacks (e.g., `collection.record_change`).

## Behavior checklist

- Never emit events directly; instead, call back into the aggregate or collection value object that supplied context.
- Respect guard rules such as immutability or type enforcement; rely on guard exceptions for invalid input.
- Use intention-revealing names (`increment_received_quantity`, `disassociate_tire`).

## Testing guidance

- Exercise entity methods through the owning aggregate or collection to ensure identity and guard logic stays consistent.
- Assert that mutations trigger the expected collaboration (e.g., change records, status transitions).

## Template

See [template.md](template.md) for the full Python template with Jinja2 placeholders and a placeholders reference table.
