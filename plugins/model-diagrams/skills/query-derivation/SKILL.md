---
name: query-derivation
description: Rules for deriving the query part of a domain diagram (Query<X>Repository, <X>Info, nested *Info, <X>Filtering, Brief<X>Info, <X>ListResult) from the command part.
when_to_use: Use when generating or regenerating the query block of a Mermaid domain diagram from its command block — consulted by the derive-query-part skill and the query-part-deriver agent.
user-invocable: false
---

# Query Part Derivation

## Purpose

A domain diagram in this project has a **command part** (the aggregate root, its
`Command<X>Repository`, child entities / value objects, domain events, and
`<<TypedDict>>` data structures) and a **query part** (the read-side classes).
The query part is almost entirely a mechanical projection of the command part.

This skill is the single source of truth for that projection. It is consulted by:

- `model-diagrams:derive-query-part` — the orchestrator skill that interviews the
  user and delegates the write.
- `model-diagrams:query-part-deriver` — the agent that parses the command part and
  writes the query classes in place.

Both must derive identical output from identical input; divergence between them is
a bug in whichever one drifted from this skill.

## Command-part inputs

From the `classDiagram` block, identify:

- **`<X>`** — the single `<<Aggregate Root>>` class. Its private fields (`-name`)
  and its computed properties (`+status`) are the source of the read model.
- **`Command<X>Repository`** — the `<<Repository>>` whose name starts with
  `Command`. Its lookup methods seed the query repository.
- **Child classes** — every `<<Entity>>` / `<<Value Object>>` reachable from `<X>`
  through composition (`*--`) or aggregation (`o--`).
- **Command-side `<<TypedDict>>`** — `*Data` types and shared types (e.g.
  `Globals`, `ParsingError`). These are reuse candidates (see *Type reuse rule*).

Domain events, domain services, and `Command<X>Repository` itself are **not**
projected — the query part ignores them.

`<x>` below is the aggregate name in `snake_case`; `<X>` is the class name.

## Query-part outputs

Emit these six class kinds, in this order, at the **tail of the `classDiagram`
block** — after the last command class, before the closing ` ``` `.

### 1. `Query<X>Repository` `<<Repository>>`

- `find_<x>(<x>_id: str) <X>Info | None` — always emitted; the projection of
  `Command<X>Repository.<x>_of_id`.
- For each **alternate lookup** on the command repository — any method returning
  the aggregate `<X>` that is not `<x>_of_id` (e.g. `template_of_source_id`,
  `project_with_details`) — a `find_<x>_by_<thing>(<same params>) <X>Info | None`.
  `<thing>` is the distinguishing noun (`template_of_source_id` →
  `find_template_by_source`; `project_with_details` → `find_project_by_details`).
  Whether each alternate lookup is projected is a **feedback point** (see below).
- `find_<x>s(filtering: <X>Filtering | None, pagination: Pagination | None) <X>ListResult`
  — always emitted.
- `has_*` methods, `save`, and `delete` are **never** projected.

`Pagination` is an external shared type — reference it, never declare it.

### 2. `<X>Info` `<<TypedDict>>`

The full read model. One field per aggregate-root field, all public (`+`),
applying the *Field flattening rules*. Computed properties (`+status`, `+errors`)
are included as plain fields. Field omission is a **feedback point**.

### 3. Nested `<Child>Info` `<<TypedDict>>`

For every child collection surfaced in `<X>Info` (or recursively in another
`<Child>Info`), emit a `<Child>Info` `<<TypedDict>>` derived from the child class
by the same rules — **unless the type reuse rule applies**.

### 4. `<X>Filtering` `<<TypedDict>>`

Optional scalar filter fields, each typed `T | None`. The proposed default set is
every filterable scalar on the aggregate — typically `name`, `code`, `enabled`,
`status`, and aggregate-specific scalars (`evo_version`, `project_type`, …).
`id`, `created_at`, and `updated_at` are excluded. The final set is a
**feedback point**.

### 5. `Brief<X>Info` `<<TypedDict>>`

The list-row projection: **every scalar field of `<X>Info`**, dropping every
`list[...]` field and every nested-`<<TypedDict>>` field. Keeps `id`, `code`,
`name`, `enabled` / `status`, identity scalars (`source_id`, `evo_version`),
`created_at`, `updated_at`.

### 6. `<X>ListResult` `<<TypedDict>>`

Exactly two fields:

- `<x>s: list[Brief<X>Info]` — the field name is the `snake_case` plural of the
  aggregate. When the plain plural reads awkwardly, a `_list` suffix is used
  (e.g. `conversion_reqs_list`).
- `total: int`.

## Field flattening rules

Applied when projecting any class (`<X>` or a child) into a `*Info` `<<TypedDict>>`:

- **Scalar field** (`str`, `int`, `bool`, `datetime`, `str | None`, …) — copied
  verbatim, visibility changed to `+`.
- **Single value-object field** (`details: Details`) — **inlined**: the VO's own
  scalar fields are spliced in, the VO field itself disappears. `DomainType` with
  `details: Details { name, description }` → `DomainTypeInfo` carries `name` and
  `description`, not `details`.
- **Collection field** — a Collection Value Object (`categories: Categories`) or a
  direct list (`lookups: list[Lookup]`) — **flattened** to `<field>: list[<Child>Info]`.
- **Computed property** (`+status: str`) — copied as a plain field.

## Type reuse rule

When a field's projected shape exactly matches an existing **command-side
`<<TypedDict>>`**, reference that type instead of minting a parallel `*Info`:

- A whole child whose read shape equals an existing TypedDict → reuse it
  (`Globals` is referenced directly by `TemplateInfo`; `ParsingError` by
  `ConversionReqsInfo`).
- A single field whose element type matches a command-side TypedDict → reference
  it inside the otherwise-new `*Info` (`LookupInfo` is minted because `Lookup`
  carries an `id` the command `LookupData` lacks, but its `arguments` /
  `response` fields still reuse `LookupArgumentData` / `EntryItemData`).

Mint a new `<Child>Info` only when the shape genuinely diverges. The rule is
applied per field, recursively.

## Relationship arrows

After the query classes, emit:

```
Query<X>Repository --> <X>Info : returns
Query<X>Repository --> <X>ListResult : returns
Query<X>Repository --> <X>Filtering : takes as argument
```

For each nested collection field in an `*Info`:

- Minted `<Child>Info` → composition: `<Parent>Info *-- "<mult>" <Child>Info`.
- Reused command-side TypedDict → lollipop: `<Parent>Info --() "<mult>" <Type>`.

`<mult>` is the multiplicity of the collection in the command part — for a
flattened Collection VO it is the Collection-VO-to-element multiplicity
(`Categories *-- "0..n" Category` → `TemplateInfo *-- "0..n" CategoryInfo`).

Always emit `<X>ListResult *-- "0..n" Brief<X>Info`.

## Regeneration (in-place replace)

The query part may already exist (a re-run after the command part changed).
Recognize the existing query classes by name — `Query<X>Repository`, `<X>Info`,
every nested `<Child>Info`, `<X>Filtering`, `Brief<X>Info`, `<X>ListResult` — and
their arrows. Remove all of them, then re-emit the freshly derived query part at
the tail of the `classDiagram` block. Command classes and the `## Invariants`
prose are never touched.

## Feedback points

Three derivation decisions are not mechanical and are settled by interviewing the
user. Defaults below apply when no feedback is given.

| Decision | Default |
|---|---|
| Which alternate command-repo lookups become `find_<x>_by_*` | all of them |
| Which aggregate fields are omitted from `<X>Info` | none — full mirror |
| Which scalars `<X>Filtering` exposes | the proposed default set above |
