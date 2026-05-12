# Application Spec Updater — Per-Side Regen

This note documents the design of `/application-spec:update-specs`, the surgical update skill for the application-spec siblings inside `<dir>/<stem>.application/`. It is the application-side counterpart to `/persistence-spec:update-specs` and `/domain-spec:update-specs`.

The chosen approach is **per-side snapshot regen** — re-run all the writers for the dirty side(s), reuse the existing exceptions enricher, the per-side merger, and `services-finder`. It is designed to chain from domain `/update-specs` as an opt-in step, but is also independently invocable.

For the catalog of update types and their per-section impact, see the sibling [`update-types.md`](update-types.md).
For the persistence-side counterpart this design is modelled on, see [`plugins/persistence-spec/notes/spec-updater-approaches.md`](../../persistence-spec/notes/spec-updater-approaches.md).
For the domain-side counterpart, see [`plugins/domain-spec/notes/spec-updater-approach-b.md`](../../domain-spec/notes/spec-updater-approach-b.md).

---

## Goal

Keep the application-spec siblings inside `<stem>.application/` aligned with the domain diagram after a domain change, **without re-running `/application-spec:generate-specs` from scratch**. The updater:

- Runs as a chained step at the tail of `/update-specs` (domain), opt-in by file presence (`<stem>.application/commands.specs.md` exists).
- May be invoked standalone for cases where the domain spec is up-to-date but the application spec drifted.
- Consumes the same `<stem>.domain/updates.md` report the domain and persistence updaters consume.
- Never re-diffs the diagram, never invokes `domain-spec:updates-detector` directly.
- Does not preserve hand-edits inside the spec — the operator's contract is that the spec is regenerated from the diagrams, not curated.

The updater handles **only the domain-driven axis**. Changes that originate in `<stem>.commands.md` / `<stem>.queries.md` (the application-service diagrams) are out of scope here — see *What this updater does NOT cover* below.

---

## Inputs

- `<domain_diagram>` — the same first-positional argument every application-spec orchestrator takes, at `<dir>/<stem>.md`.
- `<dir>/<stem>.domain/updates.md` — already on disk (produced by `domain-spec:updates-detector`, either as Step 0 of `/update-specs` or by an explicit prior invocation).
- `<dir>/<stem>.application/commands.specs.md` and `<dir>/<stem>.application/queries.specs.md` — already on disk (produced by an earlier `/application-spec:generate-specs` run); the files the updater modifies in place.

The two hand-authored sibling diagrams (`<stem>.commands.md`, `<stem>.queries.md`) are still consumed by the writers (they're the source of truth for collaborator wiring and method shape) but are **not diffed** by this updater.

If any of the prior-run output files is missing, the updater hard-fails with operator instructions. The updater is **not** the first-run pipeline; `/application-spec:generate-specs` owns first-run.

---

## Output

In place under `<dir>/<stem>.application/`:

- `commands.specs.md` and/or `queries.specs.md` — replaced wholesale (per dirty side).
- `services.md` — re-validated and re-emitted from the freshly merged specs.
- `updates.md` — emitted on every successful run (always, including no-op exits) for a future `/application-spec:update-code` consumer. The schema for this file is out of scope for this note; see *Out-of-scope* below.

The diagram files are untouched; no other plugin's folder is touched; no backup or rollback file is produced.

---

## Architectural insight: snapshot-only, per-side scope

Two structural facts dominate the design.

### Every application-spec section is a snapshot

Unlike persistence-spec, where `§2.Migrations` is an append-only log of cumulative changesets, every section of `commands.specs.md` and `queries.specs.md` is a **pure snapshot** — fully regeneratable from the three diagrams (plus, for `## Application Exceptions`, the method flows the methods writer just produced). There is no migration-log analog, no row-immutability contract, no delta-driven appender.

So the architectural complexity that drove persistence-spec to a hybrid "Snapshot + Log" design does not apply here: every modified section is regenerated from current inputs.

### The two sides are independent

`commands.specs.md` and `queries.specs.md` live in separate files, are produced by separate writer agents, and consume separate hand-authored diagrams. A domain change touches at most:

- **Commands side** — `## Method Specifications` and `## Application Exceptions`. (`## Dependencies` is a pure function of the commands diagram and is byte-stable on any domain-only change.)
- **Queries side** — `## Method Specifications` and `## Application Exceptions`. (`## Dependencies` is a pure function of the queries diagram, similarly byte-stable.)

Per `update-types.md` § "Mapping `affected_categories` → application-spec impact", many domain deltas affect only one side: aggregate-API and `<<Value Object>>` changes are commands-only; query-repo finder and external-interface churn are queries-only. So the natural unit of regen is one side, not the whole pipeline.

### Why per-side, not per-method-block

Three granularities are conceivable:

1. **Whole-pipeline regen** — re-run `/application-spec:generate-specs` end-to-end. Correct, simplest, but produces a noisy `git diff` (regenerates both sides, both exception sets, the services report) for a one-line change.
2. **Per-side regen (chosen)** — re-run only the dirty side's writers + the exceptions enricher + that side's merger + `services-finder`.
3. **Per-method-block splice** — splice only the regenerated `### Method:` blocks into the existing `<side>.specs.md`, leaving untouched method blocks byte-identical.

(2) is the sweet spot:

- The two writers regenerate a whole side's `## Method Specifications` in one pass (they have no "regenerate method X only" mode), so a per-method splicer would need to diff fresh writer output against the live file at `### Method:` granularity — the application-side analog of `spec-updater-approach-b.md` on the domain side. High implementation cost.
- Hand-edits inside the spec are explicitly **not** a preservation goal. The main payoff of per-method splicing — protecting untouched class blocks from regen drift — is what justified Approach B for the domain spec, where the `<stem>.specs.md` carries up to dozens of class blocks. Each application-side `specs.md` carries one `## Method Specifications` section per side; the unit of "untouched content" is much smaller.
- Per-side gives the unaffected side a guaranteed byte-stable diff (its `specs.md` is not touched at all). That's most of the diff-noise win, at zero new agent code.

---

## Pipeline

```
domain updates report ──┐
                        ├─► [0] preflight (orchestrator-owned)
                        │
domain diagram ─────────┤
                        ├─► [1] dispatch tier
                        │
                        ├─► [2] per-side regen (parallel where both sides fire)
                        │       commands-deps-writer + commands-methods-writer  (if commands dirty)
                        │       queries-deps-writer  + queries-methods-writer   (if queries  dirty)
                        │
                        ├─► [3] application-exceptions-specifier
                        │       (auto-skips sides whose .methods.md is absent)
                        │
                        ├─► [4] specs-merger (parallel per dirty side)
                        │       commands  (if commands dirty)
                        │       queries   (if queries  dirty)
                        │
                        ├─► [5] services-finder
                        │       (re-validates against current diagrams)
                        │
                        ├─► [6] emit updates.md
                        │
                        └─► [7] report
```

Steps 0–1 are pure orchestrator-owned parse/checks. Steps 2–6 are agent invocations.

---

## Step 0 — Preflight

Verify inputs exist (each missing input is its own hard-fail with a one-line operator instruction):

| Check | Hard-fail code |
|---|---|
| `<dir>/<stem>.domain/updates.md` exists | 0a |
| `<dir>/<stem>.application/commands.specs.md` exists | 0b |
| `<dir>/<stem>.application/queries.specs.md` exists | 0c |
| `<dir>/<stem>.commands.md` exists | 0d |
| `<dir>/<stem>.queries.md` exists | 0e |

Then parse `updates.md` into a working set:

| Variable | Source |
|---|---|
| `affected_categories: set` | `## Affected Categories` |
| `removed_classes: { name → stereotype }` | `## Class Lifecycle → Removed` |
| `added_classes: { name → stereotype }` | `## Class Lifecycle → Added` |
| `stereotype_changed: { name → (old, new) }` | `## Class Lifecycle → Stereotype Changed` |
| `touched_classes: set` | headings under `## Per-Class Changes` ∪ all of the above |
| `repo_finder_dirty: { command, query }` | true on the matching side iff `Command<AggregateRoot>Repository` / `Query<AggregateRoot>Repository` has a Member added/removed/changed entry |
| `service_method_dirty: bool` | true iff any `<<Service>>` referenced by the commands diagram has a Member changed entry |
| `degraded_baseline: bool` | true iff Summary contains the `_warning: HEAD ..._` line |

---

## Step 1 — Dispatch tier

Apply gates in order; first match wins. The four tiers mirror `update-types.md` § "Dispatch tiers".

### Tier 1 — Hard-fail

Each prints exactly one `ERROR:` line and exits, directing the operator to `/application-spec:generate-specs <domain_diagram>` (after reconciling the commands/queries diagrams where the message says so). Gates evaluated in order:

| Gate | Condition | Reason |
|---|---|---|
| 1a | `degraded_baseline` | Cannot operate against a degraded baseline |
| 1b | `stereotype_changed` non-empty | Cross-category move means the class is no longer the kind of thing the spec assumed; subsumes the aggregate-root case |
| 1c | aggregate-root removed | `<AggregateRoot>Commands` / `<AggregateRoot>Queries` lose their anchor (a rename also moves the diagram filenames — a coordinated multi-file rename the updater can't perform) |
| 1d | `Command<AggregateRoot>Repository` or `Query<AggregateRoot>Repository` interface added or removed | Methods writers abort; a domain aggregate without its repositories cannot back an application service |
| 1e | `Command<AggregateRoot>Repository` loses `save(...)` | `commands-methods-writer` Step 4 aborts |
| 1f | Domain `<<Service>>` removed / stereotype-changed / renamed while still referenced by the commands diagram | `commands-methods-writer` and `services-finder` both abort; route to "reconcile the commands diagram, then re-run" |

For 1f the orchestrator detects the service-class lifecycle from `## Class Lifecycle` and cross-checks against the commands diagram's `--() : uses` edges. If the operator already removed the collaborator edge from the commands diagram, this is a commands-diagram-axis change (out of scope here) — skip the gate.

### Tier 2 — Regen the commands side

Mark `commands_dirty = true` if any of the following hold:

- `affected_categories ∩ {aggregates, value-objects}` is non-empty.
- `repo_finder_dirty.command` is true.
- `service_method_dirty` is true.
- Any P1/P2 prose change keyed to the aggregate root or to a method that resolves to the commands side.
- Any class `C ∈ added_classes ∪ touched_classes` is the aggregate root, an `<<Entity>>` composed by the root, or a `<<Value Object>>` composed by the root or by an entity.

### Tier 3 — Regen the queries side

Mark `queries_dirty = true` if any of the following hold:

- `repo_finder_dirty.query` is true.
- A query-side external-interface operation referenced by a `queries-methods-writer` Step 5a hint is added/removed/renamed (detected from `## Per-Class Changes` on a class whose stereotype is `<<Service>>` and whose name matches an `I<Interface>` the queries diagram references).
- `affected_categories ∩ {data-structures}` non-empty *and* the `<<TypedDict>>`'s field set changed in a way that could affect a `queries-methods-writer` Returns shape-hint clause.
- Any P1/P2 prose change keyed to a method that resolves to the queries side.

### Tier 4 — No-op

If neither side is dirty after the above, the updater:

1. Skips Steps 2–5.
2. Still runs Step 6 (emit `updates.md` with all sections `_no changes_`).
3. Still runs Step 7 (operator one-liner).

Tier 4 fires for any of:

- `affected_categories` empty (per the report-template footer contract this implies no class lifecycle and no per-class changes — only orphan prose, which is byte-neutral for the application spec at this granularity).
- `affected_categories ⊆ {domain-events, commands}` — events and domain commands never appear in the application method specs (the publish/dispatch steps are generic).
- `affected_categories = {repositories-services}` and the only contributor is a `<<Service>>` not referenced by either application diagram.
- A bounded-context `title:` rename in `## Orphan Prose Changes → Preamble` and nothing else — the application spec doesn't consume the domain title.
- A pure prose change that doesn't touch any advisory channel the methods writers consume.

Note: the bullet "the only contributor is a `<<Service>>` not referenced by either application diagram" requires cross-checking class names in `## Per-Class Changes` against `--() : uses` edges in the commands/queries diagrams. The orchestrator does this once during preflight.

Tiers 2 and 3 are not mutually exclusive — a multi-category domain change (`update-types.md` § C4) fans out to both sides.

---

## Step 2 — Per-side regen (parallel where both sides fire)

For each dirty side, fan out the writer agents in parallel.

If `commands_dirty`, emit in one message:

- `application-spec:commands-deps-writer` with prompt `<domain_diagram>`.
- `application-spec:commands-methods-writer` with prompt `<domain_diagram>`.

If `queries_dirty`, emit in the same message (or a sibling message if commands isn't dirty):

- `application-spec:queries-deps-writer` with prompt `<domain_diagram>`.
- `application-spec:queries-methods-writer` with prompt `<domain_diagram>`.

When both sides are dirty, all four writers fan out together in a single message — the same parallel pattern `/application-spec:generate-specs` uses today.

The writers each `mkdir -p` the per-plugin folder and write fresh fragments (`<side>.deps.md`, `<side>.methods.md`, `<side>.exceptions.md` stub) to disk. They do not read the prior `<side>.specs.md` and have no idempotency contract beyond "output is a function of inputs" — re-running on identical diagrams produces byte-identical output modulo LLM nondeterminism.

A side's `## Dependencies` section is byte-stable on any domain-only change (it's a pure function of the application-service diagram). Re-running the deps-writer is therefore an LLM-drift cost we accept rather than a correctness requirement; it is run unconditionally on a dirty side because the merger requires the fragment on disk.

### Abort-and-reconcile

The methods writers may abort with a one-sentence error rather than producing a fragment. The conditions:

- `commands-methods-writer` aborts when an aggregate-root method that a command method resolves to has been renamed/removed (Step 5c match fails), or when the chosen load-step finder has no remaining subset (Step 5d), or when a domain `<<Service>>` referenced by the commands diagram is missing/stereotype-changed (Step 4).
- `queries-methods-writer` aborts when a `Query<AggregateRoot>Repository` finder a query method needs has been renamed/removed (Step 5e same-name match fails), or when an external-interface operation a hint references no longer resolves (Step 5a).

Tier 1 catches the structural cases (1c, 1f). The remaining cases — aggregate-root method renamed/removed under a stable root; query-repo finder renamed under a stable interface; external-interface operation renamed — surface only when the writer runs. The orchestrator detects the abort, prints a single `ERROR:` line with the writer's message, instructs the operator to reconcile the relevant application-service diagram, and exits non-zero. The other side's writers (if launched in parallel) still complete; their outputs are left in place because the orchestrator does not roll back partial writes — see *Failure semantics* below.

---

## Step 3 — Enrich application exceptions

After all Step 2 writers return, invoke `application-spec:application-exceptions-specifier` with prompt `<domain_diagram>`.

The agent processes both sides in one call but auto-skips a side whose `<side>.methods.md` is absent (the agent's existing contract — "A side's `.exceptions.md` is **missing** when the file does not exist or contains no `## Application Exceptions` heading — that side is skipped"). Because Step 2 only writes fragments for the dirty side, the unaffected side's fragments don't exist on disk (deleted by the prior `generate-specs` run's merger), and the enricher leaves the unaffected side's `<side>.specs.md` untouched.

This is the load-bearing reason per-side regen requires no contract change to existing agents — the disk-presence check the enricher already performs is exactly the per-side scoping the updater needs.

---

## Step 4 — Merge fragments per dirty side (parallel)

After the enricher returns, fan out the mergers in parallel for the dirty sides only:

- `application-spec:specs-merger` with prompt `<domain_diagram> commands` (if `commands_dirty`).
- `application-spec:specs-merger` with prompt `<domain_diagram> queries` (if `queries_dirty`).

Each merger consolidates its side's three fragments into `<side>.specs.md` (overwriting the prior file) and deletes the fragments. The unaffected side's `<side>.specs.md` is left byte-identical.

---

## Step 5 — Re-run services-finder

After the merger(s) return, invoke `application-spec:services-finder` with prompt `<domain_diagram>`. It re-reads the freshly merged specs plus the domain diagram and rewrites `services.md`.

This step always runs after Step 4 (regardless of which sides were dirty) because:

- A commands-side regen may add/drop a `## Dependencies → Domain Services` bullet, which changes the services report.
- A queries-side regen may add/drop a `## Dependencies → External Interfaces` bullet on the queries side.
- A domain `<<Service>>` lifecycle change that *was* validated in Tier 1 / Tier 4 may still need the report regenerated to drop / re-include the service.

`services-finder` is a pure function of the merged specs + the domain diagram; re-running it on a stable input is byte-stable modulo LLM drift in prose summaries.

---

## Step 6 — Emit updates.md

Invoke `application-spec:application-updates-writer` (new agent, see *Required artifacts* below) which:

- Recovers the pre-update specs via `git show HEAD:<spec_file>` for both `commands.specs.md` and `queries.specs.md`.
- Reads the post-update specs from disk.
- Diffs each pair to extract per-method-block additions, removals, and modifications, plus per-section deltas for `## Application Exceptions` and `services.md`.
- Reads the sibling `<stem>.domain/updates.md` only as an enrichment source for `Source delta` lookups (missing is non-fatal — falls back to `(unknown source)`).
- Writes `<dir>/<stem>.application/updates.md` from scratch, describing the deltas plus an `## Affected Artifacts` footer keyed to per-aggregate application files for the future `/application-spec:update-code` consumer.

**Determinism**: structured-input-driven, not LLM-creative — same byte-stable contract as `command-repo-spec-updates-writer`. The `## Affected Artifacts` table is mechanically derived (Commands Methods Changes → `application/<aggregate>/<aggregate>_commands.py`; Queries Methods Changes → `application/<aggregate>/<aggregate>_queries.py`; Application Exceptions Changes → exception classes in `domain/<aggregate>/exceptions.py`; Services Changes → `containers.py` + per-service infrastructure stubs + conftest fixtures; tests → `tests/integration/<aggregate>/test_<aggregate>_commands.py` and `..._queries.py`).

**Standalone invocability**: supported. The writer reads everything from disk (working tree + git HEAD + sibling `<stem>.domain/updates.md`), so it doesn't require an orchestrator wrapper.

The writer runs on every successful orchestrator run, including Tier 4 no-op — those produce a report with every section `_no changes_` and an empty Affected Artifacts table. This keeps the future `/application-spec:update-code` consumer's contract simple: `updates.md` always exists after a successful run.

The full schema for `<stem>.application/updates.md` (section list, body conventions, footer shape, sentinel design) is owned by a sibling design note, [`updates-report.md`](updates-report.md) — to be written alongside this updater, mirroring the persistence-spec split between `spec-updater-approaches.md` and `updates-report.md`.

---

## Step 7 — Report

One sentence:

```
"Updated <stem>.application/{commands.specs.md, queries.specs.md, services.md}
 (regenerated commands side | regenerated queries side | regenerated both sides | no application-spec changes)
 and emitted <stem>.application/updates.md."
```

---

## Hard-fail conditions

| Condition | Detection | Reason |
|---|---|---|
| **0a. Missing `<stem>.domain/updates.md`** | file not on disk | Updater is not the first-run pipeline |
| **0b. Missing `<stem>.application/commands.specs.md`** | file not on disk | Updater is not the first-run pipeline |
| **0c. Missing `<stem>.application/queries.specs.md`** | file not on disk | Updater is not the first-run pipeline |
| **0d. Missing `<stem>.commands.md`** | file not on disk | A required hand-authored diagram |
| **0e. Missing `<stem>.queries.md`** | file not on disk | A required hand-authored diagram |
| **1a. Degraded baseline** | `_warning: HEAD ...` line in updates.md Summary | Cannot operate against a degraded baseline |
| **1b. Stereotype change (any class)** | non-empty `## Class Lifecycle → Stereotype Changed` | Cross-category move; subsumes aggregate-root case |
| **1c. Aggregate-root removal** | bullet with stereotype `<<Aggregate Root>>` under `## Class Lifecycle → Removed` | The application services lose their anchor |
| **1d. `Command/Query<AggregateRoot>Repository` interface lifecycle change** | a matching `<<Repository>>` class added or removed | Methods writers abort |
| **1e. `Command<AggregateRoot>Repository` loses `save(...)`** | `save(...)` member removed under the command repo's `## Per-Class Changes → Members` | `commands-methods-writer` Step 4 aborts |
| **1f. Domain `<<Service>>` removed / stereotype-changed / renamed while referenced by the commands diagram** | service class lifecycle entry + edge in commands diagram | `commands-methods-writer` and `services-finder` abort |
| **2-abort. Methods writer aborted at runtime** | one-line error from `commands-methods-writer` or `queries-methods-writer` | A method-specific reconciliation case missed by Tier 1; route to "reconcile the commands/queries diagram, then re-run" |

Errors 0a–1f are evaluated before any agent runs and produce a clean abort with no writes. Error 2-abort surfaces during Step 2; the orchestrator captures the writer's stdout error and surfaces it with the same operator instruction. Concurrent writers on the other side may have completed; their fragments are left on disk to be re-consumed (or replaced) on a subsequent successful run.

---

## Idempotency

Re-running `/application-spec:update-specs` against unchanged inputs must produce byte-identical output modulo LLM prose drift.

- **Steps 0–1** are deterministic checks and parsing.
- **Step 2** invokes LLM agents (`*-deps-writer`, `*-methods-writer`); they regenerate from current diagrams on every run, so output is stable modulo LLM nondeterminism. This is `git diff` noise, not an idempotency failure — same contract as the persistence-spec writers (see [`spec-updater-approaches.md`](../../persistence-spec/notes/spec-updater-approaches.md) § Idempotency).
- **Step 3** (`application-exceptions-specifier`) is deterministic from its inputs (Base / Code / Constructor / Message inferred from exception name + raising-method identity params).
- **Step 4** (`specs-merger`) is mechanical — concatenates fragments in a fixed order.
- **Step 5** (`services-finder`) is LLM-driven over a small input; treat as drift-prone but content-stable.

No sentinel comments are needed. Unlike persistence's `<!-- appended-from updates-hash:<hash> -->` (which guards the append-only migrations log), every section here is a snapshot — re-running over an unchanged domain `updates.md` simply reproduces the same content.

---

## Failure semantics and recovery

The orchestrator does not roll back partial writes. **Re-running `/application-spec:update-specs` after fixing the trigger is the supported recovery path.**

Specific failure modes:

- **Tier 1 hard-fail (0a–1f)** — no writes; operator runs `/application-spec:generate-specs` (or first reconciles the indicated diagram).
- **Step 2 writer abort (2-abort)** — the aborting side's fragments may be in any state (the writer aborts mid-flow); the other side's fragments may have completed if running in parallel. Operator reconciles the application-service diagram per the writer's error message and re-runs `/application-spec:update-specs`. The next run's Step 2 overwrites whatever fragments are on disk.
- **Step 3/4/5 failure** — rare; agent-level errors. Operator re-runs.

Steps 3, 4, and 5 are idempotent on stable Step-2 outputs, so partial completion of those steps is recoverable by re-running the orchestrator from the start.

---

## Chaining contract: domain `/update-specs` → application `/update-specs`

`/application-spec:update-specs` is designed to slot into `/update-specs` (domain) as a chained step, alongside the persistence chain.

```
/update-specs <domain_diagram>
│
├─ Steps 0–8  (existing: detect, preflight, prune, regen, splice, exceptions, replan, cleanup)
│
├─ Step 9     If <stem>.persistence/command-repo-spec.md exists,
│              invoke /persistence-spec:update-specs <domain_diagram>
│
└─ Step 10    If <stem>.application/commands.specs.md exists,
               invoke /application-spec:update-specs <domain_diagram>
```

Both downstream chains are **opt-in by file presence**. The application chain skips silently for aggregates that have no application layer.

The application updater is also independently invocable for situations where the domain spec is up-to-date but the application spec drifted (e.g. operator re-ran `/persistence-spec:generate-specs` and wants the application layer caught up too).

The same chaining shape extends to `rest-api-spec` and `messaging-spec` updaters as Steps 11, 12 — each opt-in by file presence, each independently invocable, each reading the same `<stem>.domain/updates.md`.

### Chained-step error handling

If the application updater hard-fails inside the chained invocation:

- Domain `/update-specs` reports its own steps as successful.
- The chained-step error surfaces with a clear "application updater failed" prefix, including the operator instruction.
- The domain artifacts are not rolled back — they are correct.
- The application spec remains in whatever state the chained skill left it in (Tier 1 fails before any write; 2-abort may leave fresh fragments on disk on the *non-aborting* side, which are picked up cleanly by the next run).

The exit status of `/update-specs` reflects the chained failure (non-zero) so CI can detect it, but the surface message distinguishes "domain succeeded; application chain failed."

---

## What this updater does NOT cover

- **Commands/queries-diagram changes are out of scope.** Most application-spec changes in practice — a command/query method added/removed, a method signature changed, a collaborator added/dropped, multi-tenancy added — originate in the *application-service* diagrams (`<stem>.commands.md`, `<stem>.queries.md`), and `<stem>.domain/updates.md` does not capture them. A complete application-spec updater needs an `application-spec:updates-detector` analog that diffs those two diagrams (emitting its own `<stem>.application/diagram-updates.md` or extending this updater's `updates.md`). That work is a separate concern; it can be added later and wired through the same dispatch tiers (Tier 2 / Tier 3) by re-running the relevant side's writers.
- **Aggregate-root rename cascades to diagram filenames.** Per `application-spec:naming-conventions`, the aggregate stem drives `<stem>.commands.md`, `<stem>.queries.md`, and `<stem>.application/`. A domain-`updates.md`-driven updater cannot perform that cascade; the operator renames the diagrams, then re-runs `/application-spec:generate-specs`. Surfaces as Tier 1 hard-fail 1c.
- **Multi-tenancy flips.** Application-spec multi-tenancy is a property of the application-service method signatures (the `application-exceptions-specifier`'s `<has_tenant>` detection scans method parameter lists), not of the domain root. A domain-only `tenant_id` flip is byte-neutral here — it takes effect only once the commands/queries diagrams' method signatures are updated (a commands/queries-diagram-axis change).
- **Bounded-context `title:` rename.** The `<AggregateRoot>Commands` / `<AggregateRoot>Queries` class names come from the commands/queries diagrams' class nodes, not from the domain `title:`. Tier 4 no-op.
- **Code regen.** The `<aggregate>_commands.py` / `<aggregate>_queries.py` implementations, infrastructure stubs, test fakes, DI providers, conftest fixtures, the application exception classes appended to the domain aggregate's `exceptions.py`, and the integration tests are owned by `/application-spec:generate-code`. They are out of scope for this updater. The `updates.md` emitted at Step 6 is the input contract a future `/application-spec:update-code` will consume.
- **`updates.md` schema design.** The Step-6 report's exact schema (sections, body conventions, footer shape, sentinel design) is owned by a sibling [`updates-report.md`](updates-report.md) note, mirroring the persistence-spec split. Step 6 ships with v1 of the updater; the sibling note must land alongside it.
- **Hand-edits inside the spec.** Per the writer/merger contract, the spec is regenerated from the diagrams, not curated. The unaffected side's `specs.md` is preserved byte-identically (the chosen approach's main payoff), but inside a regenerated side, manual edits are wholesale replaced.
- **Concurrent updaters.** Two operators on parallel branches both re-running the updater produce a normal Git merge conflict on `commands.specs.md` / `queries.specs.md` / `services.md`, resolved by standard merge tooling. Not an updater bug.

---

## Required artifacts

| Artifact | Status | Owns |
|---|---|---|
| `commands-deps-writer` | unchanged | re-runs in Step 2 (commands dirty) |
| `commands-methods-writer` | unchanged | re-runs in Step 2 (commands dirty) |
| `queries-deps-writer` | unchanged | re-runs in Step 2 (queries dirty) |
| `queries-methods-writer` | unchanged | re-runs in Step 2 (queries dirty) |
| `application-exceptions-specifier` | unchanged | runs in Step 3; auto-skips a side whose `.methods.md` is absent |
| `specs-merger` | unchanged | runs per dirty side in Step 4 |
| `services-finder` | unchanged | re-runs in Step 5 |
| `application-spec:application-updates-writer` | **new agent** | runs in Step 6; emits `<stem>.application/updates.md` |
| `application-spec:updates-report-template` | **new skill** | report schema + rendering rules; auto-loaded by `application-updates-writer` and (later) the `/application-spec:update-code` consumer |
| `application-spec:update-specs` (orchestrator skill) | **new skill** | the `SKILL.md` driving Steps 0–7 |
| `notes/updates-report.md` | **new design note** | sibling to this doc; owns the `<stem>.application/updates.md` schema design rationale |

The persistence-spec design split (schema-as-skill + design-as-note) is reused verbatim:

- The **skill** (`updates-report-template`) is a condensed contract document — schema + rendering rules — auto-loaded by both the producer agent (when rendering) and the future code-updater (when parsing).
- The **note** (`updates-report.md`) is the *why* — design rationale, alternative-detector trade-offs, lifecycle/ownership, worked example.

No existing agent's contract changes. No existing skill's contract changes. The four writers, the exceptions specifier, the merger, and `services-finder` keep their current input/output behaviour; the per-side scoping the updater needs is given for free by the exceptions specifier's existing disk-presence skip.

---

## Alternatives considered

| Approach | Status | Why not |
|---|---|---|
| **A. Whole-pipeline regen** | rejected | Re-runs both sides regardless of which is dirty; produces noisy diffs (regenerates the unaffected side's `## Method Specifications` and `## Application Exceptions` for nothing) and re-runs `services-finder` on a doubly-redundant input. Equivalent to invoking `/application-spec:generate-specs`. |
| **B. Per-method-block splice** | rejected | The writers regenerate a whole side's methods section in one pass (no per-method mode). A splicer would need to diff fresh writer output against the live file at `### Method:` granularity — significant new agent code. The main payoff (preserving untouched class blocks from regen drift) is what justified Approach B for the *domain* spec, where one `specs.md` carries dozens of class blocks; here each side carries a single `## Method Specifications` section, so the unit of "untouched content" is much smaller. Not worth the implementation cost given hand-edits aren't a preservation goal. |
| **Per-side regen (chosen)** | **accepted** | Reuses every existing writer, the exceptions enricher, the merger, and `services-finder` verbatim. Requires no contract changes to those agents — the exceptions enricher's existing per-side disk-presence skip provides the per-side scoping for free. The unaffected side's `specs.md` is byte-stable (zero diff). The new orchestration logic is preflight + tier dispatch — small, mechanical, regex-friendly. |

The persistence-spec design (`spec-updater-approaches.md`) anticipates this updater as **Step 10 of domain `/update-specs`** — opt-in by file presence (`<stem>.application/commands.specs.md` exists), reading the same `<stem>.domain/updates.md`. The chained step covers only the domain-driven axis; the commands/queries-diagram axis remains a separate trigger (an `application-spec:updates-detector` invocation, or a fresh `/application-spec:generate-specs` run).
