---
name: patterns
description: "Umbrella catalog of all domain-spec DDD pattern references. Each pattern lives in a sibling folder of this file — `<pattern-name>/` containing `index.md` (the pattern doc) plus optional `template.md`/`examples.md` companions. Load to resolve pattern names to their reference docs by path instead of per-pattern skill invocations."
---

# Domain-spec pattern catalog (umbrella)

This skill is a path-resolution anchor: it registers **one** catalog entry for all domain-spec
pattern references. The pattern docs themselves are **supporting files** in folders next to this
`SKILL.md` and are never auto-loaded — consumers Read them on demand.

## Resolution rule

Every pattern named `<pattern-name>` resolves to the **folder** `<pattern-name>/` sibling to this
file:

- the pattern document is always `<pattern-name>/index.md`;
- companions, when present, sit in the same folder (`template.md` — the Jinja2-style code
  template the implementers render; `examples.md` — worked examples). Relative links inside
  `index.md` (e.g. `[template.md](template.md)`) resolve within that folder.

A pattern name that has no matching folder is an **error** — report it loudly; never skip it
silently.

## Catalog

| Pattern | Folder | Companions |
|---|---|---|
| aggregate-data-fixtures | [aggregate-data-fixtures/](aggregate-data-fixtures/) | template.md |
| aggregate-fixtures | [aggregate-fixtures/](aggregate-fixtures/) | template.md |
| aggregate-root | [aggregate-root/](aggregate-root/) | template.md |
| aggregate-unit-tests | [aggregate-unit-tests/](aggregate-unit-tests/) | template.md |
| class-spec-template | [class-spec-template/](class-spec-template/) | — |
| collection-value-objects | [collection-value-objects/](collection-value-objects/) | template.md |
| commands | [commands/](commands/) | template.md |
| constructor-guard-type-mapping | [constructor-guard-type-mapping/](constructor-guard-type-mapping/) | — |
| delegation-and-event-propagation | [delegation-and-event-propagation/](delegation-and-event-propagation/) | template.md |
| domain-events | [domain-events/](domain-events/) | template.md |
| domain-exceptions | [domain-exceptions/](domain-exceptions/) | template.md |
| domain-pattern-selection | [domain-pattern-selection/](domain-pattern-selection/) | examples.md |
| domain-services | [domain-services/](domain-services/) | template.md |
| domain-typed-dicts | [domain-typed-dicts/](domain-typed-dicts/) | template.md |
| entity | [entity/](entity/) | template.md |
| flat-constructor-arguments | [flat-constructor-arguments/](flat-constructor-arguments/) | template.md |
| guards-and-checks | [guards-and-checks/](guards-and-checks/) | template.md |
| optional-values | [optional-values/](optional-values/) | — |
| package-layout | [package-layout/](package-layout/) | — |
| query-dtos | [query-dtos/](query-dtos/) | template.md |
| repositories | [repositories/](repositories/) | template.md |
| statuses | [statuses/](statuses/) | template.md |
| updates-report-template | [updates-report-template/](updates-report-template/) | — |
| value-object | [value-object/](value-object/) | template.md |

> **Status: demotion pilot.** These folders are verbatim copies of the standalone
> `domain-spec:<pattern>` skills (each `SKILL.md` renamed to `index.md`), made to test the
> umbrella-skill demotion approach (`notes/active-skills-footprint.md` §0.4). The standalone
> skills remain registered and authoritative until the pilot is accepted.
