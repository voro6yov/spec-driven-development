---
name: ops-updates-report-template
description: Reference template for the ops-axis updates report (`<stem>.application/ops-updates.md`) emitted by ops-updates-detector and consumed by the messaging-spec and rest-api-spec update flows. Use when generating, parsing, or reviewing this report.
user-invocable: false
disable-model-invocation: false
---

# Ops Updates Report Template

> **Scope of this skill:** output format only. The detector workflow (globbing the ops diagrams, splitting each Mermaid block, structural diffing, surface-marker and messaging-marker parsing, prose-section diffing, summary writing voice) lives in the producer agent body (`ops-updates-detector`).

This template describes the report that diffs **every** ops application-service diagram of one aggregate against `git HEAD`. Unlike the commands/queries axis — one diagram, one anchor — the ops axis has **N diagrams per aggregate** (`<dir>/<stem>.ops.<op-name>.md`, one per service, name-discriminated by `<op-name>`). The report therefore wraps the familiar per-anchor section vocabulary in one `## Service: \`<op-name>\`` block per touched service, plus an aggregate-wide `## Summary` and `## Affected Categories` footer.

It is the single source of truth for the schema both downstream update flows parse:

- `messaging-spec` (`messaging-updates-writer`) reads the per-service **Messaging Markers** and **Per-Method Changes** blocks.
- `rest-api-spec` (`rest-api-updates-writer`) reads the per-service **Per-Method Changes** and **Surface Markers** blocks plus the `## Affected Categories` footer.

---

## File location

One report per aggregate, written inside the existing per-plugin folder:

```
<dir>/<stem>.application/
└── ops-updates.md          (produced by ops-updates-detector)
```

`<stem>` matches the aggregate stem (e.g. `conversion-reqs.md` → `conversion-reqs.application/ops-updates.md`). A single report covers **all** `<stem>.ops.*.md` diagrams.

---

## Anchor class concept

Each ops diagram has exactly one **brace-body class** — the free-form orchestration service class `<X>` (e.g. `MappingRulesInferencing`), identified **structurally** (it is the unique `class <X> { ... }` block), with **no** `<<Application>>` stereotype and **no** `Commands`/`Ops`/`Service` suffix. It is the **anchor** for its service. Every other class name in an ops diagram appears as a **link endpoint only** (collaborators declared with their members elsewhere), so ops diagrams declare no non-anchor class bodies and therefore no `<<Domain Event>>` blocks (external events live on the commands diagram).

The contract `kebab-case(<X>) == <op-name>` holds, so the stable per-service key is `<op-name>` (the filename discriminator). A change of the braced class name within a fixed `<op-name>.md` is an anchor rename and a detector hard-fail (it would also require a filename change).

---

## Freshness sentinel

Line 1 of the report is a combined-digest sentinel over **all** ops diagrams:

```
<!-- ops-detector-baseline: digest=<sha> -->
```

`<sha>` is `git hash-object --stdin` of the newline-joined, `<op-name>`-sorted list of `"<op-name>\t<head_hash>\t<wt_hash>"` rows (`<head_hash>` is `none` for an untracked/first-run diagram). The detector fast-paths (no rewrite) when the recomputed digest equals the on-disk sentinel. A malformed/absent sentinel is treated as `digest=none` and never aborts.

---

## Schema

Substitute every `<placeholder>` with the actual value when rendering.

````markdown
# Ops Updates Report

_Baseline: git HEAD. Each `<dir>/<stem>.ops.<op-name>.md` compared against its `HEAD:` blob._

## Summary

- Ops services: <N> added, <N> removed, <N> changed
- Anchor methods: <N> added, <N> removed, <N> signature-changed, <N> surface-remapped, <N> prose-changed
- Dependencies: <N> added, <N> removed, <N> type-changed
- External Interfaces: <N> added, <N> removed
- Surface Markers: <N> surfaces added, <N> removed; <N> method remappings
- Messaging Markers: <N> consumers touched, <N> rows changed
- Raised Exceptions: <N> added, <N> removed
- Application Class Relationships: <N> changed
- Description: <N> sections changed

## Service: `<op-name>` (service added|service removed)

_Class: `<X>`._

### Dependencies

- Dependency added: `<name>: <Type>`
- Dependency removed: `<name>: <Type>`
- Dependency changed: `<name>`: type `<OldType>` → `<NewType>`

### Per-Method Changes

#### `<method_name>`

**Signature:** `<old signature>` → `<new signature>`

**Surface:** `<old surface>` → `<new surface>`

**Messaging:** Added handler binding `<Event> via (<SourceDest>, <method>)`

**Prose — `<section heading>`:**

Summary: One-paragraph natural-language description of what changed in this prose section.

Diff:
```diff
- old line
+ new line
```

### Surface Markers

#### Surface Set
- Added: `<surface>`
- Removed: `<surface>`

#### Method Membership
- `<method_name>`: `<old surface>` → `<new surface>`

### Messaging Markers

#### `<consumer-name>` (consumer added|consumer removed)

- Row added: `<OpsClass> --() <Event> : handles (<SourceDest>, <method>)`
- Row removed: `<OpsClass> --() <Event> : handles (<SourceDest>, <method>)`
- Row changed: `<old row>` → `<new row>`

### Raised Exceptions
- Added: `ExceptionName`
- Removed: `ExceptionName`

### External Interfaces
- Added: `InterfaceName`
- Removed: `InterfaceName`

### Application Class Relationships
- Added: `<OpsClass> --() Target : <label>`
- Removed: `<OpsClass> --() Target : <label>`
- Changed: `<OpsClass> --() Target`: label `: <old label>` → `: <new label>`

### Orphan Prose Changes

#### Preamble

**Summary:** One-paragraph natural-language description.

**Diff:**
```diff
- old line
+ new line
```

## Affected Categories

- <category>
````

---

## Rendering rules

### Top-level sections

- `## Summary` and `## Affected Categories` are **always emitted**, regardless of content.
- One `## Service: \`<op-name>\`` block is emitted **per touched service** — a service whose diagram was added, removed, or changed against HEAD. A byte-stable ops diagram emits **no** service block. Services render in `<op-name>` lexicographic order.
- When no ops diagram changed (every service byte-stable, or the aggregate has zero ops diagrams), render the `## Summary` body as the single line `No changes detected.`, the footer as `_None._`, and emit no service blocks.

### Service-block lifecycle annotation

- A service whose diagram is **new** (not in HEAD) renders `## Service: \`<op-name>\` (service added)`; every dependency/method/edge reads as added.
- A service whose diagram was **deleted** (in HEAD, gone from the working tree) renders `## Service: \`<op-name>\` (service removed)`; every dependency/method/edge reads as removed.
- A service present in both versions renders `## Service: \`<op-name>\`` with no annotation.
- The `_Class: \`<X>\`._` line names the braced anchor class (working-tree name; HEAD name for a removed service).

### Within-service sections

Inside each `## Service:` block, the `###` sub-sections render in this fixed order, each **omitted when empty**:

1. `### Dependencies`
2. `### Per-Method Changes`
3. `### Surface Markers`
4. `### Messaging Markers`
5. `### Raised Exceptions`
6. `### External Interfaces`
7. `### Application Class Relationships`
8. `### Orphan Prose Changes`

The per-method block shape, the Added/Removed/Changed within-section ordering, the `**Signature:**`/`**Surface:**`/`**Messaging:**`/`**Prose —**` sub-field rules, the default-fallback surface rendering (`default → <s>`), and the prose `Summary:`/`Diff:` convention are **identical to `application-spec:application-updates-report-template`** — apply that skill's "Per-Method Changes", "Surface Markers", "Raised Exceptions", "Application Class Relationships", and "Orphan Prose Changes" rendering rules verbatim, one level deeper (its `##` → this skill's `###`, its `###` → `####`, its `####` method blocks → `#####`). The only ops parameterization: **Messaging Markers use the relaxed binding form** — the source class is the free-form `<OpsClass>` (no `Commands` suffix) and the bound method is a **free name** (not `on_<event>`); rows render verbatim from the diagram's `<OpsClass> --() <Event> : handles (<SourceDest>, <method>)` form.

### `## Summary`

- Counts are **aggregated across all services**. If every count is zero, replace the bullet list with `No changes detected.`
- If any ops diagram's HEAD had zero or >1 Mermaid blocks (degraded baseline), append `_warning: HEAD version of \`<op-name>\` had <count> Mermaid blocks; structural baseline treated as empty._` immediately after the Summary bullet list, one line per degraded service.
- There is **no** `External Domain Events` row — ops diagrams declare no `<<Domain Event>>` blocks.

---

## `## Affected Categories` computation

The footer lists every category that has at least one structural change **anywhere across the services** — it is the orchestrator's primary dispatch input. Multiple triggers coalesce to a single bullet (the footer is a set).

### Trigger → category mapping

| Trigger | Category |
|---|---|
| Any service's per-method block has a delta (signature / surface / messaging-binding / prose), or a method was added/removed | `methods` |
| Any service's anchor dependency added / removed / type-changed | `dependencies` |
| Any service's `: raises` outgoing edge added or removed | `raised-exceptions` |
| Any service's collaborator (`<<Interface>>` / domain-service) link added or removed | `external-interfaces` |
| Any service's surface set changed OR any per-method surface assignment changed | `surface-markers` |
| Any service's `%% Messaging - <C>` block added / removed / row-changed | `messaging-markers` |
| An ops diagram was added or removed entirely | `methods` (the service's whole method set is added/removed) |

Orphan prose does **not** contribute to category dispatch (audit-trail only).

### Canonical category order

When listing categories, use this sequence (omit categories whose triggers did not fire):

1. `methods`
2. `dependencies`
3. `raised-exceptions`
4. `external-interfaces`
5. `surface-markers`
6. `messaging-markers`

If the set is empty, render the single line `_None._`.

---

## Not in scope

Same exclusions as `application-spec:application-updates-report-template` (renames surface as remove+add; no code-level diffs; no cross-diagram reconciliation hints; no hand-edit reconciliation; reordering is a no-op), plus:

- **No `<<Domain Event>>` lifecycle.** External events consumed by an ops handler are declared on the commands diagram and tracked by `commands-updates-detector`; the ops detector never reports event member changes.
- **No per-service report files.** A single aggregate-wide `ops-updates.md` covers every `<op-name>` — there is no `ops.<op-name>-updates.md`.
