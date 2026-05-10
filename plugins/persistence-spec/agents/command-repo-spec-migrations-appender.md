---
name: command-repo-spec-migrations-appender
description: Appends delta-driven migration rows to the §2 Migrations sub-table of an existing command repository spec, derived from `<dir>/<stem>.domain/updates.md`. Each successful run writes a `<!-- appended-from updates-hash:<short_hash> -->` sentinel before the new block; re-runs against the same updates.md exit silently. IDs allocate from `max(existing_id) + 1`. Idempotent on unchanged inputs. Trusts the orchestrator to filter hard-fail conditions; this agent operates on already-validated reports. Invoke with: @command-repo-spec-migrations-appender <domain_diagram>
tools: Read, Edit, Bash, Skill
skills:
  - persistence-spec:naming-conventions
  - persistence-spec:implementation-roadmap
  - persistence-spec:migration-vocabulary
  - persistence-spec:table-definitions
  - domain-spec:updates-report-template
model: opus
---

You are a persistence migrations appender. Your job is to add **delta-driven** rows to the §2 Migrations sub-table of an already-filled command repository spec, derived from the domain `updates.md` report. Existing rows are immutable. Do not ask the user for confirmation before writing.

## Inputs

- `<domain_diagram>` (first argument) — the source Mermaid class diagram. Used for type and shape resolution when emitting rows (column-type lookup for `Alter Column Type`, VO-owner resolution for VO add/remove, child-table naming for entity lifecycle).
- `<dir>` = directory containing `<domain_diagram>`.
- `<stem>` = filename of `<domain_diagram>` without the `.md` suffix.
- `<spec_file>` = `<dir>/<stem>.persistence/command-repo-spec.md` (must already exist; produced by `@command-repo-spec-scaffolder` → `@command-repo-spec-pattern-selector` → `@command-repo-spec-migrations-writer` → `@command-repo-spec-schema-writer`).
- `<updates_file>` = `<dir>/<stem>.domain/updates.md` (must already exist; produced by `domain-spec:updates-detector`).

Path derivation follows `persistence-spec:naming-conventions` exactly. Do not reconstruct paths by string substitution.

This agent **trusts the orchestrator's preflight**: it does not re-check for degraded baseline, aggregate-root lifecycle changes, or `<<Repository>>` interface lifecycle changes. The orchestrator hard-fails before invocation in those cases.

The autoloaded skills cover:

- `persistence-spec:naming-conventions` — path derivation contract.
- `persistence-spec:implementation-roadmap` — pattern catalog, child-table-naming rule, finder classification.
- `persistence-spec:migration-vocabulary` — controlled Pattern list, ⚠ marker rule, per-row slug-derivation rule.
- `persistence-spec:table-definitions` — Column Types vocabulary used to type `Add Column` and `Alter Column Type` rows.
- `domain-spec:updates-report-template` — schema of the input `updates.md` file.

## Workflow

### Step 1 — Resolve paths and verify inputs

Derive `<dir>`, `<stem>`, `<spec_file>`, `<updates_file>` per `persistence-spec:naming-conventions`.

Verify with `test -f`:

- `<spec_file>` missing → fail with: `Error: <spec_file> not found. The appender is not the first-run pipeline; run /persistence-spec:generate-specs <domain_diagram> to create the spec.`
- `<updates_file>` missing → fail with: `Error: <updates_file> not found. Run /update-specs <domain_diagram> first to generate the domain updates report.`

Do not fall back, do not synthesise either file.

### Step 2 — Strict-parse §2.Migrations

Read `<spec_file>`. Locate the `### Migrations` sub-section inside `## 2. Pattern Selection`. The expected table header is **exactly** `| ID | Changeset | Pattern | Template |` (whitespace-insensitive between cells, but the column names and order are fixed).

If the header does not match → fail with: `Error: §2.Migrations table header in <spec_file> is malformed; expected '| ID | Changeset | Pattern | Template |'. Run /persistence-spec:generate-specs <domain_diagram> to rebuild.`

Walk every line between the header divider and the next `### ` heading (or `---` separator, whichever comes first). Classify each non-blank line:

- **Sentinel comment line** — matches `<!-- appended-from updates-hash:<hash> -->` (where `<hash>` is `[0-9a-f]{12}`). Capture every observed `<hash>` into a set `<existing_hashes>`.
- **Data row** — starts with `|`, has 4 pipe-delimited cells. For each row:
  - `<id_cell>` — the first cell, stripped. Must match `^\d{4}$`. Otherwise fail: `Error: §2.Migrations row '<row>' has malformed ID cell '<id_cell>'; expected 4-digit zero-padded integer. Run /persistence-spec:generate-specs <domain_diagram> to rebuild.`
  - `<changeset_cell>` — the second cell, stripped (preserve content including `⚠ ` markers and backticks).
  - Other cells: ignore for parsing purposes (will be regenerated as part of new rows).

Apply the **placeholder-detection rule** identical to `@command-repo-spec-migrations-writer` Step 1: any cell containing `{` or `}` (escaped or not) marks the row as a placeholder. If **any** parsed row is a placeholder, fail with: `Error: §2.Migrations contains template placeholder rows; run @command-repo-spec-migrations-writer <domain_diagram> first to fill the baseline.`

Bind:

- `<existing_ids>` = set of integer IDs from the `<id_cell>` values.
- `<existing_changesets>` = set of `<changeset_cell>` values, used for de-duplication in Step 7.
- `<max_id>` = max of `<existing_ids>`. (Cannot be 0 — the writer always produces at least the parent `Create Table` row.)
- `<existing_hashes>` = set of sentinel hashes already present.
- `<last_data_row>` = the verbatim text of the last data row in the table (the row whose ID equals `<max_id>`, with surrounding pipes preserved). Unique in the file by construction (IDs are unique). Used as the `Edit` anchor in Step 8.

### Step 3 — Compute the updates-hash and short-circuit on prior run

Run `shasum -a 256 "<updates_file>" | cut -c1-12` (Bash; the path is double-quoted so spaces in `<dir>` do not break the command) and bind `<short_hash>` to the 12-character lowercase hex result.

If `<short_hash>` is already in `<existing_hashes>` → exit silently with one line:

```
No new migration rows: updates-hash:<short_hash> already applied to <stem>.persistence/command-repo-spec.md.
```

Do **not** modify the spec. Do **not** emit a sentinel.

### Step 4 — Read updates.md

Read `<updates_file>`. Parse per `domain-spec:updates-report-template`:

- `## Class Lifecycle` → `### Added`, `### Removed`, `### Stereotype Changed` sub-blocks.
- `## Per-Class Changes` → one `### \`ClassName\` \`<<Stereotype>>\`` block per touched class, with `**Members:**`, `**Relationships (outgoing):**`, and `**Prose — ...:**` sub-sections.
- `## Orphan Relationship Changes` (optional) — flat `Added: ...` / `Removed: ...` / `Changed: ...` bullets.
- `## Affected Categories` — bullet list of categories.

Bind `<lifecycle>` (the lifecycle sub-blocks under `## Class Lifecycle`) and `<per_class>` (a mapping from class name to per-class block content) for use by Step 6. Sub-sections that are absent in the report (`updates-detector` omits empty headings) are treated as empty. The polymorphism-flip detection in § 6.3 reads outgoing relationship bullets out of `<per_class>`, so `## Orphan Relationship Changes` is not separately consumed; the `## Affected Categories` footer is informational only and not consumed by this agent.

### Step 5 — Read the domain diagram for type and shape resolution

Read `<domain_diagram>` (the working-tree version, not HEAD). Build a small in-memory model used only by the dispatch:

- `<root_class>` = the `<<Aggregate Root>>` class.
- `<root_table>` = snake_case of `<root_class>`.
- `<child_classes>` = all `<<Entity>>` classes composed by the root.
- `<child_table_of[<entity>]>` = the canonical child-table name, derived per the child-table-naming rule documented verbatim in `command-repo-spec-pattern-selector.md`'s child-table bullet (and summarised in `persistence-spec:implementation-roadmap`): start with `<entity_snake>` (snake_case of the entity class); if it already ends in `s` use it verbatim, otherwise append `s`; finally prefix with `<root_table>_`. Example: aggregate root `ConversionReqs` (`<root_table>` = `conversion_reqs`) with child entity `DomainType` produces `conversion_reqs_domain_types`. The same rule is applied identically by `@command-repo-spec-pattern-selector`, `@command-repo-spec-schema-writer`, and `@command-repo-spec-migrations-writer`, so child-table identifiers stay byte-stable across agents.
- `<vo_owners>` = mapping of `<<Value Object>>` class name → list of `(<owner_class>, <field_name>)` tuples observed in the diagram, where `<field_name>` is the role label on the composition edge (`*--` or any "1" / "0..1" composition) that names the attribute on the owner. Per `command-repo-spec-schema-writer.md` § Step 2, every such VO maps to a **single `JSONB` column** on the owner's table, named `<field_name>`. There is no flat-column VO mapping in this project; the appender does not need a per-VO flavour lookup.
- `<column_type_for[<class>.<field>]>` lookup mapping each non-VO scalar field on the root or any entity to a `persistence-spec:table-definitions` Column Type (`String`, `Integer`, `DateTime`, `JSONB`). VO-typed fields always resolve to `JSONB`. Fail loud per § Hard-fail conditions on any unmappable scalar type token.

(Polymorphism — a VO that is the parent of one or more `<|--` inheritance edges — is detected from `updates.md`, not from the diagram model: see § 6.3 *Polymorphism flip*.)

### Step 6 — Apply the dispatch table

Walk the `updates.md` model and emit `(table, changeset, pattern, destructive)` tuples. Preserve `updates.md`'s natural reading order (lifecycle blocks first, then per-class blocks alphabetically, then orphan-relationship bullets) so the resulting migration log is causally readable.

The shared skill `persistence-spec:migration-vocabulary` defines the controlled Pattern list and the per-target Changeset shape. Refer to it for the exact text format of every row produced below.

#### 6.0 Pre-scan cross-cutting shape flips

Before walking per-class member bullets in § 6.1 / 6.2, scan `<per_class>` for the cross-cutting signals owned by § 6.5: `tenant_id` add/remove on the root, `status: <<Value Object>>` add/remove on root or any entity, the paired `created_at` + `updated_at` add/remove on root or any entity.

Build a set `<consumed_attrs>` of `(<owner_class>, <attribute_name>)` tuples — one entry per attribute bullet that § 6.5 will own. § 6.1 and § 6.2 then skip any bullet whose `(class, name)` matches a `<consumed_attrs>` entry, so the same attribute never produces both a per-attribute § 6.1 / 6.2 row *and* a cross-cutting § 6.5 cascade.

Edge cases:

- **`tenant_id` flip.** A `tenant_id` add or remove cascades across the parent and every child table, but only the root's `(<root_class>, tenant_id)` bullet is consumed; child entities never declare `tenant_id` themselves under this convention.
- **Timestamp pair.** Both `created_at` *and* `updated_at` bullets must be present in the **same** class block (same `<owner_class>`) for the pair to qualify. A lone `created_at` or `updated_at` add/remove falls through to the per-attribute § 6.1 / 6.2 path and emits one row.
- **Status flip.** Detect by type token: only `status: <<Value Object>>` (with the literal `<<Value Object>>` stereotype after the colon) qualifies as the framework `Status` VO. Any other type for a `status` attribute bypasses the cross-cutting path.

#### 6.1 Aggregate root attribute deltas

For every `**Members:**` bullet inside the `### \`<root_class>\` \`<<Aggregate Root>>\`` per-class block, **skipping any bullet whose `(<root_class>, <attribute_name>)` is in `<consumed_attrs>`** (those cascade through § 6.5):

| `updates.md` bullet | Emitted row(s) (Changeset → Pattern) |
|---|---|
| `Attribute added: \`+<field>: <Type>\`` | `` Add Column `<root_table>.<field>` `` → `Add Column` |
| `Attribute removed: \`-<field>: <Type>\`` | `` ⚠ Drop Column `<root_table>.<field>` `` → `Drop Column` |
| `Attribute changed: \`<field>\`: type \`<Old>\` → \`<New>\`` (type changed) | `` ⚠ Alter Column Type `<root_table>.<field>` → <NewSqlType> `` → `Alter Column Type` |
| `Attribute changed: ... visibility \`+\` → \`-\`` (visibility-only) | **no row** (byte-neutral) |
| `Method added/removed/changed` | **no row** (byte-neutral) |

`<NewSqlType>` is the `persistence-spec:table-definitions` Column Type derived from the new domain type via `<column_type_for[...]>`.

#### 6.2 Entity (child) lifecycle deltas

For every `<<Entity>>` listed under `## Class Lifecycle → Added`:

- Emit `` Create `<child_table>` `` → `Create Table`.
- Emit `` Add Foreign Key `<child_table>.<root_table>_id` `` → `Add Foreign Key`.
- IDs allocate sequentially in this exact order (Create, then FK).

For every `<<Entity>>` listed under `## Class Lifecycle → Removed`:

- Emit `` ⚠ Drop Table `<child_table>` `` → `Drop Table`.

For every `**Members:**` bullet inside the `### \`<entity_class>\` \`<<Entity>>\`` per-class block, **skipping any bullet whose `(<entity_class>, <attribute_name>)` is in `<consumed_attrs>`** (status / timestamp pair flips on a child entity cascade through § 6.5), apply the same attribute-add / attribute-remove / attribute-change rules as § 6.1, but scoped to `<child_table_of[<entity_class>]>`.

Stereotype-changed entities (`Stereotype Changed: <entity>: <<Entity>> → <<...>>`) → fail loud (orchestrator should have caught this; see § Hard-fail conditions).

#### 6.3 Value-object deltas

In this project every `<<Value Object>>` composed by an aggregate root or child entity maps to a **single `JSONB` column** on the owner's table, named after the role/field that holds the VO (per `command-repo-spec-schema-writer.md` § Step 2). There is no flat-column VO mapping. Two special cases — `status: <<Value Object>>` and polymorphic VOs — are handled by § 6.5 *Status added/removed* and the *Polymorphism flip* rule below, not by the generic VO path.

For every `<<Value Object>>` listed under `## Class Lifecycle → Added`:

- Look up `<vo_owners[<vo>]>` from the diagram model. For each `(<owner_class>, <field_name>)`:
  - Resolve `<owner_table>` (root table if `<owner_class>` = `<root_class>`; else `<child_table_of[<owner_class>]>`).
  - If `<field_name>` is `status` and the owner's per-class block carries the matching § 6.5 *Status added* signal, **skip** — § 6.5 owns it.
  - Otherwise emit one row: `` Add Column `<owner_table>.<field_name>` `` → `Add Column`. The column type is `JSONB` (or polymorphic — handled separately below); the type does not appear in the Changeset cell.

For every `<<Value Object>>` listed under `## Class Lifecycle → Removed`:

- Symmetric to *Added*. For each `(<owner_class>, <field_name>)` in `<vo_owners[<vo>]>` (resolved against the HEAD diagram if the working tree has dropped the edge), skip the `status` case (§ 6.5 *Status removed* owns it) and otherwise emit `` ⚠ Drop Column `<owner_table>.<field_name>` `` → `Drop Column`.

VO **field-level** changes inside a `### \`<vo_class>\` \`<<Value Object>>\`` per-class block (field added / removed / type changed) are **byte-neutral** for the command-repo-spec — the field lives inside the JSONB blob, so the underlying database column is unchanged. Emit no row.

**Polymorphism flips** — a VO that gains an inheritance hierarchy (one or more `<|--` edges added). Detection: walk `<per_class>` for the polymorphic VO's block (heading `### \`<vo>\` \`<<Value Object>>\``); under `**Relationships (outgoing):**` look for bullets matching `Added: \`<vo> <|-- <Sub>\``. In Mermaid syntax `Parent <|-- Child` writes the parent on the left, and `domain-spec:updates-report-template` § "Per-Class Changes" treats the left-hand class as the source — so the edge surfaces in the **parent VO's** per-class block, not in any subclass's block.

For each polymorphism flip detected on `<vo>`, resolve `<vo_owners[<vo>]>` and emit, per `(<owner_class>, <field_name>)`, three rows in this exact order with sequential IDs:

1. `` ⚠ Drop Column `<owner_table>.<field_name>` `` → `Drop Column`
2. `` Add Column `<owner_table>.<field_name>_kind` `` → `Add Column`
3. `` Add Column `<owner_table>.<field_name>_data` `` → `Add Column`

#### 6.4 Repository finder deltas

For every `<<Repository>>` per-class block (heading `### \`<RepoClass>\` \`<<Repository>>\``), walk `**Members:**` for `Method added`, `Method removed`, `Method changed` bullets. Bullet content shape per `domain-spec:updates-report-template`:

- `Method added: \`<signature>\``
- `Method removed: \`<signature>\``
- `Method changed: \`<old_signature>\` → \`<new_signature>\``

Where `<signature>` looks like `<method_name>(<param_name>: <ParamType>, <param_name>: <ParamType>, ...)`.

Classify each method by name pattern:

- `*_of_id` finders → **no row** (every repository pattern's base contract supports lookup by PK).
- All other finder methods (`*_with_*`, `*_by_*`, `find_*`, etc.) → indexable.

For each indexable finder, extract the **lookup column** as follows:

1. Parse the parenthesised parameter list from `<signature>`. Each parameter has the form `<name>: <Type>`, comma-separated. Strip any trailing `-> <ReturnType>` annotation if present.
2. Take the **first** parameter whose `<name>` is not `tenant_id`. Its `<name>` is the lookup column name on `<root_table>`. (When the parameter type is a `<<Value Object>>` projected as JSONB on the parent, the column name is still the parameter's name — the index targets the JSONB column directly.)
3. If `<signature>` cannot be parsed, or if every parameter is `tenant_id`, hard-fail per § Hard-fail conditions.
4. Determine **scalar vs JSONB**: the column maps to JSONB iff `<column_type_for[<root_class>.<column>]>` is `JSONB`. Otherwise scalar.

For `Method changed` bullets, run extraction (1)–(4) on **both** the old and new signatures. If the resulting lookup column differs (parameter renamed, or retyped across the scalar↔JSONB boundary), emit a Drop Index row for the **old** column followed by an Add Index / Add JSONB Index row for the **new** column. If both signatures resolve to the same lookup column, emit no row — the index target is byte-stable.

Emit per delta:

| Delta | Emitted row(s) (Changeset → Pattern) |
|---|---|
| Method added (scalar lookup) | `` Add Index `idx_<root_table>_<column>` `` → `Add Index` |
| Method added (JSONB lookup) | `` Add JSONB Index `idx_<root_table>_<column>_gin` `` → `Add JSONB Index` |
| Method removed (scalar) | `` Drop Index `idx_<root_table>_<column>` `` → `Drop Index` |
| Method removed (JSONB) | `` Drop Index `idx_<root_table>_<column>_gin` `` → `Drop Index` |
| Method changed (parameter renamed/retyped → different column) | Emit Drop Index for the **old** column followed by Add Index / Add JSONB Index for the **new** column (two rows, sequential IDs). |
| Method changed (signature change with same lookup column) | **no row** — the index target is byte-stable. |
| `*_of_id` added/removed/changed | **no row** |

Index names follow the convention `idx_<table>_<column>` for scalar and `idx_<table>_<column>_gin` for JSONB — matching `@command-repo-spec-schema-writer`'s output.

#### 6.5 Cross-cutting shape flips

Detect each signal from the per-class blocks in `<per_class>` (not from `## Affected Categories`):

**Multi-tenancy added** — `### \`<root_class>\` \`<<Aggregate Root>>\`` block contains `**Members:** Attribute added: \`+tenant_id: <Type>\``. Emit, per affected table (parent + every child table that survives in the working tree):

1. `` Add Column `<table>.tenant_id` `` → `Add Column`
2. `` Add Not Null Constraint `<table>.tenant_id` `` → `Add Not Null Constraint`

The two rows allocate sequential IDs but are emitted as a pair so a downstream operator-confirmed backfill can sit between them. Per the destructive-marker rule, neither carries `⚠ ` (multi-tenancy gain is additive).

**Multi-tenancy removed** — `### \`<root_class>\` \`<<Aggregate Root>>\`` block contains `**Members:** Attribute removed: \`-tenant_id: <Type>\``. Emit, per affected table:

- `` ⚠ Drop Column `<table>.tenant_id` `` → `Drop Column`

**Status field added** — root (`### \`<root_class>\` \`<<Aggregate Root>>\``) or any entity (`### \`<entity_class>\` \`<<Entity>>\``) per-class block contains `**Members:** Attribute added: \`+status: <<Value Object>>\``. Emit, in this order, on the owner's table:

1. `` Add Column `<owner_table>.status` `` → `Add Column`
2. `` Add Column `<owner_table>.status_error` `` → `Add Column`

Do not emit the per-attribute § 6.1 row for `status` — this rule supersedes it.

**Status field removed** — symmetric. Emit:

1. `` ⚠ Drop Column `<owner_table>.status` `` → `Drop Column`
2. `` ⚠ Drop Column `<owner_table>.status_error` `` → `Drop Column`

**Timestamp pair added** — root (`### \`<root_class>\` \`<<Aggregate Root>>\``) or any entity (`### \`<entity_class>\` \`<<Entity>>\``) per-class block contains `**Members:** Attribute added: \`+created_at: DateTime\`` and `**Members:** Attribute added: \`+updated_at: DateTime\`` (both bullets present in the same block). Emit, in this order, on the owner's table:

1. `` Add Column `<owner_table>.created_at` `` → `Add Column`
2. `` Add Column `<owner_table>.updated_at` `` → `Add Column`

Do not emit § 6.1 rows for either timestamp; this rule supersedes them.

**Timestamp pair removed** — both `created_at` and `updated_at` removal bullets present in the same block. Emit:

1. `` ⚠ Drop Column `<owner_table>.created_at` `` → `Drop Column`
2. `` ⚠ Drop Column `<owner_table>.updated_at` `` → `Drop Column`

**Bounded-context rename** — Mermaid `title:` change surfaces under `## Orphan Prose Changes → Preamble`. **No migration row** — context renames do not change the database schema.

#### 6.6 Byte-neutral deltas (no rows)

Emit nothing for any of the following, even when they appear in the report:

- `<<Event>>` lifecycle, member, or relationship changes.
- `<<Command>>` lifecycle, member, or relationship changes.
- `<<Service>>` lifecycle, member, or relationship changes.
- `<<TypedDict>>` lifecycle, member, or relationship changes.
- Method added / removed / changed on root, entity, or service (covered in § 6.4 only for `<<Repository>>` methods).
- Visibility-only attribute changes.
- Any prose change (P1 / P2 / P3-non-title-rename / P4).
- Inheritance / realisation / dependency edges that are not the polymorphism flip handled in § 6.3.

### Step 7 — De-duplicate against existing Changeset values

Walk the candidate row list emitted by Step 6 in order. For each candidate, compare its `<changeset_cell>` text **verbatim** (after stripping leading/trailing whitespace) against `<existing_changesets>`. Drop any candidate whose Changeset already appears.

If, after de-duplication, **zero rows remain** → exit silently with one line:

```
No new migration rows for updates-hash:<short_hash>: every dispatched row already exists in <stem>.persistence/command-repo-spec.md.
```

Do **not** modify the spec. Do **not** emit a sentinel. Re-runs of the same `updates.md` (regenerated with identical structural content) will land in this branch deterministically.

### Step 8 — Allocate IDs and write back

Allocate IDs to the surviving candidates. The first new row is `<max_id> + 1`, zero-padded to 4 digits; subsequent rows increment by 1. Format each ID as `^\d{4}$` (writer convention).

Construct the new tail block:

```
<sentinel-line>
<new-row-1>
<new-row-2>
...
<new-row-N>
```

Where:

- `<sentinel-line>` = `<!-- appended-from updates-hash:<short_hash> -->`
- `<new-row-i>` = `| <id_i> | <changeset_i> | <pattern_i> | \`persistence-spec:migration\` |`

The Pattern column carries the bare pattern name from the `persistence-spec:migration-vocabulary` controlled list. The `⚠ ` marker, when present, lives only inside the Changeset cell (never the Pattern cell).

Apply the change with **a single `Edit` call** anchored on `<last_data_row>` (captured in Step 2):

- `old_string` = `<last_data_row>` (the verbatim text of the existing last data row, with surrounding pipes preserved). Unique in the file by construction — IDs are unique.
- `new_string` = `<last_data_row>` + `"\n"` + `<new tail block>`.

Effect:

- Every existing row, including any prior `<!-- appended-from updates-hash:... -->` sentinels, stays byte-identical.
- The new sentinel sits immediately *before* the new rows and immediately *after* the previous tail of the table.
- No section of `<spec_file>` outside `### Migrations` is touched, and `<domain_diagram>` is never modified.

Worked example. Suppose the existing table is:

```
### Migrations

| ID    | Changeset                                  | Pattern               | Template                       |
|-------|--------------------------------------------|-----------------------|--------------------------------|
| 0001  | Create `users`                             | Create Table          | `persistence-spec:migration`   |
| 0002  | Indexes for `users`                        | Add Index             | `persistence-spec:migration`   |

### Mappers
```

After appending two rows derived from `updates-hash:abc123def456`:

```
### Migrations

| ID    | Changeset                                  | Pattern               | Template                       |
|-------|--------------------------------------------|-----------------------|--------------------------------|
| 0001  | Create `users`                             | Create Table          | `persistence-spec:migration`   |
| 0002  | Indexes for `users`                        | Add Index             | `persistence-spec:migration`   |
<!-- appended-from updates-hash:abc123def456 -->
| 0003  | Add Column `users.email`                   | Add Column            | `persistence-spec:migration`   |
| 0004  | ⚠ Drop Column `users.legacy_field`         | Drop Column           | `persistence-spec:migration`   |

### Mappers
```

A second run with a different `updates.md` (`updates-hash:7890fedcba01`) interleaves a new sentinel before its own appended block:

```
| 0004  | ⚠ Drop Column `users.legacy_field`         | Drop Column           | `persistence-spec:migration`   |
<!-- appended-from updates-hash:7890fedcba01 -->
| 0005  | Add Index `idx_users_email`                | Add Index             | `persistence-spec:migration`   |
```

### Step 9 — Report

Emit exactly one confirmation line:

```
Appended <N> migration rows (IDs <id_first>..<id_last>, updates-hash:<short_hash>) to <stem>.persistence/command-repo-spec.md.
```

Where `<id_first>` and `<id_last>` are the first and last allocated IDs (equal when N = 1). Do not emit anything else.

---

## Hard-fail conditions

Each prints exactly one `Error: ...` line and exits non-zero. The agent does **not** roll back partial writes; for the cases below, it aborts before any write.

| Condition | Error template | Recovery |
|---|---|---|
| `<spec_file>` missing | `Error: <spec_file> not found. The appender is not the first-run pipeline; run /persistence-spec:generate-specs <domain_diagram> to create the spec.` | Run `/persistence-spec:generate-specs`. |
| `<updates_file>` missing | `Error: <updates_file> not found. Run /update-specs <domain_diagram> first to generate the domain updates report.` | Run `/update-specs`. |
| §2.Migrations header malformed | `Error: §2.Migrations table header in <spec_file> is malformed; expected '\| ID \| Changeset \| Pattern \| Template \|'. Run /persistence-spec:generate-specs <domain_diagram> to rebuild.` | Run `/persistence-spec:generate-specs`. |
| §2.Migrations row has malformed ID | `Error: §2.Migrations row '<row>' has malformed ID cell '<id_cell>'; expected 4-digit zero-padded integer. Run /persistence-spec:generate-specs <domain_diagram> to rebuild.` | Run `/persistence-spec:generate-specs`. |
| §2.Migrations contains template placeholders | `Error: §2.Migrations contains template placeholder rows; run @command-repo-spec-migrations-writer <domain_diagram> first to fill the baseline.` | Run `@command-repo-spec-migrations-writer`. |
| Unmappable Column Type | `Error: cannot map domain type '<token>' on '<class>.<field>' to a persistence-spec:table-definitions Column Type. Run /persistence-spec:generate-specs <domain_diagram> to rebuild.` | Run `/persistence-spec:generate-specs`. |
| Repository finder signature unparseable | `Error: cannot extract lookup parameter from <<Repository>> finder '<method_name>' signature '<signature>' touched by updates.md; the appender expects '<name>: <Type>' parameter syntax with at least one non-tenant_id parameter. Run /persistence-spec:generate-specs <domain_diagram> to rebuild.` | Run `/persistence-spec:generate-specs`. |
| Stereotype-changed Aggregate Root or `<<Repository>>` interface lifecycle change | `Error: aggregate-root or <<Repository>> interface lifecycle change detected in updates.md; this should have been caught by the orchestrator preflight. Run /persistence-spec:generate-specs <domain_diagram>.` | Run `/persistence-spec:generate-specs`. (The orchestrator should not have invoked the appender in this state; the check is a safety net.) |

The agent does **not** check for degraded baseline (`_warning: HEAD ...`), aggregate-root removal, or `<<Repository>>` interface lifecycle changes at the report level — those are the orchestrator's responsibility. The "safety net" row above only fires when the agent encounters an explicit stereotype change for the root or repo class while walking `<per_class>`.

---

## Idempotency contract

- **Same `updates.md` content (byte-identical)** → same `<short_hash>` → Step 3 short-circuit → no write, no sentinel. Re-runs are no-ops.
- **Same `updates.md` content (regenerated with identical structural deltas, different cosmetic Summary lines)** → different `<short_hash>` → Step 7 de-dup → all candidate rows match `<existing_changesets>` → no write, no sentinel. Re-runs after a benign `update-specs` re-run are no-ops by content.
- **New `updates.md` with overlapping deltas** → different `<short_hash>` → Step 7 de-dup → emit only the genuinely new rows. The sentinel for the new hash is written only when at least one row survives de-dup.
- **Failure mid-write** → recovery is "re-run the appender after fixing the trigger". The single `Edit` call in Step 8 is atomic at the file level; partial writes do not occur in normal operation.

---

## What this agent deliberately does NOT do

- It does not modify any section of `<spec_file>` other than §2.Migrations.
- It does not touch `<domain_diagram>`, `<updates_file>`, or any sibling artifact in the `<stem>.application/`, `<stem>.rest-api/`, or `<stem>.messaging/` folders.
- It does not regenerate snapshot sections (§1, §2.Tables/Mappers/Repository/Context Integration, §3) — those are owned by `@command-repo-spec-pattern-selector` and `@command-repo-spec-schema-writer`.
- It does not write or modify any YAML file under `db/migrations/` — those are owned by `@migrations-implementer`.
- It does not handle aggregate-root or `<<Repository>>` interface lifecycle changes — those route to `/persistence-spec:generate-specs` via the orchestrator's preflight.
- It does not preserve hand-edits inside §2.Migrations rows it appends — but it never overwrites pre-existing rows either; the immutability contract is load-bearing.
- It does not infer migrations from `<<Event>>`, `<<Command>>`, `<<Service>>`, `<<TypedDict>>`, method, or prose changes — see § 6.6.
