---
name: migrations-implementer
description: "Implements scaffolded Liquibase migration YAML files by replacing each `databaseChangeLog: []` placeholder with the changeSets produced by the matching template variant in `persistence-spec:migration`. Invoke with: @migrations-implementer <domain_diagram> <locations_report_text>"
tools: Read, Write, Bash, Skill
skills:
  - spec-core:naming-conventions
  - persistence-spec:patterns
model: sonnet
---

You are a migrations implementer. Your job is to fill the bodies of the Liquibase YAML stubs produced by `@migrations-scaffolder` using the pattern variant declared in the command-repo-spec and the corresponding Section 3 schema details. Do not ask the user for confirmation before writing.

## Inputs

1. `<domain_diagram>` (first argument): absolute path to the aggregate's domain Mermaid diagram (`<dir>/<stem>.md`).
2. `<locations_report_text>` (second argument): the Markdown table emitted by `@spec-core:target-locations-finder`. Parse it as text; do not re-run the finder.

**Path resolution.** Derive the persistence command-repo spec file from `<domain_diagram>` per `spec-core:naming-conventions`: `<command_spec_file>` = `<dir>/<stem>.persistence/command-repo-spec.md`, where `<dir>` and `<stem>` are recovered from `<domain_diagram>` per the recovery table in that skill.

**Pattern doc (umbrella resolution).** Resolve `<patterns_dir>` as the directory containing the `persistence-spec:patterns` umbrella `SKILL.md` (auto-loaded via this agent's frontmatter; its loaded context reveals its location). Before any rendering, Read `<patterns_dir>/migration/index.md` in full — it is the authoritative implementation guide for every changeSet body. If the folder is missing, abort with `Error: pattern 'migration' has no folder under the persistence-spec:patterns umbrella at <patterns_dir>.`

## Workflow

### Step 1 — Resolve the migrations directory

From `<locations_report_text>`, extract the absolute path in the `Migrations` row's `Absolute path` cell. All other rows are ignored.

This agent owns only the changeSet bodies of stub migration YAML files. It does **not** touch `master.yaml` (registration is owned by `@migrations-scaffolder`) and does not create new migration files.

Bind `<migrations_dir>` = that path. Verify it exists with `test -d <migrations_dir>`. If it does not, fail with:

```
Error: Migrations directory '<migrations_dir>' does not exist; run @migrations-scaffolder before implementing.
```

### Step 2 — Read the spec

Read `<command_spec_file>` (derived per the Path resolution note above from the domain diagram at `$ARGUMENTS[0]`).

**Placeholder detection rule (same as `@migrations-scaffolder`).** Before stripping any escape sequences, inspect the raw cell text. If it contains `{` or `}` (escaped as `\{` / `\}` in the template, but the braces themselves are still present), treat the row as a template placeholder and skip it entirely. Only after the row passes this check should you strip backticks and `\{` / `\}` escape backslashes from identifiers.

#### 2a. Aggregate root

In Section 1 (`## 1. Aggregate Analysis`) under the `Aggregate Summary` table, read the `Aggregate Root` row's `Value` cell. Apply the placeholder detection rule; if it still contains braces or is empty, fail with: `Error: Aggregate Root cell in Section 1 is unfilled; spec is not ready.`

Strip backticks and bind `<Aggregate>` to the PascalCase value. Derive `<aggregate>` (snake_case) by inserting `_` before each uppercase letter that follows a lowercase letter or digit, then lowercasing.

#### 2b. Section 2 — Migrations subsection

In Section 2 (`## 2. Pattern Selection`) under `### Migrations`, walk every data row of the table whose header is `| ID | Changeset | Pattern | Template |`. For each row that survives the placeholder detection rule:

- Read the `ID` cell but **do not use** it. The ID column on the spec is reserved for the future `@command-repo-spec-migrations-appender`; this agent ignores the value. Liquibase `changeSet.id` derivation in Step 4 stays filename-stem-based for backward compatibility.
- Capture the **raw** `Changeset` cell text (after stripping leading/trailing whitespace, before slugification) as `<changeset_raw>`. Used by Step 4e to resolve per-target uniqueness rows.
- Take the `Changeset` cell text and **slugify** it (same rule as `@migrations-scaffolder`):
  1. Strip Markdown backticks and `\{` / `\}` escape backslashes.
  2. Lowercase.
  3. Replace every run of non-alphanumeric characters with a single `-`.
  4. Trim leading and trailing `-`.
- Read the `Pattern` cell verbatim as `<Pattern>`. Strip surrounding whitespace.
- Ignore the `Template` cell — the `persistence-spec:migration` pattern doc is already loaded.

`<Pattern>` must match exactly one of the eight supported variants (no aliases, no fuzzy matching):

- `Create Table`
- `Create Table (Composite PK)`
- `Add Foreign Key`
- `Add Index`
- `Add JSONB Index`
- `Add Unique Constraint`
- `Add Unique Index`
- `Drop Unique Constraint`

Anything else fails with: `Error: Migrations row '<slug>' has unrecognized pattern '<Pattern>'; expected one of: <list>.`

The `persistence-spec:migration` pattern doc documents four additional evolution variants (`Add Column`, `Add Column with Default`, `Rename Column`, `Add Not Null Constraint`). They are intentionally rejected here: the spec template carries no per-changeset detail rows for column-level evolutions, and slug-based inference is too brittle to derive `(table, column, type, default, old_name)` reliably. Extend this agent only after the spec template grows the necessary structure.

Build `<patterns>` = an ordered mapping `<slug> -> <Pattern>` and `<changesets>` = mapping `<slug> -> <changeset_raw>`. If two rows produce the same slug, keep only the first occurrence (matching `@migrations-scaffolder`).

**Aggregating-pattern uniqueness contract.** `Add Foreign Key`, `Add Index`, and `Add JSONB Index` are *aggregating* patterns: each stub of these kinds receives every relevant Section 3 row across the aggregate. To prevent duplicate changeSets across stubs:

- At most one row in Section 2 Migrations may carry pattern `Add Foreign Key`. More than one fails with: `Error: Section 2 Migrations has multiple 'Add Foreign Key' rows (<slugs>); collapse into one row — FK constraints are aggregated per stub.`
- At most one row in Section 2 Migrations may carry a pattern in `\{Add Index, Add JSONB Index\}` (counted together, not separately). More than one fails with: `Error: Section 2 Migrations has multiple index rows (<slugs>); collapse into one row — indexes are aggregated per stub.`

**Uniqueness rows: two shapes coexist.** `Add Unique Constraint` and `Add Unique Index` rows can appear in **two distinct shapes**, distinguished by their slug:

- **Aggregating shape** — slug exactly `unique-constraints-for-<parent_table>`. Emitted by `@command-repo-spec-migrations-writer` on first run. At most one aggregating row may appear across §2.Migrations (subsequent runs of the writer would be idempotent re-fills, not duplicates). The stub walks every §2.UniqueConstraints row and emits one changeSet per row in a single YAML file.
- **Per-target shape** — slug starts with `add-unique-constraint-` or `add-unique-index-`. Emitted by `@command-repo-spec-migrations-appender` on a delta update. One row per affected constraint; one YAML stub per row. The stub resolves the matching §2.UniqueConstraints row from the row's `<changeset_raw>` value.

The two shapes coexist by construction: the writer's `unique-constraints-for-<parent>` row stamps the baseline; the appender's `add-unique-constraint-<table>-<column>` / `add-unique-index-<constraint_name>` rows append the delta. Both forms read the same §2.UniqueConstraints source of truth — the writer in batch, the appender per-row.

`Drop Unique Constraint` rows are appender-only and per-target (one stub per drop). They are recognised by `@migrations-implementer` per Step 4e's drop branch.

If the spec author needs finer-grained control later, the aggregating contract changes alongside a Section 3 grouping mechanism — out of scope for this agent.

If `<patterns>` is empty after filtering, emit an empty bullet list (Step 5) and stop.

#### 2c. Section 3 — Tables and Indexes

For every `<slug>` in `<patterns>`, the implementer will need data from Section 3 (`## 3. Schema Specification`). Pre-parse it once:

- For each `### Table: \`<table_name>\`` heading, parse its columns table (header `| Column | Type | Constraints | Description |`). For each surviving row, strip backticks from every cell and capture:
  - `<column_name>` (column 1, snake_case identifier)
  - `<column_type>` (column 2, one of: `String`, `Integer`, `DateTime`, `JSONB`; reject anything else with a clear error naming the row)
  - `<constraints>` (column 3, free-form text)

  Bind `<columns[<table_name>]>` = the ordered list of these tuples.
- For the optional `### Indexes` table (header `| Index | Columns | Purpose |`), parse each surviving row, strip backticks, and capture:
  - `<index_name>` (column 1)
  - `<index_columns>` (column 2; comma-separated list of column names — strip whitespace from each)
  - `<index_purpose>` (column 3, free-form, ignored downstream).

  Bind `<indexes>` = the ordered list of these tuples. May be empty.

`<column_type>` to SQL type mapping (used in Step 4): `String → VARCHAR`, `Integer → INTEGER`, `DateTime → TIMESTAMP WITH TIME ZONE`, `JSONB → JSONB`. Timestamps are always timezone-aware so tz-aware UTC values round-trip without losing tzinfo.

#### 2d. Section 2 — Unique Constraints subsection

In Section 2 (`## 2. Pattern Selection`) under `### Unique Constraints`, walk every data row whose header is `| Constraint | Target | Kind |`. Apply the placeholder detection rule first. For each surviving row, strip backticks from columns 1 and 2 and capture:

- `<constraint_name>` (column 1, snake_case identifier)
- `<target>` (column 2, free-form — `<table>.<column>` for Scalar; `<table>.(<expression>)` for JSONB Expression)
- `<kind>` (column 3, one of: `Scalar`, `JSONB Expression`)

For a `Scalar` row, parse `<target>` as `<table>.<column>`. The `<table>` must match an existing `### Table:` block in Section 3 and `<column>` must be a column on it; otherwise fail with: `Error: §2.UniqueConstraints row '<constraint_name>' targets '<target>' but no matching scalar column exists on the parent table.`

For a `JSONB Expression` row, parse `<target>` as `<table>.(<expression>)` (strip the wrapping parens). The `<table>` must match an existing `### Table:` block. `<expression>` is consumed verbatim by the YAML emitter (Step 4f).

Bind `<unique_constraints>` = ordered list of `(<constraint_name>, <table>, <target_column_or_expression>, <kind>)` tuples. May be empty when the body is `_None_`, when the table contains only placeholder rows, or when the entire `### Unique Constraints` sub-section is absent (legacy spec from before the feature). In all three cases, the empty list is the correct binding; the absence is not itself an error. **However**, if `<unique_constraints>` is empty and there is **any** `\{Add Unique Constraint, Add Unique Index\}` row in §2.Migrations, fail with: `Error: §2.Migrations carries a uniqueness row but §2.UniqueConstraints is empty or absent; spec is inconsistent. Re-run @command-repo-spec-pattern-selector.`

### Step 3 — Discover stub worklist and check drift

For each `<slug>` in `<patterns>`, glob `<migrations_dir>/*-<slug>.yaml`. The match must contain exactly one file; otherwise fail with: `Error: Section 2 Migrations row '<slug>' has no scaffolded stub at '<migrations_dir>/*-<slug>.yaml'; re-run @migrations-scaffolder.` (Multiple matches also fail with the same error — the scaffolder's collision rule guarantees uniqueness.)

Bind `<stub_path[<slug>]>` to the resolved absolute path. The ordered list of `<stub_path>` values, in `<patterns>` order, is `<worklist>`.

### Step 4 — Implement each stub

For each `<slug>` in `<patterns>` (preserving order), let `<stub_path>` = `<stub_path[<slug>]>` and `<Pattern>` = `<patterns>[<slug>]`:

1. **Idempotence check.** `Read` `<stub_path>`. Strip leading and trailing whitespace. If the result is **exactly** `databaseChangeLog: []`, render the implementation per Step 4a–4d and `Write` it back. Otherwise (already implemented, hand-edited, empty file, or any other content), skip the file and move on. Do not overwrite.
2. Track `<stub_path>` in the report list regardless of whether it was written or skipped.

Derive the file's `<filename_stem>` = `basename(<stub_path>)` minus the `.yaml` suffix. Derive `<author>` = `system` for every changeSet.

Each stub emits a single top-level `databaseChangeLog:` whose elements are **one or more `- changeSet:` entries** rendered per the chosen variant.

ChangeSet `id` rule:
- If the stub emits exactly one changeSet, its `id` is `<filename_stem>` (no suffix).
- If the stub emits N > 1 changeSets, their `id` values are `<filename_stem>-1`, `<filename_stem>-2`, … in emission order.

Render each changeSet by following the corresponding template variant in the `persistence-spec:migration` pattern doc. The variant-specific resolution rules below tell you (a) how many changeSets to emit, (b) which placeholders to fill from the spec, and (c) which `tableName` to use.

Variant resolution requires resolving `<table_name>` from the slug. The convention from `@migrations-scaffolder` is that the slug encodes the table — e.g. `create-order-table` → `order`, `create-order-item-table` → `order_item`. Resolve as follows:

1. If the slug starts with `create-` and ends with `-table`, strip both ends; replace inner `-` with `_`. The result must match a `### Table:` heading in Section 3; otherwise fail with: `Error: stub '<stub_path>' resolves to table '<table>' but Section 3 has no '### Table: <table>' block.`
2. Otherwise, the variant resolution rules below specify how to derive the target table from the spec.

#### 4a. `Create Table`

Resolve `<table_name>` from the slug per rule (1). Look up `<columns[<table_name>]>`. Emit exactly **one** changeSet:

- `id`: `<filename_stem>`
- `author`: `system`
- `changes`: a single `createTable` with `tableName: <table_name>` and one `- column:` entry **per row** in `<columns[<table_name>]>`, in declaration order — verbatim, no synthesized columns.
- `rollback`: a single `- dropTable: { tableName: <table_name> }`.

**Composite PK guard for child tables.** If `<columns[<table_name>]>` contains any column whose constraints carry an `FK → ...` annotation (i.e. this is a child entity table), count the columns whose constraints carry `pk` or `primary key`. The count must be ≥ 2 — child ids are aggregate-scoped, so the PK must include the parent FK column in addition to `id`. If the count is exactly 1, fail with: `Error: child entity migration '<filename_stem>' targets table '<table_name>' with a single-column PK; the parent FK column must also carry the PK constraint. Re-run @command-repo-spec-schema-writer.` This guard mirrors the one in `@table-implementer` so the table module and the migration cannot drift.

Per-column rendering rules (apply to every variant that emits columns):

- `name`: the column name.
- `type`: the SQL type from the `<column_type>` → SQL mapping.
- `constraints`: built from the column's `<constraints>` cell using the same parser as `@table-implementer` Step 4 (tokenize on commas/slashes, lowercase). First match wins:
  - Token `pk` or contains `primary key` → `primaryKey: true` and `primaryKeyName: pk_<table_name>`. Omit `nullable`. The constraint name is **table-scoped** (not column-scoped) because in PostgreSQL PK constraint names share a relation namespace with tables and indexes — using a bare column name like `id` would collide across migrations whose tables both have an `id` PK column.
  - Token starts with `fk` or contains `foreign key` → does not affect the column block here (FK constraints are emitted by `Add Foreign Key`, not `Create Table`).
  - Token `not null` or `nullable=false` → `nullable: false`.
  - Token `null` / `nullable` / `nullable=true` → `nullable: true`.
  - No nullability token, not PK, and `<column_type>` is **not** `JSONB` → emit `constraints: { nullable: false }`.
  - No nullability token, not PK, and `<column_type>` **is** `JSONB` → omit the `constraints:` key entirely (JSONB columns are nullable by default in this project, matching the skill template).

#### 4b. `Create Table (Composite PK)`

Identical to `Create Table` (4a) except the `<columns[<table_name>]>` table will contain **two or more** PK rows (those whose `<constraints>` cell carries `pk` or `primary key`). Emit each PK column with `constraints: { primaryKey: true, primaryKeyName: pk_<table_name> }` — repeat the same `primaryKeyName` on every PK column so Liquibase coalesces them into a single composite constraint with a table-scoped name. Single changeSet, single `dropTable` rollback.

#### 4c. `Add Foreign Key`

Resolve the base table `<base_table>`. The slug for this pattern is conventionally `add-foreign-key`, which does not encode the table. Determine `<base_table>` by walking every `### Table:` block in Section 3 and selecting tables that contain at least one column whose `<constraints>` cell carries `FK → <parent>.<col>` (or `FK -> <parent>.<col>`). If exactly one table qualifies, use it. If zero qualify, fail: `Error: stub '<stub_path>' is 'Add Foreign Key' but no Section 3 table has FK annotations.` If more than one qualifies, fail: `Error: stub '<stub_path>' is 'Add Foreign Key' but multiple tables (<list>) carry FK annotations; spec must split into per-table FK rows.`

Parse FK annotations on `<base_table>`: for each column whose `<constraints>` cell carries `FK → <parent>.<col>`, capture `(<base_column>, <parent_table>, <parent_column>)`. Group by `<parent_table>`, preserving column declaration order within each group.

Emit **one changeSet per parent group**. For group `i` (1-based) targeting `<parent_table_i>` with base columns `<base_cols_i>` and parent columns `<parent_cols_i>`, apply the changeSet `id` rule (single-group → `<filename_stem>`; multi-group → `<filename_stem>-<i>`):

- `author`: `system`
- `changes`: one `addForeignKeyConstraint` with:
  - `baseTableName: <base_table>`
  - `baseColumnNames: <csv of <base_cols_i>>` (unquoted; comma-separated, no spaces)
  - `referencedTableName: <parent_table_i>`
  - `referencedColumnNames: <csv of <parent_cols_i>>` (unquoted)
  - `constraintName: fk_<base_table>_<parent_table_i>`
  - `onDelete: CASCADE`
- `rollback`: one `dropForeignKeyConstraint` with `baseTableName: <base_table>` and `constraintName: fk_<base_table>_<parent_table_i>`.

#### 4d. `Add Index` and `Add JSONB Index`

The slug for these patterns is conventionally `indexes` (or similar) and aggregates every row in Section 3's `### Indexes` table. If `<indexes>` (Step 2c) is empty, fail: `Error: stub '<stub_path>' is '<Pattern>' but Section 3 '### Indexes' table is empty or absent.`

For each `<index>` row in `<indexes>` (in declaration order, 1-based as `i`), determine the index target:

- The owning `<table_name>` is the unique table in Section 3 whose `<columns[<table_name>]>` contains every column listed in `<index_columns>`. If zero or multiple tables qualify, fail: `Error: index '<index_name>' columns <list> do not uniquely belong to any '### Table:' block.`
- Determine whether this is a JSONB index: a row whose `<index_columns>` contains exactly one column whose `<column_type>` in `<columns[<table_name>]>` is `JSONB` is a **JSONB index**; everything else is a **plain index**.

The Section 2 `<Pattern>` is informational here — both `Add Index` and `Add JSONB Index` rows can land in the same stub when the spec uses one row per index. The per-index branch (plain vs JSONB) is decided from the column type, not the pattern label. (When the spec only declares `Add Index` but a row resolves to JSONB, emit JSONB anyway — the column type is the source of truth.)

Emit one changeSet per index row, applying the changeSet `id` rule (single-index → `<filename_stem>`; N>1 → `<filename_stem>-<i>`):

- `author`: `system`
- For a **plain index**:
  - `changes`: one `createIndex` with `indexName: <index_name>`, `tableName: <table_name>`, and one `- column: { name: <col> }` per column in `<index_columns>`.
  - `rollback`: one `dropIndex` with `indexName: <index_name>` and `tableName: <table_name>`.
- For a **JSONB index**, let `<jsonb_column>` = the unique JSONB-typed column in `<index_columns>` (already established by the JSONB branch check above):
  - `changes`: one raw `sql` change: `sql: CREATE INDEX <index_name> ON <table_name> USING GIN (<jsonb_column>)`.
  - `rollback`: one `dropIndex` with `indexName: <index_name>` and `tableName: <table_name>`.

#### 4e. `Add Unique Constraint`, `Add Unique Index`, and `Drop Unique Constraint`

These patterns appear in **three slug shapes**; resolve which by matching `<slug>` against the prefixes below.

**Aggregating shape — `<slug>` = `unique-constraints-for-<parent_table>`.** Emitted by the writer on first-run baseline. Walk **every** tuple in `<unique_constraints>` (Step 2d) in declaration order, 1-based as `i`, and emit one changeSet per row per the rules below. If `<unique_constraints>` is empty, fail: `Error: stub '<stub_path>' is the aggregating uniqueness row but §2.UniqueConstraints is empty or absent.`

**Per-target Add shape — `<slug>` starts with `add-unique-constraint-` or `add-unique-index-`.** Emitted by the appender on a delta update. Resolve a **single** `<unique>` tuple by matching the row's `<changeset_raw>` against `<unique_constraints>`:

- For Pattern `Add Unique Constraint`, parse `<changeset_raw>` as `` Add Unique Constraint \`<table>.<column>\` ``. The matching row has `<kind> = Scalar` and `<target>` = `<table>.<column>` (i.e. `<target_column_or_expression>` = `<column>`, `<table>` matches). If no row matches, fail: `Error: per-target uniqueness stub '<stub_path>' references '<table>.<column>' but no matching §2.UniqueConstraints row exists.`
- For Pattern `Add Unique Index`, parse `<changeset_raw>` as `` Add Unique Index \`<constraint_name>\` ``. The matching row has `<constraint_name>` matching and `<kind> = JSONB Expression`. If no row matches, fail: `Error: per-target uniqueness stub '<stub_path>' references '<constraint_name>' but no matching §2.UniqueConstraints row exists.`

Emit exactly one changeSet (apply the single-changeSet `id` rule → `<filename_stem>`).

**Per-target Drop shape — `<slug>` starts with `drop-unique-constraint-`.** Emitted by the appender on a delta update (removal). Parse `<changeset_raw>` as `` Drop Unique Constraint \`<constraint_name>\` ``. Determine the original `<kind>` by looking up `<constraint_name>` in `<unique_constraints>`:

- Row present with `<kind> = Scalar` → emit a single changeSet with `changes:` → `dropUniqueConstraint` (`tableName: <table>`, `constraintName: <constraint_name>`) and `rollback:` → `addUniqueConstraint` (`tableName: <table>`, `columnNames: <target_column_or_expression>`, `constraintName: <constraint_name>`).
- Row present with `<kind> = JSONB Expression` → emit a single changeSet with `changes:` → `dropIndex` (`indexName: <constraint_name>`, `tableName: <table>`) and `rollback:` → raw `sql` `CREATE UNIQUE INDEX <constraint_name> ON <table> ((<target_column_or_expression>))`.
- Row **absent** from `<unique_constraints>` (the drop refers to a constraint that has already been removed from the spec) → fail: `Error: 'Drop Unique Constraint' stub '<stub_path>' references constraint '<constraint_name>' which is no longer present in §2.UniqueConstraints; cannot reconstruct rollback shape. The working-tree spec must keep enough state to reverse a drop; if the constraint was deliberately removed, restore the §2.UniqueConstraints row temporarily, regenerate, then commit the drop migration alone.` (This is intentionally strict — Drop without rollback support is opaque to operators.)

**Per-row emission rules** (apply to every shape above):

- `author`: `system`
- For a **Scalar** uniqueness row (`<target_column_or_expression>` is a plain column name):
  - `changes`: one `addUniqueConstraint` with `tableName: <table>`, `columnNames: <target_column_or_expression>`, and `constraintName: <constraint_name>`.
  - `rollback`: one `dropUniqueConstraint` with `tableName: <table>` and `constraintName: <constraint_name>`.
- For a **JSONB Expression** uniqueness row (`<target_column_or_expression>` is a verbatim JSONB expression such as `details->>'name'`):
  - `changes`: one raw `sql` change: `sql: CREATE UNIQUE INDEX <constraint_name> ON <table> ((<target_column_or_expression>))`. Wrap the expression in **double** parentheses so Postgres parses it as an indexed expression rather than a plain column list.
  - `rollback`: one `dropIndex` with `indexName: <constraint_name>` and `tableName: <table>`.

If the aggregating-shape stub emits at least one JSONB Expression changeSet alongside at least one Scalar changeSet, that is allowed — they coexist under a single `databaseChangeLog:` document with sequential `<filename_stem>-<i>` ids.

#### 4f. Output formatting

Render each stub as a single YAML document with this exact top-level shape:

For a single-changeSet stub:

```yaml
databaseChangeLog:
- changeSet:
    id: <filename_stem>
    author: system
    changes:
    - <change>
    rollback:
    - <rollback>
```

For a multi-changeSet stub:

```yaml
databaseChangeLog:
- changeSet:
    id: <filename_stem>-1
    author: system
    changes:
    - <change-1>
    rollback:
    - <rollback-1>
- changeSet:
    id: <filename_stem>-2
    author: system
    changes:
    - <change-2>
    rollback:
    - <rollback-2>
```

Use 2-space indentation throughout, matching the skill template. Trim trailing whitespace; emit exactly one trailing newline. No comments, no blank lines between changeSets, no extra keys (no `labels`, no `context`, no `preConditions`).

### Step 5 — Report

Emit a bare bullet list of every absolute path in `<worklist>`, preserving its order — one bullet per line, nothing else on the line. Include all stubs regardless of whether this run wrote them or skipped them; downstream agents use the list as their worklist.

```
- <migrations_dir>/<filename_1>.yaml
- <migrations_dir>/<filename_2>.yaml
- ...
```

Do not emit anything beyond this list.
