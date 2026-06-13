---
name: patterns
description: "Umbrella catalog of all persistence-spec pattern references. Each pattern lives in a sibling folder of this file — `<pattern-name>/` containing `index.md` (the pattern doc). Load to resolve pattern names to their reference docs by path instead of per-pattern skill invocations."
---

# Persistence-spec pattern catalog (umbrella)

This skill is a path-resolution anchor: it registers **one** catalog entry for all persistence-spec
pattern references. The pattern docs themselves are **supporting files** in folders next to this
`SKILL.md` and are never auto-loaded — consumers Read them on demand.

## Resolution rule

Every pattern named `<pattern-name>` resolves to the **folder** `<pattern-name>/` sibling to this
file:

- the pattern document is always `<pattern-name>/index.md`;
- companions, when present, sit in the same folder. Relative links inside `index.md` resolve
  within that folder. (No persistence-spec pattern currently ships a companion.)

A pattern name that has no matching folder is an **error** — report it loudly; never skip it
silently.

## Catalog

| Pattern | Folder | Companions |
|---|---|---|
| cleanup-fixtures | [cleanup-fixtures/](cleanup-fixtures/) | — |
| collection-fixtures | [collection-fixtures/](collection-fixtures/) | — |
| command-repo-spec-template | [command-repo-spec-template/](command-repo-spec-template/) | — |
| command-repository | [command-repository/](command-repository/) | — |
| implementation-roadmap | [implementation-roadmap/](implementation-roadmap/) | — |
| mappers | [mappers/](mappers/) | — |
| migration | [migration/](migration/) | — |
| migration-vocabulary | [migration-vocabulary/](migration-vocabulary/) | — |
| persistence-fixtures | [persistence-fixtures/](persistence-fixtures/) | — |
| query-context | [query-context/](query-context/) | — |
| query-repository | [query-repository/](query-repository/) | — |
| repository-test-rules | [repository-test-rules/](repository-test-rules/) | — |
| table-definitions | [table-definitions/](table-definitions/) | — |
| unit-of-work | [unit-of-work/](unit-of-work/) | — |
| updates-report-template | [updates-report-template/](updates-report-template/) | — |
