---
name: guards-and-checks
description: Guards and Checks pattern for DDD Python. Use when implementing attribute validation, custom Check classes, ImmutableCheck usage, Guard descriptors, or enforcing domain-specific rules on entity/value object attributes.
user-invocable: false
disable-model-invocation: false
---

# Guards and Checks Pattern

**Type:** Supporting

## Purpose

- Centralize attribute validation for entities and value objects using descriptors.
- Compose reusable `Check` strategies to enforce immutability, type safety, formats, and domain-specific rules.

## Structure

- `Guard[type]` is declared as a class attribute; assignments run default checks (`NoneCheck`, `TypeCheck`) plus custom checks.
- `ImmutableCheck` prevents reassignment after the first successful set, matching aggregate invariants.
- Custom checks subclass `Check` and implement `is_correct`, raising `IllegalArgument` with a descriptive message.

## Usage patterns

- Always pass the runtime type to the guard (e.g., `Guard[ShipmentInfo](ShipmentInfo, ImmutableCheck())`).
- Compose multiple checks to express complex constraints (length, pattern, chronological order).
- Use `AttributeName` helper to ensure private storage names remain unique across descriptors.

## Module organization

- Place all custom `Check` classes in a dedicated `checks.py` module at the domain package root.
- Do **not** define checks inline within entity or value object modules.

## Testing guidance

- Exercise guard validation via aggregate or value-object constructors; expect `IllegalArgument` for invalid assignments.
- Prefer targeted unit tests for bespoke checks to keep failure messages meaningful.

## Template

See [template.md](template.md) for the full Python template with Jinja2 placeholders and a placeholders reference table.
