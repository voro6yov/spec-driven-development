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

| Pattern | Folder | Companions | Registered twin |
|---|---|---|---|
| application-service-integration-test-rules | [application-service-integration-test-rules/](application-service-integration-test-rules/) | — | — |
| application-updates-report-template | [application-updates-report-template/](application-updates-report-template/) | — | ✦ |
| commands | [commands/](commands/) | — | — |
| commands-dependencies-template | [commands-dependencies-template/](commands-dependencies-template/) | — | — |
| commands-methods-template | [commands-methods-template/](commands-methods-template/) | — | — |
| dependency-injection-patterns | [dependency-injection-patterns/](dependency-injection-patterns/) | — | — |
| domain-exceptions | [domain-exceptions/](domain-exceptions/) | template.md | ⟵ vendored from domain-spec |
| fake-implementations | [fake-implementations/](fake-implementations/) | — | ✦ |
| fake-override-fixtures | [fake-override-fixtures/](fake-override-fixtures/) | — | ✦ |
| interfaces | [interfaces/](interfaces/) | — | — |
| ops | [ops/](ops/) | — | — |
| ops-updates-report-template | [ops-updates-report-template/](ops-updates-report-template/) | — | ✦ |
| queries-dependencies-template | [queries-dependencies-template/](queries-dependencies-template/) | — | — |
| queries-methods-template | [queries-methods-template/](queries-methods-template/) | — | — |
| queries-pattern | [queries-pattern/](queries-pattern/) | — | — |
| retry-transaction | [retry-transaction/](retry-transaction/) | — | — |
| services-report-template | [services-report-template/](services-report-template/) | — | ✦ |
| settings | [settings/](settings/) | — | — |
| updates-report-template | [updates-report-template/](updates-report-template/) | — | — |

> **Authoritative copies & dual-homed twins.** For most patterns these folders are the **only**
> copy — the standalone `application-spec:<pattern>` skills were deregistered (Wave 1 of the
> umbrella-skill demotion, `notes/active-skills-footprint.md` §0.4/§0.5). The five rows marked
> ✦ are **dual-homed**: a standalone skill `application-spec:<pattern>` is still registered
> because foreign plugins consume it; it remains the authoritative source until Wave 3 demotes
> it. The umbrella copy must stay **byte-identical** to its registered twin — when editing a ✦
> pattern, edit the standalone skill first, then re-sync `<pattern>/index.md` from it.
>
> **Vendored pattern.** `domain-exceptions` is a **vendored copy** of `domain-spec`'s pattern —
> the application layer reuses the domain-exceptions codegen template (+ `template.md`) to render
> `<<Application Exception>>` classes. It is an **independent** copy: deliberately **not** synced
> to `domain-spec:patterns/domain-exceptions`, free to diverge as application-exception rendering
> evolves. Edit it here directly; there is no upstream twin to re-sync.
