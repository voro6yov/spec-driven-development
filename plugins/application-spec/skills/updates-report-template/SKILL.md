---
name: application-spec:updates-report-template
description: Reference template for the application updates report (`<stem>.application/updates.md`) emitted by `application-updates-writer`. Use when generating, parsing, or reviewing an application updates report. Covers the rendered schema (per-section delta blocks), rendering rules, the `## Affected Artifacts` footer specification, the top-of-file sentinel, and the hash format.
user-invocable: false
disable-model-invocation: false
---

# Application Updates Report Template

> **Consumers:**
> - `application-updates-writer` agent — renders the report; uses these rules to compute the per-section delta blocks and the `## Affected Artifacts` footer.
> - `/application-spec:update-code` skill (future) — parses the report to dispatch per-artifact code edits.

> **Scope of this skill:** output format only. Workflow (loading the three specs from working tree + git HEAD, parsing each version, computing deltas, rendering) lives in the `application-updates-writer` agent body.

---

## Schema

The report is **per-artifact**: a flat header (`## Summary`) anchors the run, four per-section delta blocks describe what changed inside the specs, and a flat `## Affected Artifacts` footer lists every generated file the code updater must touch. Substitute every `<placeholder>` with the actual value when rendering.

````markdown
<!-- domain-updates-hash:<hash> -->

# Application Updates Report

## Summary

- Aggregate stem: `<stem>`
- Pre-update specs:
  - `commands.specs.md` hash: <sha256>
  - `queries.specs.md` hash: <sha256>
  - `services.md` hash: <sha256>
- Post-update specs:
  - `commands.specs.md` hash: <sha256>
  - `queries.specs.md` hash: <sha256>
  - `services.md` hash: <sha256>
- Domain updates source: `<dir>/<stem>.domain/updates.md` (hash: <sha256>)
- Warnings:
  - <warning text>

## Commands Methods Changes

### Added
- `<method_signature>`
  - Source delta: <short_phrase>
  - Aggregate call: `<call>` | _none_ (factory)
  - Load step: `<call>` | _none_ (factory)
  - Collaborators: `<call>`, ... | _none_
  - Raises: `<ExceptionName>` (when <condition>) | _none_

### Removed
- `<method_signature>`
  - Source delta: <short_phrase>

### Modified
- `<method_signature>`
  - Source delta: <short_phrase>
  - Sub-sections changed:
    - <Sub-section name>
    - ...

## Queries Methods Changes

### Added
- `<method_signature>`
  - Source delta: <short_phrase>
  - Repository call: `<call>` | _none_ (external-interface)
  - External-Interface shape: yes | no
  - Returns: `<type_token>`

### Removed
- `<method_signature>`
  - Source delta: <short_phrase>

### Modified
- `<method_signature>`
  - Source delta: <short_phrase>
  - Sub-sections changed:
    - <Sub-section name>
    - ...

## Application Exceptions Changes

### Added
- `<ExceptionName>`
  - Side(s): commands | queries | commands, queries
  - Source delta: <short_phrase>
  - Base: `<BaseClass>`
  - Code: `<code>`
  - Constructor: `<ctor_signature>`
  - Message pattern: `<f-string>`

### Removed
- `<ExceptionName>`
  - Side(s): commands | queries | commands, queries
  - Source delta: <short_phrase>

### Modified
- `<ExceptionName>`
  - Side(s): commands | queries | commands, queries
  - Source delta: <short_phrase>
  - Sub-sections changed:
    - <Base | Code | Constructor | Message>: <old> → <new>
    - ...

## Services Changes

### Added
- `<ServiceIdentifier>`
  - Classification: <domain | external>
  - Interfaces: `<I1>`, `<I2>`
  - Consumers: `<Consumer1>`, `<Consumer2>`
  - Source delta: <short_phrase>

### Removed
- `<ServiceIdentifier>`
  - Classification: <domain | external>
  - Source delta: <short_phrase>

### Modified
- `<ServiceIdentifier>`
  - Source delta: <short_phrase>
  - Sub-sections changed:
    - Classification: <old> → <new>
    - Interfaces added: `<I>`; removed: `<I>`
    - Consumers added: `<C>`; removed: `<C>`

## Affected Artifacts

| Path | Action | Driving section |
|---|---|---|
| `application/<aggregate>/<aggregate>_commands.py` | modify | Commands Methods Changes (Added, Modified-Method Flow, Removed) |
| `application/<aggregate>/<aggregate>_queries.py` | modify | Queries Methods Changes (Added, Modified-Method Flow, Removed) |
| `domain/<aggregate>/exceptions.py` | modify | Application Exceptions Changes (any) |
| `infrastructure/services/<attr_name>/<attr_name>.py` | add | Services Changes (Added) |
| `infrastructure/services/<attr_name>/__init__.py` | modify | Services Changes (Added, Removed) |
| `infrastructure/services/<attr_name>/<attr_name>.py` | remove | Services Changes (Removed) |
| `tests/fakes/fake_<attr_name>.py` | add | Services Changes (Added) |
| `tests/fakes/fake_<attr_name>.py` | remove | Services Changes (Removed) |
| `tests/fakes/__init__.py` | modify | Services Changes (Added, Removed) |
| `containers.py` | modify | Services Changes (any) |
| `tests/conftest.py` | modify | Services Changes (any) |
| `tests/integration/<aggregate>/test_<aggregate>_commands.py` | modify | Commands Methods Changes (Added, Removed) |
| `tests/integration/<aggregate>/test_<aggregate>_queries.py` | modify | Queries Methods Changes (Added, Removed) |
````

---

## Rendering rules

### Top-of-file sentinel

The first line of the file is an HTML comment recording the SHA256 of `<dir>/<stem>.domain/updates.md`:

```
<!-- domain-updates-hash:<sha256> -->
```

When `<stem>.domain/updates.md` does not exist on disk, render `<sha256>` as `(none)`. The sentinel line itself is always emitted on line 1, followed by one blank line, then the `# Application Updates Report` heading.

The sentinel is the consumer's primary skip-on-replay signal: a downstream `/application-spec:update-code` run that already applied a report carrying the same `domain-updates-hash` may early-exit.

### Top-level sections

All six sections are **always emitted** with their headings, in this canonical order:

1. `## Summary`
2. `## Commands Methods Changes`
3. `## Queries Methods Changes`
4. `## Application Exceptions Changes`
5. `## Services Changes`
6. `## Affected Artifacts`

When a section other than `## Summary` and `## Affected Artifacts` has no content, render its body as the single literal line `_no changes_`. Do not omit the heading.

### Within-section ordering

For sections with `### Added` / `### Removed` / `### Modified` sub-blocks (`Commands Methods Changes`, `Queries Methods Changes`, `Application Exceptions Changes`, `Services Changes`):

- Sub-block order is fixed: `### Added`, `### Removed`, `### Modified`.
- Within each sub-block, items are ordered alphabetically by name (method signature, exception name, service identifier).
- Sub-blocks are individually omitted when empty (no heading, no `_None._` placeholder).
- If all three sub-blocks are empty, the parent section's body is `_no changes_`.

The application-spec has no append-only history (unlike persistence's `§2.Migrations`); every section is a snapshot and is fully alphabetised.

### Modified sub-section ordering

Inside a `### Modified` entry, the `Sub-sections changed:` list follows a canonical per-side order. Skip absent sub-sections silently — Modified inherently means "only what changed".

| Side | Canonical order |
|---|---|
| Commands Methods | `Purpose`, `Requires Aggregate State`, `Method Flow`, `Postconditions` |
| Queries Methods | `Purpose`, `Method Flow`, `Returns` |
| Application Exceptions | `Base`, `Code`, `Constructor`, `Message` |
| Services | `Classification`, `Interfaces`, `Consumers` |

### Section: Summary

- The five lines **Aggregate stem**, **Pre-update specs** (3 sub-bullets), **Post-update specs** (3 sub-bullets), and **Domain updates source** are always emitted. The Summary section never reduces to `_no changes_`.
- Hashes are rendered per the **Hash format** rule below.
- The **Domain updates source** value is `_none_` when no domain `updates.md` exists; otherwise it includes the path plus a parenthesised hash (`<dir>/<stem>.domain/updates.md (hash: <sha256>)`).
- The **Warnings** line is omitted entirely when there are no warnings. When present, it introduces a sub-bullet list. Warning categories (each rendered only when applicable):
  - First-run baseline: `first-run baseline: HEAD did not contain <spec_file>; entire post-update spec reported as Added.`
  - Domain updates source missing: `domain updates source not found; all source_delta values fell back to '(unknown source)'.`
- Generated-at timestamps are **not** included in the Summary — they would break the byte-stability contract.

### Section: Commands Methods Changes

- **Added** entries render the canonical method-shape preview:
  - `Source delta` — short phrase from the domain `updates.md` lookup, or `(unknown source)`.
  - `Aggregate call` — the verbatim `<call>` from the method's flow (e.g. `User.new(...)`, `user.update_email(email)`); `_none_ (factory)` when the method is a factory and never reaches the aggregate.
  - `Load step` — the verbatim `Call <repo>.<finder>(<args>)` from the flow; `_none_ (factory)` for factories.
  - `Collaborators` — comma-separated list of `<service>.<method>(<args>)` calls; `_none_` when absent.
  - `Raises` — list of `<ExceptionName> (when <condition>)` pairs derived from the flow's `If <condition>, raise <X>` lines; `_none_` when absent.
- **Removed** entries render only the verbatim signature plus a `Source delta` bullet.
- **Modified** entries render the verbatim signature plus a `Source delta` bullet plus a `Sub-sections changed:` list. Each sub-section appears as a bullet in the canonical order above. No within-sub-section delta is rendered (v1 design — see Open Question #1 in `notes/updates-report.md`).

If all three sub-blocks are empty, the section body is `_no changes_`.

### Section: Queries Methods Changes

- **Added** entries render the canonical query-shape preview:
  - `Source delta` — short phrase or `(unknown source)`.
  - `Repository call` — the verbatim `Call <query_repo>.<finder>(<args>)` from the flow; `_none_ (external-interface)` for External-Interface-shape methods.
  - `External-Interface shape` — `yes` when the method's flow names an `I<Interface>` collaborator instead of the query repository; `no` otherwise.
  - `Returns` — the return-type token verbatim (e.g. `ResultSet[UserSummary]`, `User`, `bool`).
- **Removed** entries: signature + `Source delta`.
- **Modified** entries: signature + `Source delta` + `Sub-sections changed:` list (canonical order: Purpose, Method Flow, Returns).

If all three sub-blocks are empty, the section body is `_no changes_`.

### Section: Application Exceptions Changes

The two sides (`commands.specs.md` and `queries.specs.md`) are **unified** in this section. An exception class that appears in both files renders as a single entry — its `Side(s)` line lists `commands, queries`. An exception unique to one side lists that side only.

- **Added** entries render the full inferred class spec:
  - `Side(s)` — `commands` | `queries` | `commands, queries`.
  - `Source delta` — short phrase or `(unknown source)`.
  - `Base` — the base class (e.g. `NotFound`, `AlreadyExists`).
  - `Code` — the snake_case error code.
  - `Constructor` — the constructor signature.
  - `Message pattern` — the f-string.
- **Removed** entries: name + `Side(s)` + `Source delta`.
- **Modified** entries: name + `Side(s)` + `Source delta` + `Sub-sections changed:` list. Each changed sub-section bullet shows `<old> → <new>` (the entire spec field, not a within-field diff).

If all three sub-blocks are empty, the section body is `_no changes_`.

### Section: Services Changes

- **Added** entries render the full service shape:
  - `Classification` — `domain` | `external`.
  - `Interfaces` — comma-separated list.
  - `Consumers` — comma-separated list.
  - `Source delta` — short phrase or `(unknown source)`.
- **Removed** entries: identifier + `Classification` + `Source delta`.
- **Modified** entries: identifier + `Source delta` + `Sub-sections changed:` list. Sub-sections (canonical order: Classification, Interfaces, Consumers):
  - `Classification: <old> → <new>` (single-line value).
  - `Interfaces added: <I1>, <I2>; removed: <I3>` — render only the non-empty halves; omit the entire bullet when both halves are empty.
  - `Consumers added: <C1>; removed: <C2>` — same rule.

If all three sub-blocks are empty, the section body is `_no changes_`.

---

## `## Affected Artifacts` computation

The footer is a flat dispatch table. The code updater walks it top-to-bottom. Compute as follows:

1. **From Commands Methods Changes**:
   - When `### Added` or `### Removed` is non-empty, **or** any `### Modified` entry has `Method Flow` in its `Sub-sections changed:` list:
     - Emit `application/<aggregate>/<aggregate>_commands.py | modify | Commands Methods Changes (Added, Modified-Method Flow, Removed)`.
   - When `### Added` or `### Removed` is non-empty:
     - Emit `tests/integration/<aggregate>/test_<aggregate>_commands.py | modify | Commands Methods Changes (Added, Removed)`.
   - Spec-only sub-section changes (`Purpose` / `Postconditions` / `Requires Aggregate State` only — no `Method Flow`) emit **no** `Affected Artifacts` row.

2. **From Queries Methods Changes**: same shape with `<aggregate>_queries.py` and `test_<aggregate>_queries.py`. Spec-only sub-section changes (`Purpose` / `Returns` only — no `Method Flow`) emit no row.

3. **From Application Exceptions Changes**:
   - When the section is not `_no changes_`:
     - Emit `domain/<aggregate>/exceptions.py | modify | Application Exceptions Changes (any)`.

4. **From Services Changes**:
   - For each `### Added` row whose `Classification` is `domain` or `external`:
     - `infrastructure/services/<attr_name>/<attr_name>.py | add | Services Changes (Added)`.
     - `infrastructure/services/<attr_name>/__init__.py | modify | Services Changes (Added)`.
     - `tests/fakes/fake_<attr_name>.py | add | Services Changes (Added)`.
   - For each `### Removed` row:
     - `infrastructure/services/<attr_name>/<attr_name>.py | remove | Services Changes (Removed)`.
     - `infrastructure/services/<attr_name>/__init__.py | modify | Services Changes (Removed)`.
     - `tests/fakes/fake_<attr_name>.py | remove | Services Changes (Removed)`.
   - When at least one row is added or removed:
     - `tests/fakes/__init__.py | modify | Services Changes (Added, Removed)`.
   - When the section is not `_no changes_`:
     - `containers.py | modify | Services Changes (any)`.
     - `tests/conftest.py | modify | Services Changes (any)`.

The table header (`| Path | Action | Driving section |` plus the divider row) is always emitted. When every section above is `_no changes_`, the table has no data rows.

### Row ordering

Within the table, rows are emitted in the section-rule order above (Commands Methods → Queries Methods → Application Exceptions → Services → Tests). Within each section's contribution, follow the within-section ordering of the source section (alphabetical by name). Service rows are grouped per-service-identifier in alphabetical order; the three add/remove file rows for a single service are emitted in the order shown above (`<attr_name>.py` → `__init__.py` → `fake_<attr_name>.py`).

### Action vocabulary

The `Action` column is a closed set: `add`, `modify`, `remove`. No other values are emitted.

### `<aggregate>` and `<attr_name>` substitution

- `<aggregate>` is the snake_case form of the aggregate stem (`<stem>` with `-` replaced by `_`). Example: stem `purchase-order` → `<aggregate>` = `purchase_order`. Drives `application/<aggregate>/<aggregate>_commands.py`, `application/<aggregate>/<aggregate>_queries.py`, `domain/<aggregate>/exceptions.py`, `tests/integration/<aggregate>/test_<aggregate>_commands.py`, `tests/integration/<aggregate>/test_<aggregate>_queries.py`.
- `<attr_name>` for a service is the **Attr name** bullet from that service's `## <ServiceIdentifier>` block in `services.md` (the snake_case identifier, e.g. `email_service`). Drives `infrastructure/services/<attr_name>/<attr_name>.py`, `infrastructure/services/<attr_name>/__init__.py`, `tests/fakes/fake_<attr_name>.py`.

---

## Hash format

All hashes in this report are SHA256 of UTF-8 file content, rendered in **lowercase hex**, full **64-character** form.

When a hash cannot be computed (file missing or unreadable), render the value literally as `(none)`. Never substitute zeros.

---

## Determinism contract

- Byte-stable inputs (working-tree specs, HEAD specs, sibling `<dir>/<stem>.domain/updates.md`) → byte-stable report.
- Re-running the writer with no new changes produces a report whose every section after `## Summary` is `_no changes_`, an empty Affected Artifacts row list, and the same sentinel hash.
- Section ordering, sub-block ordering, and within-block ordering rules above are absolute. No source-defined deviation.
- The Summary section deliberately excludes a `Generated at` timestamp (a wall-clock value would break byte-stability).
