---
name: aggregate-root
description: Aggregate Root pattern for DDD Python. Use when implementing aggregate root classes, coordinating child entities/value objects, accumulating domain events/commands, or when the spec contains <<Aggregate Root>> stereotype.
user-invocable: false
disable-model-invocation: false
---

# Aggregate Root Pattern

**Type:** Primary

## Purpose

- Encapsulate invariants for a domain concept and guard all mutations behind domain methods.
- Coordinate child entities/value objects and accumulate domain events/commands for the application layer to dispatch.

## Structure

- Declare guards for every attribute to enforce immutability, types, or custom rules using `Guard` and `ImmutableCheck`.
- Accept DTOs or primitives in constructors/factories; store collaborators such as collection value objects and info value objects.
- Maintain `events: list[Event]` and optional `commands: list[Command]` lists as mutable collections on the instance.

## Behavior checklist

- Provide alternative constructors for different ingestion paths (e.g., `from_data`, `from_dynamics_data`).
- Expose intent-revealing methods that mutate state and delegate detailed work to collection/value objects.
- Update timestamps or derived metadata whenever state changes.
- Append events immediately after successful state transitions, either directly or via collaborators.

## Testing guidance

- Write unit tests per method using PTDD: assert guard failures, side effects on collaborators, and emitted events (order and payload).
- Use fakes for child collections when verifying orchestration to isolate aggregate rules.

## Template

See [template.md](template.md) for the full Python template with Jinja2 placeholders and a placeholders reference table.
