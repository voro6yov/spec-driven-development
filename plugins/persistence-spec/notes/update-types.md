# Persistence Spec Update Types

Analysis of how every kind of domain-diagram delta — as emitted by `domain-spec:updates-detector` into `<dir>/<stem>.domain/updates.md` — ripples into the **command repository spec** sibling at `<dir>/<stem>.persistence/command-repo-spec.md`.

The goal is to enumerate every distinct kind of change a persistence-spec updater would have to handle, so it can dispatch the right action per change rather than re-running `/persistence-spec:generate-specs` from scratch and overwriting append-only history in §2.Migrations.

This is the persistence-side analog of `plugins/domain-spec/notes/update-types.md` (and `plugins/domain-spec/notes/spec-updater-approach-b.md`). It assumes the domain `updates.md` is already produced; the persistence updater **consumes that report directly** and never re-diffs the diagram.

The chosen updater design — **snapshot regen for snapshot sections + delta-driven append for §2.Migrations** — is documented in [`spec-updater-approaches.md`](spec-updater-approaches.md). This file catalogs the input deltas; the design doc defines the output behaviour.

---

## Snapshot vs append-only log

The command-repo-spec mixes two fundamentally different kinds of section, and the updater treats them differently:

- **Snapshot sections** describe the *current state* of the persistence layer. Every cell is a function of the current diagram; they are fully regeneratable. Update behaviour: **wholesale regen** (read the diagram, replace the section).
- **The append-only log section** (§2.Migrations only) describes the *cumulative history* of changesets — each row corresponds to a real `db/migrations/<id>_<slug>.yaml` file. Once a row is committed, regenerating it from the current diagram produces a stale or incorrect schema state for any environment that already ran the prior version. Update behaviour: **delta-driven append** (existing rows immutable; new rows derived from `updates.md` and stacked on top).

This split is load-bearing. A naive full-regen is correct for snapshot sections and wrong for §2.Migrations.

---

## Persistence spec sections and their sensitivity

The command-repo-spec has three filled sections plus the scaffold-owned `Implementation` block. Section ownership now splits across four writer agents to support the snapshot/log dichotomy:

| Section | Kind | Owner agent | Sensitive to |
|---|---|---|---|
| **§1 Aggregate Analysis** — Purpose, Aggregate Summary (root, has-children, multi-tenant, JSONB VOs, polymorphism), Implementation | snapshot | `command-repo-spec-pattern-selector` (rows 1–5) + `command-repo-spec-scaffolder` (Implementation block) | Aggregate *shape* — which classes exist, how they relate, the bounded context name, the Python package path |
| **§2 Pattern Selection** (Tables, Mappers, Repository + Alt Lookups, Context Integration) | snapshot | `command-repo-spec-pattern-selector` | Aggregate shape **plus** the `<<Repository>>` finder set |
| **§2.Migrations** | append-only log | `command-repo-spec-migrations-writer` (first run) + `command-repo-spec-migrations-appender` (updates) | Per-domain-change deltas as captured by `updates.md` |
| **§3 Schema Specification** — ER diagram, per-table column lists, Indexes | snapshot | `command-repo-spec-schema-writer` | Field-level changes on root, child entities, and flat-column value objects; also the Alternative Lookups list from §2 |

Note that §2.Migrations is **carved out of `command-repo-spec-pattern-selector`'s ownership** — the snapshot/log split requires it. See `spec-updater-approaches.md` § "Agent reorganization" for the contract changes.

The downstream persistence artifacts (`tables/`, `migrations/`, `mappers/`, `command_<aggregate>_repository.py`, repo tests) are owned by `/persistence-spec:generate-code`. They are **out of scope** for the spec updater — the spec is the source of truth and code regeneration is its own concern (analogous to `notes/code-updater-approach-c.md` on the domain side). One contract requirement crosses the boundary: `migrations-implementer` must be **append-only** — it never overwrites an existing `db/migrations/<id>_<slug>.yaml`. This mirrors the §2.Migrations row-immutability rule on the spec side.

---

## Domain shape constraints

Load-bearing facts about how persistence relates to the domain diagram:

- **The domain diagram is the single source of truth.** The persistence spec is a derived artifact; there is no second diagram to diff. The trigger for a persistence update is therefore `<stem>.domain/updates.md`, not a separate persistence diff.
- **Exactly one `<<Aggregate Root>>` per diagram.** The same invariant the domain updater leans on. Removal of the root is malformed; stereotype change of the root requires a full regen.
- **Domain `<<Event>>` and `<<Command>>` classes do not persist.** They are emitted / dispatched. A pure event-or-command change in the domain footer means the command-repo-spec is byte-stable — the persistence updater can early-exit.
- **Repository ABCs are domain-owned.** The `<<Repository>>` interface lives in the domain diagram; the persistence spec selects an implementation pattern and lists alternative lookups that mirror its abstract finders. Finder churn on the ABC is a category that *does* affect the persistence spec.
- **`<<Service>>` classes do not contribute to the command-repo-spec.** Services are not persisted. A `repositories-services` footer entry is only persistence-relevant when the change touches the `<<Repository>>` member of that category, never the `<<Service>>` member.
- **Context name comes from the diagram's Mermaid `title:` directive**, not from any class. A pure prose/title change therefore touches §1's Implementation/Context-name labelling and §2's UoW class names without showing up in any `affected_categories` entry — see *Out-of-band signals* below.

---

## Mapping `affected_categories` → persistence impact

Per the canonical category order from `domain-spec:updates-report-template`:

### 1. `data-structures` (`<<TypedDict>>`)

Predominantly a query-side concern. Command-side persistence impact is narrow but non-zero:

- **TypedDict consumed by an aggregate factory / flat constructor** that maps repository rows to aggregates → mapper hydration order may shift in §2.Mappers; no §3 column impact unless the constructor keys correspond 1:1 to columns.
- **TypedDict referenced from a `<<Repository>>` finder return type** (e.g. paginated read DTO) → command-side spec is unaffected because the command repository persists the aggregate, not the DTO. Defer to a future `query-repo-spec` updater.
- Any other TypedDict change is **byte-neutral for the command-repo-spec** — the persistence updater can skip the regen step entirely when `data-structures` is the only affected category.

### 2. `value-objects` (`<<Value Object>>`)

Highest-impact category for the command-repo-spec. Shape and field changes all land here:

- **VO added on the root or on a child entity** → §2.Mappers gains a `<VO>Mapper` row (variant: Simple / Complex / Collection — picked by VO shape) on regen; §3 gains new flat columns *or* a single JSONB column on the owner's table on regen; §2.Migrations gains one `Add Column` row appended per affected column.
- **VO removed** → §2.Mappers loses the row on regen; §3 loses the columns on regen; §2.Migrations gains one `⚠ Drop Column` row appended per affected column. The migration history is preserved — the original `Create Table` / `Add Column` rows that introduced the columns remain in §2.Migrations as historical record.
- **VO field added / removed / typed / re-nullabilitied** → flat-column add/drop/alter on regen when the VO maps to flat columns (corresponding `Add Column` / `⚠ Drop Column` / `⚠ Alter Column Type` row appended to §2.Migrations); JSONB shape change is application-level (no migration row) when the VO maps to a single JSONB column. Nullability flips flow into the constraints column.
- **VO becomes polymorphic** (subtype branches appear under it) → §1 polymorphism flag flips, §2 gains a `Polymorphic Mapper` row, §3 replaces a single JSONB projection with the discriminator pair `<attr>_kind: String NULL` and `<attr>_data: JSONB NULL`. §2.Migrations gains three rows: ⚠ Drop Column `<table>.<attr>`, Add Column `<table>.<attr>_kind`, Add Column `<table>.<attr>_data`.
- **Collection-of-VO multiplicity flip on the root** → may promote what was a single JSONB column into a collection-VO mapper variant, or (rarely) into a child table with FK if the diagram restereotypes the inner item to `<<Entity>>`.

### 3. `domain-events` (`<<Event>>`)

**No command-side persistence impact today.** Skip this category at dispatch time.

(If an event-store pattern is ever added — e.g. an outbox table, event-sourced aggregate, or event-replay snapshot — this row gains entries.)

### 4. `commands` (`<<Command>>`)

**No persistence impact.** Domain `<<Command>>` dataclasses are message-bus payloads, not persisted state. Skip.

### 5. `aggregates` (`<<Aggregate Root>>`, `<<Entity>>`)

The largest blast radius — touches every section:

- **Root attribute add / remove / type change** → §3 column row regenerated; mapper row updates on regen if the attribute is a value-object reference; §2.Migrations gains one appended `Add Column` / `⚠ Drop Column` / `⚠ Alter Column Type` row per change.
- **Root gains / loses `tenant_id`** → §1 multi-tenant flag flips, §2 Table pattern flips Simple ↔ Composite PK on regen, every Alternative Lookup gains/loses a tenant arg on regen, every child Table-with-FK shifts between `(parent_id, id)` and `(parent_id, id, tenant_id)` PKs on regen, every index in §3 gains/loses a `tenant_id` column on regen. §2.Migrations gains the appended cascade — Add Column `<table>.tenant_id` (initially nullable) followed by Add Not Null Constraint for the *gain* case, or ⚠ Drop Column `<table>.tenant_id` per affected table for the *loss* case. The original `Create Table` rows in §2.Migrations are preserved as historical record.
- **Entity added (new child)** → §1 has-children flag flips on, §2 gains `<Child>Table` (Table with FK) / `<Child>EntityMapper` rows on regen, repository pattern flips Simple → With Children, mapper variant flips Full / Minimal → Aggregate Mapper with Children, §3 gains a child table block + an FK index. §2.Migrations gains two appended rows: Create `<child_table>` + Add Foreign Key `<child_table>.<parent_id>`.
- **Entity removed** → mirror of "added"; §1/§2/§3 regen drops the child references; §2.Migrations gains an appended ⚠ Drop Table `<child_table>` row. Destructive on populated databases — the appender flags but emits; downstream `migrations-implementer` policy decides whether to honour it without operator confirmation.
- **Entity attribute add / remove / type change** → restricted to the child table's columns in §3 (regen) and the matching `<Child>EntityMapper` row in §2 (regen); does not touch the parent table's section. §2.Migrations gains an appended `Add Column` / `⚠ Drop Column` / `⚠ Alter Column Type` row scoped to the child table.
- **Method added/removed/changed on root or entity** → **byte-neutral for the command-repo-spec.** Methods describe behaviour, not state. Skip.
- **Multiplicity flip on a composition relationship** (e.g. `"1"` → `"0..*"` or vice versa) — restructures column-vs-child-table and shifts mapper variant. Equivalent in spec impact to entity added/removed when it crosses the "single inline VO ↔ collection child entity" boundary.
- **Status field change on the root or a child entity** (presence flip of a `status: <<Value Object>>` field) → §3 owner's table gains/loses a `status: String NOT NULL` column + a nullable `status_error` column (typed `String` when the `Status` VO's `error` field is a plain string, `JSONB` when it carries a structured payload) on regen; §2 mapper variant may flip Minimal → Full to enable the status block. §2.Migrations gains two appended rows (`Add Column status` + `Add Column status_error`) on the *gain* case; two `⚠ Drop Column` rows on the *loss* case.
- **Timestamp pair change** (presence flip of the `created_at` / `updated_at` pair) → §3 owner's table gains/loses both `DateTime(timezone=True)` columns on regen; §2 mapper variant may flip Minimal → Full to enable the timestamp block. §2.Migrations gains two appended `Add Column` (or `⚠ Drop Column`) rows.
- **Aggregate root removed** → hard-fail (mirror of `update-specs` 1c).
- **Aggregate root stereotype demoted to `<<Entity>>` or anything else** → hard-fail (the spec's anchor class no longer exists; route to `/persistence-spec:generate-specs`).

### 6. `repositories-services` (`<<Repository>>`, `<<Service>>`)

Repository finder churn lands here. Service churn does not — the persistence updater filters this category by stereotype:

- **`<<Repository>>` finder added** → if the finder name is `*_of_id`, **no spec impact** (the by-id finder is part of every repository pattern's base contract). If the finder is a non-`*_of_id` lookup (e.g. `*_with_*`, `*_by_*`, `find_*`), §2.Repository → Alternative Lookups gains a bullet on regen, §3.Indexes gains a row on regen, and §2.Migrations gains an appended `Add Index` (scalar field) or `Add JSONB Index` (JSONB field) row.
- **`<<Repository>>` finder removed** → §2 Alt-Lookup bullet and §3.Indexes row drop on regen; §2.Migrations gains an appended `Drop Index` row. The original `Add Index` row that introduced the index remains in §2.Migrations as historical record.
- **`<<Repository>>` finder signature changed** (parameter renamed, retyped, or its multiplicity flipped) → §3.Indexes row's column list updates on regen; the Alt-Lookup bullet text is rewritten on regen. §2.Migrations gains two appended rows: Drop Index `idx_<table>_<old_column>` + Add Index `idx_<table>_<new_column>`.
- **`<<Repository>>` interface itself added or removed** — should not happen on an established aggregate, but if it does, treat as malformed-report (mirror of root-removal hard-fail), since a domain aggregate without a repository is not persistable.
- **`<<Service>>` added / removed / changed** → **byte-neutral for the command-repo-spec.** Skip the category entry when its only contributor is a `<<Service>>` change.

---

## Out-of-band signals (not in `affected_categories`)

Three persistence-relevant signals are not directly emitted as a `affected_categories` entry. The updater must derive them from member/relationship deltas in `## Per-Class Changes` and from the Mermaid frontmatter:

- **Multi-tenancy flip** — derive from "`tenant_id` attribute added to the aggregate root" or "`tenant_id` attribute removed from the aggregate root" entries inside the root's Members table. Triggers a shape-change cascade through snapshot sections §1 / §2 / §3 even when no other category-mate is affected, **plus** appended `Add Column tenant_id …` / `⚠ Drop Column tenant_id` rows in §2.Migrations per affected table.
- **Children flip** — derive from any `<<Entity>>` class lifecycle entry (added or removed under `## Class Lifecycle`) **or** from a composition multiplicity flip on the root that crosses the "0..1 → 0..*" boundary. The `aggregates` category fires anyway in those cases, so this signal is informational rather than dispatch-determining; it determines *what kind* of regen §1 / §2 / §3 need (and which appended rows the migrations appender emits).
- **Bounded-context rename** — derive from a change in the diagram's Mermaid `title:` directive. This shows up in the `## Orphan Prose Changes → Preamble` block (the title is part of the preamble), **not** in `affected_categories`. It triggers snapshot regen of §1 (Purpose / Implementation labelling) and §2 (UoW class names) only; **no §2.Migrations row is appended** because a context rename does not change the database schema.

---

## Update types

Mirroring the domain-spec catalog (L / M / R / P / C codes), here is the persistence-spec response to each:

### L. Lifecycle updates (whole-class)

- **L1. Class added** — dispatch by stereotype:
  - `<<Aggregate Root>>` → impossible on an existing spec; treat as malformed.
  - `<<Entity>>` → snapshot regen of §1 has-children flag, §2 (`<Child>Table` / `<Child>EntityMapper` / repository pattern flip / mapper variant) and §3 (child table block + FK index); §2.Migrations gains appended Create `<child_table>` + Add Foreign Key rows.
  - `<<Value Object>>` → snapshot regen of §1 JSONB VO list, §2 Mapper row, §3 columns / JSONB column on the owner's table; §2.Migrations gains appended `Add Column` rows (one per VO field for flat-mapped VOs; one JSONB column for JSONB-mapped VOs).
  - `<<TypedDict>>` → byte-neutral unless the new TypedDict is a finder return type (rare; even then, query-side concern).
  - `<<Event>>` / `<<Command>>` / `<<Service>>` → byte-neutral.
  - `<<Repository>>` → impossible on an existing spec; treat as malformed.
- **L2. Class removed** — symmetric to L1: the snapshot sections regen *without* the removed class's rows; §2.Migrations gains appended destructive rows (`⚠ Drop Table` for entities, `⚠ Drop Column` per affected column for VOs). The historical `Create Table` / `Add Column` rows that introduced the entity / VO remain in §2.Migrations as audit trail.
- **L3. Stereotype changed** — hard-fail (route to `/persistence-spec:generate-specs`). The cross-category move requires the spec body to be re-rendered under the new pattern catalog.

### M. Member updates (in-class, signature-affecting)

- **M1. Attribute added/removed on root or entity** — §3 column row regen; §2 mapper row regen if the attribute is a VO reference; §2.Migrations gains an appended `Add Column` (added) or `⚠ Drop Column` (removed) row. Potentially flips multi-tenancy, children, status, or timestamp signals (see *Out-of-band signals*).
- **M2. Attribute type changed** — §3 column type change on regen; §2 mapper row may need variant change if the type flips between scalar and value object on regen; §2.Migrations gains an appended `⚠ Alter Column Type` row.
- **M3. Attribute visibility changed** — **byte-neutral for the command-repo-spec.** Visibility is a domain-layer encapsulation concern; the persistence layer reads private state via the mapper unconditionally.
- **M4. Method added/removed on root/entity/service** — **byte-neutral.** Methods are behaviour, not state. (Method changes on `<<Repository>>` are a separate axis — covered under M5 as finder churn.)
- **M5. `<<Repository>>` method signature changed** (finder churn) — see `repositories-services` mapping above. §2 Alt-Lookups bullet regen, §3 Indexes regen, §2.Migrations gains an appended `Add Index` / `Drop Index` row (or both, for signature changes that rename the indexed column).

### R. Relationship updates (cross-class topology)

- **R1. Composition added/removed** (`*--`) — ownership topology change:
  - Root → `<<Entity>>` composition added → entity-added path (children flip).
  - Root → `<<Entity>>` composition removed → entity-removed path.
  - Root or entity → `<<Value Object>>` composition added/removed → VO-added/-removed path.
- **R2. Dependency added/removed** (`-->`) — for `: emits ...` labels this adds/removes a `<<Event>>` (no persistence impact). For service-injection dependencies this is also no-op. The only persistence-relevant `-->` change is when the dependency endpoint is a `<<Repository>>` interface (rare on an established aggregate; treat as informational).
- **R3. Realization added/removed** (`--()`) — command-handler surface; no persistence impact.
- **R4. Inheritance added/removed** (`<|--`) — the only persistence-relevant case is a hierarchy that introduces a discriminator on a `<<Value Object>>` or `<<Entity>>` → §1 polymorphism flag flips, §2 gains `Polymorphic Mapper` on regen, §3 swaps single JSONB for `<attr>_kind` / `<attr>_data` pair on regen. §2.Migrations gains three appended rows: ⚠ Drop Column `<table>.<attr>`, Add Column `<table>.<attr>_kind`, Add Column `<table>.<attr>_data`.
- **R5. Multiplicity changed** — see "Multiplicity flip" under `aggregates` mapping; the boundary that matters is "single inline → collection".
- **R6. Label changed** (e.g. `: emits OrderPlaced` → `: emits OrderConfirmed`) — event-name rename; no persistence impact.
- **R7. Orphan relationship change** — the unresolved source class is typically an inferred `<<Event>>` or `<<Command>>`; no persistence impact. If the orphan resolves to a `<<Repository>>` interface (very rare), treat as malformed.

### P. Prose updates (semantic, not structural)

- **P1. Class-keyed prose changed** — narrative is not consumed by the command-repo-spec. **Byte-neutral.**
- **P2. Method-keyed prose changed** — same as P1. **Byte-neutral.**
- **P3. Orphan prose changed — `Preamble`** — refresh the §1 Purpose sentence (one-liner) **only if** the bounded-context name changed; otherwise byte-neutral. Detect by comparing the `title:` directive in the diff body.
- **P4. Orphan prose changed — free-form** (`Notes`, `Glossary`, etc.) — **byte-neutral.** These do not influence the spec.

### C. Composite / derived signals

- **C1. Pure prose change, zero structural** — typically byte-neutral for the persistence spec; the rare exception is a P3 bounded-context rename, which triggers a §1/§2-only snapshot regen (no migration row — context renames don't change the database schema).
- **C2. Pure structural, zero prose** — standard regen-plus-append path; the writer agents do not consume prose, so they produce identical snapshot output regardless of prose changes; the appender emits exactly the rows the structural deltas dictate.
- **C3. `Affected Categories` empty** — early-exit (no-op) for the persistence updater. Even orphan prose changes (P3 bounded-context rename) are typically harmless to defer until the next real domain change.
- **C4. `Affected Categories` spans multiple** — fan out to the corresponding sections; §1 + §2.{Tables, Mappers, Repository, Context Integration} always regenerate together (same writer agent), §3 re-runs whenever attribute-level changes are present, and §2.Migrations gains one or more appended rows for each structural delta in the report.
- **C5. First-run / degraded baseline** (HEAD warning) — hard-fail (route to `/persistence-spec:generate-specs`).

---

## Section-affected matrix

Quick lookup for "given an update type, what happens in each section":

| Update kind | §1 Aggregate Analysis | §2 Pattern Selection (excl. Migrations) | §2 Migrations | §3 Schema Specification |
|---|---|---|---|---|
| Aggregate root lifecycle (added / removed / stereotype change) | hard-fail |
| `<<Repository>>` interface lifecycle change | hard-fail |
| Entity added/removed | regen | regen | append (Create Table + FK / Drop Table) | regen |
| Entity attribute add/remove/type | regen | regen | append (Add Column / Drop Column / Alter Column) | regen child table block |
| Root attribute add/remove/type (non-tenant) | regen | regen | append (Add Column / Drop Column / Alter Column) | regen parent table block |
| Multi-tenancy flip (`tenant_id` add/remove on root) | regen | regen | append (Add Column tenant_id … / Drop Column tenant_id) | regen |
| Status field flip on root or entity | regen | regen (mapper variant Minimal ↔ Full) | append (Add status + status_error / Drop both) | regen owner's table |
| Timestamp pair flip | regen | regen (mapper variant Minimal ↔ Full) | append (Add created_at + updated_at / Drop both) | regen owner's table |
| VO added/removed/changed (non-polymorphic) | regen (JSONB VO list) | regen (Mapper row) | append (Add Column / Drop Column per affected column) | regen owner's table |
| VO becomes polymorphic | regen (polymorphism flag) | regen (Polymorphic Mapper row) | append (Drop original column + Add `<attr>_kind` + Add `<attr>_data`) | regen owner's table |
| `<<Repository>>` finder added/removed/changed (non-`*_of_id`) | — | regen (Alt-Lookups list) | append (Add Index / Drop Index) | regen Indexes |
| `<<Repository>>` finder added/removed/changed (`*_of_id`) | — | — | — | — |
| Bounded-context rename (Mermaid title) | regen Purpose | regen UoW class names | — | — |
| `<<Event>>` / `<<Command>>` / `<<Service>>` lifecycle or member change | — | — | — | — |
| TypedDict / domain-event prose / class prose | — | — | — | — |

Legend:
- **regen** — the snapshot writer agent re-runs and replaces the section content from the current diagram. Existing content is discarded.
- **append** — `command-repo-spec-migrations-appender` adds new rows to the bottom of §2.Migrations with fresh sequential IDs. Existing rows are byte-stable.
- **— (byte-stable)** — section is not touched.
- **hard-fail** — the updater bails out with a clear operator instruction (see *Hard-fail conditions* below).

§1 and §2 (excluding Migrations) are owned by `command-repo-spec-pattern-selector`, so they always regenerate together when either is dirty. §2.Migrations is owned by the dedicated migrations agents (writer for first-run, appender for updates) and operates independently. §3 has its own writer (`command-repo-spec-schema-writer`) and can be regenerated independently of §1/§2.

The "append" column captures the new rows the appender emits per delta type. See `spec-updater-approaches.md` § "Delta-to-changeset dispatch" for the full row-emission rules and the destructive-change `⚠ ` flagging convention.

---

## Hard-fail conditions

Mirror the domain `update-specs` failure semantics. Each prints exactly one `ERROR:` line and exits, with text directing the operator to `/persistence-spec:generate-specs <domain_diagram>`:

- **Aggregate root removal** in `## Class Lifecycle → Removed` — cannot prune the root from a persistence spec without invalidating the whole spec.
- **Aggregate root stereotype change** in `## Class Lifecycle → Stereotype Changed` (old or new bucket = `<<Aggregate Root>>`) — whole pattern catalog re-applies.
- **`<<Repository>>` interface lifecycle change** (added or removed) — a domain aggregate without a repository is not persistable; reject as malformed.
- **Degraded baseline** (`_warning: HEAD ...` line in the report Summary) — same reason as domain.
- **Multi-tenancy flip + children flip in the same diff** — *optional* hard-fail. The shape change is large enough that regeneration from scratch is safer than splicing two pattern flips simultaneously. Worth a flag, not necessarily a default.

---

## Out-of-scope but worth flagging to the operator

These belong in operator-facing warnings, not in the spec content itself:

- **Migration safety on populated databases.** Drop-column, drop-index, alter-column-type, and drop-table changesets are destructive. The appender emits these rows with a `⚠ ` prefix in the Changeset column; downstream `migrations-implementer` policy decides whether to skip flagged rows, emit them with operator-confirmation guards, or block code generation until the operator resolves the flag. See `spec-updater-approaches.md` § "Destructive change handling".
- **Tenant column removal.** Multi-tenancy removal drops `tenant_id` from every table and rewrites every PK / FK constraint. The appender emits the cascade of `⚠ Drop Column` rows; the operator must author the data-preserving migration manually if any tenant data must be reconciled before the column drops.
- **Attribute renames.** Renames are reported by `updates-detector` as `remove + add`, so the appender emits `⚠ Drop Column` + `Add Column`. This is correct but data-destructive; an operator who actually wants a rename must replace those two rows with a single `Rename Column` changeset before the implementer runs.
- **Concurrent updaters.** Two operators on parallel branches can both allocate the same next migration ID. This is a Git merge conflict, not a bug — standard merge tooling resolves it. Worth documenting in operator instructions.
- **Query-side ripple.** Today the command-repo-spec is the only persistence spec. If TypedDict / DTO shapes change and a query repository projects them, that is a separate concern — worth a future `/persistence-spec:update-query-specs` rather than overloading this skill.
- **Code regen.** This skill stops at the spec. Downstream tables, migrations, mappers, and repos are owned by `/persistence-spec:generate-code`. The downstream `migrations-implementer` MUST be append-only — never overwrite an existing `db/migrations/<id>_<slug>.yaml` file. Verify this contract; if today's implementer overwrites, the spec-side immutability fix doesn't help the actual migrations.

---

## Dispatch tiers for a persistence-spec updater

Three natural tiers fall out of the type list, mirroring the domain-spec dispatch tiers:

1. **Hard-fail** — root lifecycle changes, root stereotype changes, repository-interface lifecycle changes, degraded baseline. Operator runs `/persistence-spec:generate-specs`.
2. **Snapshot regen + log append** — every other update type. Re-run `command-repo-spec-pattern-selector` for §1 + §2.{Tables, Mappers, Repository, Context Integration} dirt and/or `command-repo-spec-schema-writer` for §3 dirt against the existing scaffolded spec; **then** invoke `command-repo-spec-migrations-appender` to add delta-driven rows to §2.Migrations. Existing §2.Migrations rows are byte-stable.
3. **No-op** — empty `affected_categories`, or `affected_categories ⊆ {domain-events, commands}`, or `repositories-services` whose only contributor is a `<<Service>>` change, or pure prose changes that don't touch the bounded-context title.

The lighter "no-op" tier is the persistence equivalent of the `domain-spec` "C3 empty footer" early-exit. The middle "snapshot regen + log append" tier is the standard path for any structural domain change — and is the load-bearing reason §2.Migrations is owned by a separate appender agent rather than swept up in the snapshot writer's regen.
