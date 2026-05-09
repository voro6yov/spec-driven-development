# Persistence Spec Updater — Design

This note documents the design of `/persistence-spec:update-specs`, the surgical update skill for `<dir>/<stem>.persistence/command-repo-spec.md`. It is the persistence-side counterpart to `/update-specs` for `domain-spec`.

The chosen approach is **Snapshot regen + append-only migrations log**, chained from domain `/update-specs` as an opt-in final step.

For the catalog of update types and their per-section impact, see the sibling [`update-types.md`](update-types.md).
For the design of the per-update report this skill emits as its terminal output, see the sibling [`updates-report.md`](updates-report.md).
For the upstream domain updater design that this skill chains onto, see [`plugins/domain-spec/notes/spec-updater-approach-b.md`](../../domain-spec/notes/spec-updater-approach-b.md).

---

## Goal

Keep `<stem>.persistence/command-repo-spec.md` aligned with the domain diagram after a domain change, **without requiring any manual operator edits to the persistence spec**. The updater:

- Runs as a chained step at the tail of `/update-specs` (domain), opt-in by file presence.
- May be invoked standalone for cases where the domain spec is up-to-date but the persistence spec drifted.
- Consumes the same `<stem>.domain/updates.md` report the domain updater consumes.
- Never re-diffs the diagram, never invokes `domain-spec:updates-detector` directly.
- Does not preserve hand-edits inside the spec — the operator's contract is that the spec is regenerated from the diagram, not curated.

---

## Inputs

- `<domain_diagram>` — the same first-positional argument every persistence-spec orchestrator takes.
- `<stem>.domain/updates.md` — already on disk (produced by `domain-spec:updates-detector`, either as Step 0 of `/update-specs` or by an explicit prior invocation).
- `<stem>.persistence/command-repo-spec.md` — already on disk (produced by an earlier `/persistence-spec:generate-specs` run); the file the updater modifies in place.

If either of the latter two files is missing, the updater hard-fails with operator instructions. The updater is **not** the first-run pipeline; `/persistence-spec:generate-specs` owns first-run.

---

## Output

`<stem>.persistence/command-repo-spec.md`, modified in place:

- §1 (Aggregate Analysis), §2.{Tables, Mappers, Repository, Context Integration}, and §3 (Schema Specification) are wholesale-regenerated from the current diagram.
- §2.Migrations gains new appended rows derived from `updates.md`. Existing §2.Migrations rows are byte-stable.
- The diagram file is untouched; no other plugin's folder is touched; no backup or rollback file is produced.

---

## Architectural insight: snapshot vs append-only log

The persistence spec mixes two fundamentally different kinds of section, and the updater must treat them differently.

### Snapshot sections

§1, §2.{Tables, Mappers, Repository, Context Integration}, and §3 describe the **current state** of the persistence layer for the aggregate. Every cell is a function of the current diagram. They are fully regeneratable.

For these sections, "Approach A" (full regen) is correct — read the current diagram, throw away the existing content, write fresh content. The output is identical to what `/persistence-spec:generate-specs` would produce on a clean run.

### The append-only log section

§2.Migrations describes the **cumulative history** of changesets that have been or will be deployed against the database. Each row corresponds to a real `<id>_<slug>.yaml` file under `db/migrations/` (managed downstream by `migrations-implementer`). Once a row is committed, it represents a deployed (or about-to-be-deployed) database operation; rewriting it produces stale or incorrect schema state in any environment that already ran the prior version.

For this one section, "Approach A" is **wrong**. Concrete failure mode:

| Time | Aggregate state | Correct §2.Migrations | What full regen produces |
|---|---|---|---|
| T0 | `users { id, tenant_id, name }` | `0001 Create users (id, tenant_id, name)` | `0001 Create users (id, tenant_id, name)` ✓ |
| T1 | add `email` field | `0001 Create users (...)` *(immutable)* + `0002 Add Column users.email` | `0001 Create users (id, tenant_id, name, email)` ✗ |

At T1, full regen produces a fresh-DB-correct migration list but loses the historical record. Any environment that already ran the T0 migration never gets `email` because there is no `Add Column` changeset.

The fix: §2.Migrations is append-only. Existing rows are immutable; new rows are computed from the *delta* in `updates.md` and appended with fresh IDs.

### The split

The chosen approach is therefore hybrid:

| Section | Update behaviour |
|---|---|
| §1 Aggregate Analysis | Snapshot regen |
| §2 Tables | Snapshot regen |
| §2 Migrations | **Delta-driven row append** — existing rows immutable |
| §2 Mappers | Snapshot regen |
| §2 Repository (+ Alt Lookups) | Snapshot regen |
| §2 Context Integration | Snapshot regen |
| §3 Schema Specification | Snapshot regen |

Conceptually simple: every section either fully regenerates or is append-only. No row-level splicer in between.

---

## Agent reorganization

To support the snapshot/log split cleanly, `command-repo-spec-pattern-selector`'s ownership of §2.Migrations is moved to two new dedicated agents.

| Agent | Status | Owns |
|---|---|---|
| `command-repo-spec-scaffolder` | unchanged | seed file + §1.Implementation pre-fill |
| `command-repo-spec-pattern-selector` | **modified** — drops §2.Migrations | §1 + §2.{Tables, Mappers, Repository, Context Integration} |
| `command-repo-spec-schema-writer` | unchanged | §3 |
| `command-repo-spec-migrations-writer` | **new** | §2.Migrations on first run (snapshot baseline) |
| `command-repo-spec-migrations-appender` | **new** | §2.Migrations on update (delta append); also **returns** the structured appended-row list to the orchestrator (consumed by `command-repo-spec-updates-writer` at Step 5) |
| `command-repo-spec-updates-writer` | **new** | `<stem>.persistence/updates.md` — composes the per-update report at Step 5 (see [`updates-report.md`](updates-report.md)) |

The two new agents share most of their logic — delta-to-changeset dispatch and row formatting — but operate against different inputs:

- `migrations-writer` dispatches against the **full diagram** (as if every class were freshly added), allocating IDs starting at `0001`.
- `migrations-appender` dispatches against **`updates.md`**, allocating IDs starting at `max(existing_id) + 1`.

They could share an underlying skill that holds the dispatch table.

### Pattern-selector contract change

`command-repo-spec-pattern-selector` currently fills the entire `## 2. Pattern Selection` section, including the `### Migrations` sub-table. The contract change:

- The agent leaves the `### Migrations` heading intact.
- It writes a placeholder body under that heading: a single comment row `| _ | Owned by command-repo-spec-migrations-writer | _ | _ |` that the downstream migrations agent overwrites.
- The agent's idempotency guard ignores the `### Migrations` body for the purpose of "already filled" detection — it only looks at the other §2 sub-tables.

### First-run pipeline

`/persistence-spec:generate-specs` becomes:

```
scaffolder
  → pattern-selector       # §1 + §2.{Tables, Mappers, Repository, Context Integration}
  → migrations-writer      # §2.Migrations (snapshot baseline, IDs 0001..0NNN)
  → schema-writer          # §3
```

### Update pipeline

`/persistence-spec:update-specs` is described in detail below.

---

## Migration row schema

Each §2.Migrations row is augmented from the current template with a stable ID column.

```
### Migrations

| ID    | Changeset                                  | Pattern               | Template                       |
|-------|--------------------------------------------|-----------------------|--------------------------------|
| 0001  | Create `users`                              | Create Table          | `persistence-spec:migration`   |
| 0002  | Create `users_address`                      | Create Table          | `persistence-spec:migration`   |
| 0003  | Add Foreign Key `users_address.user_id`     | Add Foreign Key       | `persistence-spec:migration`   |
| 0004  | Add Index `idx_users_email`                 | Add Index             | `persistence-spec:migration`   |
| 0005  | Add Column `users.phone`                    | Add Column            | `persistence-spec:migration`   |
| 0006  | ⚠ Drop Column `users.legacy_field`          | Drop Column           | `persistence-spec:migration`   |
```

**Columns:**

- **ID** — monotonically increasing zero-padded sequence number (`0001` … `9999`). Allocated by whichever migrations agent appends the row. Once written, the ID is frozen — the updater never reassigns IDs. (Open question on cap; see below.)
- **Changeset** — human-readable summary. Destructive operations (`Drop Column`, `Drop Table`, `Drop Index`, `Alter Column Type`) are prefixed with `⚠ ` so reviewers and downstream agents notice them.
- **Pattern** — controlled vocabulary, drives the YAML emitted by `migrations-implementer`.
- **Template** — always `persistence-spec:migration`.

**Pattern vocabulary:**

| Pattern | Direction |
|---|---|
| `Create Table` / `Create Table (Composite PK)` | additive |
| `Add Foreign Key` | additive |
| `Add Index` / `Add JSONB Index` | additive |
| `Add Column` | additive |
| `Add Not Null Constraint` | additive (but data-sensitive) |
| `Drop Column` | destructive |
| `Drop Index` | additive (re-runnable) but loses index |
| `Drop Table` | destructive |
| `Alter Column Type` | destructive (most type changes lose data) |

The ID column is new — the current template omits it because first-run migrations are positionally enumerated. The updater requires stable IDs to enforce the immutability contract and to map rows to YAML filenames.

### YAML file mapping

`migrations-implementer` (downstream of the spec updater, owned by `/persistence-spec:generate-code`) maps each §2.Migrations row to a file:

```
db/migrations/<id>_<pattern_slug>.yaml
```

Examples:

- Row `0001 Create users` → `db/migrations/0001_create_users.yaml`
- Row `0005 Add Column users.phone` → `db/migrations/0005_add_column_users_phone.yaml`

`master.yaml` lists these in ID order. The implementer is **append-only**: it skips any row whose corresponding YAML already exists on disk; writes a new YAML for any new row. **Never overwrites existing files.** This is a contract change worth verifying against the current `migrations-implementer` agent.

---

## Update workflow

```
/persistence-spec:update-specs <domain_diagram>
│
├─ Step 0  Read inputs
│           ├─ <stem>.domain/updates.md           (must already exist)
│           └─ <stem>.persistence/command-repo-spec.md  (must already exist)
│           If either is missing → hard-fail with operator instructions.
│           Pre-update spec content is preserved (in memory or temp file)
│           for consumption by command-repo-spec-updates-writer at Step 5.
│
├─ Step 1  Preflight (orchestrator-owned, pure parse)
│           Apply gates in order:
│             1a. degraded baseline (HEAD warning) → hard-fail
│             1b. root removed / root stereotype change → hard-fail
│             1c. <<Repository>> interface lifecycle change → hard-fail
│             1d. nothing persistence-relevant → no-op exit
│
├─ Step 2  Section reset (snapshot sections only)
│           Replace §1, §2.{Tables, Mappers, Repository, Context Integration},
│           and §3 bodies with template placeholders.
│           §2.Migrations is left untouched — it is not a snapshot section.
│
├─ Step 3  Snapshot regen (sequential)
│           Invoke command-repo-spec-pattern-selector
│             → fills §1 + §2.{Tables, Mappers, Repository, Context Integration}
│           Invoke command-repo-spec-schema-writer
│             → fills §3
│
├─ Step 4  Append delta migrations
│           Invoke command-repo-spec-migrations-appender
│             ├─ reads existing §2.Migrations rows; computes max(ID)
│             ├─ reads <stem>.domain/updates.md
│             ├─ applies delta-to-changeset dispatch table
│             ├─ appends new rows with IDs starting at max(ID) + 1
│             └─ returns structured appended-row list to the orchestrator
│
├─ Step 5  Emit updates.md
│           Invoke command-repo-spec-updates-writer
│             ├─ reads pre-update spec snapshot (captured at Step 0)
│             ├─ reads post-update spec from disk
│             ├─ reads appended-row list returned by Step 4
│             └─ writes <stem>.persistence/updates.md
│           See `updates-report.md` for the report schema and agent contract.
│
└─ Step 6  Report
           "Updated <stem>.persistence/command-repo-spec.md
            (snapshot sections regenerated; appended N migration rows:
             <id1>, <id2>, ...; emitted <stem>.persistence/updates.md)<orphan_prose_clause>."
```

Steps 0–2 are pure orchestrator-owned text manipulation. Steps 3, 4, and 5 are agent invocations. Steps run sequentially (no parallel benefit at this volume).

### No-op exits (Step 1d)

The updater early-exits with success when:

- `affected_categories` in `updates.md` is empty (no domain change of any kind).
- `affected_categories ⊆ {domain-events, commands}` — events and commands don't persist.
- `affected_categories = {repositories-services}` and the only changed members are `<<Service>>` (filter by stereotype; `<<Service>>` does not contribute to persistence).
- All changes are pure prose (P1, P2, P4) and the bounded-context Mermaid title is byte-stable.

In all no-op cases, the updater still invokes `command-repo-spec-updates-writer` at Step 5 to emit a `_no changes_` report — this keeps the consumer's contract simple (an `updates.md` exists after every successful run). Then prints one line and exits 0.

---

## Delta-to-changeset dispatch

`command-repo-spec-migrations-appender` reads `<stem>.domain/updates.md` and applies this dispatch table. Each match emits one or more rows. Rows are emitted in `updates.md`'s natural order so the migration log is causally readable.

### Aggregate root attribute deltas

| `updates.md` entry | Appended changeset(s) |
|---|---|
| Member added on root: `<field>: <type>` | Add Column `<table>.<field>` (typed via `table-definitions` Column Types) |
| Member removed on root: `<field>` | ⚠ Drop Column `<table>.<field>` |
| Member type changed on root: `<field>: <old> → <new>` | ⚠ Alter Column Type `<table>.<field>` → `<new_sql_type>` |
| Member nullability flip on root: required → optional | Drop Not Null Constraint `<table>.<field>` |
| Member nullability flip on root: optional → required | Add Not Null Constraint `<table>.<field>` (data-sensitive) |

### Entity (child) lifecycle deltas

| `updates.md` entry | Appended changeset(s) |
|---|---|
| `<<Entity>>` added (new child entity collection on root) | Create `<child_table>` + Add Foreign Key `<child_table>.<parent_id>` (two rows, IDs are sequential) |
| `<<Entity>>` removed | ⚠ Drop Table `<child_table>` |
| Member added on entity: `<field>: <type>` | Add Column `<child_table>.<field>` |
| Member removed on entity | ⚠ Drop Column `<child_table>.<field>` |
| Member type changed on entity | ⚠ Alter Column Type `<child_table>.<field>` → `<new_sql_type>` |

### Value-object deltas

| `updates.md` entry | Appended changeset(s) |
|---|---|
| `<<Value Object>>` added with **flat-column** mapping | one Add Column `<table>.<field>` per VO field; nullability matches each field's optionality |
| `<<Value Object>>` added with **JSONB** mapping | Add Column `<table>.<vo_field>` typed `JSONB` (single column) |
| `<<Value Object>>` removed | ⚠ Drop Column for each affected column |
| `<<Value Object>>` field added (flat-mapped VO) | Add Column `<table>.<field>` |
| `<<Value Object>>` field removed (flat-mapped VO) | ⚠ Drop Column `<table>.<field>` |
| `<<Value Object>>` field added (JSONB-mapped VO) | no migration (JSONB shape changes are application-level) |
| `<<Value Object>>` becomes polymorphic | ⚠ Drop Column `<table>.<vo_field>` + Add Column `<table>.<vo_field>_kind` (`String NULL`) + Add Column `<table>.<vo_field>_data` (`JSONB NULL`) |

### Repository finder deltas

| `updates.md` entry | Appended changeset(s) |
|---|---|
| New `<<Repository>>` finder (non-`*_of_id`) over scalar field | Add Index `idx_<table>_<column>` |
| New `<<Repository>>` finder over JSONB field | Add JSONB Index `idx_<table>_<column>_gin` |
| Removed `<<Repository>>` finder | Drop Index `idx_<table>_<column>` |
| Repository finder signature changed (parameter retyped/renamed) | Drop Index `idx_<table>_<old_column>` + Add Index `idx_<table>_<new_column>` |
| New `*_of_id` finder | no migration (every table already supports lookup by PK) |

### Cross-cutting shape flips (out-of-band signals)

| Domain delta | Appended changeset(s) |
|---|---|
| Multi-tenancy added (`tenant_id` member added on root) | Add Column `<table>.tenant_id` (`String`, initially nullable) + Add Not Null Constraint `<table>.tenant_id` (after backfill — operator-confirmed) + index updates as needed for child tables |
| Multi-tenancy removed (`tenant_id` member removed) | ⚠ Drop Column `<table>.tenant_id` (and per child table) |
| Status field added on root or entity (presence flip of `status: <<Value Object>>`) | Add Column `<table>.status` (`String NOT NULL`) + Add Column `<table>.status_error` (`String NULL`) |
| Status field removed | mirror: two ⚠ Drop Column rows |
| Timestamp pair added (`created_at` + `updated_at`) | two Add Column rows typed `DateTime(timezone=True)` |
| Timestamp pair removed | mirror: two ⚠ Drop Column rows |
| Bounded-context rename (Mermaid title) | no migration (snapshot regen handles UoW class names; no DB change) |

### Byte-neutral deltas (no rows emitted)

The appender does **not** infer migrations from:

- `<<Event>>` lifecycle or member changes
- `<<Command>>` lifecycle or member changes
- `<<Service>>` lifecycle or member changes
- `<<TypedDict>>` lifecycle or member changes (command-side)
- Method add/remove/changed on any class (methods are behaviour, not state)
- Any prose change (P1, P2, P4)
- Any inheritance/realization edge change that isn't part of a polymorphism flip

---

## Destructive change handling

Some delta types correspond to data-destructive migrations. The appender emits these rows but flags each one with the `⚠ ` prefix in the Changeset column:

```
| 0007 | ⚠ Drop Column `users.legacy_field` | Drop Column | `persistence-spec:migration` |
```

Destructive patterns (always flagged):

- `Drop Column`
- `Drop Table`
- `Alter Column Type`
- Drop Column `<table>.tenant_id` (multi-tenancy removal)

Downstream `migrations-implementer` policy options:

- **Strict.** Skip any row with `⚠ ` prefix; require operator to remove the prefix manually after authoring a data-preserving migration.
- **Permissive.** Emit the YAML anyway with explicit operator-confirmation guards.
- **Block.** Refuse to emit any code until a `⚠ ` row is resolved.

The appender's contract is "emit with warning marker." The implementer policy is out of scope for this updater.

---

## Hard-fail conditions

Each prints exactly one `ERROR:` line and exits non-zero. The error directs the operator to `/persistence-spec:generate-specs <domain_diagram>` for cases that surgical update cannot handle.

| Condition | Detection | Reason |
|---|---|---|
| **0a. Missing `<stem>.domain/updates.md`** | file not on disk | The updater is not the first-run pipeline; the report must already exist |
| **0b. Missing `<stem>.persistence/command-repo-spec.md`** | file not on disk | The updater is not the first-run pipeline; the spec must already exist |
| **1a. Degraded baseline** | `_warning: HEAD ...` line in updates.md Summary | Cannot operate against a degraded baseline |
| **1b. Aggregate root lifecycle change** | root in `## Class Lifecycle → Removed`, or root listed under `Stereotype Changed` (old or new bucket) | The spec's anchor class is invalid; full regen needed |
| **1c. `<<Repository>>` interface lifecycle change** | repository class added or removed under `## Class Lifecycle` | A domain aggregate without a repository is not persistable; malformed-report condition |

The error messages explicitly direct the operator to `/persistence-spec:generate-specs <domain_diagram>` — not to fix the report or retry. `/generate-specs` rebuilds from scratch and re-establishes the snapshot baseline; on next update the appender resumes from the new max ID.

---

## Idempotency

Re-running `/persistence-spec:update-specs` against unchanged inputs must produce byte-identical output (no new migration rows, no spurious diff in snapshot sections beyond LLM nondeterminism).

- **Steps 0–2** are deterministic file operations.
- **Step 3** invokes LLM agents; they may produce minor prose drift (e.g. the `Purpose` sentence). This is `git diff` noise, not an idempotency failure.
- **Step 4** is the load-bearing case. The appender must detect that the deltas implied by `updates.md` have already been applied to §2.Migrations. The detection mechanism:
  - Each appender run records a sentinel comment at the start of the appended block: `<!-- appended-from updates-hash:<hash> -->` where `<hash>` is a content hash of `updates.md`.
  - On re-run, the appender computes the same hash. If the sentinel for that hash already exists in §2.Migrations, the appender exits without emitting rows.

The sentinel approach is precise (no false positives) and simple (no ID-arithmetic across runs). It does require a small comment line to live inside the spec, which is fine because Markdown table syntax tolerates HTML comments between rows.

If the operator regenerates `<stem>.domain/updates.md` (e.g. by re-running `/update-specs` after fixing a diagram), the hash changes, and the appender re-engages — but only emits rows for *new* deltas, because the dispatch table is keyed off `updates.md` content.

---

## Chaining contract: domain `/update-specs` → persistence `/update-specs`

`/persistence-spec:update-specs` is designed to slot into `/update-specs` (domain) as a chained final step.

```
/update-specs <domain_diagram>
│
├─ Steps 0–8  (existing: detect, preflight, prune, regen, splice, exceptions, replan, cleanup)
│
└─ Step 9     If <stem>.persistence/command-repo-spec.md exists,
              invoke /persistence-spec:update-specs <domain_diagram>
              (otherwise skip — persistence not initialized for this aggregate)
```

The chained step is **opt-in by file presence**: if the operator has run `/persistence-spec:generate-specs` for this aggregate at any time in the past, the persistence spec exists and the update chain fires. Otherwise the chain skips silently — purely-domain-modeled aggregates without a persistence layer don't pay any cost.

The persistence updater is also independently invocable for situations where the domain spec is up-to-date but the persistence spec drifted (e.g. operator manually edited the diagram and ran `/persistence-spec:generate-specs` once, then re-edited).

The same chaining shape is intended to extend to `application-spec`, `rest-api-spec`, and `messaging-spec` updaters as Steps 10, 11, 12 — each opt-in by file presence, each independently invocable. Each downstream updater reads the same `<stem>.domain/updates.md` rather than maintaining its own diff.

### Chained-step error handling

If the persistence updater hard-fails inside the chained invocation:

- Domain `/update-specs` reports its own steps as successful.
- The chained-step error surfaces with a clear "persistence updater failed" prefix, including the operator instruction (`run /persistence-spec:generate-specs`).
- The domain artifacts are not rolled back — they are correct.
- The persistence spec remains in whatever state it was in before the chained invocation (the chained skill aborts before any write).

The exit status of `/update-specs` reflects the chained failure (non-zero) so CI can detect it, but the surface message distinguishes "domain succeeded; persistence chain failed."

---

## Failure semantics and recovery

The orchestrator does not roll back partial writes. **Re-running `/persistence-spec:update-specs` after fixing the trigger is the supported recovery path.** Each step is idempotent on stable inputs (per the Idempotency section above).

The only failure modes that cannot be retried through are the hard-fail conditions (0a, 0b, 1a, 1b, 1c). Each error message explicitly directs the operator to the correct fix:

- 0a/0b: run the missing prerequisite (`/update-specs` or `/persistence-spec:generate-specs`).
- 1a/1b/1c: run `/persistence-spec:generate-specs <domain_diagram>` for a fresh baseline.

---

## What the updater deliberately does NOT do

- It does not regenerate `<stem>.persistence/command-repo-spec.md` from scratch — that is `/persistence-spec:generate-specs`.
- It does not touch the diagram file or its `## Artifacts` index — `/persistence-spec:generate-specs` already linked them.
- It does not modify §2.Migrations rows that exist before the run — the immutability contract is load-bearing.
- It does not modify the YAML files under `db/migrations/` — those are owned by `/persistence-spec:generate-code`.
- It does not handle aggregate-root or `<<Repository>>` interface lifecycle changes — those route to `/persistence-spec:generate-specs`.
- It does not invoke `domain-spec:updates-detector` directly — the report is expected on disk by the time this skill runs.
- It does not propose database-level rollback for destructive changesets — the `⚠ ` marker is the extent of its safety affordance.
- It does not handle the query-side spec — that is a future `/persistence-spec:update-query-specs` concern.
- It does not preserve hand-edits inside the spec — the operator's contract is that the spec is regenerated from the diagram.

---

## Open questions

- **Migration ID format.** Zero-padded sequential (`0001`, `0002`, …) is simplest but caps at 9999 — sufficient for any realistic single aggregate, but tight for very long-lived projects. Timestamp-based (`20260308_143022_create_users`) scales without limit but is less skimmable. Liquibase changeSet IDs accept either; the choice is a downstream `migrations-implementer` concern. The spec just needs *some* stable per-row ID.
- **Multi-update batching.** If an operator makes ten domain changes before running the updater, the appender emits ten new migration rows. That's correct but produces a noisy migration history. Whether to coalesce (e.g. squash all `Add Column users.X` rows from a single update run into a single migration file) is a downstream `migrations-implementer` policy choice; the spec keeps them separate so the audit trail is per-domain-change.
- **`migrations-implementer` immutability enforcement.** This skill assumes `migrations-implementer` will *not* overwrite existing YAML files. That is a contract change worth verifying — if today's implementer overwrites, the spec-side immutability fix doesn't help the actual migrations.
- **Sentinel format.** The `<!-- appended-from updates-hash:<hash> -->` sentinel sits inside §2.Migrations as an HTML comment. Markdown renderers handle this correctly, but worth verifying that the implementer agents skip comments when parsing rows.
- **Diagram-only changes that affect §2.Migrations indirectly.** A bounded-context rename (Mermaid `title:` change) updates UoW class names in §2.Context Integration but does not produce a database migration. The dispatch table correctly emits no row in this case, but it's a worth-flagging case for reviewers.
- **Concurrent updaters.** If two operators run `/persistence-spec:update-specs` in parallel against the same spec (e.g. two branches), they may allocate the same next ID. This is a merge-conflict scenario, not an updater bug — the spec is a Git-tracked file and standard merge tooling resolves it. Worth documenting as expected behaviour.

---

## Alternatives considered

The earlier comparison (Approaches A–E in the prior version of this note) led to recommending Approach B (section-scoped regen, designed to preserve hand-edits). That recommendation was overturned by two clarifications from the operator:

1. **Hand-edits are not a goal.** Approach B's value over Approach A was preserving manual edits during regen. With hand-edits explicitly out of scope, Approach A becomes simpler and equally correct for snapshot sections.
2. **§2.Migrations is append-only history, not snapshot.** Both Approaches A and B are *wrong* for §2.Migrations: regenerating from scratch loses migration history, and section-scoped regen of §2 also rewrites §2.Migrations rows. Neither approach alone is sufficient.

The chosen approach — **snapshot regen for snapshot sections + delta-driven append for §2.Migrations**, chained from domain `/update-specs` — is structurally hybrid but conceptually simple: every section either fully regenerates or is append-only, with no in-between row-level splicer.

| Approach | Status | Why not |
|---|---|---|
| **A. Full regen** | rejected | Wrong for §2.Migrations (loses history) |
| **B. Section-scoped regen** | rejected | Justified by hand-edit preservation, which is out of scope; also wrong for §2.Migrations |
| **C. Row-level splicer** | rejected | Significant new agents, duplicates row-shape knowledge from writers, narrow value when hand-edits aren't in scope |
| **D. Idempotent writers** | rejected | Pushes splicer complexity into writers without the row-preservation benefit |
| **E. Hybrid: B + row-splicer for §3.Indexes** | rejected | Sub-case of C; same trade-off |
| **Snapshot + Log (chosen)** | **accepted** | Correct for both kinds of section; minimal new logic; chains cleanly from domain `/update-specs` |
