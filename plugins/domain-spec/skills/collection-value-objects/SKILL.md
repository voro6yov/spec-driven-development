---
name: collection-value-objects
description: Collection Value Objects pattern for DDD Python. Use when implementing aggregate-owned collections of entities, orchestrating batch mutations, enforcing collection-level policies (overages, shortages), or managing change batching.
user-invocable: false
disable-model-invocation: false
---

# Collection Value Objects Pattern

**Type:** Supporting

## Purpose

- Provide aggregate-owned orchestration over groups of entities or typed dicts while keeping the aggregate thin.
- Batch mutations, enforce collection-level policies (e.g., overage handling), and surface derived data (shortages, bypassed items).

## Structure

- Implemented as `ValueObject`s with internal containers (`dict`, `list`) guarded as immutable attributes.
- Accept optional serialized state in `__init__` and normalize it (e.g., index by natural key).
- Offer a `new()` classmethod to create empty collections for fresh aggregates.

## Behavior checklist

- Delegate per-element changes to rich entities or typed dict factories.
- Receive the owning aggregate as a parameter when events must be appended or batch thresholds need aggregate context.
- Maintain supporting metadata (`changes` queue, `overages` map) and expose computed flags (`has_overages`).
- Keep private helpers (`_get_item`, `_get_overage`) to centralize lookup error handling via domain exceptions.

## Testing guidance

- Unit-test collection methods in isolation with fake aggregates capturing appended events.
- Cover both happy paths and fallbacks (creating overages, batch flushing) to ensure invariants remain enforced.

## Template

See [template.md](template.md) for the full Python template with Jinja2 placeholders and a placeholders reference table.
