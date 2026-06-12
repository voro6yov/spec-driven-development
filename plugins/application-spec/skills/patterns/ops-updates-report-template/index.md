---
name: ops-updates-report-template
description: Reference template for the ops-axis updates report (`<stem>.application/ops-updates.md`) emitted by ops-updates-detector and consumed by the application-spec code-update flow plus the messaging-spec and rest-api-spec update flows. Use when generating, parsing, or reviewing this report.
user-invocable: false
disable-model-invocation: false
---

# Ops Updates Report Template

> **Scope of this skill:** output format only. The detector workflow (globbing the ops diagrams, splitting each Mermaid block, structural diffing, surface-marker and messaging-marker parsing, prose-section diffing, summary writing voice) lives in the producer agent body (`ops-updates-detector`).

This template describes the report that diffs **every** ops application-service diagram of one aggregate against `git HEAD`. Unlike the commands/queries axis — one diagram, one anchor — the ops axis has **N diagrams per aggregate** (`<dir>/<stem>.ops.<op-name>.md`, one per service, name-discriminated by `<op-name>`). The report therefore wraps the familiar per-anchor section vocabulary in one `## Service: \`<op-name>\`` block per touched service, plus an aggregate-wide `## Summary` and `## Affected Categories` footer.

It is the single source of truth for the schema every downstream flow parses:

- `application-spec` (`code-brief-writer`, the `/update-code` Phase-1 gather agent) reads the aggregate-wide **Affected Artifacts** table (to enumerate the ops impl / exceptions / test files Phase 2 must touch) plus the per-service **Per-Method Changes** and **Raised Exceptions** blocks (for the member bullets).
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

**Surface:** `<old surface set>` → `<new surface set>`

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
- `<method_name>`: `<old surface set>` → `<new surface set>`

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

## Affected Artifacts

| Path | Action | Driving section |
|---|---|---|
| application/<agg>/<op_snake>.py | modify | Service: `<op-name>` (Per-Method Changes; Dependencies) |
| domain/<agg>/exceptions.py | modify | Service: `<op-name>` (Raised Exceptions) |
| tests/integration/<agg>/test_<op_snake>.py | modify | Service: `<op-name>` (Per-Method Changes: Added/Removed) |
````

---

## Rendering rules

### Top-level sections

- `## Summary`, `## Affected Categories`, and `## Affected Artifacts` are **always emitted**, regardless of content.
- One `## Service: \`<op-name>\`` block is emitted **per touched service** — a service whose diagram was added, removed, or changed against HEAD. A byte-stable ops diagram emits **no** service block. Services render in `<op-name>` lexicographic order.
- When no ops diagram changed (every service byte-stable, or the aggregate has zero ops diagrams), render the `## Summary` body as the single line `No changes detected.`, the `## Affected Categories` footer as `_None._`, the `## Affected Artifacts` table as the header row only (no data rows), and emit no service blocks.

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

The per-method block shape, the Added/Removed/Changed within-section ordering, the `**Signature:**`/`**Surface:**`/`**Messaging:**`/`**Prose —**` sub-field rules, the surface-set rendering (each side a canonical-ordered comma-joined surface set, with the implicit-default singleton rendered as `default` — e.g. `default → <s>`, `v1 → v1, internal`), and the prose `Summary:`/`Diff:` convention are **identical to `application-spec:application-updates-report-template`** — apply that skill's "Per-Method Changes", "Surface Markers", "Raised Exceptions", "Application Class Relationships", and "Orphan Prose Changes" rendering rules verbatim, one level deeper (its `##` → this skill's `###`, its `###` → `####`, its `####` method blocks → `#####`). The only ops parameterization: **Messaging Markers use the relaxed binding form** — the source class is the free-form `<OpsClass>` (no `Commands` suffix) and the bound method is a **free name** (not `on_<event>`); rows render verbatim from the diagram's `<OpsClass> --() <Event> : handles (<SourceDest>, <method>)` form.

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

## `## Affected Artifacts` computation

This table is the **application code-update** consumer's enumeration of the on-disk files Phase 2 must touch for the ops axis — the ops counterpart of the `## Affected Artifacts` table `application-spec:application-updates-report-template` derives for the commands/queries axis. It is **mechanically derived** from the per-service structural deltas (Step 4 of `ops-updates-detector`); orphan prose never contributes a row.

### Path placeholders

Per `spec-core:naming-conventions`, given aggregate stem `<stem>` and a touched service `<op-name>`:

- `<agg>` = `<stem>` with every `-` replaced by `_` (the aggregate Python package dir name).
- `<op_snake>` = `<op-name>` with every `-` replaced by `_` (the ops service module name; the braced anchor class `<X>` lives in `application/<agg>/<op_snake>.py`).

All paths are **repo-package-root-relative** (they begin with `application/`, `domain/`, or `tests/`), exactly as the commands/queries `updates.md` table renders them.

### Derivation rules (per touched service `<op-name>`)

Let the service lifecycle be `added` (new at HEAD-absent), `removed` (deleted), or `changed` (present both versions). The per-row **Action** is `add` for an added service, `remove` for a removed service, and `modify` for a changed service — except the shared `exceptions.py` row, which is always `modify`.

| Rule | Trigger (any of) | Row |
|---|---|---|
| O1 — impl module | the service has ≥1 Per-Method delta (added / removed / signature / surface / messaging / prose), **or** ≥1 Dependencies or External-Interfaces delta, **or** the service was added/removed | `application/<agg>/<op_snake>.py` — action per lifecycle — Driving `Service: \`<op-name>\` (<sub-sections that fired, ';'-joined>)` |
| O2 — integration tests | the service has a **structural** method `added` or `removed`, **or** the service was added/removed | `tests/integration/<agg>/test_<op_snake>.py` — action per lifecycle — Driving `Service: \`<op-name>\` (Per-Method Changes: <Added/Removed>)` |
| O3 — application exceptions | the service has ≥1 Raised Exceptions `Added` or `Removed` | `domain/<agg>/exceptions.py` — action `modify` — Driving `Service: \`<op-name>\` (Raised Exceptions)` |

**Coalescing.** `domain/<agg>/exceptions.py` is a single shared file across every ops service (and across the commands/queries `updates.md`). Emit it **at most once** in this table even when several services add/remove exceptions; the Driving cell lists every contributing `Service: \`<op-name>\``, `; `-joined. The application `code-brief-writer` further coalesces this row with the same path in the commands/queries `updates.md`.

**Deliberately not emitted.** Ops dependency/interface churn that adds or removes a **service** (a new collaborator `<<Interface>>` / domain-service) also moves `services.md`, and the commands/queries `application-updates-writer` already derives the `containers.py` / `tests/conftest.py` / `infrastructure/services/<x>/…` / `tests/fakes/…` rows from that `services.md` diff (its `services-finder` includes ops services). This ops table therefore emits **only** the three ops-owned artifacts above — the ops impl module (whose own `__init__` constructor is rewired for the dependency change via the O1 row), its raised exceptions, and its integration tests — and never duplicates the DI/fake wiring rows.

### Ordering

Render rows grouped by service in `<op-name>` lexicographic order, and within a service in the rule order O1, O3, O2 (impl, exceptions, tests) — matching the commands/queries table's impl-before-tests convention. The coalesced `exceptions.py` row renders once at the position of the first contributing service.

---

## Not in scope

Same exclusions as `application-spec:application-updates-report-template` (renames surface as remove+add; no code-level diffs; no cross-diagram reconciliation hints; no hand-edit reconciliation; reordering is a no-op), plus:

- **No `<<Domain Event>>` lifecycle.** External events consumed by an ops handler are declared on the commands diagram and tracked by `commands-updates-detector`; the ops detector never reports event member changes.
- **No per-service report files.** A single aggregate-wide `ops-updates.md` covers every `<op-name>` — there is no `ops.<op-name>-updates.md`.
