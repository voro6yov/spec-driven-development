---
name: patterns
description: "Umbrella catalog of all application-spec pattern references. Each pattern lives in a sibling folder of this file — `<pattern-name>/` containing `index.md` (the pattern doc). Load to resolve pattern names to their reference docs by path instead of per-pattern skill invocations."
---

# Application-spec pattern catalog (umbrella)

This skill is a path-resolution anchor: it registers **one** catalog entry for all application-spec
pattern references. The pattern docs themselves are **supporting files** in folders next to this
`SKILL.md` and are never auto-loaded — consumers Read them on demand.

## Resolution rule

Every pattern named `<pattern-name>` resolves to the **folder** `<pattern-name>/` sibling to this
file:

- the pattern document is always `<pattern-name>/index.md`;
- companions, when present, sit in the same folder. Relative links inside `index.md` resolve
  within that folder. (Only `domain-exceptions` ships a companion — `template.md`.)

A pattern name that has no matching folder is an **error** — report it loudly; never skip it
silently.

## Catalog

| Pattern | Folder | Companions |
|---|---|---|
| application-service-integration-test-rules | [application-service-integration-test-rules/](application-service-integration-test-rules/) | — |
| commands | [commands/](commands/) | — |
| commands-dependencies-template | [commands-dependencies-template/](commands-dependencies-template/) | — |
| commands-methods-template | [commands-methods-template/](commands-methods-template/) | — |
| dependency-injection-patterns | [dependency-injection-patterns/](dependency-injection-patterns/) | — |
| domain-exceptions | [domain-exceptions/](domain-exceptions/) | template.md |
| fake-implementations | [fake-implementations/](fake-implementations/) | — |
| fake-override-fixtures | [fake-override-fixtures/](fake-override-fixtures/) | — |
| interfaces | [interfaces/](interfaces/) | — |
| ops | [ops/](ops/) | — |
| queries-dependencies-template | [queries-dependencies-template/](queries-dependencies-template/) | — |
| queries-methods-template | [queries-methods-template/](queries-methods-template/) | — |
| queries-pattern | [queries-pattern/](queries-pattern/) | — |
| retry-transaction | [retry-transaction/](retry-transaction/) | — |
| services-report-template | [services-report-template/](services-report-template/) | — |
| settings | [settings/](settings/) | — |
| updates-report-template | [updates-report-template/](updates-report-template/) | — |

> **`domain-exceptions`** is a **vendored, independent** copy of `domain-spec`'s pattern (with its `template.md` companion) — the application layer renders `<<Application Exception>>` classes from it and may evolve it freely; there is no upstream sync obligation.
