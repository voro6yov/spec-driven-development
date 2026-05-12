# REST API Updates Report — Design

This note describes the design of `<dir>/<stem>.rest-api/updates.md`, the **REST-API-side analog of the domain updates report** (`<dir>/<stem>.domain/updates.md`).

It is the input contract a future `/rest-api-spec:update-code` skill will consume to surgically update generated REST API artifacts (per-surface serializers, endpoint modules, the FastAPI app wiring, fixtures, endpoint tests) without re-running `/rest-api-spec:generate-code` from scratch — analogous to how `domain-spec:code-updater` consumes the domain `updates.md` (see [`plugins/domain-spec/notes/code-updater-approach-c.md`](../../domain-spec/notes/code-updater-approach-c.md)) and how `<stem>.persistence/updates.md` feeds the persistence code updater (see [`plugins/persistence-spec/notes/updates-report.md`](../../persistence-spec/notes/updates-report.md), the note this one is modelled on).

For the catalog of *upstream* domain deltas that drive the REST API spec updater, see [`update-types.md`](update-types.md). For the spec updater design that produces the artifacts this report captures, see [`spec-updater-approach.md`](spec-updater-approach.md).

---

## Goal

Capture, in structured form, every change `/rest-api-spec:update-specs` made to `<stem>.rest-api/spec.md`, in a shape that lets a downstream code updater dispatch per-artifact updates without re-diffing the spec.

The report:

- Is **persistent** (committed alongside the spec) so it survives between `update-specs` and `update-code`.
- Is **per-artifact** rather than per-class: it lists *which generated files change* (and how), not which domain classes changed. The domain `updates.md` already covers per-class deltas; this report's job is to project them onto REST API artifacts.
- Is **surface-scoped**: every per-table section is grouped by `## Surface: <name>` (matching `spec.md`'s own organization), because the generated code is laid out per surface (`api/serializers/<surface>/`, `api/endpoints/<surface>/`).
- Is **stable** between identical inputs — same domain `updates.md` hash + same pre-update spec → byte-identical report.
- Is **self-contained** for the code updater: combined with the updated spec, it has everything needed to compute the on-disk edits.

---

## Lifecycle and ownership

### Producer

`<stem>.rest-api/updates.md` is produced by `/rest-api-spec:update-specs` as a **side effect** of the spec update — emitted in the same run that rewrites `spec.md` (Step 3, see *Workflow integration* below). This is the same asymmetry the persistence side draws against the domain side:

| Aspect | Domain | REST API |
|---|---|---|
| Source of truth | Mermaid diagram (human-edited) | `spec.md` (generated) |
| Detection | git diff of diagram + prose | known by producer (the spec updater just rewrote the affected tables) |
| Re-diffing | unavoidable (the diagram is the only ground truth) | the spec is generated — there is no operator-intent hidden in the spec text that a separate detector would surface |

The spec updater receives `<stem>.domain/updates.md`, decides which of `response-fields-writer` / `request-fields-writer` / `parameter-mapping-writer` to re-run (per `spec-updater-approach.md` § "Dispatch tier"), re-runs them, and then emits this report. Producing a structured per-artifact report at the end of that run is a near-zero-cost byproduct — and the actual diff is recovered by the producer agent directly from `git show HEAD:<spec_file>` vs the working tree, so the orchestrator stays stateless.

#### Alternative considered: standalone `rest-api-spec:updates-detector`

A standalone detector would `git diff` `spec.md` before/after and emit the report. Rejected for the same reasons as the persistence side: it duplicates work the spec updater already performed; the spec is generated, not curated; and there is no higher-fidelity intent to recover from a separate pass. The producer agent already *does* recover the diff from `git HEAD` — but it runs as Step 3 of the updater, not as a standalone pre-pass, because there is nothing for a pre-pass to detect (the trigger is the domain `updates.md`, not a diff of `spec.md`).

> **Distinct from the commands/queries-diagram detector.** `spec-updater-approach.md` § "What this updater does NOT cover" calls for a *shared* `application-spec:updates-detector` that diffs `<stem>.commands.md` / `<stem>.queries.md` and feeds both the application updater and the REST updater the commands/queries-diagram axis. That is a different artifact from this report: the commands/queries detector is an *input* to `/rest-api-spec:update-specs` (telling it which endpoints/methods/surfaces changed); `<stem>.rest-api/updates.md` is the *output* of `/rest-api-spec:update-specs` (telling the code updater which generated files to touch). When the commands/queries detector lands, its deltas widen the set of `spec.md` changes the updater makes — and therefore the set of artifacts this report records — but it does not replace this report.

### Consumer

`<stem>.rest-api/updates.md` is consumed by the future `/rest-api-spec:update-code` skill — an analog of `domain-spec:update-code`. The code updater walks the report's `## Affected Artifacts` footer to dispatch per-file updates, reading the per-section bodies for the structured delta details.

It is **not** chained automatically into `/update-specs`. Code regeneration is a separate operator-driven step (same contract as the domain and persistence sides: spec updates on every diagram edit; code updates on demand).

### First-run pipeline

`/rest-api-spec:generate-specs` does **not** produce this report. The report describes deltas, not absolute state. On first run, `/rest-api-spec:generate-code` runs against `spec.md` directly with no report to consult.

---

## Producer architecture

The producer is split into two artifacts that mirror the persistence side's `updates-report-template` skill + `command-repo-spec-updates-writer` agent pair (which in turn mirror the domain side's `updates-report-template` skill + `updates-detector` agent).

### Reference skill: `rest-api-spec:updates-report-template`

A condensed *contract* document — schema + rendering rules, not design rationale — auto-loaded by:

- The producer agent (when rendering the report).
- The future `/rest-api-spec:update-code` consumer (when parsing the report).

Covers:

- Top-level section order (Summary → Resource Basics Changes → Endpoint Inventory Changes → Response Fields Changes → Request Fields Changes → Parameter Mapping Changes → Affected Artifacts).
- Per-section body conventions (`### Surface: <name>` grouping; Added / Removed / Modified buckets under each surface; closed action-verb vocabulary `add | modify | remove`; `_no changes_` rendering for empty sections and empty surfaces).
- Within-section ordering rules (surfaces in canonical order — versioned by integer, then non-versioned alphabetically, per `rest-api-spec:surface-markers`; within a surface, Added (by endpoint path) → Removed (by endpoint path) → Modified (by endpoint path); for nested-type deltas inside a Modified endpoint sub-block, nested types in first-mention order).
- Affected Artifacts table shape (path + action + driving-section columns).
- Sentinel placement (HTML comment recording the source domain `updates.md` hash, used by the consumer for skip-on-replay detection).

The split between schema-as-skill and design-as-notes is the same one the domain and persistence sides draw — the *why* lives here in the notes; the *how to render and parse* lives in the skill.

### Agent: `rest-api-spec:rest-api-updates-writer`

A small, deterministic agent invoked at the tail of `/rest-api-spec:update-specs` — also standalone-invocable. Composes `<stem>.rest-api/updates.md` by diffing the working-tree `spec.md` against `git HEAD`; reads the sibling domain `updates.md` only as an enrichment source for `Source delta` lookups. Does not consult any orchestrator-supplied runtime state.

The workflow shape mirrors `command-repo-spec-updates-writer` exactly: a single positional arg, recover the pre-update baseline via `git show HEAD:<file>`, write a sibling report. The schema is fully mechanical, so there is no LLM-creative step (no prose summarization).

**Arguments**:

- `<domain_diagram>` — first and only positional arg. Used solely to recover `<dir>` and `<stem>` per `rest-api-spec:naming-conventions`. The diagram itself is not parsed. (The query-vs-command classification of each endpoint — needed to route a changed endpoint to a query serializer vs a command serializer — is read off `spec.md` itself: an operation appearing in a `### Table 2: Query Endpoints` row is a query endpoint; one in a `### Table 3: Command Endpoints` row is a command endpoint. No diagram parse is needed.)

**Reads (filesystem)**:

1. **Working-tree spec** — `<dir>/<stem>.rest-api/spec.md` (must exist; otherwise hard-fail with "run `/rest-api-spec:generate-specs` first").
2. **HEAD spec** — recovered via `git ls-files --full-name` + `git show HEAD:<repo_path>`. First-run handling: missing-at-HEAD → empty baseline; the entire post-update spec is reported as Added.
3. **Domain updates report** — `<dir>/<stem>.domain/updates.md` (sibling). Missing is non-fatal; `Source delta` falls back to `(unknown source)` and the Summary line renders `_none_`.

**Reads (auto-loaded skills)**: `rest-api-spec:naming-conventions`, `rest-api-spec:updates-report-template`, `rest-api-spec:surface-markers` (for canonical surface ordering in the report).

**Output**: `<dir>/<stem>.rest-api/updates.md`, written from scratch (replaces any prior file).

**Determinism**: structured-input-driven, not LLM-creative. Re-running with byte-identical inputs (working tree + HEAD blob + domain `updates.md`) produces a byte-identical report. The Affected Artifacts table is mechanically derived:

- Response Fields Changes (Surface `S`, endpoint with Operation `OP`) → `api/serializers/<S>/<OP>.py` modify (query serializer).
- Request Fields Changes (Surface `S`, endpoint `OP`) → `api/serializers/<S>/<OP>.py` modify (command serializer).
- Parameter Mapping Changes (Surface `S`, any endpoint) → `api/endpoints/<S>/<plural>.py` modify (all endpoints of a surface share one module, so multiple per-endpoint changes in `S` collapse to one row).
- Endpoint Inventory Changes (Surface `S`, Added/Removed endpoint) → `api/serializers/<S>/<OP>.py` add/remove + `api/endpoints/<S>/<plural>.py` modify + `api/serializers/<S>/__init__.py` modify + `api/serializers/__init__.py` modify + `api/endpoints/<S>/__init__.py` modify + `api/endpoints/__init__.py` modify + `<pkg>/constants.py` modify + `<pkg>/entrypoint.py` modify. *(Commands/queries-axis only — never produced by a domain-only update; listed for when that axis is wired in.)*
- Resource Basics Changes (Surfaces row changed — a new surface) → the per-surface aggregators + `entrypoint.py` + `constants.py`, and (internal surface added) `<api_pkg>/api/auth.py` modify. *(Commands/queries-axis only.)*
- Any non-empty per-table section in Surface `S` → `tests/integration/<resource>/test_<plural>_<S>_api.py` modify.

**Standalone invocability**: supported. The writer reads everything it needs from disk (working tree + git HEAD + sibling files), so it does not require an orchestrator wrapper. Useful for testing, operator-driven recovery (e.g. when a prior `update-specs` run hard-failed after rewriting `spec.md`), and CI verification. The orchestrator (`/rest-api-spec:update-specs`) is one of several callers.

### Workflow integration

Slots into `/rest-api-spec:update-specs` as Step 3, between the table-writer regen (Step 2) and the operator one-liner (Step 4):

```
Step 0  Preflight (file checks + parse updates.md + scan commands/queries diagrams for the referenced-type set)
Step 1  Dispatch tier
Step 2  Table-writer regen (sequential)   (response-fields-writer / request-fields-writer / parameter-mapping-writer)
Step 3  Emit updates.md                   (rest-api-updates-writer)
Step 4  Report (operator one-liner)
```

The orchestrator does not need to capture pre-update `spec.md` content or the writers' edit lists — the report writer recovers the diff directly: pre-update content via `git show HEAD:<spec_file>`, post-update content from the working tree. This keeps the orchestrator stateless and lets the writer also run standalone.

The writer runs on every successful spec update, including the Tier-3 no-op early-exit at Step 1 — those produce a report with every section `_no changes_` and an empty Affected Artifacts table. This keeps the consumer's contract simple: `updates.md` always exists after a successful run. The writer does **not** run when the workflow hard-fails before Step 3 (degraded baseline, stereotype change, aggregate-root removal/rename, abort-and-reconcile on a renamed referenced type, or a runtime writer abort in Step 2) — there is no transition to describe.

---

## File location and naming

```
<dir>/<stem>.rest-api/
├── spec.md            (the resource spec)
└── updates.md         (this report)
```

Mirrors the domain and persistence conventions: `<dir>/<stem>.domain/updates.md` next to `<dir>/<stem>.domain/spec.md`; `<dir>/<stem>.persistence/updates.md` next to `<dir>/<stem>.persistence/command-repo-spec.md`.

---

## Report schema

Top-level structure (canonical section order):

```markdown
# REST API Updates Report

## Summary
## Resource Basics Changes
## Endpoint Inventory Changes
## Response Fields Changes
## Request Fields Changes
## Parameter Mapping Changes
## Affected Artifacts
```

Each section's body is either a structured delta block or `_no changes_`. Sections never disappear — empty sections render as `_no changes_` so the parser doesn't have to discriminate "absent" vs "no-op". Within a section, surfaces that have no changes render as `_no changes_` under their `### Surface: <name>` heading (or the surface is simply omitted — the template skill picks one convention; this note recommends *omit unchanged surfaces* to keep the report short, since a domain-only change typically touches one surface out of several).

### Section: Summary

A small preamble. Mirrors the domain and persistence reports' Summary blocks.

```markdown
## Summary

- Spec: docs/file/file.rest-api/spec.md
- Pre-update spec hash: <sha256 of spec.md before this run>
- Post-update spec hash: <sha256 of spec.md after this run>
- Domain updates source: docs/file/file.domain/updates.md (hash: <sha256>)
- Generated at: 2026-05-11T09:14:00Z
- Warnings: _none_
```

The two spec hashes pin the report to a specific transition; the code updater verifies the post-update hash matches the on-disk `spec.md` before consuming the report (defends against the operator running `update-code` after a stale report). The `Warnings` line carries operator-facing notes — e.g. `Nested type \`OldName\` is still referenced by a method signature in file.queries.md — the spec writer would have aborted; this report describes the state before that abort` (only emitted if the writer somehow ran past an abort condition; normally the workflow hard-fails first).

### Section: Resource Basics Changes

Tracks Table 1 deltas — Resource name, Plural, Router prefix, Surfaces.

```markdown
## Resource Basics Changes

- Resource name: was `File`, now `File` (_unchanged_)
- Plural: was `files`, now `files` (_unchanged_)
- Router prefix: was `/files`, now `/files` (_unchanged_)
- Surfaces: was `v1`, now `v1, internal` (surface added: `internal`)
```

Each line is `<field>: was X, now Y` or `_unchanged_`. If every field is unchanged, the section is `_no changes_`. **For a domain-only update this section is always `_no changes_`** — a Resource-name change is a hard-fail (the run never reaches Step 3), and Surfaces changes are a commands/queries-diagram-axis concern. The section exists for when that axis is wired in.

### Section: Endpoint Inventory Changes

Tracks Tables 2 (Query Endpoints) and 3 (Command Endpoints) deltas, per surface. Drives `api/endpoints/<surface>/<plural>.py` (the endpoint functions) and `api/serializers/<surface>/<operation>.py` (add/remove of serializer modules).

```markdown
## Endpoint Inventory Changes

### Surface: v1

#### Added
- `POST /{id}/redact` (redact) → `FileCommands.redact` — command endpoint
  - Description: Redact the file

#### Removed
- `GET /{id}/legacy-content` (find_file_legacy_content) — query endpoint

#### Modified
- `GET /{id}` (find_file)
  - Description: was "Retrieve a single File" → "Retrieve a single File with optional heavy fields (Wish List pattern)"
```

**For a domain-only update this section is always `_no changes_`** — Tables 2/3 are pure functions of the application-service diagrams. The section exists for the commands/queries-diagram axis. (When that axis lands: an Added endpoint carries its full Table 2/3 row so the code updater scaffolds the serializer module + endpoint function; a Removed endpoint triggers deletion + aggregator pruning; a Modified endpoint with only a Description change is cosmetic — the code updater may skip it or re-emit the endpoint's docstring.)

### Section: Response Fields Changes

Tracks Table 4 deltas, per surface, per query endpoint — response-DTO field rows, `**Nested:**` sub-tables, and `**Query Parameters:**` blocks. Drives the query serializer module `api/serializers/<surface>/<operation>.py`.

```markdown
## Response Fields Changes

### Surface: v1

#### Modified
- `GET /{id}` (find_file)
  - Source delta: `data-structures: FileInfo attribute text added`
  - Response field added: `text: TextExtraction | None` (includable)
  - Nested type added: `TextExtraction` (fields: `content: str`, `language: str`, `page_count: int`)
  - Query parameter modified: `include` heavy-field list `preparation_result`, `classification_result` → `preparation_result`, `classification_result`, `text`
- `GET /` (find_files)
  - Source delta: `value-objects: FileFiltering attribute mime_type added`
  - Query parameter added: `mime_type: str \| None` (decomposed from composite `FileFiltering`; default `None`)
```

Buckets are `Added` / `Removed` / `Modified` keyed by endpoint (an endpoint moves to `Modified` whenever any of its response fields, nested sub-tables, or query parameters changed; an endpoint only appears under `Added` / `Removed` here if Table 2 itself changed — which is the Endpoint Inventory section's job — so in practice this section is all-`Modified`). Within a `Modified` endpoint sub-block, the deltas are: `Response field added/removed/retyped`, `Nested type added/removed`, `Nested type \`X\` field added/removed/retyped`, `Query parameter added/removed/retyped`, `Binary response: …` (the endpoint switched to/from a binary placeholder). The `Source delta` line is the matching `<stem>.domain/updates.md` per-class change (best-effort lookup; `(unknown source)` if the sibling report is missing).

### Section: Request Fields Changes

Tracks Table 5 deltas, per surface, per command endpoint — body-field rows and `**Nested:**` sub-tables. Drives the command serializer module `api/serializers/<surface>/<operation>.py`.

```markdown
## Request Fields Changes

### Surface: v1

#### Modified
- `POST /{id}/document-types` (assign_document_types)
  - Source delta: `value-objects: DocumentTypeRequest attribute confidence added`
  - Nested type `DocumentTypeRequest` field added: `confidence: float \| None` (Optional)
```

Same bucket / delta-verb conventions as Response Fields Changes, minus the query-parameter and binary-response deltas (Table 5 has neither): `Request field added/removed/retyped`, `Nested type added/removed`, `Nested type \`X\` field added/removed/retyped`, `Body switched to/from empty-body placeholder`.

### Section: Parameter Mapping Changes

Tracks Table 6 deltas, per surface, per endpoint — the parameter→source sub-blocks. For a domain-only update the only Table 6 delta is a `Constructed from query params <f1>, <f2>, … → <Type>` source line whose constituent-field list changed (because a composite query-param type gained/lost a field). Drives `api/endpoints/<surface>/<plural>.py` (the endpoint function's app-service call kwargs / query-param-to-domain-object construction).

```markdown
## Parameter Mapping Changes

### Surface: v1

#### Modified
- `GET /` (find_files)
  - Source delta: `value-objects: FileFiltering attribute mime_type added`
  - Source line changed: `filtering` — `Constructed from query params \`status\`, \`name\` → FileFiltering` → `Constructed from query params \`status\`, \`name\`, \`mime_type\` → FileFiltering`
```

Bucket conventions match the other per-table sections. Other delta verbs (for the commands/queries-diagram axis): `Parameter added/removed` (the method gained/lost a parameter → a new/removed row), `Source reclassified` (e.g. a parameter moved from `Request body` to `Path param` because the path shape changed).

### Section: Affected Artifacts

A flat dispatch table. The code updater walks this footer top-to-bottom.

```markdown
## Affected Artifacts

| Path | Action | Driving section |
|---|---|---|
| `api/serializers/v1/find_file.py` | modify | Response Fields Changes (Surface: v1) |
| `api/serializers/v1/find_files.py` | modify | Response Fields Changes (Surface: v1) |
| `api/serializers/v1/assign_document_types.py` | modify | Request Fields Changes (Surface: v1) |
| `api/endpoints/v1/files.py` | modify | Parameter Mapping Changes (Surface: v1) |
| `tests/integration/file/test_files_v1_api.py` | modify | Response/Request/Parameter Mapping Changes (Surface: v1) |
```

Action vocabulary is closed: `add`, `modify`, `remove`. (`unchanged` files are not listed — the table only contains files the code updater must touch.) Paths are relative to the API package root (`<api_pkg>/`) for `api/...` entries and to the project root for `tests/...` / `<pkg>/...` entries — the same convention the persistence report uses for its `tables/...` vs `tests/...` entries; the code updater resolves them against the `target-locations-finder` report it runs first.

This footer is the REST-API analog of the domain `## Affected Categories` footer and the persistence `## Affected Artifacts` footer. It serves the same purpose: a flat, machine-parseable dispatch list.

---

## Per-section → code-action mapping

Quick-reference matrix the code updater dispatches against:

| Report section | Drives | Action verbs |
|---|---|---|
| Resource Basics Changes — Resource name/Plural/Router prefix | *(never happens on a domain-only update — hard-fail)* | — |
| Resource Basics Changes — Surfaces (surface added) | New per-surface package + aggregators; `entrypoint.py` `include_router`; `constants.py`; `api/auth.py` (if `internal`) | add, modify |
| Endpoint Inventory Changes — Added | New `api/serializers/<S>/<OP>.py`; new endpoint function in `api/endpoints/<S>/<plural>.py`; per-surface + root serializer aggregators; per-surface + root endpoint aggregators | add, modify |
| Endpoint Inventory Changes — Removed | Delete `api/serializers/<S>/<OP>.py`; prune endpoint function + aggregators | remove, modify |
| Endpoint Inventory Changes — Modified (Description only) | Re-emit endpoint docstring | modify |
| Response Fields Changes — Modified | Edit the response serializer body (`<Operation>Response` + nested sub-serializers + `<Operation>Request` query-params class) in `api/serializers/<S>/<OP>.py` | modify |
| Request Fields Changes — Modified | Edit the request serializer body (`<Operation>Request` + nested sub-serializers) in `api/serializers/<S>/<OP>.py` | modify |
| Parameter Mapping Changes — Modified | Edit the endpoint function's app-service call kwargs / query-param-to-domain-object construction in `api/endpoints/<S>/<plural>.py` | modify |
| Any per-table section non-empty in Surface `S` | Re-run / splice the surface's endpoint test module `tests/integration/<resource>/test_<plural>_<S>_api.py` | modify |

The code updater dispatches on `(section, surface, action verb)` to pick the right agent or template (e.g. `query-serializers-implementer` / `command-serializers-implementer` for serializer-body edits, `endpoints-implementer` for endpoint-function edits, `tests-implementer` for the test module, `app-integrator` for the aggregators/wiring when an endpoint or surface was added/removed).

---

## Worked example

Domain change: add a heavy field `text: TextExtraction | None` to the `FileInfo` `<<Query DTO>>` (the response DTO of `FileQueries.find_file`), and add a `mime_type: str` field to the `FileFiltering` `<<Value Object>>` (the composite filtering parameter of `FileQueries.find_files`). Both surface in `spec.md`; both are picked up by the conservative Tier-2 rule (`value-objects` / `data-structures` non-empty → re-run `response-fields-writer` + `request-fields-writer` + `parameter-mapping-writer`). `request-fields-writer` re-runs but produces a byte-stable Table 5 (no command method references either type). Single surface (`v1`).

`<stem>.rest-api/updates.md`:

```markdown
# REST API Updates Report

## Summary

- Spec: docs/file/file.rest-api/spec.md
- Pre-update spec hash: a1b2c3...
- Post-update spec hash: d4e5f6...
- Domain updates source: docs/file/file.domain/updates.md (hash: 7890ab...)
- Generated at: 2026-05-11T09:14:00Z
- Warnings: _none_

## Resource Basics Changes
_no changes_

## Endpoint Inventory Changes
_no changes_

## Response Fields Changes

### Surface: v1

#### Modified
- `GET /{id}` (find_file)
  - Source delta: `data-structures: FileInfo attribute text added`
  - Response field added: `text: TextExtraction | None` (includable)
  - Nested type added: `TextExtraction` (fields: `content: str`, `language: str`, `page_count: int`)
  - Query parameter modified: `include` heavy-field list `preparation_result`, `classification_result` → `preparation_result`, `classification_result`, `text`
- `GET /` (find_files)
  - Source delta: `value-objects: FileFiltering attribute mime_type added`
  - Query parameter added: `mime_type: str \| None` (decomposed from composite `FileFiltering`; default `None`)

## Request Fields Changes
_no changes_

## Parameter Mapping Changes

### Surface: v1

#### Modified
- `GET /` (find_files)
  - Source delta: `value-objects: FileFiltering attribute mime_type added`
  - Source line changed: `filtering` — `Constructed from query params \`status\`, \`name\` → FileFiltering` → `Constructed from query params \`status\`, \`name\`, \`mime_type\` → FileFiltering`

## Affected Artifacts

| Path | Action | Driving section |
|---|---|---|
| `api/serializers/v1/find_file.py` | modify | Response Fields Changes (Surface: v1) |
| `api/serializers/v1/find_files.py` | modify | Response Fields Changes (Surface: v1) |
| `api/endpoints/v1/files.py` | modify | Parameter Mapping Changes (Surface: v1) |
| `tests/integration/file/test_files_v1_api.py` | modify | Response/Parameter Mapping Changes (Surface: v1) |
```

The code updater walks the footer, dispatches each row (`find_file.py` / `find_files.py` → re-emit the response serializer bodies + the `include` / query-param classes; `files.py` → re-emit the `find_files` endpoint's `FileFiltering` construction; `test_files_v1_api.py` → re-run / splice the surface's tests), and produces the on-disk edits.

> Note `request-fields-writer` re-ran in Step 2 of the updater (the conservative Tier-2 rule fired on `value-objects`), but produced a byte-identical Table 5 — so Request Fields Changes is `_no changes_` and no command serializer appears in Affected Artifacts. The report is derived from the *actual* `spec.md` diff, not from which writers the orchestrator chose to run.

---

## Determinism and idempotency

- **Byte-stable inputs → byte-stable report.** Same `git HEAD` `spec.md` blob + same working-tree `spec.md` + same domain `updates.md` → byte-identical report.
- **Re-running `/rest-api-spec:update-specs` with no new domain changes** produces a report whose every section is `_no changes_` and whose Affected Artifacts table is empty. The code updater treats an empty report as a no-op.
- **The report reflects the spec diff, not the orchestrator's dispatch decisions.** If the conservative Tier-2 rule re-runs a writer that ends up producing a byte-stable table, that table's section is `_no changes_` — the writer's run is invisible to the report.
- **Section ordering is canonical** (Summary → Resource Basics → Endpoint Inventory → Response Fields → Request Fields → Parameter Mapping → Affected Artifacts).
- **Within each section**, surfaces appear in canonical order (versioned by integer, then non-versioned alphabetically); within a surface, Added (by endpoint path) → Removed (by endpoint path) → Modified (by endpoint path); within a Modified endpoint sub-block, nested-type deltas in first-mention order.
- **Affected Artifacts** rows appear in driving-section order (Resource Basics → Endpoint Inventory → Response Fields → Request Fields → Parameter Mapping), and within a section, in surface order then endpoint-path order, with the per-surface test module last.

---

## Cross-resource edits

For the **domain-driven axis** there are **no cross-resource edits** — a domain change only touches Tables 4/5/6 of one resource's `spec.md`, which drives only that resource's `api/serializers/<surface>/` and `api/endpoints/<surface>/` modules and its own endpoint test module. Unlike the persistence side's per-context `unit_of_work/` and `query_context/` packages (shared across aggregates), the REST layer's per-surface serializer and endpoint modules are resource-private.

The one place a *commands/queries-diagram-axis* change could ripple beyond a single resource's modules is the **project-wide aggregators and wiring** — `<api_pkg>/serializers/__init__.py`, `<api_pkg>/endpoints/__init__.py`, `<pkg>/entrypoint.py`, `<pkg>/constants.py`, and (internal-surface) `<api_pkg>/api/auth.py` — when an endpoint module or a whole surface is added/removed. The code updater handles these as **patch targets**, not regen targets (additive `include_router` lines, additive constants, additive star-import lines), exactly as the existing `app-integrator` agent does — and `app-integrator` is already idempotent, so running the code updater twice on the same report produces no incremental change. For the domain-driven axis these files never appear in Affected Artifacts.

---

## What the report deliberately does NOT include

- **Source domain class names beyond the `Source delta` one-liner.** The report describes spec-level deltas in terms of endpoints, serializer fields, nested types, and query parameters. The domain `updates.md` is the trail back to class-level deltas; readers needing more follow the upstream report.
- **Code-level diffs or generated source text.** The report says **what** to change; the code updater owns **how** (which serializer/endpoint template variant, which splicer logic).
- **Serializer / endpoint Python bodies.** Response Fields / Request Fields Changes record the field-level deltas and the nested-type shapes; the actual Pydantic serializer classes and FastAPI endpoint functions are owned by the implementer agents and their skills (`rest-api-spec:response-serializers`, `:request-serializers`, `:nested-response-serializers`, `:query-params`, `:endpoints`, …) and produced by the code updater.
- **Test-level granularity.** Per-surface test modules are listed in Affected Artifacts as `modify`; the code updater (and its companion test-splicer) decides per-test surgery from `spec.md`, not from this report. This mirrors the domain and persistence code updaters' approach.
- **Hand-edit reconciliation hints.** Hand-edits in generated artifacts (and in `spec.md`'s mechanical Description/Validation prose) are not preserved — per the spec updater contract. The code updater can flag divergence but the report doesn't pre-classify it.
- **Stable-throughput artifacts** — the shared serializer modules (`error.py`, `configured_base_serializer.py`, `json_utils.py`), `tests/conftest.py`'s resource-agnostic API-client fixtures, and (absent an internal-surface addition) `api/auth.py` and `error_handlers.py`. Those are installed once by `/rest-api-spec:generate-rest-api-deps` and never move on a domain change.
- **Domain-diagram or commands/queries-diagram content.** This report is about `spec.md` deltas. The commands/queries-diagram axis (endpoint/method/surface churn) gets its own detector (the shared `application-spec:updates-detector`); when that lands, its deltas widen this report's coverage but its raw output is not re-stated here.

---

## Hard-fail conditions

The report is not produced (the run hard-fails before reaching Step 3) when:

- The spec updater itself hard-fails — degraded baseline, any stereotype change, aggregate-root removal/rename, the abort-and-reconcile gate on a renamed/removed referenced type, or a runtime abort from a table writer. See `spec-updater-approach.md` § "Hard-fail conditions".
- The working-tree `spec.md` is missing or unparseable.
- The post-update `spec.md` hash cannot be computed (filesystem error).

In all other cases the report is emitted, even if every section is `_no changes_`.

---

## Open questions

1. **Sentinel for re-run detection.** The report should carry a top-of-file HTML-comment sentinel recording the source domain `updates.md` hash (`<!-- rest-api-updates from domain-updates-hash:<hash> -->`), so a code updater can detect "I already applied this report" and skip. The persistence side has the same open item; whatever placement / format that converges on, this report adopts.

2. **Multi-update batching.** If the operator runs `/rest-api-spec:update-specs` N times before catching up with `/rest-api-spec:update-code`, do we stack N reports or merge them? Recommended (same as the persistence side): each `update-specs` run writes a fresh `updates.md` *replacing* the prior one, but if a prior report's `domain-updates-hash` sentinel hasn't been consumed yet (the code updater leaves its own marker on consumption), fold its Affected Artifacts into the new report so nothing is dropped. Open: whether the folding is the producer's contract or the consumer's.

3. **Omit-vs-render unchanged surfaces.** This note recommends *omitting* a surface from a per-table section when it has no changes (keeps domain-only reports short — they typically touch one surface). The persistence side renders every section even when `_no changes_`; the surface-level analog could go either way. The template skill makes the call; downstream parsing must handle whichever convention is chosen (treat an absent `### Surface:` as `_no changes_`).

4. **Commands/queries-axis folding.** When the shared `application-spec:updates-detector` lands, `/rest-api-spec:update-specs` will also re-run `endpoint-tables-writer` (and possibly `resource-spec-initializer` for a plural change) — populating the Resource Basics Changes and Endpoint Inventory Changes sections this schema reserves. Open: whether that detector's report is passed *through* to `rest-api-updates-writer` as an additional `Source delta` enrichment source, or whether the writer keeps deriving everything from the `spec.md` diff alone (the latter keeps the writer's input set minimal but loses the "this endpoint changed because the queries diagram changed" provenance).

5. **Side-effect vs separate skill — resolved for v1.** The producer is a dedicated `rest-api-spec:rest-api-updates-writer` agent invoked at Step 3 of `/rest-api-spec:update-specs` (see *Producer architecture* above), with the schema captured in the auto-loaded `rest-api-spec:updates-report-template` skill — the same shape the persistence side settled on.

6. **Concurrent updaters.** If two operators run `/rest-api-spec:update-specs` in parallel against the same spec, both write `updates.md`. This is a Git merge conflict on a generated file — same shape as the spec-side concurrent-updater problem. Document as expected behaviour, no code support needed.

---

## Relationship to the domain / persistence / application updates reports

| Aspect | Domain | Persistence | Application | REST API |
|---|---|---|---|---|
| File path | `<dir>/<stem>.domain/updates.md` | `<dir>/<stem>.persistence/updates.md` | `<dir>/<stem>.application/updates.md` | `<dir>/<stem>.rest-api/updates.md` |
| Sibling of | the diagram | `command-repo-spec.md` | `commands.specs.md` / `queries.specs.md` | `spec.md` |
| Producer | `domain-spec:updates-detector` (standalone agent) | `/persistence-spec:update-specs` (side-effect, Step 5) | `/application-spec:update-specs` (side-effect, Step 6) | `/rest-api-spec:update-specs` (side-effect, Step 3) |
| Producer detection method | git diff of diagram + prose | known by producer (already has the deltas; recovers diff from `git HEAD`) | same | same |
| Grouping | per-class | per-artifact | per-artifact | per-artifact, surface-scoped |
| Footer | `## Affected Categories` (DDD categories) | `## Affected Artifacts` (file paths + action verbs) | `## Affected Artifacts` | `## Affected Artifacts` |
| Consumed by | spec updaters (domain, persistence, application, rest-api) **and** domain code updater | persistence code updater (only) | application code updater (only) | rest-api code updater (only) |
| Lifecycle | persistent (committed) | persistent (committed) | persistent (committed) | persistent (committed) |
| First-run | not produced | not produced | not produced | not produced |
| Hard-fails preempt emit | yes | yes | yes | yes |

The reports are **chained**: domain `updates.md` drives every spec updater; each spec updater produces a layer-specific `updates.md`; each layer-specific `updates.md` drives that layer's code updater.

```
diagram edit
   │
   ▼
domain-spec:updates-detector
   │
   ▼
<stem>.domain/updates.md ──┬──► /update-specs (domain) ──────────► domain spec siblings
                           │
                           ├──► /persistence-spec:update-specs ──► <stem>.persistence/command-repo-spec.md
                           │                                   └──► <stem>.persistence/updates.md ──► /persistence-spec:update-code ──► tables/, mappers/, migrations/, repos
                           │
                           ├──► /application-spec:update-specs ──► <stem>.application/{commands,queries}.specs.md
                           │                                   └──► <stem>.application/updates.md ──► /application-spec:update-code ──► <aggregate>_commands.py, _queries.py, services
                           │
                           └──► /rest-api-spec:update-specs ────► <stem>.rest-api/spec.md
                                                               └──► <stem>.rest-api/updates.md ──► /rest-api-spec:update-code ──► api/serializers/, api/endpoints/, app wiring, endpoint tests

                       (separately)
<stem>.commands.md / <stem>.queries.md edit
   │
   ▼
application-spec:updates-detector  (shared — feeds the commands/queries-diagram axis of both /application-spec:update-specs and /rest-api-spec:update-specs)
```

Each layer follows the same shape: a layer-specific `updates.md` is emitted by the spec updater for that layer and consumed by the code updater for the same layer; the rest-api layer additionally takes a second trigger (the shared commands/queries-diagram detector) for the axis the domain `updates.md` doesn't cover.
