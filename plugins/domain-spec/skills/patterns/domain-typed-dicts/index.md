---
name: domain-typed-dicts
description: Domain TypedDicts pattern for DDD Python. Use when implementing type-safe internal domain data structures, lightweight aggregations within aggregates, or factory classes for complex TypedDict construction.
user-invocable: false
disable-model-invocation: false
---

# Domain TypedDicts Pattern

**Type:** Primary

## Purpose

- Represent structured data within domain aggregates as type-safe dictionaries.
- Provide lightweight data structures for internal domain state (entities, records, metadata).
- Enable aggregates to work with structured data without requiring full entity/value object overhead.

## Structure

- Use `TypedDict` (without `total=False`) to represent required-field structures.
- Include `__all__` exports for explicit module exports.
- Group related TypedDicts in the same module when tightly coupled; separate when reused across aggregates.
- Support nested TypedDicts for composition.
- Use `Literal` types for status fields when values are constrained to specific strings.

## Optional Factory Pattern

- Create a Factory class when construction logic is complex (e.g., matching records, computing scores).
- Factory `new` classmethod returns the TypedDict instance with all required fields populated.
- Keep factories in the same module as the TypedDict they construct.

## When to use TypedDict vs Value Object

**Use TypedDict** when:
- Data is simple and primarily used for storage/retrieval
- No behavioral methods or complex validation are needed
- Mutations are acceptable and happen within aggregate boundaries
- Performance is a concern (TypedDicts are lighter than value objects)

**Use Value Object** when:
- You need immutability guarantees
- You need equality-by-value semantics
- You need behavioral methods or computed properties
- You need guard-based validation

## Testing guidance

- Validate TypedDict structure through type checking and sample data fixtures.
- Test Factory classes to ensure they produce correctly structured TypedDicts.

## Template

See [template.md](template.md) for the full Python template with Jinja2 placeholders and examples.
