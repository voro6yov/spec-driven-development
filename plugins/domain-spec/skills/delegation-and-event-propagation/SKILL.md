---
name: delegation-and-event-propagation
description: Delegation and Event Propagation pattern for DDD Python. Use when implementing collaborators that mutate internal state and emit events through the owning aggregate, or when keeping aggregate methods thin by delegating to collection value objects.
user-invocable: false
disable-model-invocation: false
---

# Delegation and Event Propagation Pattern

**Type:** Supporting

## Purpose

- Keep aggregate methods small by delegating to collaborators that understand collection semantics while ensuring a single event source.
- Guarantee every collaborator emits events through the owning aggregate rather than storing its own event log.

## Technique

1. Aggregates create collaborators with references to themselves (directly or passed into methods).
2. Collaborators mutate their internal state and append events to `aggregate.events` immediately before returning control.
3. Collaborators can re-enter aggregate methods (e.g., batching via `load.add_collection_changes`) to centralize final actions.

## Implementation cues

- Methods accept `(reference, aggregate)` so they can inspect aggregate state and push events.
- Event classes remain colocated with the collaborator that triggers them, but only the aggregate stores the resulting instances.
- Use helper methods (e.g., `_on_item_incremented`) to keep event batching logic dry.

## Testing guidance

- Provide a fake aggregate capturing the `events` list when unit-testing collaborators.
- Assert that delegation preserves invariants (batch sizes, bypass behavior) and that emitted events match the aggregate's identity.

## Template

See [template.md](template.md) for the full Python template with Jinja2 placeholders and an example.
