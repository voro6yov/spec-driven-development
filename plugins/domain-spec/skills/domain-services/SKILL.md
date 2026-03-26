---
name: domain-services
description: Domain Services and Interfaces pattern for DDD Python. Use when defining operations that depend on infrastructure or external systems, implementing ABCs or Protocols for dependency injection, or when the spec contains <<Service>> stereotype.
user-invocable: false
disable-model-invocation: false
---

# Domain Services & Interfaces Pattern

**Type:** Primary

## Purpose

- Define operations that belong to the domain but depend on infrastructure or external systems (file parsing, persistence gateways).
- Preserve hexagonal boundaries by keeping only the interface/protocol inside the domain layer.

## Structure

- Prefer ABCs or typing `Protocol`s for collaborations that need duck typing.
- Keep method signatures focused on domain concepts rather than transport models.
- Co-locate service definitions next to the aggregates they support to simplify discovery.

## Usage patterns

- Application services inject concrete implementations that satisfy these interfaces.
- Domains depend on services without knowing the infrastructure by accepting the interface via constructor or method injection.
- Keep interfaces tiny and intention-specific; compose multiple services if an operation spans unrelated responsibilities.

## Testing guidance

- During unit tests, stub or fake the interface to provide deterministic responses, enabling PTDD around aggregate behavior.

## Template

See [template.md](template.md) for the full Python template with Jinja2 placeholders and examples.
