---
name: statuses
description: Statuses pattern for DDD Python. Use when implementing lifecycle state value objects, type-safe status constants with factory methods and boolean checks, or replacing magic string comparisons in entities.
user-invocable: false
disable-model-invocation: false
---

# Statuses Pattern

**Type:** Supporting

## Purpose

- Model the lifecycle state of an entity or process using a dedicated Value Object.
- Encapsulate valid state values and provide type-safe ways to create and check states.
- Prevent "magic string" comparisons throughout the codebase.

## Structure

- Use the shared `ValueObject` metaclass to inherit guard-based equality and repr behavior.
- Define valid status strings as class constants (e.g., `IN_PROGRESS = "inProgress"`).
- Use a single `status` attribute protected by a `Guard` with `ImmutableCheck`.
- Provide `classmethod` factories for each state (e.g., `completed() -> "Status"`).
- Provide boolean properties for state checking (e.g., `is_completed -> bool`).
- Implement `__call__` to return the raw status string for serialization/logging.

## Usage in aggregates

- Declare the status attribute with a `Guard` of the Status type (without `ImmutableCheck`, since status can change):

  ```python
  status = Guard[StatusType](StatusType)
  ```

- Accept a `str` parameter in the constructor, initialize as a Status instance:

  ```python
  self.status = StatusType(status)
  ```

- For state transitions, replace the Status object:

  ```python
  self.status = StatusType.completed()
  ```

## Behavior checklist

- Status objects are immutable; state transitions involve replacing the Status object in the parent entity.
- Do not use Python `Enum`; use this pattern to allow behavior methods and integrate with the `Guard` system.
- Keep the internal representation simple (string).

## Testing guidance

- Verify equality: `Status.completed() == Status.completed()`
- Verify inequality: `Status.completed() != Status.in_progress()`
- Test boolean flags: `Status.completed().is_completed` is `True`
- Test raw value access via `__call__()`

## Template

See [template.md](template.md) for the full Python template with Jinja2 placeholders and an example.
