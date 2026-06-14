---
name: authoring-workflow
description: The ordered procedure for authoring a complete diagram set from a domain description — which files to emit, the build order within each, and the self-review pass against the theme docs.
user-invocable: false
---

# Authoring workflow

**Applies to:** authoring a new aggregate's diagram set, or a major addition to an existing one.

This is the spine that ties the per-theme convention docs together. Read it first when you are asked to *write* diagrams; load each theme doc on demand as you reach its step. Every rule referenced below lives in a sibling theme doc (`stereotypes/`, `naming/`, …) — this doc tells you the order, not the rules.

## What to emit

For an aggregate with kebab stem `<stem>`, author up to four kinds of file (see `sections-and-files/`):

| File | Always? | Contents |
|---|---|---|
| `<stem>.md` | yes | the domain diagram (aggregate root, children, VOs, TypedDicts, events, repositories) + trailing `## Invariants` + `## Implementation` + `## Artifacts` |
| `<stem>.commands.md` | yes | `<<Application>>` `<Aggregate>Commands` service + its `## Invariants` |
| `<stem>.queries.md` | yes | `<<Application>>` `<Aggregate>Queries` service (no trailing prose) |
| `<stem>.ops.<service>.md` | only for event-driven orchestration/inference | one `<<Application>>` ops class per service, N-per-aggregate (see `ops-services/`) |

A purely structural aggregate may ship only `<stem>.md` with empty command/query stubs — but prefer the full set.

## Build order

### 1. Domain diagram (`<stem>.md`)
1. **Front-matter & frame** — open the ` ```mermaid ` fence with the YAML header (`title` + `config.class.hideEmptyMembersBox: true`), then `classDiagram` (`sections-and-files/`).
2. **Aggregate root** — declare the `<<Aggregate Root>>` (`stereotypes/`); give it a bare-`str` `-id`, its descriptive/identity scalars (group cohesive ones into a Details VO — `value-objects/`), child collections, and root-only `-created_at`/`-updated_at` (`naming/`).
3. **Children & value objects** — model owned collections as plural collection VOs, leaf holders as `<<Value Object>>`, identity-bearing children as `<<Entity>>` (decide Entity-vs-VO by identity provenance — `value-objects/`). Pick the lifecycle shape (`lifecycle/`).
4. **Factories & methods** — `new(...)$` returning the owning type, intent-named alternate constructors, imperative `None`-returning mutators, fixed predicate/lookup prefixes (`naming/`).
5. **TypedDicts** — the `Data` write shapes and (if there is a query side) the `Info`/`Brief`/`Filtering`/`ListResult` read family (`typed-dicts/`).
6. **Repositories** — the CQRS `Command<X>Repository` / `Query<X>Repository` split with the fixed finder/`save` vocabulary (`repositories/`).
7. **Domain events** — `<<Domain Event>>` classes (PascalCase past-tense + identity envelope) and `emits` edges (`domain-events/`).
8. **Relationships** — wire `*--` composition with quoted cardinality, `-->` association verbs, `--()` pass-through/emission, and any `%%` markers (`relationships/`). Enforce the aggregate boundary (`aggregate-boundary/`).
9. **Invariant prose** — close with the `## Invariants` section keyed by `### <Class>` / `### <Class>.<method>` (`invariant-prose/`), then `## Implementation` + `## Artifacts` (`sections-and-files/`).

### 2. Commands & queries (`<stem>.commands.md`, `<stem>.queries.md`)
Derive the `<<Application>>` services: inject the repositories (+ `DomainEventPublisher` on commands), draw the `--()` role-label edges (`uses`/`manipulates`/`raises`/`returns`/`takes as argument`), and document each command's `## Invariants` flow (lookup-or-raise → call → persist → publish). See `application-services/`. The query derivation can be mechanized via `model-diagrams:query-derivation`.

### 3. Ops services (`<stem>.ops.<service>.md`), if applicable
For event-fed orchestration/inference, author one ops class per service with `on_<event>` handlers, the wide shared envelope, `<<Interface>>`/`<<Service>>` ports via `--() : uses`, and the handler-return-early vs demand-action-raise fork. See `ops-services/`.

## Self-review pass

Before handing off, walk each theme doc's **Review** bullets against what you wrote — they are the same canonical rules a reviewer uses to *suppress* false positives, so they double as your conformance checklist. Then optionally run `@model-diagrams:diagram-reviewer <file>` for an independent architectural pass; anything it flags that a theme doc marks canonical is a false positive, not a defect.

## Cross-references

The diagram conventions describe *notation and structure*. The downstream **code** patterns they feed live in other plugins — consult them for implementation, not for diagram authoring: `domain-spec:patterns` (domain classes), `application-spec:ops` / `application-spec:commands` (application services), `spec-core:naming-conventions` (stem & file naming, the single source of truth for the filename rules summarized in `sections-and-files/`).
