# Application Updates Report — Design

This note describes the design of `<dir>/<stem>.application/updates.md`, the **application-side analog of the domain and persistence updates reports**.

It is the input contract a future `/application-spec:update-code` skill will consume to surgically update generated application artifacts (the `<aggregate>_commands.py` / `<aggregate>_queries.py` modules, application-layer exception classes, infrastructure stubs, DI providers, conftest fixtures, integration tests) without re-running `/application-spec:generate-code` from scratch — analogous to how `domain-spec:update-code` consumes the domain `updates.md` and the future `/persistence-spec:update-code` consumes the persistence `updates.md`.

For the catalog of *upstream* domain deltas that drive the application spec updater, see [`update-types.md`](update-types.md).
For the spec updater design that produces the artifacts this report captures, see [`spec-updater-approach.md`](spec-updater-approach.md).
For the persistence-side counterpart this design is modelled on, see [`plugins/persistence-spec/notes/updates-report.md`](../../persistence-spec/notes/updates-report.md).

---

## Goal

Capture, in structured form, every change `/application-spec:update-specs` made to the application-spec siblings inside `<stem>.application/`, in a shape that lets a downstream code updater dispatch per-artifact updates without re-diffing the specs.

The report:

- Is **persistent** (committed alongside the specs) so it survives between `update-specs` and `update-code`.
- Is **per-artifact** rather than per-domain-class: it lists *which generated files change* (and how), not which domain classes changed. The domain `updates.md` already covers per-class deltas; this report's job is to project them onto application artifacts.
- Is **stable** between identical inputs — same domain `updates.md` hash + same pre-update specs → byte-identical report.
- Is **self-contained** for the code updater: combined with the updated specs, it has everything needed to compute the on-disk edits.

---

## Lifecycle and ownership

### Producer

`<stem>.application/updates.md` is produced by `/application-spec:update-specs` as **Step 6** of the orchestrator workflow (see [`spec-updater-approach.md`](spec-updater-approach.md) § Step 6). Emitted in the same run that rewrites the specs.

The architecture mirrors the persistence-side asymmetry: unlike the domain side where `domain-spec:updates-detector` runs **before** the spec updater (the diagram is human-edited and must be diffed to recover the operator's intent), the application specs are *generated* — the writer detects changes by diffing the working tree against `git HEAD`, requiring no separately-maintained pre-update snapshot.

| Aspect | Domain | Persistence | Application |
|---|---|---|---|
| Source of truth | Mermaid diagram (human-edited) | command-repo-spec (generated) | `commands.specs.md` + `queries.specs.md` + `services.md` (all generated) |
| Detection | git diff of diagram + prose | git diff of working-tree spec vs HEAD | git diff of working-tree specs vs HEAD |
| Re-diffing | unavoidable | tractable; producer already has deltas | tractable; producer already has deltas |

#### Alternative considered: standalone `application-spec:updates-detector`

A standalone detector would `git diff` the specs before/after and emit the report independently of `update-specs`. Rejected because:

- The spec updater already runs an LLM pass over the regenerated content — adding a separate diff agent duplicates work.
- The specs are generated, not curated; there is no operator-intent hidden in the spec text that a detector would need to surface beyond the structural diff.
- The lifetime mirror between "produce specs" and "describe what changed" is cleaner when both are owned by the same orchestrator step.

The closer mirror to the domain side is tempting but doesn't pay for itself.

### Consumer

`<stem>.application/updates.md` is consumed by the future `/application-spec:update-code` skill — an analog of `domain-spec:update-code` and the future `/persistence-spec:update-code`. The code updater walks the report's `## Affected Artifacts` footer to dispatch per-file updates, reading the per-section bodies for the structured delta details.

It is **not** chained automatically into `/update-specs` (domain). Code regeneration is a separate operator-driven step: spec updates on every diagram edit; code updates on demand.

### First-run pipeline

`/application-spec:generate-specs` does **not** produce this report. The report describes deltas, not absolute state. On first run, `/application-spec:generate-code` runs against the specs directly with no report to consult.

---

## Producer architecture

The producer is split into two artifacts that mirror the persistence-side `updates-report-template` skill + `command-repo-spec-updates-writer` agent pair:

### Reference skill: `application-spec:updates-report-template`

A condensed *contract* document — schema + rendering rules, not design rationale — auto-loaded by:

- The producer agent (when rendering the report).
- The future `/application-spec:update-code` consumer (when parsing the report).

Covers:

- Top-level section order (Summary → Commands Methods Changes → Queries Methods Changes → Application Exceptions Changes → Services Changes → Affected Artifacts).
- Per-section body conventions (Added / Removed / Modified buckets; closed action-verb vocabulary `add | modify | remove`; `_no changes_` rendering for empty sections).
- Within-section ordering rules (alphabetical by name on every bucket — application-spec has no append-only history).
- Affected Artifacts table shape (path + action + driving-section columns).
- Sentinel placement (HTML comment recording the source domain `updates.md` hash, used by the consumer for skip-on-replay detection).

The split between schema-as-skill and design-as-notes is the same one the domain and persistence sides draw — the *why* lives here in the notes; the *how to render and parse* lives in the skill.

### Agent: `application-updates-writer`

A small, deterministic agent invoked at the tail of `/application-spec:update-specs` — also standalone-invocable. Composes `<stem>.application/updates.md` by diffing the working-tree specs against `git HEAD`; reads the sibling domain `updates.md` only as an enrichment source for `Source delta` lookups. Does not consult any orchestrator-supplied runtime state.

The workflow shape mirrors `command-repo-spec-updates-writer` exactly: takes a single positional arg, recovers the pre-update baselines via `git show HEAD:<file>`, writes a sibling report. The application side is structurally simpler than persistence (no migrations-log row diffing, no destructive-change flagging), so the schema is fully mechanical with no LLM-creative step (no prose summarization).

**Arguments**:

- `<domain_diagram>` — first and only positional arg. Used solely to recover `<dir>` and `<stem>` per `application-spec:naming-conventions`. The diagram itself is not parsed.

**Reads (filesystem)**:

1. **Working-tree specs** —
   - `<dir>/<stem>.application/commands.specs.md` (must exist; otherwise hard-fail with "run `/application-spec:generate-specs` first").
   - `<dir>/<stem>.application/queries.specs.md` (must exist; same fail-mode).
   - `<dir>/<stem>.application/services.md` (must exist; same fail-mode).
2. **HEAD specs** — recovered via `git ls-files --full-name` + `git show HEAD:<repo_path>` for each of the three files. First-run handling: missing-at-HEAD → empty baseline; the entire post-update spec is reported as Added.
3. **Domain updates report** — `<dir>/<stem>.domain/updates.md` (sibling). Missing is non-fatal; `Source delta` falls back to `(unknown source)` and the Summary's domain-source line renders `_none_`.

**Reads (auto-loaded skills)**: `application-spec:naming-conventions`, `application-spec:updates-report-template`.

**Output**: `<dir>/<stem>.application/updates.md`, written from scratch (replaces any prior file).

**Determinism**: structured-input-driven, not LLM-creative. Re-running with byte-identical inputs (working tree + HEAD blobs + domain `updates.md`) produces a byte-identical report. The Affected Artifacts table is mechanically derived from the per-section deltas (Commands Methods Changes → `<aggregate>_commands.py` + integration test; Queries Methods Changes → `<aggregate>_queries.py` + integration test; Application Exceptions Changes → `domain/<aggregate>/exceptions.py`; Services Changes → per-service infrastructure stubs + `containers.py` + conftest).

**Standalone invocability**: supported. The writer reads everything it needs from disk (working tree + git HEAD + sibling files), so it does not require an orchestrator wrapper. Useful for testing, operator-driven recovery (e.g. when a prior `update-specs` run hard-failed mid-Step-2), and CI verification. The orchestrator (`/application-spec:update-specs`) is one of several callers.

### Workflow integration

Slots into `/application-spec:update-specs` as Step 6 (see [`spec-updater-approach.md`](spec-updater-approach.md) for the full pipeline):

```
Step 0  Preflight (file presence + parse updates.md)
Step 1  Dispatch tier
Step 2  Per-side regen (writers, parallel)
Step 3  application-exceptions-specifier
Step 4  specs-merger (per dirty side, parallel)
Step 5  services-finder
Step 6  Emit updates.md  (application-updates-writer)        ← this artifact
Step 7  Report (operator one-liner)
```

The orchestrator does not need to capture pre-update spec content — the writer recovers it directly via `git show HEAD:<spec_file>` for all three input files. This keeps the orchestrator stateless and lets the writer also run standalone.

The writer runs on every successful spec update, including Tier 4 no-op early-exit cases — those produce a report with every section `_no changes_` and an empty Affected Artifacts table. This keeps the consumer's contract simple: `updates.md` always exists after a successful run. The writer does **not** run when the workflow hard-fails before Step 6 — there is no transition to describe.

---

## File location and naming

```
<dir>/<stem>.application/
├── commands.specs.md           (commands-side spec)
├── queries.specs.md            (queries-side spec)
├── services.md                 (services report)
└── updates.md                  (this report)
```

Mirrors the domain and persistence conventions: `<dir>/<stem>.domain/updates.md` sits next to the domain spec siblings; `<dir>/<stem>.persistence/updates.md` sits next to `command-repo-spec.md`.

Per `application-spec:naming-conventions`, this file is added to the application-spec sibling-folder catalog as a new durable artifact alongside `commands.specs.md`, `queries.specs.md`, `commands.exceptions.md`, `queries.exceptions.md`, and `services.md`.

---

## Report schema

Top-level structure (canonical section order):

```markdown
# Application Updates Report

<!-- domain-updates-hash: <sha256> -->

## Summary
## Commands Methods Changes
## Queries Methods Changes
## Application Exceptions Changes
## Services Changes
## Affected Artifacts
```

Each section's body is either a structured delta block or `_no changes_`. Sections never disappear — empty sections render as `_no changes_` so the parser doesn't have to discriminate "absent" vs "no-op".

The `<!-- domain-updates-hash: <sha256> -->` sentinel at the top records the content hash of `<stem>.domain/updates.md` at production time. The future code-updater uses it for skip-on-replay detection: re-applying an already-applied report is a no-op.

### Section: Summary

A small preamble. Mirrors the persistence and domain reports' Summary blocks.

```markdown
## Summary

- Aggregate stem: `user`
- Pre-update specs:
  - `commands.specs.md` hash: <sha256 before this run>
  - `queries.specs.md` hash: <sha256 before this run>
  - `services.md` hash: <sha256 before this run>
- Post-update specs:
  - `commands.specs.md` hash: <sha256 after this run>
  - `queries.specs.md` hash: <sha256 after this run>
  - `services.md` hash: <sha256 after this run>
- Domain updates source: `dir/user.domain/updates.md` (hash: <sha256>)
- Generated at: 2026-05-08T14:32:01Z
- Warnings:
  - Method `update_email` removed but the corresponding test in `tests/integration/user/test_user_commands.py` is left orphaned (append-only test implementer).
```

The pre/post hashes pin the report to a specific transition; the code updater verifies the post-update hashes match the on-disk specs before consuming the report (defends against operator running `update-code` after a stale report).

### Section: Commands Methods Changes

Per `### Method:` block grouping, scoped to `commands.specs.md`. Drives `application/<aggregate>/<aggregate>_commands.py`.

```markdown
## Commands Methods Changes

### Added
- `register_user(email: str, name: str) -> User`
  - Source delta: `aggregates: User method new_with_email added`
  - Aggregate call: `User.new_with_email(email, name)` (factory shape)
  - Load step: _none_ (factory)
  - Collaborators: _none_
  - Raises: `UserAlreadyExistsError` (when `user_repository.user_of_email(email)` finds an existing user)

### Removed
- `update_legacy_field(user_id: UUID, legacy_field: str)`

### Modified
- `update_user_email(user_id: UUID, email: str) -> User`
  - Source delta: `repositories-services: CommandUserRepository finder user_of_email added`
  - Sub-sections changed:
    - Method Flow: load step finder switched from `user_of_id(user_id)` to `user_of_id_and_email(user_id, email)`
    - Postconditions: postcondition prose updated to mention overwritten `email` value object
  - Aggregate call: unchanged (`user.update_email(email)`)
  - Raises: unchanged
```

Sub-section vocabulary inside Modified is closed: `Purpose`, `Requires Aggregate State`, `Method Flow`, `Postconditions`. Each Modified entry lists only the sub-sections that actually changed (skipping byte-stable ones).

### Section: Queries Methods Changes

Per `### Method:` block grouping, scoped to `queries.specs.md`. Drives `application/<aggregate>/<aggregate>_queries.py`.

```markdown
## Queries Methods Changes

### Added
- `users_by_email_domain(domain: str) -> ResultSet[UserSummary]`
  - Source delta: `repositories-services: QueryUserRepository finder users_by_email_domain added`
  - Repository call: `query_user_repository.users_by_email_domain(domain)` (same-name)
  - External-Interface shape: no
  - Returns: `ResultSet[UserSummary]` (TypedDict from queries diagram)

### Removed
_no changes_

### Modified
- `user_summary(user_id: UUID) -> UserSummary`
  - Source delta: `data-structures: UserSummary field bio added`
  - Sub-sections changed:
    - Returns: shape-hint prose updated to mention new `bio` field
  - Repository call: unchanged
```

Sub-section vocabulary inside Modified: `Purpose`, `Method Flow`, `Returns`. (Queries methods have no `Requires Aggregate State` or `Postconditions` sub-sections.)

### Section: Application Exceptions Changes

Unified across both sides. Lists exception classes added/removed/modified across the merged `## Application Exceptions` sections of `commands.specs.md` and `queries.specs.md`. Drives `domain/<aggregate>/exceptions.py` (where the application-spec exception classes are emitted by `application-spec:exceptions-implementer`).

```markdown
## Application Exceptions Changes

### Added
- `UserAlreadyExistsError`
  - Side(s): commands
  - Source delta: `repositories-services: CommandUserRepository finder user_of_email added` (drives the new pair-derived exception)
  - Base: `AlreadyExistsError`
  - Code: `USER_ALREADY_EXISTS`
  - Constructor: `__init__(email: str)`
  - Message pattern: `"A user with email {email} already exists"`

### Removed
- `LegacyFieldNotFoundError`
  - Side(s): commands
  - Source delta: `aggregates: User method update_legacy_field removed`

### Modified
- `UserNotFoundError`
  - Side(s): commands, queries
  - Source delta: `repositories-services: CommandUserRepository finder user_of_id_and_email added`
  - Constructor changed: `__init__(user_id: UUID)` → `__init__(user_id: UUID, email: str)` (pair-derived from finder args)
  - Message pattern updated to include `{email}`
```

Each exception lists the side(s) that raise it (`commands`, `queries`, or both). An exception that appears in both `commands.specs.md` and `queries.specs.md` renders as a single entry, since the pair-derivation rule produces byte-identical specs across sides.

### Section: Services Changes

Tracks deltas to `services.md`. Drives multiple files (interface module, infrastructure stub, fake test module, `containers.py`, conftest).

```markdown
## Services Changes

### Added
- `EmailService`
  - Classification: External Interface
  - Interfaces: `ICanSendEmail`
  - Consumers: `UserCommands.register_user`
  - Source delta: `repositories-services: <<Service>> EmailService added (referenced by user.commands.md)`

### Removed
- `LegacyAuditService`
  - Classification: Domain Service
  - Source delta: `repositories-services: <<Service>> LegacyAuditService removed`

### Modified
- `SubjectDetection`
  - Sub-sections changed:
    - Consumers: added `UserCommands.register_user`
  - Source delta: `commands diagram: UserCommands --() SubjectDetection : uses` (this is an app-diagram-axis change, surfaces here only when the orchestrator runs against a pre-reconciled commands diagram)
```

Classification vocabulary matches `services-finder`'s output: `Domain Service` | `External Interface`.

### Section: Affected Artifacts

A flat dispatch table. The code updater walks this footer top-to-bottom.

```markdown
## Affected Artifacts

| Path | Action | Driving section |
|---|---|---|
| `application/user/user_commands.py` | modify | Commands Methods Changes (any) |
| `application/user/user_queries.py` | modify | Queries Methods Changes (any) |
| `domain/user/exceptions.py` | modify | Application Exceptions Changes (any) |
| `application/auth/email_service.py` | add | Services Changes (Added) |
| `infrastructure/services/email/email_service.py` | add | Services Changes (Added) |
| `infrastructure/services/email/__init__.py` | modify | Services Changes (Added) |
| `tests/fakes/fake_email_service.py` | add | Services Changes (Added) |
| `application/auth/legacy_audit_service.py` | remove | Services Changes (Removed) |
| `infrastructure/services/audit/legacy_audit_service.py` | remove | Services Changes (Removed) |
| `tests/fakes/fake_legacy_audit_service.py` | remove | Services Changes (Removed) |
| `containers.py` | modify | Services Changes (any) |
| `tests/conftest.py` | modify | Services Changes (any) |
| `tests/integration/user/test_user_commands.py` | modify | Commands Methods Changes (any) |
| `tests/integration/user/test_user_queries.py` | modify | Queries Methods Changes (any) |
```

Action vocabulary is closed: `add`, `modify`, `remove`. (`unchanged` files are not listed — the table only contains files the code updater must touch.)

This footer is the application analog of the persistence `## Affected Artifacts` and the domain `## Affected Categories` footers. It serves the same purpose: a flat, machine-parseable dispatch list.

---

## Per-section → code-action mapping

Quick-reference matrix the code updater dispatches against:

| Report section | Drives | Action verbs |
|---|---|---|
| Commands Methods Changes — Added | Add new method body to `<aggregate>_commands.py` (signature from spec; flow from Method Flow); add new test scenarios to `test_<aggregate>_commands.py` | modify |
| Commands Methods Changes — Removed | Remove method body from `<aggregate>_commands.py`; *flag* matching test for orphan-cleanup (warning, not removal — the existing tests-implementer is append-only) | modify |
| Commands Methods Changes — Modified — `Method Flow` | Rewrite method body (load step, aggregate call, collaborator calls, raise lines) | modify |
| Commands Methods Changes — Modified — `Postconditions` / `Purpose` / `Requires Aggregate State` | Spec-only changes; no production-code edit; tests may need a content review (warning) | — *(spec-side only; no `Affected Artifacts` row emitted unless paired with a Method Flow change)* |
| Queries Methods Changes — Added | Add new method body to `<aggregate>_queries.py`; add new test scenarios | modify |
| Queries Methods Changes — Removed | Remove method body; flag orphan tests | modify |
| Queries Methods Changes — Modified — `Method Flow` | Rewrite method body (repo call, return shape) | modify |
| Queries Methods Changes — Modified — `Returns` / `Purpose` | Spec-only; no production-code edit | — |
| Application Exceptions Changes — Added | Append exception class to `domain/<aggregate>/exceptions.py` | modify |
| Application Exceptions Changes — Removed | Remove exception class from `domain/<aggregate>/exceptions.py`; flag any remaining `raise <X>Error` references (should be none if the methods writer is consistent) | modify |
| Application Exceptions Changes — Modified | Replace exception class body in `domain/<aggregate>/exceptions.py` | modify |
| Services Changes — Added | New interface module under `application/<package>/`; new infrastructure stub under `infrastructure/services/<package>/`; new fake under `tests/fakes/`; register provider in `containers.py`; add autouse fake fixture in `tests/conftest.py` | add (new files), modify (containers, conftest) |
| Services Changes — Removed | Mirror — delete files, prune containers + conftest entries | remove (files), modify (containers, conftest) |
| Services Changes — Modified — `Consumers` | Update wiring on the consuming application service's provider in `containers.py` | modify (containers) |

The code updater dispatches on `(section, action verb, sub-section)` to pick the right edit. Spec-only sub-section changes (`Purpose`, `Returns` prose, `Postconditions` prose without a `Method Flow` change) deliberately produce **no** `Affected Artifacts` row — they're recorded in the body for audit trail and review-prompting purposes only.

---

## Worked example

Domain change: add `email: str` field to `User` aggregate root, add `user_of_email(email: str) -> User` finder to `CommandUserRepository`, and add a new `register_user_with_email` factory method on `User`.

Domain `updates.md` Affected Categories: `[aggregates, repositories-services]`.

Application updater Tier 2 fires (commands dirty); Tier 3 does not (queries unaffected).

After Steps 2–5, the orchestrator invokes `application-updates-writer`, which produces:

```markdown
# Application Updates Report

<!-- domain-updates-hash: 7890ab... -->

## Summary

- Aggregate stem: `user`
- Pre-update specs:
  - `commands.specs.md` hash: a1b2c3...
  - `queries.specs.md` hash: 5e6f7a...
  - `services.md` hash: 8b9c0d...
- Post-update specs:
  - `commands.specs.md` hash: d4e5f6...
  - `queries.specs.md` hash: 5e6f7a...   *(unchanged)*
  - `services.md` hash: 8b9c0d...        *(unchanged)*
- Domain updates source: `dir/user.domain/updates.md` (hash: 7890ab...)
- Generated at: 2026-05-08T14:32:01Z
- Warnings: _none_

## Commands Methods Changes

### Added
- `register_user_with_email(email: str, name: str) -> User`
  - Source delta: `aggregates: User method new_with_email added`
  - Aggregate call: `User.new_with_email(email, name)` (factory shape)
  - Load step: _none_ (factory)
  - Collaborators: _none_
  - Raises: `UserAlreadyExistsError` (when `user_repository.user_of_email(email)` finds an existing user)

### Removed
_no changes_

### Modified
- `register_user(name: str) -> User`
  - Source delta: `aggregates: User attribute email added`
  - Sub-sections changed:
    - Postconditions: factory seeded-fields list now includes `email`

## Queries Methods Changes
_no changes_

## Application Exceptions Changes

### Added
- `UserAlreadyExistsError`
  - Side(s): commands
  - Source delta: `repositories-services: CommandUserRepository finder user_of_email added`
  - Base: `AlreadyExistsError`
  - Code: `USER_ALREADY_EXISTS`
  - Constructor: `__init__(email: str)`
  - Message pattern: `"A user with email {email} already exists"`

### Removed
_no changes_

### Modified
_no changes_

## Services Changes
_no changes_

## Affected Artifacts

| Path | Action | Driving section |
|---|---|---|
| `application/user/user_commands.py` | modify | Commands Methods Changes (Added, Modified) |
| `domain/user/exceptions.py` | modify | Application Exceptions Changes (Added) |
| `tests/integration/user/test_user_commands.py` | modify | Commands Methods Changes (Added) |
```

Notice:

- The `register_user` `Modified` entry under Commands Methods Changes records a **Postconditions-only** change. No production-code edit follows — the seeded-fields list is spec prose; the production code's call to `User.new(...)` is unaffected by an attribute addition (the constructor signature change is the *aggregate's* concern, the call's args come from the application method's signature). So the `register_user` change does **not** add a row to `Affected Artifacts`.
- The `register_user_with_email` Added entry **does** add a row (new method body in `user_commands.py`, new test scenarios in `test_user_commands.py`).
- The `queries.specs.md` and `services.md` post-hashes match their pre-hashes — the writer detects these are byte-stable and renders `_no changes_` for those sections.

The code updater walks the footer, dispatches each row, and produces the on-disk edits.

---

## Determinism and idempotency

- **Byte-stable inputs → byte-stable report.** Same domain `updates.md` content + same pre-update specs + same post-update specs → byte-identical report.
- **Re-running `/application-spec:update-specs` with no new domain changes** produces a report whose every section is `_no changes_` and whose Affected Artifacts table is empty. The code updater treats an empty report as a no-op.
- **Section ordering is canonical** (Summary → Commands Methods Changes → Queries Methods Changes → Application Exceptions Changes → Services Changes → Affected Artifacts).
- **Within each section**, items are ordered: Added (alphabetical) → Removed (alphabetical) → Modified (alphabetical). Application-spec has no append-only history, so no chronological exception applies.
- **Modified sub-section ordering** is canonical per side:
  - Commands: `Purpose`, `Requires Aggregate State`, `Method Flow`, `Postconditions`.
  - Queries: `Purpose`, `Method Flow`, `Returns`.

Skip-on-replay detection uses the top-of-file `<!-- domain-updates-hash: <hash> -->` sentinel: a future `/application-spec:update-code` consumer compares the hash to the source domain `updates.md` it would consume; on match, the consumer can skip (configurable). This is informational, not enforced — the consumer also has its own per-artifact idempotency.

---

## Cross-aggregate edits

Two report sections imply edits to files **shared across the application package**, not just per-aggregate files:

- **Application Exceptions Changes** drives edits to `domain/<aggregate>/exceptions.py` — per-aggregate, but the file also holds *domain* exceptions for that aggregate. Application-spec exceptions are appended to it by `application-spec:exceptions-implementer`. The code updater treats exceptions.py as a **patch target** (only application-spec exception class definitions are touched; domain exceptions are preserved verbatim).
- **Services Changes** drives edits to `containers.py` (DI provider registrations) and `tests/conftest.py` (autouse fake fixtures) — both project-wide files shared across all aggregates. The code updater treats both as **patch targets**: only the lines pertaining to the affected service(s) are touched. Idempotency on these files is load-bearing — running the code updater twice on the same report produces no incremental change.

This mirrors the persistence-side `unit-of-work-integrator` and `query-context-integrator` agents' contracts (see `persistence-spec:unit-of-work-integrator` description).

---

## What the report deliberately does NOT include

- **Source domain class names** beyond what's needed for `Source delta` enrichment. The report describes spec-level deltas in terms of methods, exception classes, and services. The domain `updates.md` is the trail back to class-level deltas; readers needing that follow the upstream report.
- **Code-level diffs or generated source text.** The report says **what** to change; the code updater owns **how** (template selection, splicer logic, idempotency).
- **Application service signature changes from the commands/queries diagrams.** Those are the **app-diagram axis** ([`spec-updater-approach.md`](spec-updater-approach.md) § "What this updater does NOT cover"). When that axis is added to `/application-spec:update-specs`, this report's Commands/Queries Methods Changes sections will naturally pick up signature deltas (a method whose signature changed surfaces under Modified with a `Method Flow`-changed sub-section); the schema does not need to grow.
- **Test-level granularity beyond the file path.** Test files are listed in Affected Artifacts as `modify`; the code updater (and its companion test-splicer) decides per-fixture / per-test surgery from the spec, not from this report. Mirrors the domain code updater's approach.
- **Orphan-test cleanup.** When a method is removed, its existing test in `test_<aggregate>_commands.py` becomes orphaned. The current `commands-tests-implementer` is **append-only and signature-driven** — it does not remove tests for removed methods. The report flags this with a Summary-level warning but does not specify the cleanup. Future `/application-spec:update-code` may grow a test-pruner; for v1, manual cleanup.
- **Hand-edit reconciliation hints.** Hand-edits in generated artifacts are not preserved (per the spec updater contract). The code updater can flag divergence but the report doesn't pre-classify it.
- **`## Dependencies` section deltas.** Each `<side>.specs.md`'s `## Dependencies` section is byte-stable on any domain-only update (it's a pure function of the application-service diagram). The report has no `Dependencies Changes` section because every domain-driven run would render it `_no changes_`. When the app-diagram axis is added, a `Dependencies Changes` section becomes meaningful and can be added — the schema is open to that extension.
- **Stable-throughput artifacts** (e.g. `serializers/`, `entrypoint.py`, `api/`, persistence tables/mappers) — those belong to other layers and are not application-spec concerns.

---

## Hard-fail conditions

The report is not produced (the run hard-fails before reaching the emit step) when:

- The spec updater itself hard-fails before Step 6 (Tier 1 conditions 0a–1f, or a Step-2 writer abort). See [`spec-updater-approach.md`](spec-updater-approach.md) § "Hard-fail conditions".
- A pre-update spec is missing or unparseable when invoked standalone.
- A post-update spec hash cannot be computed (filesystem error).

In all other cases the report is emitted, even if every section is `_no changes_`.

---

## Open questions

1. **Granularity of Modified entries inside Commands/Queries Methods Changes.** Current design lists each affected sub-section by name (`Method Flow`, `Postconditions`, etc.) without a within-sub-section delta. For very long method-flow rewrites this is sufficient — the consumer re-reads the post-update spec for the new content. But for spec-prose-only changes (`Postconditions`, `Returns`) it conflates "single-bullet edit" with "wholesale rewrite". A line-count or first-line-of-diff annotation could refine. Trade-off: machine-parseability vs. human readability.

2. **Sub-section ordering inside Modified blocks.** Listed as canonical (Commands: `Purpose`, `Requires Aggregate State`, `Method Flow`, `Postconditions`). Open whether to skip absent sub-sections silently (current proposal) or render them as `_unchanged_` for symmetry. Same trade-off as `_no changes_` for empty top-level sections — current preference is "skip absent" inside Modified blocks because Modified inherently means "only what changed".

3. **Multi-update batching.** If the operator runs `/application-spec:update-specs` N times before catching up with `/application-spec:update-code`, do we stack N reports or merge them?
   - Recommended (mirrors persistence-spec): each `update-specs` run writes a fresh `updates.md` *replacing* the prior one. If the prior report's `domain-updates-hash` is still present (the consumer hasn't acknowledged it via its own sentinel), fold its Affected Artifacts into the new report so nothing is dropped.
   - Open: whether this folding is part of the producer's contract or the consumer's.

4. **Cross-aggregate ripple via `containers.py`.** When aggregate A adds a service that aggregate B's commands service consumes, the report for A includes a `containers.py` modify row, but the change *also* affects B's wiring. Should B's `<stem>.application/updates.md` also note this? Probably not — the cross-aggregate concern lives in `containers.py` and the code updater's idempotent patcher resolves it; per-report duplication would create confusing redundancy. Keep the report scoped to the operator-running aggregate.

5. **Merging signal-level deltas with prose-level edits in Modified.** A method whose `Method Flow` changes typically has cascading prose changes (`Postconditions` mentions the new flow's effects). Right now both surface as separate sub-section bullets. Open: whether to fold prose-only changes that ride alongside a flow change into a single bullet to reduce noise.

6. **Concurrent updaters.** If two operators run `/application-spec:update-specs` in parallel against the same specs, both write `updates.md`. This is a Git merge conflict on a generated file — same shape as the spec-side concurrent-updater problem. Document as expected behaviour, no code support needed.

7. **Worked example for a Services Changes ripple.** The example above doesn't exercise Services Changes because adding a `<<Service>>` is rare on the domain-only axis (it's mostly app-diagram-driven). A second worked example covering the "domain `<<Service>>` added that the commands diagram already references" case would round out the schema's coverage. Defer to the writer agent's own examples or to a test-fixtures section.

8. **Sub-section detection heuristic.** The writer detects which sub-sections of a Modified `### Method:` block changed by structural parsing (split on `**Method Flow:**`, `**Postconditions:**`, etc., from the templates in `application-spec:commands-methods-template`). Open whether to canonicalize sub-section heading shape across all templates so the parser doesn't carry an embedded vocabulary list.

---

## Relationship to the domain and persistence updates reports

| Aspect | Domain | Persistence | Application |
|---|---|---|---|
| File path | `<dir>/<stem>.domain/updates.md` | `<dir>/<stem>.persistence/updates.md` | `<dir>/<stem>.application/updates.md` |
| Sibling of | the diagram | the command-repo-spec | the commands/queries specs + services report |
| Producer | `domain-spec:updates-detector` (standalone agent) | `command-repo-spec-updates-writer` (Step 5 of `/persistence-spec:update-specs`) | `application-updates-writer` (Step 6 of `/application-spec:update-specs`) |
| Producer detection method | git diff of diagram + prose | git diff of working-tree spec vs HEAD | git diff of working-tree specs vs HEAD (three files) |
| Grouping | per-class | per-artifact (tables / mappers / migrations / repository / context-integration) | per-artifact (commands methods / queries methods / exceptions / services) |
| Footer | `## Affected Categories` (DDD categories) | `## Affected Artifacts` (file paths + action verbs) | `## Affected Artifacts` (file paths + action verbs) |
| Consumed by | spec updaters (domain, persistence, application, …) **and** domain code updater | persistence code updater (only) | application code updater (only) |
| Lifecycle | persistent (committed) | persistent (committed) | persistent (committed) |
| First-run | not produced | not produced | not produced |
| Append-only sub-section | — | `§2.Migrations` row IDs | _none_ (every section is a snapshot diff) |
| Hard-fails preempt emit | yes | yes | yes |

The three reports are **chained**: domain `updates.md` drives the persistence and application spec updaters, each of which produces its own layer-specific `updates.md`, which drives that layer's code updater:

```
diagram edit
   │
   ▼
domain-spec:updates-detector
   │
   ▼
<stem>.domain/updates.md ────┬──► /update-specs (domain) ─────► spec siblings
                             │
                             ├──► /persistence-spec:update-specs ──► <stem>.persistence/command-repo-spec.md
                             │                                  └──► <stem>.persistence/updates.md
                             │                                          │
                             │                                          ▼
                             │                                   /persistence-spec:update-code ──► tables/, mappers/, migrations/, repos/
                             │
                             └──► /application-spec:update-specs ──► <stem>.application/{commands,queries}.specs.md + services.md
                                                                  └──► <stem>.application/updates.md
                                                                          │
                                                                          ▼
                                                                   /application-spec:update-code ──► application/, infrastructure/services/, exceptions, containers.py, conftest.py, tests/
```

When `rest-api-spec` and `messaging-spec` updaters land, each layer follows the same shape: a layer-specific `updates.md` is emitted by the spec updater for that layer and consumed by the code updater for the same layer. Each layer's report is **independent** of the others — readers needing cross-layer context follow the chain back to the domain `updates.md`.
