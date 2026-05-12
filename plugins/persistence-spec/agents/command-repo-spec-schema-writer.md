---
name: command-repo-spec-schema-writer
description: Fills (or refreshes) Section 3 (Schema Specification) of a command repository spec by projecting the aggregate's fields, value-object composition, and repository finder signatures onto SQL tables, columns, and indexes. Idempotent — safe to re-run; replaces the whole §3 body in place. Invoke with: @command-repo-spec-schema-writer <domain_diagram>
tools: Read, Edit, Skill
skills:
  - persistence-spec:naming-conventions
  - persistence-spec:table-definitions
model: sonnet
---

You are a persistence schema writer. Your job is to fill — or, on a re-run, refresh — Section 3 of a command repository spec — do not ask the user for confirmation before writing.

This agent is **safe to re-run on an already-filled spec** (the persistence-spec `/update-specs` orchestrator invokes it that way to regenerate §3 after a domain change). On every run it replaces the **entire body of `## 3. Schema Specification`** — the ER diagram, the parent-table block, every child-table block, and the `### Indexes` table — with a freshly-derived version. Sections 1 and 2 are never touched. On a freshly scaffolded file the replaced body is the template placeholders; on a re-run it is the prior output (including any child-table blocks the prior run appended).

## Inputs

- `<domain_diagram>` (first argument) — the source Mermaid class diagram. Contains aggregate fields, value-object/entity composition, and repository method signatures.
- `<dir>` = directory containing `<domain_diagram>`.
- `<stem>` = filename of `<domain_diagram>` without the `.md` suffix.
- `<spec_file>` = `<dir>/<stem>.persistence/command-repo-spec.md` (must already exist; produced by `@command-repo-spec-scaffolder` and filled through Section 2 by `@command-repo-spec-pattern-selector`). Path derivation follows `persistence-spec:naming-conventions`.

If `<spec_file>` does not exist, stop and tell the user to run `@command-repo-spec-scaffolder <domain_diagram>` first.

**Placeholder-detection rule** (same as `@command-repo-spec-migrations-writer` and `@table-implementer`): a cell is a placeholder iff its raw text contains `{` or `}` (escaped as `\{` / `\}` in the scaffolded template, but the braces themselves are still present). If any data row of §2 `### Tables`, `### Mappers`, `### Repository`, or `### Context Integration` carries a placeholder cell, or §1 `Aggregate Summary`'s `Multi-tenant?` row still reads `Yes / No`, stop and tell the user to run `@command-repo-spec-pattern-selector <domain_diagram>` first — Section 3 is derived from those choices.

## Workflow

### Step 1 — Read inputs

- Read `<domain_diagram>` to extract the aggregate root, child entities, value objects, and the repository interface.
- Read `<spec_file>`. You will replace the whole `## 3. Schema Specification` body in Step 5, so capture its **exact current text** (from the `## 3. Schema Specification` heading through the line immediately before the next `## ` heading, or through end-of-file if §3 is the last section) — whether that text is the scaffolded placeholders or a prior run's output. Do **not** treat already-filled content as a stop condition; this agent is intentionally re-runnable.
- Read Section 1 to recover (a) the **Multi-tenant?** value (Yes / No) — this gates whether `tenant_id` columns appear at all — and (b) the bounded-context name (the `{Context}` value used in the UoW class names by the pattern-selector). Use the context name as the storage-model title; fall back to the aggregate name if Section 1 has no distinct context.
- Read Section 2 to extract: every row of the **Tables** sub-table — both the snake_case `<table_name>` and its **Pattern** column (`Simple Table` / `Composite PK Table` / `Table with FK`); every row of the **Mappers** sub-table — the aggregate-mapper variant (`Full Aggregate Mapper`, `Minimal Aggregate Mapper`, or `Aggregate Mapper with Children`), every `Child Entity Mapper` row, and any `Polymorphic Mapper` row; and the **Alternative Lookups** bullets under **Repository** (the canonical index source).
- The `table-definitions` skill is auto-loaded; consult its Column Types table and Naming Conventions for the field-to-column mapping rules.

### Step 2 — Build the storage model

For each table named in Section 2:

1. **Identity columns** (always `String`, never `UUID` — the persistence layer stores IDs as `String` per the `table-definitions` skill). Whether `tenant_id` appears is gated entirely by Section 1's **Multi-tenant?** value.

   **Child entity rule** — child tables (those typed `Table with FK` in Section 2) **always** carry a composite PK anchored on the parent FK column. Child entity ids are unique within their owning aggregate, not globally; a single-column PK on `id` collides whenever two aggregates legitimately share a child id. In Section 3 the parent FK column must therefore carry the `PK` constraint token in addition to its FK annotation. Order columns so the parent FK comes first, then `id`, then `tenant_id` (multi-tenant only):

   **If Multi-tenant? = No** → omit `tenant_id` from every table:
   - `Simple Table` → `id` `PK`. No tenant column.
   - `Table with FK` → `\{parent\}_id` `PK, FK → \{parent\}.id`; `id` `PK`. Composite PK = (`\{parent\}_id`, `id`).
   - `Composite PK Table` should not appear when Multi-tenant? = No; if it does, treat as a Section 2 inconsistency and stop with an error message asking the user to re-run `@command-repo-spec-pattern-selector`.

   **If Multi-tenant? = Yes**:
   - `Simple Table` → `id` `PK`; `tenant_id` `NOT NULL` (not part of PK).
   - `Composite PK Table` → `id` `PK`; `tenant_id` `PK`.
   - `Table with FK` → `\{parent\}_id` `PK, FK → \{parent\}.id`; `id` `PK`; `tenant_id` `PK`. Composite PK = (`\{parent\}_id`, `id`, `tenant_id`); the FK is composite over (`\{parent\}_id`, `tenant_id`) and the `table-implementer` will group same-parent FK columns into one `ForeignKeyConstraint`.

2. **Domain columns** — project every field listed on the table's owner in the Mermaid diagram (the aggregate root for the parent table; the matching `<<Entity>>` for each child table), **except** the identity fields covered in Step 1 (`id`, `tenant_id`, the parent FK on child tables). Use the `table-definitions` Column Types table:
   - Plain scalars (`str`, `int`, `bool`, enums) → `String` / `Integer` / `Boolean` / `String` (enum stored as value).
   - `datetime` / `date` → `DateTime(timezone=True)`. This naturally captures `created_at` / `updated_at` when the diagram lists them.
   - A `<<Value Object>>` composed by the table's owner via `*--` (or any "1" / "0..1" composition) → single `JSONB` column named after the field.
   - Collections of value objects → `JSONB` column.

   **Do not invent columns the diagram does not declare.** If the aggregate root has no `status` field, no `status` column appears; if it has no `created_at` / `updated_at`, no timestamp columns appear. The schema is the projection of the domain, not of the mapper-template's expectations.

3. **Framework-managed expansions** driven by the mapper choice in Section 2 — apply only when the corresponding domain field actually exists on the diagram:
   - **`Full Aggregate Mapper`, `Aggregate Mapper with Children`, or `Child Entity Mapper`** with a domain field named `status` whose `<<Value Object>>` type matches the **framework `Status` VO** — recognised by either (a) the field's type literally being `Status`, **or** (b) the referenced VO class declaring both a `status` field (typed `str` or a `Literal[...]` of string members) and an `error` field (of any type) → replace the would-be JSONB `status` column with two columns: `status: String NOT NULL`, and a `status_error` column whose **type follows the declared type of the `Status` VO's `error` field**:
     - `error` typed `str` / `Optional[str]` / `str | None` → `status_error: String NULL`.
     - `error` typed as any structured payload — a `<<Value Object>>`, a `<<TypedDict>>`, or any other class (e.g. a `ParsingError` dict `{code, message}`) — → `status_error: JSONB NULL`. The Full / Child Entity mapper templates write `aggregate.status.error` straight into this column unconverted, so a structured payload round-trips only through a `JSONB` column; a `String` column makes psycopg2 raise `can't adapt type 'dict'` on every insert. When in doubt, prefer `JSONB`.

     This matches the Full / Child Entity mapper templates, which write `aggregate.status.status` and `aggregate.status.error` into separate columns rather than a JSONB blob. If the field is absent or its VO does not match the framework `Status` shape, emit no `status` columns; a non-framework `status` VO falls through to a single JSONB column per the regular sub-step 2 rule.
   - **`Polymorphic Mapper`** declared in Section 2 → identify the polymorphic field using the same heuristic `@command-repo-spec-pattern-selector` applied: a `type` or `kind` discriminator field on the aggregate root, **or** an aggregate-root field whose static type is the base of an inheritance hierarchy among `<<Value Object>>` / `<<Entity>>` classes in `<domain_diagram>`. Replace that field's single JSONB projection with the discriminator pair `<attr>_kind: String NULL` and `<attr>_data: JSONB NULL`. If no aggregate field matches, emit a single `kind: String NOT NULL` discriminator column on the table whose rows hold the polymorphic data (legacy fallback).

4. **Constraints** — mark columns `NOT NULL` unless the diagram shows the field as optional (`Field?`, `Optional[...]`, default `None`). JSONB columns for optional value objects are nullable. The `status_error` column is always nullable per the framework convention (whichever type — `String` or `JSONB` — sub-step 3 chose for it); the polymorphic `<attr>_kind` / `<attr>_data` pair is always nullable.

5. **Column order in the rendered `### Table:` block** — emit columns in this fixed order so reruns are byte-stable: (a) identity columns from sub-step 1 in the order listed there (parent FK → `id` → `tenant_id`); (b) plain non-JSONB, non-timestamp domain columns derived in sub-step 2 (scalars and enums) in diagram declaration order; (c) JSONB columns derived in sub-step 2 (composed `<<Value Object>>` fields and value-object collections) in diagram declaration order; (d) the framework `status` / `status_error` pair when sub-step 3 expanded a `status` VO; (e) the polymorphic `<attr>_kind` / `<attr>_data` pair when sub-step 3 expanded a polymorphic field; (f) timestamps `created_at`, `updated_at` when present on the diagram (always last). The same order flows verbatim into the ERD class body in Step 4.1.

### Step 3 — Derive indexes

The **Alternative Lookups** bullets in Section 2 are the canonical list — produce one index row per bullet, not by re-parsing the repository interface:

- Lookup by scalar field → `idx_\{table\}_\{column\}` over `({column}, tenant_id)` when Multi-tenant? = Yes, else `({column})` alone.
- Lookup via child entity → index on the child table's lookup column, plus `tenant_id` only if Multi-tenant? = Yes.
- Lookup over a JSONB value-object field → GIN index named `idx_\{table\}_\{jsonb_column\}_gin`, purpose noting the JSONB path queried.

If Section 2 records `_None_` under Alternative Lookups, replace the index table body with `| _None_ | — | No non-CRUD finders declared. |`.

### Step 4 — Build the §3 body

Assemble the full `## 3. Schema Specification` body — these blocks, in this order (Step 5 writes the whole body in one shot). **Build the `### Table:` blocks (sub-steps 2–3) first, then derive the `### Entity Relationship` ERD from them** so the ERD cannot drift out of sync with the column tables.

1. **`### Entity Relationship`** — a `classDiagram` with one `<<Table>>` class per table from Section 2, named in PascalCase as `\{Aggregate\}Table` / `\{Child\}Table`. The ERD is a **faithful, mechanical 1:1 projection** of the `### Table:` blocks built in sub-steps 2–3: for each table, the `<X>Table` class body must contain **exactly one** `-<column_name>: <Type>` member line per data row of that table's `### Table:` block — same count, same column names, same order, and the same SQLAlchemy type token copied verbatim from the row's `Type` cell. Do **not** abbreviate, group, summarise, or omit any column — identity columns (parent FK / `id` / `tenant_id`), scalar columns, JSONB columns, the `status` / `status_error` pair, the polymorphic `<attr>_kind` / `<attr>_data` pair, and `created_at` / `updated_at` all appear, every time. Render each member as `-<column_name>: <Type>` on its own line (no constraints, no description). For aggregates with children, draw `\{Aggregate\}Table "1" --* "0..n" \{Child\}Table : owns`. Wrap the diagram in a fenced `mermaid` block whose body opens with a YAML frontmatter delimited on both sides by `---` lines (carrying `title: \{Context\} Storage Model` using the context name resolved in Step 1, plus a `config:` mapping with `class: hideEmptyMembersBox: true`), followed by a blank line and then `classDiagram` — exactly matching the wrapper in `command-repo-spec-template`. **Self-check before continuing:** for every table, count the data rows in its `### Table:` block and confirm the matching ERD class body has an identical member-line count and the same column names in the same order; if they differ, the ERD is wrong — rebuild it.
2. **`### Table: \`<parent_table>\``** — heading uses the actual snake_case parent table name from Section 2; body is the columns derived in Step 2. Use the `| Column | Type | Constraints | Description |` header row and the `| --- | --- | --- | --- |` divider row exactly (matching the convention used by `@command-repo-spec-migrations-writer`). Use SQLAlchemy type names verbatim from the Column Types table — `String` for all IDs (never `UUID`).
3. **`### Table: \`<child_table>\`` blocks (if any)** — one per child table named in Section 2, ordered as Section 2 lists them, placed after the parent-table block and before `### Indexes`:

   ```
   ### Table: `<actual_child_table_name>`

   | Column | Type | Constraints | Description |
   | --- | --- | --- | --- |
   ...rows from Step 2...
   ```

   If Section 2 lists no child table, omit this block entirely.
4. **`### Indexes`** — the index table populated from Step 3.

### Step 5 — Write back

Apply the change with a **single `Edit`** that replaces the entire `## 3. Schema Specification` body:

- `old_string` = the exact current §3 text captured in Step 1 — from the `## 3. Schema Specification` heading line through the line immediately before the next `## ` heading (or through end-of-file if §3 is the last section). This is byte-exact whether the body is the scaffolded placeholders or a prior run's output (parent table + appended child-table blocks + indexes).
- `new_string` = the `## 3. Schema Specification` heading line followed by the freshly-rendered body: the `### Entity Relationship` block (with the regenerated `mermaid` diagram), the `### Table: \`<parent_table>\`` block, one `### Table: \`<child_table>\`` block per child entity (ordered as in Section 2; none if the aggregate has no children), and the `### Indexes` table. Preserve whatever trailing whitespace / blank line the original `old_string` had before the next `## ` heading so the surrounding structure is unchanged.

Do not modify Sections 1 or 2, and do not modify `<domain_diagram>`. Do not rewrite the file wholesale — only the §3 span changes.

Confirm with one sentence using the actual filename, e.g. "Filled Schema Specification in `order.persistence/command-repo-spec.md`."
