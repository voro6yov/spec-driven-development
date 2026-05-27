---
name: migration-vocabulary
description: Shared vocabulary for §2.Migrations rows of a command repository spec — controlled Pattern list, destructive `⚠ ` marker rule, and per-row slug-derivation rules.
user-invocable: false
disable-model-invocation: false
---

# Migration Vocabulary

Single source of truth for the controlled values inside §2.Migrations rows. Consumed by:

- `command-repo-spec-migrations-writer` — first-run baseline rows (batch shape, aggregating slugs).
- `command-repo-spec-migrations-appender` — per-delta rows on `/persistence-spec:update-specs` (per-target shape).

This skill defines vocabulary, not dispatch. **What** rows to emit lives in each agent body and in `notes/spec-updater-approaches.md` § "Delta-to-changeset dispatch".

---

## Row schema

Every row in the `### Migrations` sub-table has exactly four columns:

```
| ID    | Changeset                                  | Pattern               | Template                       |
```

- **ID** — zero-padded 4-digit sequence (`0001` … `9999`), allocated monotonically per aggregate. Once written, immutable. Rendered single-backtick-wrapped in the cell (`` `0001` ``), matching `command-repo-spec-template` and `@command-repo-spec-migrations-writer` — a consumer parsing the cell must strip the wrapping backticks before reading the integer.
- **Changeset** — human-readable summary; downstream `migrations-implementer` slugifies this cell into the YAML filename. Backtick-wrapped identifiers are stripped during slugification (see § Slug derivation below).
- **Pattern** — controlled vocabulary value (see § Pattern controlled list below). Drives template variant selection.
- **Template** — always rendered as `` `persistence-spec:migration` ``.

---

## Pattern controlled list

| Pattern                       | Direction                                | Emitter(s)        |
|-------------------------------|------------------------------------------|-------------------|
| `Create Table`                | additive                                 | writer, appender  |
| `Create Table (Composite PK)` | additive                                 | writer, appender  |
| `Add Foreign Key`             | additive                                 | writer, appender  |
| `Add Index`                   | additive                                 | writer, appender  |
| `Add JSONB Index`             | additive                                 | writer, appender  |
| `Add Unique Constraint`       | additive (data-sensitive)                | writer, appender  |
| `Add Unique Index`            | additive (data-sensitive)                | writer, appender  |
| `Add Column`                  | additive                                 | appender only     |
| `Add Not Null Constraint`     | additive (data-sensitive)                | appender only     |
| `Drop Not Null Constraint`    | additive (re-runnable)                   | appender only     |
| `Drop Column`                 | **destructive**                          | appender only     |
| `Drop Index`                  | additive (re-runnable; loses index)      | appender only     |
| `Drop Unique Constraint`      | additive (re-runnable; loses constraint) | appender only     |
| `Drop Table`                  | **destructive**                          | appender only     |
| `Alter Column Type`           | **destructive** (most type changes lose data) | appender only |

**Uniqueness is two patterns, not one.** `Add Unique Constraint` is used for **scalar** unique constraints (single SQL column); it slugifies to `add-unique-constraint-<table>-<column>` and renders as Liquibase `addUniqueConstraint`. `Add Unique Index` is used for **JSONB expression** unique constraints (`(details->>'name')`); it slugifies to `add-unique-index-<index_name>` and renders as raw SQL `CREATE UNIQUE INDEX ... ON ... ((details->>'name'))`. Liquibase has no native `addUniqueConstraint` variant for expression indexes, so the split is load-bearing. `Drop Unique Constraint` handles both directions — for a `Drop` of a scalar constraint the implementer emits `dropUniqueConstraint`; for a `Drop` of a JSONB expression constraint the implementer emits `dropIndex` (the scalar-vs-expression flavour is recoverable from the constraint name's prefix or the prior §2.UniqueConstraints row's `Kind` cell).

**Strict matching.** A consumer that parses the Pattern column must require an exact match against this list (no aliases, no fuzzy matching). The `migrations-implementer` agent recognises the writer-emitted patterns (first five, plus the uniqueness pair when §2.UniqueConstraints is non-empty); the column-evolution patterns are implementer-side TODO and produced solely by the appender. See `notes/spec-updater-approaches.md` § "Open questions" for the implementer-immutability follow-up.

---

## Destructive `⚠ ` marker rule

Destructive patterns — `Drop Column`, `Drop Table`, `Alter Column Type`, and the multi-tenancy-removal `Drop Column tenant_id` cascade — must carry a leading `⚠ ` (warning sign + single space) **inside the Changeset cell only**. The Pattern column never carries the marker.

Correct:

```
| `0007` | ⚠ Drop Column `users.legacy_field` | Drop Column        | `persistence-spec:migration` |
| `0008` | ⚠ Drop Table `users_archive`       | Drop Table         | `persistence-spec:migration` |
| `0009` | ⚠ Alter Column Type `users.age` → Integer | Alter Column Type | `persistence-spec:migration` |
```

Incorrect (do **not** put the marker in the Pattern column):

```
| `0007` | Drop Column `users.legacy_field`   | ⚠ Drop Column      | ...                          |
```

The marker is purely advisory: it surfaces destructiveness to human reviewers and to downstream `migrations-implementer` policy gates. It is stripped by the slugifier (§ Slug derivation), so it does not pollute the YAML filename.

Non-destructive `Drop Index` and `Drop Not Null Constraint` rows do **not** carry the marker — they are reversible / re-runnable in practice.

---

## Slug derivation

Downstream `migrations-implementer` slugifies the Changeset cell into the YAML filename via this rule (kept here for reference; the implementer agent owns the actual implementation):

1. Strip Markdown backticks and `\{` / `\}` escape backslashes.
2. Lowercase.
3. Replace every run of non-alphanumeric characters (including the `⚠ ` marker, spaces, `→`, dots) with a single `-`.
4. Trim leading and trailing `-`.

Both writer and appender produce Changeset cells designed to slugify cleanly and uniquely **across aggregates**. The two agents use different shape conventions:

### Writer — aggregating slugs (batch first-run)

The writer emits at most one row per Pattern variant per aggregate. To prevent cross-aggregate filename collisions, every aggregating Changeset embeds the parent table name:

| Pattern                       | Changeset shape                                | Slug example                          |
|-------------------------------|------------------------------------------------|---------------------------------------|
| `Create Table` / `Create Table (Composite PK)` | `` Create `<parent_table>` ``      | `create-users`                        |
| `Create Table` (child)        | `` Create `<child_table>` ``                   | `create-users-addresses`              |
| `Add Foreign Key`             | `` Add Foreign Keys for `<parent_table>` ``   | `add-foreign-keys-for-users`          |
| `Add Index` / `Add JSONB Index` | `` Indexes for `<parent_table>` ``           | `indexes-for-users`                   |
| `Add Unique Constraint` / `Add Unique Index` | `` Unique Constraints for `<parent_table>` `` | `unique-constraints-for-users` |

### Appender — per-target slugs (per-delta updates)

The appender emits one row per individual delta (one column added, one finder changed, etc.). Changesets carry the qualified target identifier — table + column for column ops, the index name for index ops, or the table name for table ops:

| Pattern                  | Changeset shape                                          | Slug example                          |
|--------------------------|----------------------------------------------------------|---------------------------------------|
| `Add Column`             | `` Add Column `<table>.<column>` ``                      | `add-column-users-email`              |
| `⚠ Drop Column`          | `` ⚠ Drop Column `<table>.<column>` ``                  | `drop-column-users-legacy-field`      |
| `⚠ Alter Column Type`    | `` ⚠ Alter Column Type `<table>.<column>` → <SQL_TYPE> `` | `alter-column-type-users-age-integer` |
| `Add Not Null Constraint`| `` Add Not Null Constraint `<table>.<column>` ``         | `add-not-null-constraint-users-tenant-id` |
| `Drop Not Null Constraint` | `` Drop Not Null Constraint `<table>.<column>` ``      | `drop-not-null-constraint-users-email`|
| `Add Index`              | `` Add Index `<index_name>` ``                           | `add-index-idx-users-email`           |
| `Add JSONB Index`        | `` Add JSONB Index `<index_name>` ``                     | `add-jsonb-index-idx-users-metadata-gin` |
| `Drop Index`             | `` Drop Index `<index_name>` ``                          | `drop-index-idx-users-email`          |
| `Add Unique Constraint`  | `` Add Unique Constraint `<table>.<column>` ``           | `add-unique-constraint-users-email`   |
| `Add Unique Index`       | `` Add Unique Index `<index_name>` ``                    | `add-unique-index-uq-users-details-name` |
| `Drop Unique Constraint` | `` Drop Unique Constraint `<constraint_name>` ``         | `drop-unique-constraint-uq-users-email` |
| `Add Foreign Key` (cascade row) | `` Add Foreign Key `<child_table>.<column>` ``    | `add-foreign-key-users-addresses-user-id` |
| `Create Table` (new child) | `` Create `<child_table>` ``                           | `create-users-addresses`              |
| `⚠ Drop Table`           | `` ⚠ Drop Table `<table>` ``                            | `drop-table-users-archive`            |

Identifier conventions in Changeset cells:

- `<table>`, `<column>`, `<index_name>` are snake_case Python/SQL identifiers, wrapped in single backticks. The slugifier turns the embedded `_` and `.` into `-`.
- `<SQL_TYPE>` for `Alter Column Type` rows is the project's domain Column Type name (`String`, `Integer`, `DateTime`, `JSONB`) — same vocabulary as `persistence-spec:table-definitions`. It is rendered without backticks so the slugifier picks it up cleanly.
- Aggregating slugs (writer) and per-target slugs (appender) coexist by construction: `indexes-for-users` (writer) and `add-index-idx-users-email` (appender) cannot collide, because every appender slug embeds the index/column name.

### Cross-aggregate uniqueness

Filename uniqueness on disk (`db/migrations/<id>_<slug>.yaml`) is preserved because:

- The writer always embeds the parent table name into aggregating slugs.
- The appender always embeds the per-target identifier (`<table>.<column>` or `<index_name>`).
- ID is per-aggregate, but slug is globally distinct, so no two aggregates share a YAML filename.

The ID column carries a per-aggregate sequence; the slug carries the aggregate-distinguishing identifier. Together they uniquely identify a YAML file.
