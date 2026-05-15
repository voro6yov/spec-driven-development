---
name: updates-report-template
description: Reference template for the REST API updates report (`<stem>.rest-api/updates.md`) emitted by `rest-api-updates-writer`. Use when generating, parsing, or reviewing a REST API updates report. Covers the rendered schema (surface-scoped per-section delta blocks), rendering rules, the `## Affected Artifacts` footer specification, the top-of-file sentinel, and the hash format.
user-invocable: false
disable-model-invocation: false
---

# REST API Updates Report Template

> **Consumers:**
> - `rest-api-updates-writer` agent — renders the report; uses these rules to compute the per-section delta blocks and the `## Affected Artifacts` footer.
> - `/rest-api-spec:update-code` skill (future) — parses the report to dispatch per-artifact code edits.

> **Scope of this skill:** output format only. Workflow (loading `spec.md` from working tree + git HEAD, parsing each version, computing deltas, rendering) lives in the `rest-api-updates-writer` agent body.

> **Surface scoping.** Every per-table section (`## Endpoint Inventory Changes`, `## Response Fields Changes`, `## Request Fields Changes`, `## Parameter Mapping Changes`) is grouped by `### Surface: <name>` H3 sub-headings — matching `spec.md`'s own `## Surface:` organization. A surface that has no changes within a section is **omitted from that section** (not rendered with a `_no changes_` body). The consumer treats an absent `### Surface:` as `_no changes_` for that surface. `## Resource Basics Changes` tracks Table 1 only and has no surface grouping.

---

## Schema

The report is **per-artifact and surface-scoped**: a flat header (`## Summary`) anchors the run, five per-section delta blocks describe what changed inside `spec.md`, and a flat `## Affected Artifacts` footer lists every generated file the code updater must touch. Substitute every `<placeholder>` with the actual value when rendering.

````markdown
<!-- domain-updates-hash:<hash> -->

# REST API Updates Report

## Summary

- Spec: `<dir>/<stem>.rest-api/spec.md`
- Pre-update spec hash: <sha256>
- Post-update spec hash: <sha256>
- Domain updates source: `<dir>/<stem>.domain/updates.md` (hash: <sha256>)
- Warnings:
  - <warning text>

## Resource Basics Changes

- Resource name: was `<old>`, now `<new>` (_unchanged_)
- Plural: was `<old>`, now `<new>` (_unchanged_)
- Router prefix: was `<old>`, now `<new>` (_unchanged_)
- Surfaces: was `<old>`, now `<new>` (surface added: `<name>` | surface removed: `<name>`)

## Endpoint Inventory Changes

### Surface: <name>

#### Added
- `<HTTP> <PATH>` (<operation>) → `<DomainRef>` — <query | command> endpoint
  - Description: <description>

#### Removed
- `<HTTP> <PATH>` (<operation>) — <query | command> endpoint

#### Modified
- `<HTTP> <PATH>` (<operation>)
  - Operation: was `<old>` → `<new>`
  - Domain Ref: was `<old>` → `<new>`
  - Description: was "<old>" → "<new>"

## Response Fields Changes

### Surface: <name>

#### Added
- `<HTTP> <PATH>` (<operation>)
  - Source delta: <short_phrase>
  - Response fields: `<f1>: <t1>`, `<f2>: <t2>` (includable), ... | _binary (raw bytes)_
  - Nested types: `<TypeName>` (fields: `<f1>: <t1>`, `<f2>: <t2>`), ...
  - Query parameters: `<name>: <type>` (default `<default>`), ... | _none_

#### Removed
- `<HTTP> <PATH>` (<operation>)
  - Source delta: <short_phrase>

#### Modified
- `<HTTP> <PATH>` (<operation>)
  - Source delta: <short_phrase>
  - Binary response: switched <to | from> binary placeholder
  - Response field added: `<name>: <type>` (includable)
  - Response field removed: `<name>: <type>`
  - Response field retyped: `<name>`: `<old_type>` → `<new_type>`
  - Nested type added: `<TypeName>` (fields: `<f1>: <t1>`, `<f2>: <t2>`)
  - Nested type removed: `<TypeName>`
  - Nested type `<TypeName>` field added: `<name>: <type>`
  - Nested type `<TypeName>` field removed: `<name>: <type>`
  - Nested type `<TypeName>` field retyped: `<name>`: `<old_type>` → `<new_type>`
  - Query parameter added: `<name>: <type>` (default `<default>`)
  - Query parameter removed: `<name>: <type>`
  - Query parameter retyped: `<name>`: `<old_type>` → `<new_type>`
  - Query parameter modified: `<name>` — <what changed: e.g. heavy-field list `<old>` → `<new>`; default `<old>` → `<new>`; description "<old>" → "<new>">

## Request Fields Changes

### Surface: <name>

#### Added
- `<HTTP> <PATH>` (<operation>)
  - Source delta: <short_phrase>
  - Request fields: `<f1>: <t1>` (<validation>), ... | _empty body (path/auth only)_
  - Nested types: `<TypeName>` (fields: `<f1>: <t1>`, `<f2>: <t2>`), ...

#### Removed
- `<HTTP> <PATH>` (<operation>)
  - Source delta: <short_phrase>

#### Modified
- `<HTTP> <PATH>` (<operation>)
  - Source delta: <short_phrase>
  - Body: switched <to | from> empty-body placeholder
  - Request field added: `<name>: <type>` (<validation>)
  - Request field removed: `<name>: <type>`
  - Request field retyped: `<name>`: `<old_type>` → `<new_type>`
  - Request field validation changed: `<name>` — "<old>" → "<new>"
  - Nested type added: `<TypeName>` (fields: `<f1>: <t1>`, `<f2>: <t2>`)
  - Nested type removed: `<TypeName>`
  - Nested type `<TypeName>` field added: `<name>: <type>`
  - Nested type `<TypeName>` field removed: `<name>: <type>`
  - Nested type `<TypeName>` field retyped: `<name>`: `<old_type>` → `<new_type>`

## Parameter Mapping Changes

### Surface: <name>

#### Added
- `<HTTP> <PATH>` (<operation>)
  - Source delta: <short_phrase>
  - Mapping: `<param>` ← `<source>`; `<param>` ← `<source>`; ...

#### Removed
- `<HTTP> <PATH>` (<operation>)
  - Source delta: <short_phrase>

#### Modified
- `<HTTP> <PATH>` (<operation>)
  - Source delta: <short_phrase>
  - Parameter added: `<param>` ← `<source>`
  - Parameter removed: `<param>` (was `<source>`)
  - Source line changed: `<param>` — `<old_source>` → `<new_source>`
  - Source reclassified: `<param>` — `<old_source>` → `<new_source>`

## Affected Artifacts

| Path | Action | Driving section |
|---|---|---|
| `api/serializers/<surface>/<aggregate>/<operation>.py` | modify | Response Fields Changes (Surface: <surface>) |
| `api/serializers/<surface>/<aggregate>/<operation>.py` | modify | Request Fields Changes (Surface: <surface>) |
| `api/serializers/<surface>/<aggregate>/<operation>.py` | add | Endpoint Inventory Changes (Surface: <surface>) |
| `api/serializers/<surface>/<aggregate>/<operation>.py` | remove | Endpoint Inventory Changes (Surface: <surface>) |
| `api/serializers/<surface>/<aggregate>/__init__.py` | modify | Endpoint Inventory Changes (Surface: <surface>) |
| `api/endpoints/<surface>/<plural>.py` | modify | Parameter Mapping Changes (Surface: <surface>) |
| `api/endpoints/<surface>/__init__.py` | modify | Endpoint Inventory Changes (Surface: <surface>) |
| `api/endpoints/__init__.py` | modify | Endpoint Inventory Changes (Surface: <surface>) |
| `<pkg>/constants.py` | modify | Resource Basics / Endpoint Inventory Changes |
| `<pkg>/entrypoint.py` | modify | Resource Basics / Endpoint Inventory Changes |
| `<api_pkg>/auth.py` | modify | Resource Basics Changes (internal surface added) |
| `tests/integration/<resource>/test_<plural>_<surface>_api.py` | modify | <section abbreviations> Changes (Surface: <surface>) |
````

---

## Rendering rules

### Top-of-file sentinel

The first line of the file is an HTML comment recording the SHA256 of `<dir>/<stem>.domain/updates.md`:

```
<!-- domain-updates-hash:<sha256> -->
```

When `<stem>.domain/updates.md` does not exist on disk, render `<sha256>` as `(none)`. The sentinel line itself is always emitted on line 1, followed by one blank line, then the `# REST API Updates Report` heading.

The sentinel is the consumer's primary skip-on-replay signal: a downstream `/rest-api-spec:update-code` run that already applied a report carrying the same `domain-updates-hash` may early-exit.

### Top-level sections

All seven sections are **always emitted** with their headings, in this canonical order:

1. `## Summary`
2. `## Resource Basics Changes`
3. `## Endpoint Inventory Changes`
4. `## Response Fields Changes`
5. `## Request Fields Changes`
6. `## Parameter Mapping Changes`
7. `## Affected Artifacts`

When a section other than `## Summary` and `## Affected Artifacts` has no content, render its body as the single literal line `_no changes_`. Do not omit the heading.

### Surface grouping (the four per-table sections)

`## Endpoint Inventory Changes`, `## Response Fields Changes`, `## Request Fields Changes`, and `## Parameter Mapping Changes` are grouped by `### Surface: <name>` H3 sub-headings:

- A surface appears under a section **only when it has at least one change in that section**. Surfaces with no changes are **omitted** (no heading, no `_no changes_` placeholder).
- Surfaces appear in canonical order — versioned surfaces first by integer version, then non-versioned surfaces alphabetically — per `rest-api-spec:surface-markers`. In practice this is the order they already appear in `spec.md`'s Table 1 Surfaces row and its `## Surface:` section sequence; preserve that order.
- When a section has zero changed surfaces, its body is the single literal line `_no changes_`.

### Within-surface ordering (the four per-table sections)

Under each `### Surface: <name>` H3:

- Sub-bucket order is fixed: `#### Added`, `#### Removed`, `#### Modified`.
- Sub-buckets are individually omitted when empty (no heading, no placeholder).
- Within each sub-bucket, endpoints are ordered by **path** (the `<PATH>` of the `**Endpoint:**` header), then by `<HTTP>` verb for path ties.
- Inside a `#### Modified` endpoint sub-block, the delta bullets follow a fixed order:
  1. `Binary response: …` / `Body: …` (placeholder switch), if any.
  2. `Response field added` / `Request field added`, then `… removed`, then `… retyped`, then `… validation changed` (Table 5 only).
  3. `Nested type added`, then `Nested type removed`, then per-nested-type field deltas (`Nested type \`X\` field added/removed/retyped`) — nested types in **first-mention order** (the order they appear in the spec's Nested sub-tables), all of one nested type's field deltas grouped together.
  4. `Query parameter added`, then `… removed`, then `… retyped`, then `… modified` (Table 4 only).
  5. For Parameter Mapping: `Parameter added`, then `Parameter removed`, then `Source line changed`, then `Source reclassified`.
  - The `Source delta:` bullet is always first, before the delta bullets above.
- For `#### Added` endpoint sub-blocks: render the full sub-block content compactly — one `Response fields:` / `Request fields:` / `Mapping:` bullet (comma- or semicolon-separated), one `Nested types:` bullet, and (Table 4 only) one `Query parameters:` bullet. Use the `_binary (raw bytes)_` / `_empty body (path/auth only)_` italic forms when the endpoint is a binary-response or empty-body endpoint. Render `_none_` for an absent `Query parameters:` list (the `*No query parameters …*` placeholder) and `_none_` for an absent `Nested types:` list.
- For `#### Removed` endpoint sub-blocks: render only the `**Endpoint:**`-style header line plus the `Source delta:` bullet. The source state is gone; no shape is rendered.

### Endpoint header format

Every endpoint bullet across `## Endpoint Inventory Changes`, `## Response Fields Changes`, `## Request Fields Changes`, and `## Parameter Mapping Changes` opens with the same header form:

```
- `<HTTP> <PATH>` (<operation>)
```

`<HTTP> <PATH>` is verbatim from the `**Endpoint:**` line in `spec.md` (for Response/Request/Parameter-Mapping sections) or from the Table 2/3 row (for Endpoint Inventory). `<operation>` is the operation name — taken from the `(operation)` suffix on the `**Endpoint:**` line when present, otherwise resolved by matching `(<HTTP>, <PATH>)` against the surface's Table 2 / Table 3 rows. When the operation cannot be resolved, render the header without the ` (<operation>)` suffix.

### Section: Summary

- The four lines **Spec**, **Pre-update spec hash**, **Post-update spec hash**, **Domain updates source** are always emitted. The Summary section never reduces to `_no changes_`.
- Hashes are rendered per the **Hash format** rule below.
- The **Domain updates source** value is `_none_` when no domain `updates.md` exists; otherwise it includes the path plus a parenthesised hash (`<dir>/<stem>.domain/updates.md (hash: <sha256>)`).
- The **Warnings** line is omitted entirely when there are no warnings. When present, it introduces a sub-bullet list. Warning categories (each rendered only when applicable):
  - First-run baseline: `first-run baseline: HEAD did not contain <spec_file>; entire post-update spec reported as Added.`
  - Domain updates source missing: `domain updates source not found; all source-delta values fell back to '(unknown source)'.`
- A `Generated at` timestamp is **not** included — a wall-clock value would break the byte-stability contract.

### Section: Resource Basics Changes

Tracks Table 1 deltas — Resource name, Plural, Router prefix, Surfaces.

- When **any** of the four fields changed, render **all four** as `<field>: was \`<old>\`, now \`<new>\``, with a parenthetical:
  - `(_unchanged_)` for a field whose value did not change.
  - For the Surfaces field: `(surface added: \`<name>\`)` / `(surface removed: \`<name>\`)` (list all added/removed surfaces, comma-separated; both clauses when both happened).
  - Changed Resource name / Plural / Router prefix carry no parenthetical (the `was X, now Y` with `X ≠ Y` is self-evident).
- When all four fields are byte-identical, the section body is `_no changes_`.
- **On a domain-diagram-only update this section is always `_no changes_`** — a Resource-name change is a hard-fail that aborts the run before the writer runs, and Surfaces changes are a commands/queries-diagram-axis concern. The section exists for when that axis is wired into `/rest-api-spec:update-specs`; the writer still parses Table 1 and reports a change if `spec.md`'s Table 1 actually differs from HEAD (e.g. a hand-edit).

### Section: Endpoint Inventory Changes

Tracks Tables 2 (Query Endpoints) and 3 (Command Endpoints) deltas, per surface. Endpoints are keyed by `(<HTTP>, <PATH>)` within a surface.

- `#### Added` — an endpoint present in post but not pre. Render the endpoint header, the `→ \`<DomainRef>\` — <query | command> endpoint` tail (`query` when the row came from Table 2, `command` from Table 3), and a `Description:` sub-bullet.
- `#### Removed` — an endpoint present in pre but not post. Render header + `— <query | command> endpoint`.
- `#### Modified` — same `(<HTTP>, <PATH>)` in both, but Operation, Domain Ref, or Description differs. Render only the changed cells, each as `was \`<old>\` → \`<new>\`` (`Description: was "<old>" → "<new>"` with double-quotes for the prose cell).
- When a surface only exists in pre, every endpoint of that surface is `#### Removed` (and the surface drop is also recorded in `## Resource Basics Changes` → Surfaces). When a surface only exists in post, every endpoint is `#### Added`.
- **On a domain-diagram-only update this section is always `_no changes_`** — Tables 2/3 are pure functions of the `<Resource>Commands` / `<Resource>Queries` diagrams. The section exists for the commands/queries-diagram axis; the writer still reports a change if `spec.md`'s Tables 2/3 actually differ from HEAD.

### Section: Response Fields Changes

Tracks Table 4 deltas, per surface, per query endpoint — response-DTO field rows, `**Nested:**` sub-tables, and `**Query Parameters:**` blocks. Endpoints keyed by `(<HTTP>, <PATH>)` of the `**Endpoint:**` line.

- `#### Added` — a Table-4 endpoint sub-block present in post but not pre (only happens when Table 2 also gained the endpoint — a commands/queries-axis change). Render the compact full shape (`Response fields:` / `Nested types:` / `Query parameters:` bullets, or `_binary (raw bytes)_`) so the code updater can scaffold the serializer.
- `#### Removed` — present in pre but not post. Header + `Source delta:` only.
- `#### Modified` — present in both, with any difference in response fields, nested sub-tables, or query parameters. Delta vocabulary:
  - **Binary response: switched to/from binary placeholder** — the endpoint flipped to/from the `*Binary response* — returns raw \`bytes\` …` placeholder.
  - **Response field added/removed** — `\`<name>: <type>\`` (append ` (includable)` when the Source column carried the `(includable)` annotation).
  - **Response field retyped** — `\`<name>\`: \`<old_type>\` → \`<new_type>\``. (When only the `(includable)` annotation toggled with no type change, render `Response field modified: \`<name>\` — includable annotation added/removed`.)
  - **Nested type added** — `\`<TypeName>\` (fields: \`<f1>: <t1>\`, \`<f2>: <t2>\`)`. **Nested type removed** — `\`<TypeName>\``.
  - **Nested type `<TypeName>` field added/removed/retyped** — same form as the top-level field deltas, prefixed with the owning nested-type name.
  - **Query parameter added/removed** — `\`<name>: <type>\`` (append ` (default \`<default>\`)` for added).
  - **Query parameter retyped** — `\`<name>\`: \`<old_type>\` → \`<new_type>\``.
  - **Query parameter modified** — `\`<name>\` — <what changed>` for a default change (`default \`<old>\` → \`<new>\``), a description change (`description "<old>" → "<new>"`), or — for the `include` heavy-field row of the Wish List pattern — the enumerated heavy-field list (`heavy-field list \`<old list>\` → \`<new list>\``).
- The `Source delta:` bullet is the matching `<stem>.domain/updates.md` per-class change (`<category>: <ClassName> <delta_phrase>`), best-effort; `(unknown source)` when the sibling report is missing or no match is found.

### Section: Request Fields Changes

Tracks Table 5 deltas, per surface, per command endpoint — body-field rows and `**Nested:**` sub-tables. Same bucket and Source-delta conventions as Response Fields Changes. Delta vocabulary (Table 5 has neither query parameters nor a binary placeholder):

- **Body: switched to/from empty-body placeholder** — the endpoint flipped to/from the `*No request body — …*` placeholder.
- **Request field added/removed** — `\`<name>: <type>\`` (append ` (<validation>)` for added — the leading `Required`/`Optional` token suffices, e.g. `(Required)` / `(Optional)`).
- **Request field retyped** — `\`<name>\`: \`<old_type>\` → \`<new_type>\``.
- **Request field validation changed** — `\`<name>\` — "<old>" → "<new>"` (the Validation column is mechanical boilerplate; this delta is cosmetic and a code updater may skip it).
- **Nested type added/removed**, **Nested type `<TypeName>` field added/removed/retyped** — same forms as Response Fields Changes.

### Section: Parameter Mapping Changes

Tracks Table 6 deltas, per surface, per endpoint — the parameter→source rows. Endpoints keyed by `(<HTTP>, <PATH>)`. Same bucket conventions.

- `#### Added` — a Table-6 endpoint sub-block present in post but not pre. Render the compact full `Mapping:` bullet (semicolon-separated `\`<param>\` ← \`<source>\`` pairs).
- `#### Removed` — header + `Source delta:` only.
- `#### Modified` — delta vocabulary:
  - **Parameter added** — `\`<param>\` ← \`<source>\`` (a new row appeared — the method gained a parameter).
  - **Parameter removed** — `\`<param>\` (was \`<source>\`)`.
  - **Source line changed** — `\`<param>\` — \`<old_source>\` → \`<new_source>\`` (the dominant domain-driven delta: a `Constructed from query params …, → <Type>` source whose constituent-field list changed because a composite query-param type gained/lost a field).
  - **Source reclassified** — `\`<param>\` — \`<old_source>\` → \`<new_source>\`` (the provenance category changed, e.g. `Request body \`x\`` → `Path param {id}`).
  - A change of the left-column header (`Command Parameter` ↔ `Query Parameter`) indicates the endpoint flipped command/query and is recorded in `## Endpoint Inventory Changes`; render no Parameter-Mapping delta for it.
- The `Source delta:` bullet follows the Response Fields Changes convention.

---

## `## Affected Artifacts` computation

The footer is a flat dispatch table. The code updater walks it top-to-bottom and resolves each path against the `target-locations-finder` report it runs first. Compute as follows:

Resolve `<A>` = snake-case singular of the resource's `**Resource name**` (Table 1) for use in the per-aggregate sub-path.

1. **From Response Fields Changes** — for each changed surface `<S>`, for each `#### Added` / `#### Removed` / `#### Modified` endpoint with operation `<OP>`:
   - `#### Modified` → `api/serializers/<S>/<A>/<OP>.py | modify | Response Fields Changes (Surface: <S>)`.
   - `#### Added` → `api/serializers/<S>/<A>/<OP>.py | add | Endpoint Inventory Changes (Surface: <S>)` (the serializer module is new). *(Commands/queries axis only.)*
   - `#### Removed` → `api/serializers/<S>/<A>/<OP>.py | remove | Endpoint Inventory Changes (Surface: <S>)`. *(Commands/queries axis only.)*

2. **From Request Fields Changes** — same as (1) with `Request Fields Changes` as the driving section for the `modify` rows.

3. **From Parameter Mapping Changes** — for each changed surface `<S>` with at least one `#### Added` / `#### Removed` / `#### Modified` endpoint:
   - One row `api/endpoints/<S>/<plural>.py | modify | Parameter Mapping Changes (Surface: <S>)`. (All endpoints of a surface share one endpoint module — multiple per-endpoint changes in `<S>` collapse to a single row.)

4. **From Endpoint Inventory Changes** — for each surface `<S>` with any `#### Added` or `#### Removed` endpoint (commands/queries axis only):
   - `api/endpoints/<S>/<plural>.py | modify | Endpoint Inventory Changes (Surface: <S>)` (the endpoint function set changed) — dedupe with the Parameter Mapping row above into one `modify` row with the driving label `Parameter Mapping / Endpoint Inventory Changes (Surface: <S>)`.
   - `api/serializers/<S>/<A>/__init__.py | modify | Endpoint Inventory Changes (Surface: <S>)`.
   - `api/endpoints/<S>/__init__.py | modify | Endpoint Inventory Changes (Surface: <S>)`.
   - `api/endpoints/__init__.py | modify | Endpoint Inventory Changes (Surface: <S>)`.
   - `<pkg>/constants.py | modify | Endpoint Inventory Changes` and `<pkg>/entrypoint.py | modify | Endpoint Inventory Changes`.

5. **From Resource Basics Changes** — when the Surfaces row changed (a surface was added — commands/queries axis only):
   - For each newly added surface `<S>`: `api/serializers/<S>/__init__.py | add` (zero-byte), `api/serializers/<S>/<A>/__init__.py | add` (per-aggregate aggregator), `api/endpoints/<S>/__init__.py | add`, plus `api/endpoints/__init__.py | modify`, `<pkg>/constants.py | modify`, `<pkg>/entrypoint.py | modify` — all driven by `Resource Basics Changes`.
   - When the added surface is `internal`: also `<api_pkg>/auth.py | modify | Resource Basics Changes (internal surface added)`.

6. **Test artifacts (always last)** — for each surface `<S>` that has at least one change in **any** of Endpoint Inventory / Response Fields / Request Fields / Parameter Mapping:
   - `tests/integration/<resource>/test_<plural>_<S>_api.py | modify | <abbr> Changes (Surface: <S>)`, where `<abbr>` is the `/`-joined list of the contributing section abbreviations in canonical order — `Endpoint Inventory` / `Response` / `Request` / `Parameter Mapping`. Example: a surface touched by Response Fields Changes and Parameter Mapping Changes → `Response/Parameter Mapping Changes (Surface: <S>)`.
   - When the change is the *addition* of a whole new surface `<S>` (Resource Basics — Surfaces grew), the action is `add` and the driving section is `Resource Basics Changes (Surface: <S>)`.

The table header (`| Path | Action | Driving section |` plus the divider row) is always emitted. When every section above is `_no changes_`, the table has no data rows.

### Row ordering

Rows are emitted in driving-section order: **Response Fields → Request Fields → Parameter Mapping → Endpoint Inventory → Resource Basics**, and within each section in surface order (canonical) then endpoint-path order; the per-surface test-module rows come **last** (after all `api/...` and `<pkg>/...` rows), in surface order. Dedupe identical `(path, action)` pairs into one row whose driving-section label joins the contributing sections with ` / `.

### Action vocabulary

The `Action` column is a closed set: `add`, `modify`, `remove`. No other values are emitted.

### Path conventions and placeholder substitution

- `api/...` paths are relative to the API package root (`<api_pkg>/`); `tests/...` and `<pkg>/...` paths are relative to the project root. The code updater resolves both against the `target-locations-finder` report.
- `<surface>` — the surface name verbatim (e.g. `v1`, `internal`).
- `<operation>` — the operation/method name of the changed endpoint (the `(operation)` from the `**Endpoint:**` line, or the matching Table 2/3 row).
- `<plural>` — Table 1's Plural value (e.g. `files`).
- `<resource>` — the snake_case form of Table 1's Resource name (e.g. `File` → `file`, `InventoryItem` → `inventory_item`).
- `<pkg>` / `<api_pkg>` are left symbolic — they appear only in commands/queries-axis rows (Endpoint Inventory / Resource Basics), and the code updater fills them from `target-locations-finder`.

---

## Hash format

All hashes in this report are SHA256 of UTF-8 file content, rendered in **lowercase hex**, full **64-character** form.

When a hash cannot be computed (file missing or unreadable), render the value literally as `(none)`. Never substitute zeros.

---

## Determinism contract

- Byte-stable inputs (working-tree `spec.md`, HEAD `spec.md`, sibling `<dir>/<stem>.domain/updates.md`) → byte-stable report.
- Re-running the writer with no new changes produces a report whose every section after `## Summary` is `_no changes_`, an empty Affected Artifacts row list, and the same sentinel hash.
- The report reflects the actual `spec.md` diff against HEAD — not which table writers the orchestrator chose to re-run. A re-run table writer that produced byte-identical output contributes nothing to the report.
- Section ordering, surface ordering (canonical), within-surface sub-bucket ordering (Added → Removed → Modified), endpoint ordering (by path), Modified-delta ordering, and Affected-Artifacts row ordering above are absolute. No source-defined deviation.
- The Summary section deliberately excludes a `Generated at` timestamp.
