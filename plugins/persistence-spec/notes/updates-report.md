# Persistence Updates Report — Design

This note describes the design of `<dir>/<stem>.persistence/updates.md`, the **persistence-side analog of the domain updates report** (`<dir>/<stem>.domain/updates.md`).

It is the input contract a future `/persistence-spec:update-code` skill will consume to surgically update generated persistence artifacts (tables, mappers, migrations, repositories, context integration, fixtures, repo tests) without re-running `/persistence-spec:generate-code` from scratch — analogous to how `domain-spec:code-updater` consumes the domain `updates.md` (see [`plugins/domain-spec/notes/code-updater-approach-c.md`](../../domain-spec/notes/code-updater-approach-c.md)).

For the catalog of *upstream* domain deltas that drive the persistence spec updater, see [`update-types.md`](update-types.md). For the spec updater design that produces the artifacts this report captures, see [`spec-updater-approaches.md`](spec-updater-approaches.md).

---

## Goal

Capture, in structured form, every change `/persistence-spec:update-specs` made to `<stem>.persistence/command-repo-spec.md`, in a shape that lets a downstream code updater dispatch per-artifact updates without re-diffing the spec.

The report:

- Is **persistent** (committed alongside the spec) so it survives between `update-specs` and `update-code`.
- Is **per-artifact** rather than per-class: it lists *which generated files change* (and how), not which domain classes changed. The domain `updates.md` already covers per-class deltas; this report's job is to project them onto persistence artifacts.
- Is **stable** between identical inputs — same domain `updates.md` hash + same pre-update spec → byte-identical report.
- Is **self-contained** for the code updater: combined with the updated spec, it has everything needed to compute the on-disk edits.

---

## Lifecycle and ownership

### Producer

`<stem>.persistence/updates.md` is produced by `/persistence-spec:update-specs` as a **side effect** of the spec update — emitted in the same run that rewrites the spec.

This differs from the domain side, where `domain-spec:updates-detector` runs **before** the spec updater and the report is its primary output. The reason for the asymmetry:

| Aspect | Domain | Persistence |
|---|---|---|
| Source of truth | Mermaid diagram (human-edited) | command-repo-spec (generated) |
| Detection | git diff of diagram + prose | known by producer (spec updater knows what it changed) |
| Re-diffing | unavoidable (the diagram is the only ground truth) | wasted work (the spec updater already has the deltas) |

Concretely: the spec updater receives `<stem>.domain/updates.md` (which already enumerates domain-level deltas), applies dispatch rules (pattern flips, mapper-variant flips, migration-row appends, etc.), and writes the new spec. Emitting a structured per-artifact report at the end of that run is a near-zero-cost byproduct.

#### Alternative considered: standalone `persistence-spec:updates-detector`

A standalone detector would `git diff` the spec before/after and emit the report. Rejected because:

- It duplicates work the spec updater already performed.
- It loses higher-fidelity intent (the spec updater knows whether §2.Migrations gained a row by *append* or whether it was a regen artefact; `git diff` flattens that distinction).
- The spec is generated, not curated — there is no operator-intent hidden in the spec text that a separate detector would surface.

The closer mirror to the domain side is tempting but doesn't pay for itself.

### Consumer

`<stem>.persistence/updates.md` is consumed by the future `/persistence-spec:update-code` skill — an analog of `domain-spec:update-code`. The code updater walks the report's `## Affected Artifacts` footer to dispatch per-file updates, reading the per-section bodies for the structured delta details.

It is **not** chained automatically into `/update-specs`. Code regeneration is a separate operator-driven step (same contract as the domain side: spec updates on every diagram edit; code updates on demand).

### First-run pipeline

`/persistence-spec:generate-specs` does **not** produce this report. The report describes deltas, not absolute state. On first run, `/persistence-spec:generate-code` runs against the spec directly with no report to consult.

---

## Producer architecture

The producer is split into two artifacts that mirror the domain side's `updates-report-template` skill + `updates-detector` agent pair:

### Reference skill: `persistence-spec:updates-report-template`

A condensed *contract* document — schema + rendering rules, not design rationale — auto-loaded by:

- The producer agent (when rendering the report).
- The future `/persistence-spec:update-code` consumer (when parsing the report).

Covers:

- Top-level section order (Summary → Aggregate Analysis → Tables → Mappers → Repository → Migrations → Context Integration → Affected Artifacts).
- Per-section body conventions (Added / Removed / Modified buckets; closed action-verb vocabulary `add | modify | remove`; `_no changes_` rendering for empty sections).
- Within-section ordering rules (alphabetical by name, except Migrations which preserves chronological appended-row order).
- Affected Artifacts table shape (path + action + driving-section columns).
- Sentinel placement (HTML comment recording the source domain `updates.md` hash, used by the consumer for skip-on-replay detection).

The split between schema-as-skill and design-as-notes is the same one the domain side draws — the *why* lives here in the notes; the *how to render and parse* lives in the skill.

### Agent: `command-repo-spec-updates-writer`

A small, deterministic agent invoked at the tail of `/persistence-spec:update-specs` — also standalone-invocable. Composes `<stem>.persistence/updates.md` by diffing the working-tree spec against `git HEAD`; reads the sibling domain `updates.md` only as an enrichment source for `Source delta` lookups. Does not consult any orchestrator-supplied runtime state.

Naming asymmetry vs the domain side is intentional but the workflow shape mirrors `domain-spec:updates-detector` exactly: both agents take a single positional arg, recover their pre-update baseline via `git show HEAD:<file>`, and write a sibling report. The persistence side is simpler — the schema is fully mechanical, so there is no LLM-creative step (no prose summarization).

**Arguments**:

- `<domain_diagram>` — first and only positional arg. Used solely to recover `<dir>` and `<stem>` per `persistence-spec:naming-conventions`. The diagram itself is not parsed.

**Reads (filesystem)**:

1. **Working-tree spec** — `<dir>/<stem>.persistence/command-repo-spec.md` (must exist; otherwise hard-fail with "run `/persistence-spec:generate-specs` first").
2. **HEAD spec** — recovered via `git ls-files --full-name` + `git show HEAD:<repo_path>`. First-run handling: missing-at-HEAD → empty baseline; the entire post-update spec is reported as Added.
3. **Domain updates report** — `<dir>/<stem>.domain/updates.md` (sibling). Missing is non-fatal; `Source delta` falls back to `(unknown source)` and the Summary line renders `_none_`.

**Reads (auto-loaded skills)**: `persistence-spec:naming-conventions`, `persistence-spec:updates-report-template`, `persistence-spec:migration-vocabulary`.

**Output**: `<dir>/<stem>.persistence/updates.md`, written from scratch (replaces any prior file).

**Determinism**: structured-input-driven, not LLM-creative. Re-running with byte-identical inputs (working tree + HEAD blob + domain `updates.md`) produces a byte-identical report. The Affected Artifacts table is mechanically derived (Tables Changes → `tables/<x>.py` + aggregator; Mappers Changes → `mappers/<x>_mapper.py` + aggregator; Migrations Changes → `db/migrations/<id>_<slug>.yaml` + `master.yaml`; Context Integration Changes → per-context `unit_of_work/*.py` + `query_context/*.py`).

**Standalone invocability**: supported. The writer reads everything it needs from disk (working tree + git HEAD + sibling files), so it does not require an orchestrator wrapper. This is useful for testing, operator-driven recovery (e.g. when a prior `update-specs` run hard-failed), and CI verification. The orchestrator (`/persistence-spec:update-specs`) is one of several callers.

### Workflow integration

Slots into `/persistence-spec:update-specs` as a new Step 5 between the migrations append (Step 4) and the operator-facing one-liner (renumbered Step 6):

```
Step 1  Preflight (gates)
Step 2  Section reset
Step 3  Snapshot regen               (pattern-selector + schema-writer)
Step 4  Append migrations            (migrations-appender)
Step 5  Emit updates.md              (command-repo-spec-updates-writer)
Step 6  Report (operator one-liner)
```

The orchestrator does not need to capture pre-update spec content or the appender's row list — the writer recovers both directly: pre-update content via `git show HEAD:<spec_file>`; appended rows via §2.Migrations row-ID set-difference between HEAD and working tree. This keeps the orchestrator stateless and lets the writer also run standalone (without an orchestrator wrapper) for testing or operator-driven recovery.

The writer runs on every successful spec update, including no-op early-exit cases at the orchestrator's preflight gate — those produce a report with every section `_no changes_` and an empty Affected Artifacts table. This keeps the consumer's contract simple: `updates.md` always exists after a successful run. The writer does **not** run when the workflow hard-fails before Step 5 — there is no transition to describe.

---

## File location and naming

```
<dir>/<stem>.persistence/
├── command-repo-spec.md       (the spec itself)
└── updates.md                 (this report)
```

Mirrors the domain convention: `<dir>/<stem>.domain/updates.md` sits next to `<dir>/<stem>.domain/spec.md`.

---

## Report schema

Top-level structure (canonical section order):

```markdown
# Persistence Updates Report

## Summary
## Aggregate Analysis Changes
## Tables Changes
## Mappers Changes
## Repository Changes
## Migrations Changes
## Context Integration Changes
## Affected Artifacts
```

Each section's body is either a structured delta block or `_no changes_`. Sections never disappear — empty sections render as `_no changes_` so the parser doesn't have to discriminate "absent" vs "no-op".

### Section: Summary

A small preamble. Mirrors the domain report's Summary block.

```markdown
## Summary

- Spec: dir/user.persistence/command-repo-spec.md
- Pre-update spec hash: <sha256 of command-repo-spec.md before this run>
- Post-update spec hash: <sha256 of command-repo-spec.md after this run>
- Domain updates source: dir/user.domain/updates.md (hash: <sha256>)
- Generated at: 2026-05-08T14:32:01Z
- Warnings:
  - 1 destructive migration appended (Drop Column users.legacy_field)
```

The two spec hashes pin the report to a specific transition; the code updater verifies the post-update hash matches the on-disk spec before consuming the report (defends against operator running `update-code` after a stale report).

### Section: Aggregate Analysis Changes

Tracks flag flips on §1 of the spec.

```markdown
## Aggregate Analysis Changes

- Multi-tenant: was `No`, now `Yes`
- Has children: was `No`, now `Yes` (entity added: `OrderLine`)
- Polymorphism: introduced on `Notification.payload` (subtypes: `EmailPayload`, `SmsPayload`)
- JSONB value objects: added `Address`; removed `Tag`
```

Each line is `<flag>: was X, now Y` or `_unchanged_`. If every flag is unchanged, the section is `_no changes_`.

These flags don't directly drive a single code edit — they cascade through downstream sections. They're listed at the top so a reviewer can see the high-level shape change at a glance.

### Section: Tables Changes

Per-table grouping. Drives `tables/<table>.py`.

```markdown
## Tables Changes

### Added
- `users_address`
  - Pattern: `With FK + Composite PK`
  - Columns: `user_id: UUID NOT NULL`, `tenant_id: String NOT NULL`, `street: String NOT NULL`, `city: String NOT NULL`, `zip: String NULL`
  - PK: `(user_id, tenant_id, id)`
  - FK: `(user_id, tenant_id)` → `users(id, tenant_id)`
  - Indexes: _none_

### Removed
- `users_legacy_profile`

### Modified
- `users`
  - Pattern flipped: `Simple PK` → `Composite PK (with tenant_id)`
  - Columns added: `tenant_id: String NOT NULL`, `email: String NOT NULL`, `phone: String NULL`
  - Columns removed: `legacy_field: String`
  - Columns altered: `name: String(50) → String(100)`
  - Nullability flipped: `bio` (`NOT NULL` → `NULL`)
  - Indexes added: `idx_users_email` (column: `email`)
  - Indexes removed: `idx_users_legacy_field`
  - Foreign keys added: _none_
  - Foreign keys removed: _none_
```

The Added bucket includes the full table shape — the code updater scaffolds a fresh module from these fields. Modified buckets list only the deltas — the consumer reads the updated spec for the post-state of unchanged columns.

### Section: Mappers Changes

Per-mapper grouping. Drives `mappers/<x>_mapper.py` and `mappers/__init__.py` aggregator.

```markdown
## Mappers Changes

### Added
- `AddressMapper` — variant: `Simple` — table: `users` (flat columns) — owning class: `Address`

### Removed
- `LegacyProfileMapper`

### Modified
- `UserMapper`
  - Variant flipped: `Full` → `Aggregate Mapper with Children`
  - Reason: children flag turned on (`OrderLine` added)
  - Payload columns changed: `email` added; `legacy_field` removed
- `NotificationPayloadMapper`
  - Variant flipped: `Simple` → `Polymorphic`
  - Discriminator column: `payload_kind`
  - Payload column: `payload_data`
  - Subtypes: `EmailPayload`, `SmsPayload`
```

Variant names match the catalog in `persistence-spec:mappers`.

### Section: Repository Changes

Drives `command_<aggregate>_repository.py` and `query_<aggregate>_repository.py`.

```markdown
## Repository Changes

- Pattern flipped: `Simple` → `With Children`
  - Reason: children flag turned on
- Alternative Lookups added:
  - `user_of_email(email: str)` — index: `idx_users_email`
- Alternative Lookups removed:
  - `user_of_legacy_field(legacy_field: str)`
- Alternative Lookups signature changed:
  - `user_of_external_id(external_id: str)` → `user_of_external_id(external_id: UUID)`
    - Index renamed: `idx_users_external_id` (column type changed)
```

Pattern flips and lookup churn are the two changes the code updater handles separately (pattern flip = whole-module regen; lookup churn = per-method splice).

### Section: Migrations Changes

The append-only deltas. Drives **new file creation** at `db/migrations/<id>_<slug>.yaml`.

```markdown
## Migrations Changes

### Appended
- `0007 Add Column users.email` (pattern: `Add Column`)
  - Source delta: `aggregates: User attribute email added`
  - Target file: `db/migrations/0007_add_column_users_email.yaml`
- `0008 Add Index idx_users_email` (pattern: `Add Index`)
  - Source delta: `repositories-services: User finder user_of_email added`
  - Target file: `db/migrations/0008_add_index_idx_users_email.yaml`
- `0009 ⚠ Drop Column users.legacy_field` (pattern: `Drop Column`)
  - Source delta: `aggregates: User attribute legacy_field removed`
  - Target file: `db/migrations/0009_drop_column_users_legacy_field.yaml`
  - Destructive: yes

### Removed
_(always empty — migrations log is append-only)_
```

Existing YAML files are immutable; the code updater never touches them. The `Removed` bucket is rendered but always empty — kept for symmetry with the other sections.

### Section: Context Integration Changes

Drives the per-context `unit_of_work/` and `query_context/` package edits.

```markdown
## Context Integration Changes

- Bounded-context name: `inventory` → `warehouse`
- Unit of Work class names: `InventoryUnitOfWork` → `WarehouseUnitOfWork`, `AbstractInventoryUnitOfWork` → `AbstractWarehouseUnitOfWork`
- Query Context class names: `InventoryQueryContext` → `WarehouseQueryContext`, `AbstractInventoryQueryContext` → `AbstractWarehouseQueryContext`
- New aggregate wired in: `Order` (added repository attribute on UoW + QueryContext)
- Aggregate de-wired: _none_
```

If no rename and no aggregate add/remove, the section is `_no changes_`.

This is the only section whose changes can ripple into modules **owned by another aggregate's package** (the per-context UoW and QueryContext are shared). The code updater handles this carefully — see *Cross-aggregate edits* below.

### Section: Affected Artifacts

A flat dispatch table. The code updater walks this footer top-to-bottom.

```markdown
## Affected Artifacts

| Path | Action | Driving section |
|---|---|---|
| `tables/users.py` | modify | Tables Changes (Modified) |
| `tables/users_address.py` | add | Tables Changes (Added) |
| `tables/users_legacy_profile.py` | remove | Tables Changes (Removed) |
| `tables/__init__.py` | modify | Tables Changes (any) |
| `mappers/user_mapper.py` | modify | Mappers Changes (Modified) |
| `mappers/address_mapper.py` | add | Mappers Changes (Added) |
| `mappers/legacy_profile_mapper.py` | remove | Mappers Changes (Removed) |
| `mappers/__init__.py` | modify | Mappers Changes (any) |
| `command_user_repository.py` | modify | Repository Changes |
| `query_user_repository.py` | modify | Repository Changes |
| `db/migrations/0007_add_column_users_email.yaml` | add | Migrations Changes |
| `db/migrations/0008_add_index_idx_users_email.yaml` | add | Migrations Changes |
| `db/migrations/0009_drop_column_users_legacy_field.yaml` | add | Migrations Changes |
| `db/migrations/master.yaml` | modify | Migrations Changes (any) |
| `<context>/unit_of_work/abstract.py` | modify | Context Integration Changes |
| `<context>/unit_of_work/sqlalchemy.py` | modify | Context Integration Changes |
| `<context>/query_context/abstract.py` | modify | Context Integration Changes |
| `<context>/query_context/sqlalchemy.py` | modify | Context Integration Changes |
| `tests/integration/conftest.py` | modify | Tables/Mappers/Repository Changes |
| `tests/integration/test_user_repository.py` | modify | Tables/Mappers/Repository Changes |
```

Action vocabulary is closed: `add`, `modify`, `remove`. (`unchanged` files are not listed — the table only contains files the code updater must touch.)

This footer is the persistence analog of the domain `## Affected Categories` footer. It serves the same purpose: a flat, machine-parseable dispatch list.

---

## Per-section → code-action mapping

Quick-reference matrix the code updater dispatches against:

| Report section | Drives | Action verbs |
|---|---|---|
| Aggregate Analysis Changes | Cascade — flips downstream sections; no direct file edit | — |
| Tables Changes — Added | New `tables/<table>.py`; entry in `tables/__init__.py` | add, modify (init) |
| Tables Changes — Removed | Delete `tables/<table>.py`; prune `tables/__init__.py` | remove, modify (init) |
| Tables Changes — Modified | Edit Column/Index/FK lists in `tables/<table>.py` | modify |
| Tables Changes — Pattern flipped | Rewrite `tables/<table>.py` body wholesale (different template variant) | modify |
| Mappers Changes — Added | New `mappers/<x>_mapper.py`; entry in `mappers/__init__.py` | add, modify (init) |
| Mappers Changes — Removed | Delete `mappers/<x>_mapper.py`; prune `mappers/__init__.py` | remove, modify (init) |
| Mappers Changes — Variant flipped | Rewrite mapper body wholesale (new template variant) | modify |
| Mappers Changes — Payload columns changed | Edit payload-column references in mapper body | modify |
| Repository Changes — Pattern flipped | Rewrite `command_<aggregate>_repository.py` wholesale | modify |
| Repository Changes — Alt Lookups added/removed | Add/remove finder methods in command + query repos | modify |
| Migrations Changes — Appended | Scaffold new YAML at `db/migrations/<id>_<slug>.yaml`; append entry in `master.yaml` | add, modify (master) |
| Context Integration Changes — Aggregate added | Wire repository attribute into `<context>/unit_of_work/*.py` and `<context>/query_context/*.py` | modify |
| Context Integration Changes — Aggregate removed | De-wire repository attribute | modify |
| Context Integration Changes — Class renamed | Rewrite class declarations + import sites | modify |

The code updater dispatches on `(section, action verb)` to pick the right agent or template.

---

## Worked example

Domain change: add `email` field to `User` aggregate root and add `user_of_email(email: str)` finder to `UserRepository`. Single-aggregate, no children, single-tenant — a typical small change.

`<stem>.persistence/updates.md`:

```markdown
# Persistence Updates Report

## Summary

- Spec: dir/user.persistence/command-repo-spec.md
- Pre-update spec hash: a1b2c3...
- Post-update spec hash: d4e5f6...
- Domain updates source: dir/user.domain/updates.md (hash: 7890ab...)
- Generated at: 2026-05-08T14:32:01Z
- Warnings: _none_

## Aggregate Analysis Changes
_no changes_

## Tables Changes

### Modified
- `users`
  - Columns added: `email: String NOT NULL`
  - Indexes added: `idx_users_email` (column: `email`)

## Mappers Changes

### Modified
- `UserMapper`
  - Payload columns changed: `email` added

## Repository Changes

- Alternative Lookups added:
  - `user_of_email(email: str)` — index: `idx_users_email`

## Migrations Changes

### Appended
- `0007 Add Column users.email` (pattern: `Add Column`)
  - Source delta: `aggregates: User attribute email added`
  - Target file: `db/migrations/0007_add_column_users_email.yaml`
- `0008 Add Index idx_users_email` (pattern: `Add Index`)
  - Source delta: `repositories-services: User finder user_of_email added`
  - Target file: `db/migrations/0008_add_index_idx_users_email.yaml`

### Removed
_(always empty — migrations log is append-only)_

## Context Integration Changes
_no changes_

## Affected Artifacts

| Path | Action | Driving section |
|---|---|---|
| `tables/users.py` | modify | Tables Changes (Modified) |
| `mappers/user_mapper.py` | modify | Mappers Changes (Modified) |
| `command_user_repository.py` | modify | Repository Changes |
| `query_user_repository.py` | modify | Repository Changes |
| `db/migrations/0007_add_column_users_email.yaml` | add | Migrations Changes |
| `db/migrations/0008_add_index_idx_users_email.yaml` | add | Migrations Changes |
| `db/migrations/master.yaml` | modify | Migrations Changes |
| `tests/integration/conftest.py` | modify | Tables/Mappers/Repository Changes |
| `tests/integration/test_user_repository.py` | modify | Tables/Mappers/Repository Changes |
```

The code updater walks the footer, dispatches each row, and produces the on-disk edits.

---

## Determinism and idempotency

- **Byte-stable inputs → byte-stable report.** Same domain `updates.md` content + same pre-update spec → byte-identical report.
- **Re-running `/persistence-spec:update-specs` with no new domain changes** produces a report whose every section is `_no changes_` and whose Affected Artifacts table is empty. The code updater treats an empty report as a no-op.
- **Section ordering is canonical** (Summary → Aggregate Analysis → Tables → Mappers → Repository → Migrations → Context Integration → Affected Artifacts).
- **Within each section**, items are ordered: Added (alphabetical) → Removed (alphabetical) → Modified (alphabetical). Migrations preserve the appended-row order (chronological by ID, not alphabetical).

---

## Cross-aggregate edits

The Context Integration section is the one place where this report can imply edits to files **owned by another aggregate's persistence package** — specifically `<context>/unit_of_work/*.py` and `<context>/query_context/*.py`, which are shared per-context.

The code updater handles this by:

- Treating UoW and QueryContext modules as **patch targets**, not regen targets — only the lines pertaining to the current aggregate's repository attribute are touched.
- Idempotency on these files is load-bearing: running the code updater twice on the same report produces no incremental change.

This mirrors the spec-side `unit-of-work-integrator` and `query-context-integrator` agents' contracts (see `persistence-spec:unit-of-work-integrator` description).

---

## What the report deliberately does NOT include

- **Source domain class names.** The report describes spec-level deltas in terms of tables, mappers, columns. The domain `updates.md` is the trail back to class-level deltas; readers needing that follow the upstream report.
- **Code-level diffs or generated source text.** The report says **what** to change; the code updater owns **how** (template variants, splicer logic).
- **YAML migration content.** Migrations Changes records the changeset summary and pattern; the YAML body is owned by the migration template (`persistence-spec:migration`) and produced by the code updater's `migrations-implementer`.
- **Test-level granularity.** Test files are listed in Affected Artifacts as modify; the code updater (and its companion test-splicer) decides per-fixture / per-test surgery from the spec, not from this report. This mirrors the domain code updater's approach.
- **Hand-edit reconciliation hints.** Hand-edits in generated artifacts are not preserved (per the spec updater contract). The code updater can flag divergence but the report doesn't pre-classify it.
- **Stable-throughput artifacts** (e.g. `serializers/`, `entrypoint.py`) — those belong to other layers and are not persistence concerns.

---

## Hard-fail conditions

The report is not produced (the run hard-fails before reaching the emit step) when:

- The spec updater itself hard-fails (root removal, root stereotype change, repository-interface lifecycle change, degraded baseline). See `spec-updater-approaches.md` § "Hard-fail conditions".
- The pre-update spec is missing or unparseable.
- The post-update spec hash cannot be computed (filesystem error).

In all other cases the report is emitted, even if every section is `_no changes_`.

---

## Open questions

1. **Granularity of Tables Changes for column-level changes.** Current design lists each column delta inline. For very wide tables, this could be verbose. Consider a compact form (`columns: +email +phone -legacy_field ~name`) for terse output. Trade-off: machine-parseability vs. human readability.

2. **Sentinel for re-run detection.** The spec updater uses an HTML-comment sentinel inside §2.Migrations to skip re-emitting the same delta (`<!-- appended-from updates-hash:<hash> -->`). The report should carry a separate sentinel (its own `domain-updates-hash:<hash>`) so a code updater can detect "I already applied this report" and skip. Likely placement: top of the file as an HTML comment.

3. **Multi-update batching.** If the operator runs `/persistence-spec:update-specs` N times before catching up with `/persistence-spec:update-code`, do we stack N reports or merge them? Stacking preserves audit trail; merging is cleaner for the consumer.
   - Recommended: each `update-specs` run writes a fresh `updates.md` *replacing* the prior one, but if the prior report's `domain-updates-hash` is still present in the spec's migrations sentinel chain, fold its Affected Artifacts into the new report so nothing is dropped.
   - Open: whether this folding is part of the producer's contract or the consumer's.

4. **Side-effect vs separate skill — resolved for v1.** The producer is a dedicated `command-repo-spec-updates-writer` agent invoked at Step 5 of `/persistence-spec:update-specs` (see *Producer architecture* above), with the schema captured in the auto-loaded `persistence-spec:updates-report-template` skill. The original concern — that splitting the spec updater into per-section fan-out agents would make a stand-alone post-pass detector cleaner — remains as a v2+ consideration if that pressure appears.

5. **Schema-section inclusion.** §3 of the spec has its own ER diagram + per-table column lists. An earlier draft of this report had a separate "Schema Changes" section keyed off §3. It was dropped because every §3 column delta also shows up in Tables Changes (driven by §2.Tables + §3 in lockstep). If we ever decouple the two — e.g. an ER diagram that captures cross-table relationships not visible in Tables Changes — re-add the section. Today: don't.

6. **Concurrent updaters.** If two operators run `/persistence-spec:update-specs` in parallel against the same spec, both write `updates.md`. This is a Git merge conflict on a generated file — same shape as the spec-side concurrent-updater problem. Document as expected behaviour, no code support needed.

---

## Relationship to the domain updates report

| Aspect | Domain | Persistence |
|---|---|---|
| File path | `<dir>/<stem>.domain/updates.md` | `<dir>/<stem>.persistence/updates.md` |
| Sibling of | the diagram | the command-repo-spec |
| Producer | `domain-spec:updates-detector` (standalone agent) | `/persistence-spec:update-specs` (side-effect) |
| Producer detection method | git diff of diagram + prose | known by producer (already has the deltas) |
| Grouping | per-class | per-artifact |
| Footer | `## Affected Categories` (DDD categories) | `## Affected Artifacts` (file paths + action verbs) |
| Consumed by | spec updaters (domain, persistence, application, …) **and** domain code updater | persistence code updater (only) |
| Lifecycle | persistent (committed) | persistent (committed) |
| First-run | not produced | not produced |
| Hard-fails preempt emit | yes | yes |

The two reports are **chained**: domain `updates.md` drives the persistence spec updater, which produces persistence `updates.md`, which drives the persistence code updater. Each report is the input contract of the downstream skill in its lane:

```
diagram edit
   │
   ▼
domain-spec:updates-detector
   │
   ▼
<stem>.domain/updates.md ────┬──► /update-specs (domain) ────► spec siblings
                             │
                             └──► /persistence-spec:update-specs ──► <stem>.persistence/command-repo-spec.md
                                                                  └──► <stem>.persistence/updates.md
                                                                          │
                                                                          ▼
                                                                  /persistence-spec:update-code ──► tables/, mappers/, migrations/, repos
```

When `application-spec` and `rest-api-spec` updaters land, each layer follows the same shape: a layer-specific `updates.md` is emitted by the spec updater for that layer and consumed by the code updater for the same layer.
