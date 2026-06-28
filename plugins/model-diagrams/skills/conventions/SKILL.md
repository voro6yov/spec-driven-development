---
name: conventions
description: "Umbrella catalog of the project's Mermaid class-diagram conventions (domain, commands, queries, ops kinds), organized by theme. Each theme lives in a sibling folder's index.md. Load when AUTHORING, editing, or REVIEWING a diagram in this project — the docs give the canonical authoring rule and the matching review lens (what is canonical and must not be flagged)."
when_to_use: "Consult before writing, editing, or judging any Mermaid class diagram in this project. For authoring, start at authoring-workflow/ then load each theme on demand. For review, read the Review bullets of the relevant theme(s) — anything documented here as a convention is canonical by definition and must not be a finding."
user-invocable: false
---

# Diagram conventions (umbrella)

This skill is the **single source of truth** for what a valid hand-authored Mermaid class diagram looks like in this project — across all kinds (`<stem>.md` domain, `<stem>.commands.md`, `<stem>.queries.md`, `<stem>.ops.<service>.md`). It is a **path-resolution anchor**: it registers one catalog entry; the convention docs themselves are **supporting files** in sibling folders and are never auto-loaded — consumers Read them on demand.

It serves two lenses from one catalog:

- **Authoring (primary).** Each theme doc is an imperative spec — the canonical rule, the exact Mermaid notation, a worked example, and the sanctioned variations. Start at [`authoring-workflow/`](authoring-workflow/) for the ordered procedure, then load each theme as you reach it.
- **Review (suppression lens).** Each convention carries a **Review** bullet stating what a reviewer must treat as canonical and **not** flag. The `model-diagrams:diagram-reviewer` agent reads these to suppress false positives; a generic DDD reviewer would otherwise flag many of this project's deliberate conventions as "non-standard".

## Resolution rule

Every theme named `<theme>` resolves to the **folder** `<theme>/` sibling to this file; the doc is always `<theme>/index.md`. A theme name with no matching folder is an **error** — report it loudly; never skip it silently.

## How to use

- **Detect the diagram kind** from the filename (`<stem>.md` → domain; `.commands.md` → commands; `.queries.md` → queries; `.ops.<service>.md` → ops). Each theme doc states which kinds it applies to.
- **Authoring:** read [`authoring-workflow/`](authoring-workflow/), then load the theme docs in build order.
- **Reviewing:** read the Review bullets of the theme(s) the passage touches. If a pattern is documented here as canonical, do not flag it. Prefer omission over flagging when a pattern is neither documented here nor an architectural concern — false positives erode trust faster than a missed minor concern.

## Catalog

| Theme | Folder | Diagram kinds |
|---|---|---|
| Authoring workflow (start here) | [authoring-workflow/](authoring-workflow/) | all |
| Stereotypes | [stereotypes/](stereotypes/) | all |
| Naming | [naming/](naming/) | domain + application |
| Value Objects | [value-objects/](value-objects/) | domain |
| Repositories | [repositories/](repositories/) | domain + queries |
| TypedDicts / DTOs | [typed-dicts/](typed-dicts/) | domain + queries |
| Relationships | [relationships/](relationships/) | all |
| Application services (Commands & Queries) | [application-services/](application-services/) | commands + queries |
| Ops / orchestration services | [ops-services/](ops-services/) | ops |
| Aggregate boundary | [aggregate-boundary/](aggregate-boundary/) | domain |
| Lifecycle, soft-delete & concurrency | [lifecycle/](lifecycle/) | domain |
| Domain events | [domain-events/](domain-events/) | domain + commands/ops |
| Invariant prose | [invariant-prose/](invariant-prose/) | domain + commands + ops |
| Sections & file layout | [sections-and-files/](sections-and-files/) | all + the file set |

## Provenance & maintenance

- These docs are the **operational source of truth** for authoring and review. They were extracted from a cross-cutting analysis of the project's diagram corpus (the `ltsd-step` STPS domain diagrams).
- Each theme doc opens with a **`## Ground knowledge`** section: the canonical DDD pattern(s) the convention instantiates (named, with sources — Evans/Vernon/Khononov/Richardson/Lawrence/Meyer/Kleppmann) and, where applicable, the **deliberate divergence** from canon. This is what lets a reviewer cite the principle *behind* a suppression instead of asserting it, and tells authors which rules are general DDD vs. project-specific. It was distilled from the personal knowledge base; concepts are named (not wiki-linked) so the docs stay self-contained.
- This umbrella **replaces** the former single-file `model-diagrams:diagram-conventions` review skill: its five suppression conventions were folded into the matching theme docs' **Review** bullets (pass-through arrow → `relationships/`; direct-raises-only + cross-cutting invariants → `invariant-prose/`; collection Value Objects → `value-objects/`; idempotent `<X> | None` → `application-services/`).
- When the user identifies a new false positive or a new authoring rule, update the relevant theme doc here — not the reviewer agent. Keep examples concrete and grounded in real diagram files; where a convention is project-specific (not general DDD), say so, because that is what stops the false positive.
