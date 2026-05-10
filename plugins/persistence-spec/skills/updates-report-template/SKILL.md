---
name: persistence-spec:updates-report-template
description: Reference template for the persistence updates report (`<stem>.persistence/updates.md`) emitted by `command-repo-spec-updates-writer`. Use when generating, parsing, or reviewing a persistence updates report. Covers the rendered schema (per-section delta blocks), rendering rules, the `## Affected Artifacts` footer specification, the top-of-file sentinel, and the hash format.
user-invocable: false
disable-model-invocation: false
---

# Persistence Updates Report Template

> **Consumers:**
> - `command-repo-spec-updates-writer` agent — renders the report; uses these rules to compute the per-section delta blocks and the `## Affected Artifacts` footer.
> - `/persistence-spec:update-code` skill (future) — parses the report to dispatch per-artifact code edits.

> **Scope of this skill:** output format only. Workflow (loading the spec from working tree + git HEAD, parsing each version, computing deltas, rendering) lives in the `command-repo-spec-updates-writer` agent body.

---

## Schema

The report is **per-artifact**: a flat header (`## Summary`) anchors the run, seven per-section delta blocks describe what changed inside the spec, and a flat `## Affected Artifacts` footer lists every generated file the code updater must touch. Substitute every `<placeholder>` with the actual value when rendering.

````markdown
<!-- domain-updates-hash:<hash> -->

# Persistence Updates Report

## Summary

- Spec: `<dir>/<stem>.persistence/command-repo-spec.md`
- Pre-update spec hash: <sha256>
- Post-update spec hash: <sha256>
- Domain updates source: `<dir>/<stem>.domain/updates.md` (hash: <sha256>)
- Warnings:
  - <count> destructive migration(s) appended (<comma-separated changesets>)

## Aggregate Analysis Changes

- Multi-tenant: was `No`, now `Yes`
- Has children: was `No`, now `Yes` (entity added: `<EntityName>`)
- Polymorphism: introduced on `<owner>.<field>` (subtypes: `<Sub1>`, `<Sub2>`)
- JSONB value objects: added `<VO1>`; removed `<VO2>`

## Tables Changes

### Added
- `<table_name>`
  - Pattern: `<pattern>`
  - Columns: `<col>: <SqlType> <NULL|NOT NULL>`, ...
  - PK: `(<col>, ...)`
  - FK: `(<col>, ...) → <other_table>(<col>, ...)`
  - Indexes: `<index_name>` (column: `<col>`)

### Removed
- `<table_name>`

### Modified
- `<table_name>`
  - Pattern flipped: `<old_pattern>` → `<new_pattern>`
  - Columns added: `<col>: <SqlType> <NULL|NOT NULL>`, ...
  - Columns removed: `<col>: <SqlType>`, ...
  - Columns altered: `<col>: <OldType> → <NewType>`
  - Nullability flipped: `<col>` (`NOT NULL` → `NULL`)
  - Indexes added: `<index_name>` (column: `<col>`)
  - Indexes removed: `<index_name>`
  - Foreign keys added: `(<col>) → <table>(<col>)`
  - Foreign keys removed: `(<col>) → <table>(<col>)`

## Mappers Changes

### Added
- `<MapperName>` — variant: `<variant>` — table: `<table>` — owning class: `<DomainClass>`

### Removed
- `<MapperName>`

### Modified
- `<MapperName>`
  - Variant flipped: `<old_variant>` → `<new_variant>`
  - Reason: <short_phrase>
  - Payload columns changed: `<col>` added; `<col>` removed
  - Discriminator column: `<col>`
  - Subtypes: `<Sub1>`, `<Sub2>`

## Repository Changes

- Pattern flipped: `<old_pattern>` → `<new_pattern>`
  - Reason: <short_phrase>
- Alternative Lookups added:
  - `<finder_signature>` — index: `<index_name>`
- Alternative Lookups removed:
  - `<finder_signature>`
- Alternative Lookups signature changed:
  - `<old_signature>` → `<new_signature>`
    - Index renamed: `<old_index>` → `<new_index>` (<short_phrase>)

## Migrations Changes

### Appended
- `<id> <changeset_text>` (pattern: `<pattern>`)
  - Source delta: <short_phrase>
  - Target file: `db/migrations/<id>_<slug>.yaml`
  - Destructive: yes

### Removed
_(always empty — migrations log is append-only)_

## Context Integration Changes

- Bounded-context name: `<old>` → `<new>`
- Unit of Work class names: `<old>` → `<new>`, `<old>` → `<new>`
- Query Context class names: `<old>` → `<new>`, `<old>` → `<new>`
- New aggregate wired in: `<AggregateName>`
- Aggregate de-wired: `<AggregateName>`

## Affected Artifacts

| Path | Action | Driving section |
|---|---|---|
| `tables/<table>.py` | add | Tables Changes (Added) |
| `tables/<table>.py` | modify | Tables Changes (Modified) |
| `tables/<table>.py` | remove | Tables Changes (Removed) |
| `tables/__init__.py` | modify | Tables Changes (any) |
| `mappers/<x>_mapper.py` | add | Mappers Changes (Added) |
| `mappers/<x>_mapper.py` | modify | Mappers Changes (Modified) |
| `mappers/<x>_mapper.py` | remove | Mappers Changes (Removed) |
| `mappers/__init__.py` | modify | Mappers Changes (any) |
| `command_<aggregate>_repository.py` | modify | Repository Changes |
| `query_<aggregate>_repository.py` | modify | Repository Changes |
| `db/migrations/<id>_<slug>.yaml` | add | Migrations Changes |
| `db/migrations/master.yaml` | modify | Migrations Changes (any) |
| `<context>/unit_of_work/abstract.py` | modify | Context Integration Changes |
| `<context>/unit_of_work/sqlalchemy.py` | modify | Context Integration Changes |
| `<context>/query_context/abstract.py` | modify | Context Integration Changes |
| `<context>/query_context/sqlalchemy.py` | modify | Context Integration Changes |
| `tests/integration/conftest.py` | modify | Tables/Mappers/Repository Changes |
| `tests/integration/test_<aggregate>_repository.py` | modify | Tables/Mappers/Repository Changes |
````

---

## Rendering rules

### Top-of-file sentinel

The first line of the file is an HTML comment recording the SHA256 of `<dir>/<stem>.domain/updates.md`:

```
<!-- domain-updates-hash:<sha256> -->
```

When `<stem>.domain/updates.md` does not exist on disk, render `<sha256>` as `(none)`. The sentinel line itself is always emitted on line 1, followed by one blank line, then the `# Persistence Updates Report` heading.

The sentinel is the consumer's primary skip-on-replay signal: a downstream `/persistence-spec:update-code` run that already applied a report carrying the same `domain-updates-hash` may early-exit.

### Top-level sections

All eight sections are **always emitted** with their headings, in this canonical order:

1. `## Summary`
2. `## Aggregate Analysis Changes`
3. `## Tables Changes`
4. `## Mappers Changes`
5. `## Repository Changes`
6. `## Migrations Changes`
7. `## Context Integration Changes`
8. `## Affected Artifacts`

When a section other than `## Summary` and `## Affected Artifacts` has no content, render its body as the single literal line `_no changes_`. Do not omit the heading.

### Within-section ordering

For sections with `### Added` / `### Removed` / `### Modified` sub-blocks (`Tables Changes`, `Mappers Changes`):

- Sub-block order is fixed: `### Added`, `### Removed`, `### Modified`.
- Within each sub-block, items are ordered alphabetically by name (table name, mapper name).
- Sub-blocks are individually omitted when empty (no heading, no `_None._` placeholder).
- If all three sub-blocks are empty, the parent section's body is `_no changes_`.

For `Migrations Changes`:

- `### Appended` rows preserve **chronological appended-row order by ID** (lowest ID first). Not alphabetical.
- `### Removed` is rendered with the literal body `_(always empty — migrations log is append-only)_` whenever `### Appended` is non-empty (kept for symmetry with the other sections).
- If `### Appended` is empty, the parent section's body is `_no changes_` and `### Removed` is omitted.

For `Aggregate Analysis Changes`, `Repository Changes`, `Context Integration Changes`: emit one bullet per non-stable flag/value. Bullet order is fixed per the Schema block above. If every line would be `_unchanged_`, the section's body is `_no changes_`.

### Section: Summary

- The four lines **Spec**, **Pre-update spec hash**, **Post-update spec hash**, **Domain updates source** are always emitted. The Summary section never reduces to `_no changes_`.
- Hashes are rendered per the **Hash format** rule below.
- The **Domain updates source** value is `_none_` when no domain `updates.md` exists; otherwise it includes the path plus a parenthesised hash (`<dir>/<stem>.domain/updates.md (hash: <sha256>)`).
- The **Warnings** line is omitted entirely when there are no warnings. When present, it introduces a sub-bullet list. The destructive-migration warning renders as `<count> destructive migration(s) appended (<comma-separated changesets>)`.

### Section: Aggregate Analysis Changes

Track these flag flips. Render one bullet per flag whose value differs between pre-update and post-update spec; skip unchanged flags.

- Multi-tenant — `Yes` / `No`. Bullet: `Multi-tenant: was <old>, now <new>`.
- Has children — `Yes` / `No`. When flipping `No → Yes`, append `(entity added: <EntityName>)` (single entity) or `(entities added: <Comma>, <Sep>)` (multiple). When flipping `Yes → No`, append the symmetric `(entity removed: ...)`.
- Polymorphism — `None` / `<owner>.<field>`. When introduced, render `Polymorphism: introduced on <owner>.<field> (subtypes: <Sub1>, <Sub2>)`. When removed, render `Polymorphism: removed on <owner>.<field>`.
- JSONB value objects — list-valued. Render `JSONB value objects: added <VO1>; removed <VO2>` with either clause omitted when empty.

If every flag is unchanged, the section is `_no changes_`.

### Section: Tables Changes

- Added rows include the full table shape: Pattern, Columns, PK, FK, Indexes. Each non-empty list renders inline; empty lists render as `_none_`.
- Modified rows list only the deltas: pattern flips, column add/remove/alter/nullability flip, index add/remove, FK add/remove. Sub-bullets are individually omitted when empty (no `_none_` placeholder for the absent kind).
- Removed rows list only the table name.

### Section: Mappers Changes

- Added rows list variant + table + owning class on a single bullet line per the Schema block.
- Modified rows list variant flips (with reason), payload-column changes, and (for polymorphic mappers only) discriminator + subtypes. Sub-bullets are individually omitted when empty.
- Removed rows list only the mapper name.

### Section: Repository Changes

- Pattern flip is one bullet with a single `Reason: <short_phrase>` sub-bullet.
- Alternative Lookups Added / Removed / Signature Changed are three sub-buckets. Render each header (`Alternative Lookups added:`, etc.) only when its bucket is non-empty.
- A signature-change entry that triggers an index rename includes a sub-bullet `Index renamed: <old> → <new> (<short_phrase>)`.

### Section: Migrations Changes

- Each `### Appended` row renders as:

  ```
  - `<id> <changeset_text>` (pattern: `<pattern>`)
    - Source delta: <short_phrase>
    - Target file: `db/migrations/<id>_<slug>.yaml`
    - Destructive: yes
  ```

  - The `Destructive: yes` sub-bullet is **omitted** when the row is non-destructive. There is no `Destructive: no` form.
  - The `Source delta` value is the literal string `(unknown source)` when the writer cannot trace the row to a domain delta.
  - `<changeset_text>` includes the leading `⚠ ` marker for destructive rows, verbatim from the spec's Changeset cell.
  - `<id>` is the 4-digit zero-padded ID from §2.Migrations.
  - `<slug>` is derived from `<changeset_text>` per `persistence-spec:migration-vocabulary` § Slug derivation.

- The `### Removed` heading is rendered with the literal body `_(always empty — migrations log is append-only)_` whenever `### Appended` has at least one row. When `### Appended` is empty, the parent section is `_no changes_` and `### Removed` is omitted.

### Section: Context Integration Changes

- Bounded-context name change is one bullet (`Bounded-context name: <old> → <new>`).
- Unit of Work class-name changes are one bullet listing the abstract+concrete pair separated by `, ` (`Unit of Work class names: AbstractFooUnitOfWork → AbstractBarUnitOfWork, FooUnitOfWork → BarUnitOfWork`).
- Query Context class-name changes are the symmetric bullet for the query-context pair.
- `New aggregate wired in:` and `Aggregate de-wired:` are two separate bullets. Each is omitted when its set is empty.

If no rename and no aggregate add/remove occurred, the section is `_no changes_`.

---

## `## Affected Artifacts` computation

The footer is a flat dispatch table. The code updater walks it top-to-bottom. Compute as follows:

1. **From Tables Changes**:
   - For each entry under `### Added`: `tables/<table>.py | add | Tables Changes (Added)`.
   - For each entry under `### Removed`: `tables/<table>.py | remove | Tables Changes (Removed)`.
   - For each entry under `### Modified`: `tables/<table>.py | modify | Tables Changes (Modified)`.
   - If any of the three sub-buckets is non-empty, also emit `tables/__init__.py | modify | Tables Changes (any)`.

2. **From Mappers Changes**: same shape as Tables, with `mappers/<x>_mapper.py` (where `<x>` is the snake_case form of the mapper's owning class) and `mappers/__init__.py`.

3. **From Repository Changes**: when the section is not `_no changes_`, emit:
   - `command_<aggregate>_repository.py | modify | Repository Changes`
   - `query_<aggregate>_repository.py | modify | Repository Changes`

4. **From Migrations Changes**:
   - For each appended row: `db/migrations/<id>_<slug>.yaml | add | Migrations Changes`.
   - When at least one row is appended, also emit `db/migrations/master.yaml | modify | Migrations Changes (any)`.

5. **From Context Integration Changes**: when the section is not `_no changes_`, emit (in this order):
   - `<context>/unit_of_work/abstract.py | modify | Context Integration Changes`
   - `<context>/unit_of_work/sqlalchemy.py | modify | Context Integration Changes`
   - `<context>/query_context/abstract.py | modify | Context Integration Changes`
   - `<context>/query_context/sqlalchemy.py | modify | Context Integration Changes`

6. **Test artifacts**: when **any** of Tables / Mappers / Repository sections is not `_no changes_`, emit:
   - `tests/integration/conftest.py | modify | Tables/Mappers/Repository Changes`
   - `tests/integration/test_<aggregate>_repository.py | modify | Tables/Mappers/Repository Changes`

The table header (`| Path | Action | Driving section |` plus the divider row) is always emitted. When every section above is `_no changes_`, the table has no data rows.

### Row ordering

Within the table, rows are emitted in the section-rule order above (Tables → Mappers → Repository → Migrations → Context Integration → Tests). Within each section's contribution, follow the within-section ordering of the source section (alphabetical by name; chronological by ID for Migrations).

### Action vocabulary

The `Action` column is a closed set: `add`, `modify`, `remove`. No other values are emitted.

### `<aggregate>` and `<context>` substitution

- `<aggregate>` is the snake_case form of the aggregate root class name (matches the rest of the persistence-spec stack: `command_<aggregate>_repository.py`, `query_<aggregate>_repository.py`, `test_<aggregate>_repository.py`).
- `<context>` is the bounded-context name read from §2.Context Integration of the post-update spec. When the spec's UoW class names carry no `<Context>` segment (e.g. `AbstractUnitOfWork`), the `<context>/` prefix collapses to the empty string — emit `unit_of_work/abstract.py` directly.

---

## Hash format

All hashes in this report are SHA256 of UTF-8 file content, rendered in **lowercase hex**, full **64-character** form.

When a hash cannot be computed (file missing or unreadable), render the value literally as `(none)`. Never substitute zeros.

---

## Determinism contract

- Byte-stable inputs (working-tree spec, HEAD spec, sibling `<dir>/<stem>.domain/updates.md`) → byte-stable report.
- Re-running the writer with no new changes produces a report whose every section after `## Summary` is `_no changes_`, an empty Affected Artifacts row list, and the same sentinel hash.
- Section ordering, sub-block ordering, and within-block ordering rules above are absolute. No source-defined deviation.
