---
name: domain-events
description: Domain Events pattern for DDD Python. Use when implementing domain events, capturing state transitions, emitting events from aggregates or collection value objects, or when the spec contains <<Domain Event>> stereotype.
user-invocable: false
disable-model-invocation: false
---

# Domain Events Pattern

**Type:** Primary

## Purpose

- Capture state transitions inside the domain model so other bounded contexts or workflows can react.
- Provide auditability for aggregates by recording every significant change.

## Structure

- Implemented as `@dataclass` descendants of `Event` containing only primitives or value-object references.
- Named after the past-tense action (e.g., `LoadUploaded`, `ConveyorStopped`).
- Declared next to the aggregate or collection that emits them to keep locality of reference.

## Emission rules

- Aggregates append events to `self.events` immediately after the mutation completes.
- Collection value objects or helper factories receive the aggregate instance and append events there, preventing duplicated event stores.
- Commands may also be queued alongside events if downstream workflows require synchronous replies.

## Testing guidance

- Assert full event payloads (not just type) to ensure all contextual fields are populated.
- Verify that failure paths do not append events.

## Template

See [template.md](template.md) for the full Python template with Jinja2 placeholders and a placeholders reference table.
