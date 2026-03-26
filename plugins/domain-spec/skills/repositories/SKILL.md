---
name: repositories
description: Repositories pattern for DDD Python. Use when defining aggregate persistence boundaries, implementing command/query repository interfaces, or when the spec contains <<Repository>> stereotype.
user-invocable: false
disable-model-invocation: false
---

# Repositories Pattern

**Type:** Primary

## Purpose

- Abstract persistence of aggregates while respecting command-query segregation.
- Allow application services to request aggregates or query DTOs without leaking ORM or storage details.

## Structure

- **Command repositories** extend `ABC` and expose methods like `save` plus targeted lookups (`load_of_id`).
- **Query repositories** use `typing.Protocol` when multiple adapters must satisfy the same contract; they return typed dict DTOs with metadata.
- Pagination concerns live in the domain layer via `Pagination` and `PaginatedResultMetadataInfo` types.

## Usage patterns

- Command side returns aggregate instances or `None`; query side returns serializable DTO trees.
- Keep repository modules minimal, focusing on interface definitions and type aliases.
- Domain services or application handlers supply repositories to aggregates when persistence is required.

## Testing guidance

- Fake repositories should live in `tests/fakes` and implement both command and query contracts for PTDD loops.

## Template

See [template.md](template.md) for command and query repository templates with Jinja2 placeholders and examples.
