---
name: query-dtos
description: Query DTOs pattern for DDD Python. Use when defining TypedDict data transfer objects for repositories, aggregate factory inputs, query responses with pagination metadata, or when the spec contains <<Query DTO>> stereotype.
user-invocable: false
disable-model-invocation: false
---

# Query DTOs Pattern

**Type:** Supporting

## Purpose

- Capture the shape of inbound/outbound data exchanged between the domain, repositories, and external services.
- Keep query responses serializable and explicit about metadata (pagination, counts).

## Structure

- Use `TypedDict` (optionally `total=False`) to represent flexible payloads.
- Group DTOs by aggregate to keep schemas easy to locate (`LoadData`, `LoadsInfo`).
- Compose shared building blocks like `PaginatedResultMetadataInfo` and `ResultSetInfo` for consistent paging output.

## Usage patterns

- Aggregates accept DTOs in factory/class methods so parsing happens outside constructors.
- Query repositories return DTOs to API/application layers, which serialize them without touching aggregates.
- Keep DTO modules free of behavior — only structure lives here.

## Testing guidance

- Validate DTO compatibility via typing and sample payload fixtures; prefer factory helpers in tests to reduce repetition.

## Template

See [template.md](template.md) for the full Python template with Jinja2 placeholders and examples.
