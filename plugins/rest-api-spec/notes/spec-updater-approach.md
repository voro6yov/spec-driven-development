# REST API Spec Updater — Per-Writer Regen

This note documents the design of `/rest-api-spec:update-specs`, the surgical update skill for `<dir>/<stem>.rest-api/spec.md`. It is the REST-API-side counterpart to `/persistence-spec:update-specs`, `/application-spec:update-specs`, and `/domain-spec:update-specs`.

The chosen approach is **per-writer snapshot regen** — re-run only the table-writer agent(s) whose owned table a domain delta touches, reuse them verbatim, never touch the unaffected tables. It is designed to chain from domain `/update-specs` as an opt-in step, but is also independently invocable.

For the catalog of update types and their per-table impact, see the sibling [`update-types.md`](update-types.md).
For the application-side counterpart this design is modelled on, see [`plugins/application-spec/notes/spec-updater-approach.md`](../../application-spec/notes/spec-updater-approach.md).
For the persistence-side counterpart (the hybrid snapshot+log design that this one deliberately *does not* need), see [`plugins/persistence-spec/notes/spec-updater-approaches.md`](../../persistence-spec/notes/spec-updater-approaches.md).
For the domain-side counterpart, see [`plugins/domain-spec/notes/spec-updater-approach-b.md`](../../domain-spec/notes/spec-updater-approach-b.md).
For the **commands/queries-diagram-axis integration** (the second consumption axis the v1 updater described below has since grown), see the sibling [`commands-queries-integration-approach.md`](commands-queries-integration-approach.md) — it extends Steps 0/1/2/3/5 to consume two additional detector reports and recruits `resource-spec-initializer` and `endpoint-tables-writer` into the updater's writer repertoire. Several call-outs in this note (most notably in the Goal section and in *What this updater does NOT cover*) are scoped to the domain axis only and are superseded by that integration note for the commands/queries axes.

---

## Goal

Keep `<stem>.rest-api/spec.md` aligned with the domain diagram after a domain change, **without re-running `/rest-api-spec:generate-specs` from scratch**. The updater:

- Runs as a chained step at the tail of `/update-specs` (domain), opt-in by file presence (`<stem>.rest-api/spec.md` exists).
- May be invoked standalone for cases where the domain spec is up-to-date but the REST spec drifted.
- Consumes the same `<stem>.domain/updates.md` report the domain, persistence, and application updaters consume.
- Never re-diffs the diagram, never invokes `domain-spec:updates-detector` directly.
- Does not preserve hand-edits inside a regenerated table — the operator's contract is that the spec is regenerated from the diagrams, not curated.

This note's design covers **the domain-driven axis only**. The commands/queries-diagram axis was a deliberate v1 omission (the updater used to early-exit on most domain changes because the domain diagram's contribution to the REST spec is genuinely narrow) but has since been added as an additional consumption axis — see [`commands-queries-integration-approach.md`](commands-queries-integration-approach.md). For *domain-only* edits the v1 byte-stable / early-exit characterization still holds; once commands/queries-diagram triggers are unioned in, the median REST-spec change comes from the app-service axis and exercises the writer repertoire that note describes. Sections of this note that say "the median change is a no-op" or "the domain diagram's contribution is so narrow that the updater early-exits" should be read as scoped to a domain-only edit.

---

## Inputs

- `<domain_diagram>` — the same first-positional argument every rest-api-spec orchestrator takes, at `<dir>/<stem>.md`.
- `<dir>/<stem>.domain/updates.md` — already on disk (produced by `domain-spec:updates-detector`, either as Step 0 of `/update-specs` or by an explicit prior invocation).
- `<dir>/<stem>.rest-api/spec.md` — already on disk (produced by an earlier `/rest-api-spec:generate-specs` run); the file the updater modifies in place.
- `<dir>/<stem>.commands.md` and `<dir>/<stem>.queries.md` — already on disk; **not diffed** by this updater, but the orchestrator scans their `<Resource>Commands` / `<Resource>Queries` class bodies to compute the *referenced-type set* (Step 0) and the table-writer agents read them in full.

If any required file is missing the updater hard-fails with operator instructions. The updater is **not** the first-run pipeline; `/rest-api-spec:generate-specs` owns first-run.

---

## Output

In place under `<dir>/<stem>.rest-api/`:

- `spec.md` — modified in place: only the affected `**Nested:**` sub-tables, `**Query Parameters:**` rows, and Table 6 `Constructed from query params … → <Type>` source lines are regenerated (a domain-only change never touches Table 1, Table 2, or Table 3, and never touches a surface whose endpoints' referenced types are unchanged). Whichever of Tables 4/5/6 a dirty writer owns is rewritten wholesale by that writer; the other tables are byte-stable.
- `updates.md` — emitted on every successful run (including no-op exits) for a future `/rest-api-spec:update-code` consumer. The schema for this file is out of scope for this note; see *Required artifacts*.

The three diagram files are untouched; no other plugin's folder is touched; no backup or rollback file is produced.

---

## Architectural insight: snapshot-only, per-writer scope

Three structural facts dominate the design.

### Every section of `spec.md` is a snapshot

Unlike persistence-spec, where `§2.Migrations` is an append-only log of cumulative changesets, every table of `spec.md` is a **pure snapshot** — fully regeneratable from the three diagrams. There is no migration-log analog, no row-immutability contract, no delta-driven appender. So the architectural complexity that drove persistence-spec to a hybrid "Snapshot + Log" design does not apply: every modified table is regenerated from current inputs.

### `spec.md` is one file, owned table-by-table by five writers

`resource-spec-initializer` owns Table 1. `endpoint-tables-writer` owns Tables 2 and 3 (and updates Table 1's Surfaces row). `response-fields-writer` owns Table 4 (response sub-tables + `**Nested:**` sub-tables + `**Query Parameters:**` blocks). `request-fields-writer` owns Table 5. `parameter-mapping-writer` owns Table 6. Each writer parses the diagrams fresh and rewrites only its owned table in place.

Per `update-types.md` § "REST API spec sections and their domain-sensitivity", a domain delta reaches **only** Tables 4, 5, and 6, and only through nested-type / composite-query-param resolution against the domain diagram:

- A response-DTO or nested-response-type field change → `response-fields-writer` (Table 4).
- A nested-request-type field change → `request-fields-writer` (Table 5).
- A composite query-param type's field-list change → `response-fields-writer` (the decomposed `**Query Parameters:**` rows) **and** `parameter-mapping-writer` (the `Constructed from query params … → <Type>` source line).

`endpoint-tables-writer` and `resource-spec-initializer` are **never** re-run for a domain-only change: Tables 1/2/3 are pure functions of the application-service diagrams plus the `<<Aggregate Root>>` class name, and the only domain delta that touches the `<<Aggregate Root>>` name (a root rename / removal / stereotype-demotion) is a *hard-fail*, not a regen.

### The two referenced-type axes are independent

A domain change touching only nested *response* types re-runs only `response-fields-writer`. One touching only nested *request* types re-runs only `request-fields-writer`. A composite-query-param field change re-runs `response-fields-writer` + `parameter-mapping-writer`. The natural regen unit is therefore "the dirty table writer(s)", not the whole pipeline — the application-spec "per-side regen" idea, narrowed from two sides to three table writers.

### Why per-writer, not per-sub-block

Three granularities are conceivable:

1. **Whole-pipeline regen** — re-run `/rest-api-spec:generate-specs` end-to-end. Correct, simplest, but re-runs `endpoint-tables-writer` and `resource-spec-initializer` for nothing, rewrites all six tables across all surfaces, and produces a noisy `git diff` for a one-field change inside one nested type. Equivalent to invoking `/rest-api-spec:generate-specs`.
2. **Per-writer regen (chosen)** — re-run only the dirty table writer(s) (`response-fields-writer` / `request-fields-writer` / `parameter-mapping-writer`).
3. **Per-sub-block splice** — splice only the regenerated `**Nested:**` sub-tables, `**Query Parameters:**` rows, and Table 6 source lines into the existing `spec.md`, leaving every other sub-block byte-identical.

(2) is the sweet spot:

- The three table writers each regenerate their whole owned table in one pass — they have no "regenerate sub-block X only" mode — so a per-sub-block splicer would have to diff fresh writer output against the live file at `**Nested:**` / `**Endpoint:**` granularity. That's the rest-api analog of `spec-updater-approach-b.md` on the domain side, and it's the meaty new agent that approach (B) was built around. Significant implementation cost.
- The main payoff of per-sub-block splicing — protecting untouched content from regen drift — is what justified Approach B for the *domain* spec, where one `specs.md` carries dozens of class blocks. Here a domain-only change touches at most a handful of `**Nested:**` sub-tables and the `include` / `Constructed from …` rows; a dirty writer rewrites *one* table (`response-fields-writer` rewrites Table 4, etc.), and on unchanged inputs reproduces the same content modulo LLM drift. The unit of "untouched content" the splice would protect is small, and hand-edits aren't a preservation goal.
- Per-writer regen gives every table the dirty writers *don't* own a guaranteed byte-stable diff (Table 1, Tables 2/3, and whichever of Tables 4/5/6 isn't dirty are not touched at all). That's most of the diff-noise win, at zero new agent code.

The cost accepted: when a dirty writer re-runs, it rewrites its *whole* table — every endpoint's sub-block in Table 4, not just the one whose nested type changed — so endpoints whose referenced types are unchanged get re-emitted (byte-stable modulo LLM drift). This is the same "LLM drift is `git diff` noise, not a correctness failure" contract the persistence-spec and application-spec writers already operate under.

---

## Pipeline

```
domain updates report ──┐
                        ├─► [0] preflight (orchestrator-owned: file checks + parse updates.md
                        │       + scan <stem>.commands.md / <stem>.queries.md for the referenced-type set)
domain diagram ─────────┤
                        ├─► [1] dispatch tier
                        │
                        ├─► [2] table-writer regen (SEQUENTIAL — they share spec.md)
                        │       response-fields-writer     (if response_fields_dirty)
                        │       request-fields-writer      (if request_fields_dirty)
                        │       parameter-mapping-writer   (if parameter_mapping_dirty)
                        │
                        ├─► [3] emit <stem>.rest-api/updates.md
                        │
                        └─► [4] report
```

Steps 0–1 are pure orchestrator-owned parse/checks. Steps 2–3 are agent invocations. Step 2 is **sequential** (not parallel like the application-spec updater's per-side fan-out) because the three table writers all edit the single `spec.md` in place with anchored `Edit` calls — running them concurrently risks one writer's edit landing on a stale view of the file. Sequence them response → request → parameter-mapping, the same order `/rest-api-spec:generate-specs` uses.

---

## Step 0 — Preflight

Verify inputs exist (each missing input is its own hard-fail with a one-line operator instruction):

| Check | Hard-fail code |
|---|---|
| `<dir>/<stem>.domain/updates.md` exists | 0a |
| `<dir>/<stem>.rest-api/spec.md` exists | 0b |
| `<dir>/<stem>.commands.md` exists | 0c |
| `<dir>/<stem>.queries.md` exists | 0d |

Then parse `updates.md` into a working set:

| Variable | Source |
|---|---|
| `affected_categories: set` | `## Affected Categories` |
| `removed_classes: { name → stereotype }` | `## Class Lifecycle → Removed` |
| `added_classes: { name → stereotype }` | `## Class Lifecycle → Added` |
| `stereotype_changed: { name → (old, new) }` | `## Class Lifecycle → Stereotype Changed` |
| `touched_data_types: set[str]` | names of `<<TypedDict>>` / `<<Value Object>>` / `<<Command>>` classes appearing under `## Per-Class Changes` (member changes), `## Class Lifecycle → Added`, or `## Class Lifecycle → Removed` |
| `removed_or_renamed_data_types: set[str]` | the subset of `touched_data_types` that appear under `## Class Lifecycle → Removed` (a rename is reported as `removed (old) + added (new)`, so the old name is here) |
| `degraded_baseline: bool` | true iff Summary contains the `_warning: HEAD ..._` line |

Then scan the two application-service diagrams (`Read` + a cheap pass over the `<Resource>Commands` / `<Resource>Queries` class bodies, applying the same surface-marker-tolerant method-line regex the writers use):

| Variable | Derivation |
|---|---|
| `commands_referenced_types: set[str]` | every PascalCase token appearing as a parameter type on a public `<Resource>Commands` method (after stripping `\| None`, `list[...]`, `dict[...]`, `Literal[...]` wrappers) |
| `queries_referenced_types: set[str]` | every PascalCase token appearing as a return type or a parameter type on a public `<Resource>Queries` method (same unwrapping) |

These are the *direct* references. Transitive references (a referenced type whose field is itself a custom type that changed) are not computed here — the writer resolves them recursively, and the conservative v1 dispatch (below) re-runs the relevant writer whenever *any* `data-structures` / `value-objects` change is present, so a missed transitive reference still gets picked up.

---

## Step 1 — Dispatch tier

Apply gates in order; first match wins.

### Tier 1 — Hard-fail

Each prints exactly one `ERROR:` line and exits, directing the operator to `/rest-api-spec:generate-specs <domain_diagram>` (after reconciling the commands/queries diagrams where the message says so). Gates evaluated in order:

| Gate | Condition | Reason |
|---|---|---|
| 1a | `degraded_baseline` | Cannot operate against a degraded baseline |
| 1b | `stereotype_changed` non-empty | Cross-category move means the class is no longer the kind of thing the spec assumed; subsumes the aggregate-root case |
| 1c | Any bullet with stereotype `<<Aggregate Root>>` under `## Class Lifecycle → Removed` | The resource loses its anchor (a rename — `removed (old) <<Aggregate Root>>` + `added (new) <<Aggregate Root>>` — also moves all three diagram filenames and the `<stem>.rest-api/` folder: a coordinated multi-file rename the updater can't perform) |
| 1d | `removed_or_renamed_data_types ∩ (commands_referenced_types ∪ queries_referenced_types)` non-empty | A `<<TypedDict>>` / `<<Value Object>>` / `<<Command>>` referenced by an app-service method's return/parameter type was renamed or removed; `response-fields-writer` / `request-fields-writer` / `parameter-mapping-writer` would abort with `Cannot resolve …`. **Abort-and-reconcile**: instruct the operator to update the method's type token in `<stem>.commands.md` / `<stem>.queries.md` (or drop the reference), then re-run. |

Gate 1d is the rest-api analog of the application-spec updater's "abort-and-reconcile" — but here it is detectable *before* any writer runs (from `updates.md` + the Step-0 diagram scan), so it is a Tier-1 gate rather than a runtime surprise. (A *transitively*-referenced renamed/removed type can still slip past it and surface as a runtime abort in Step 2 — see below.)

### Tier 2 — Regen the dirty table writer(s)

Compute the dirty flags:

- `response_fields_dirty = (affected_categories ∩ {data-structures, value-objects}) ≠ ∅`
- `request_fields_dirty = (affected_categories ∩ {data-structures, value-objects}) ≠ ∅`  **or**  (`affected_categories` contains `commands` **and** `touched_data_types ∩ commands_referenced_types` contains a `<<Command>>` dataclass)
- `parameter_mapping_dirty = (affected_categories ∩ {data-structures, value-objects}) ≠ ∅`

This is the **conservative v1 rule**: a `data-structures` or `value-objects` change anywhere re-runs all three table writers. It over-regenerates (re-runs a writer even when the changed type is purely internal to the aggregate and never surfaces in the REST spec — producing a byte-stable Table 4/5/6 modulo LLM drift), but it is correct without computing the domain diagram's type-reference graph, and the diff is small. A `commands`-category change re-runs only `request-fields-writer`, and only when a changed `<<Command>>` dataclass is *directly* a command-method parameter type — keeping the common `commands`-fires case (an inferred-command rename, no Table 5 reference) a no-op.

> **v2 optimization (not in the first cut).** Narrow the dirty flags by intersecting `touched_data_types` (plus its transitive closure over the domain diagram's `<<Value Object>>` / `<<TypedDict>>` field types) against `queries_referenced_types` (for `response_fields_dirty` / the composite-query-param part of `parameter_mapping_dirty`) and `commands_referenced_types` (for `request_fields_dirty`). This skips a writer entirely when none of its referenced types changed. It costs a domain-diagram type-graph walk in the orchestrator; defer until the no-drift diff matters more than the implementation cost.

### Tier 3 — No-op

If none of `response_fields_dirty` / `request_fields_dirty` / `parameter_mapping_dirty` is set after the above, the updater:

1. Skips Step 2.
2. Still runs Step 3 (emit `updates.md` with all sections `_no changes_`).
3. Still runs Step 4 (operator one-liner).

Tier 3 fires for any of:

- `affected_categories` empty (per the report-template footer contract this implies no class lifecycle and no per-class changes — only orphan prose, which is byte-neutral for the REST spec).
- `affected_categories ⊆ {domain-events, commands (with no changed `<<Command>>` directly a command-method param type), aggregates, repositories-services}` — `domain-events` and `repositories-services` never reach the REST spec; `aggregates` reaches it only via the root-identity hard-fail spike (caught by 1b/1c above), never as a regen signal; `commands` reaches it only via the rare Table 5 nested-`<<Command>>` case.
- A pure prose change (P1–P4) — always byte-neutral for the REST spec; no writer consumes domain prose.
- A bounded-context `title:` rename in `## Orphan Prose Changes → Preamble` and nothing else.
- A domain-only `tenant_id` flip on the aggregate root (REST-spec multi-tenancy is an app-diagram property).

Tier 3 is hit far more often here than in any other downstream updater — the domain diagram's contribution to the REST spec is so narrow that the median domain change is a flat no-op.

---

## Step 2 — Table-writer regen (sequential)

For each dirty writer, **in this order**, invoke it with prompt `<domain_diagram>` and wait for completion before invoking the next:

1. `rest-api-spec:response-fields-writer` — if `response_fields_dirty`.
2. `rest-api-spec:request-fields-writer` — if `request_fields_dirty`.
3. `rest-api-spec:parameter-mapping-writer` — if `parameter_mapping_dirty`.

Each writer parses `<stem>.commands.md` / `<stem>.queries.md` / `<stem>.md` fresh, locates its owned table inside `spec.md`, and rewrites it in place (Edit, not Write — anchored on the table's H3 heading + body, per-Surface section). The writers have no idempotency contract beyond "output is a function of inputs" — re-running on identical diagrams produces byte-identical output modulo LLM nondeterminism. They do not read `<stem>.domain/updates.md`.

**Why sequential, not parallel.** All three edit the single `spec.md`. The application-spec updater can fan its two sides out in parallel because `commands.specs.md` and `queries.specs.md` are separate files; here they aren't. The `/rest-api-spec:generate-specs` orchestrator already runs these three writers sequentially for the same reason (the `generate-code` skill makes the analogous "do not run in parallel" note about the serializer implementers that share aggregator `__init__.py` files).

### Runtime abort (2-abort)

A table writer can abort at runtime even though Tier-1 gate 1d passed — specifically when a renamed/removed type is referenced *transitively* (a referenced type's field, or that field's field, …) rather than directly, so the Step-0 scan didn't catch it. The writer surfaces `Cannot resolve response DTO <Name>` / `Cannot resolve nested type <Name>` / `Cannot resolve query-param composite <Type>` and produces no edit. The orchestrator captures the writer's stdout error, surfaces it with the operator instruction ("reconcile the commands/queries diagram so the type resolves, then re-run `/rest-api-spec:update-specs`"), and exits non-zero. Earlier-sequenced writers may have already edited `spec.md`; those edits are left in place (the orchestrator does not roll back — see *Failure semantics*) and a subsequent successful run overwrites them.

---

## Step 3 — Emit `<stem>.rest-api/updates.md`

Invoke `rest-api-spec:rest-api-updates-writer` (new agent) which:

- Recovers the pre-update `spec.md` via `git show HEAD:<dir>/<stem>.rest-api/spec.md`.
- Reads the post-update `spec.md` from disk.
- Diffs the pair to extract per-table / per-Surface / per-endpoint deltas (which `**Nested:**` sub-tables gained/lost/changed rows, which `**Query Parameters:**` blocks changed, which Table 6 source lines changed).
- Reads the sibling `<stem>.domain/updates.md` only as an enrichment source for `Source delta` lookups (missing is non-fatal — falls back to `(unknown source)`).
- Writes `<dir>/<stem>.rest-api/updates.md` from scratch, with an `## Affected Artifacts` footer keyed to per-surface code files for the future `/rest-api-spec:update-code` consumer (Table 4 changes → `api/serializers/<surface>/<operation>.py` query serializers; Table 5 changes → command serializers; Table 6 changes → endpoint module kwargs in `api/endpoints/<surface>/<plural>.py`; plus the always-implicated `tests/integration/<resource>/test_<plural>_<surface>_api.py`).

**Determinism**: structured-input-driven, not LLM-creative — same byte-stable contract as `command-repo-spec-updates-writer` (persistence). **Standalone-invocable**: reads everything from disk (working tree + git HEAD + sibling domain `updates.md`). Runs on every successful orchestrator run, including Tier-3 no-op (produces all-`_no changes_` + an empty Affected Artifacts table) so the future code-updater's contract is simple: `updates.md` always exists after a successful run.

The full schema for `<stem>.rest-api/updates.md` (section list, body conventions, footer shape, sentinel design) is owned by a sibling design note, [`updates-report.md`](updates-report.md) — to be written alongside this updater, mirroring the persistence-spec and application-spec splits between `spec-updater-approach*.md` and `updates-report.md`. Step 3 ships with v1 of the updater; the sibling note must land alongside it. (If the `updates.md` emission is judged out of scope for the first cut, Step 3 can be dropped from v1 and added later — the rest of the updater does not depend on it.)

---

## Step 4 — Report

One sentence:

```
"Updated <stem>.rest-api/spec.md
 (regenerated Table 4 | Table 5 | Table 6 | Tables 4 & 6 | Tables 4, 5 & 6 | no REST-spec changes)
 and emitted <stem>.rest-api/updates.md."
```

---

## Hard-fail conditions

| Condition | Detection | Reason |
|---|---|---|
| **0a. Missing `<stem>.domain/updates.md`** | file not on disk | Updater is not the first-run pipeline |
| **0b. Missing `<stem>.rest-api/spec.md`** | file not on disk | Updater is not the first-run pipeline (also catches an aggregate-root rename — the new stem's spec doesn't exist at `<new-stem>.rest-api/spec.md`) |
| **0c. Missing `<stem>.commands.md`** | file not on disk | A required hand-authored diagram |
| **0d. Missing `<stem>.queries.md`** | file not on disk | A required hand-authored diagram |
| **1a. Degraded baseline** | `_warning: HEAD ...` line in `updates.md` Summary | Cannot operate against a degraded baseline |
| **1b. Stereotype change (any class)** | non-empty `## Class Lifecycle → Stereotype Changed` | Cross-category move; subsumes the aggregate-root case |
| **1c. Aggregate-root removal (or the removed half of a rename)** | bullet with stereotype `<<Aggregate Root>>` under `## Class Lifecycle → Removed` | The resource loses its anchor; a rename also moves all three diagram filenames + the `<stem>.rest-api/` folder |
| **1d. Referenced data type renamed/removed** | a `<<TypedDict>>` / `<<Value Object>>` / `<<Command>>` under `## Class Lifecycle → Removed` whose name still appears as a return/parameter type token in `<stem>.commands.md` / `<stem>.queries.md` | The table writer would abort `Cannot resolve …`; route to "reconcile the commands/queries diagram, then re-run" (abort-and-reconcile, not a full hard-fail — the rest of the spec is fine) |
| **2-abort. Table writer aborted at runtime** | one-line error (`Cannot resolve response DTO / nested type / query-param composite …`) from `response-fields-writer` / `request-fields-writer` / `parameter-mapping-writer` | A *transitively*-referenced renamed/removed type the Step-0 scan missed; route to "reconcile the commands/queries diagram, then re-run" |

Errors 0a–1d are evaluated before any agent runs and produce a clean abort with no writes. Error 2-abort surfaces during Step 2; the orchestrator captures the writer's error and surfaces it with the same operator instruction.

---

## Idempotency

Re-running `/rest-api-spec:update-specs` against unchanged inputs must produce byte-identical output modulo LLM prose drift.

- **Steps 0–1** are deterministic checks and parsing.
- **Step 2** invokes LLM agents (`response-fields-writer`, `request-fields-writer`, `parameter-mapping-writer`); they regenerate their owned table from current diagrams on every run, so output is stable modulo LLM nondeterminism. This is `git diff` noise, not an idempotency failure — same contract as the persistence-spec and application-spec writers.
- **Step 3** (`rest-api-updates-writer`) is deterministic from its inputs (working tree + git HEAD + sibling domain `updates.md`).

No sentinel comments are needed. Unlike persistence's `<!-- appended-from updates-hash:<hash> -->` (which guards the append-only migrations log), every table here is a snapshot — re-running over an unchanged domain `updates.md` simply reproduces the same content.

---

## Failure semantics and recovery

The orchestrator does not roll back partial writes. **Re-running `/rest-api-spec:update-specs` after fixing the trigger is the supported recovery path.**

- **Tier 1 hard-fail (0a–1c)** — no writes; operator runs `/rest-api-spec:generate-specs` (or first reconciles the indicated diagram).
- **Tier 1 abort-and-reconcile (1d)** — no writes; operator updates the offending type token in `<stem>.commands.md` / `<stem>.queries.md`, then re-runs `/rest-api-spec:update-specs`.
- **Step 2 writer abort (2-abort)** — earlier-sequenced writers may have already edited `spec.md`; the aborting writer made no edit. Operator reconciles the commands/queries diagram per the writer's error message and re-runs; the next run re-runs *all* dirty writers from the top (idempotent), overwriting whatever partial edits are on disk.
- **Step 3 failure** — rare; `spec.md` is already correct (Step 2 completed). Operator re-runs; Step 2 re-runs harmlessly (byte-stable) and Step 3 retries.

---

## Chaining contract: domain `/update-specs` → rest-api `/update-specs`

`/rest-api-spec:update-specs` is designed to slot into `/update-specs` (domain) as a chained step, alongside the persistence and application chains:

```
/update-specs <domain_diagram>
│
├─ Steps 0–8   (existing: detect, preflight, prune, regen, splice, exceptions, replan, cleanup)
│
├─ Step 9      If <stem>.persistence/command-repo-spec.md exists,
│               invoke /persistence-spec:update-specs <domain_diagram>
│
├─ Step 10     If <stem>.application/commands.specs.md exists,
│               invoke /application-spec:update-specs <domain_diagram>
│
└─ Step 11     If <stem>.rest-api/spec.md exists,
                invoke /rest-api-spec:update-specs <domain_diagram>
```

All downstream chains are **opt-in by file presence** and **independent of each other** — the rest-api updater reads the Mermaid diagrams directly, not the application or persistence specs, so Steps 9/10/11 (and a future Step 12 for messaging) have no ordering dependency and could run in parallel; chaining them sequentially is just simpler. The rest-api chain skips silently for aggregates that have no REST layer.

The rest-api updater is also independently invocable for situations where the domain spec is up-to-date but the REST spec drifted (e.g. the operator re-ran `/application-spec:generate-specs` and wants the REST layer caught up too).

### Chained-step error handling

If the rest-api updater hard-fails inside the chained invocation:

- Domain `/update-specs` (and the persistence/application chained steps) report their own steps as successful.
- The chained-step error surfaces with a clear "rest-api updater failed" prefix, including the operator instruction.
- The domain / persistence / application artifacts are not rolled back — they are correct.
- `spec.md` remains in whatever state the chained skill left it in (Tier 1 fails before any write; 2-abort may leave some tables regenerated, which the next run overwrites).

The exit status of `/update-specs` reflects the chained failure (non-zero) so CI can detect it, but the surface message distinguishes "domain succeeded; rest-api chain failed."

---

## What this updater does NOT cover

(The commands/queries-diagram axis was the v1 omission documented here; it has since been added via [`commands-queries-integration-approach.md`](commands-queries-integration-approach.md) and is no longer listed below.)

- **Aggregate-root rename cascades to diagram filenames and the plugin folder.** Per `rest-api-spec:naming-conventions`, the aggregate stem drives `<stem>.md`, `<stem>.commands.md`, `<stem>.queries.md`, and `<stem>.rest-api/`. A domain-`updates.md`-driven updater cannot perform that cascade; the operator renames the diagrams and the folder, then re-runs `/rest-api-spec:generate-specs`. Surfaces as Tier 1 hard-fail 1c (and/or 0b).
- **Multi-tenancy flips.** REST-spec `tenant_id` handling (dropped from the body in Table 5, excluded from the query-parameter list in Table 4, sourced as `Auth context` in Table 6) is a property of the app-service method signatures (`tenant_id: str` parameters), not of the domain root. A domain-only `tenant_id` flip is byte-neutral here — it takes effect only once the commands/queries diagrams' method signatures are updated (a commands/queries-diagram-axis change). Deliberate divergence from persistence-spec; matches application-spec.
- **Bounded-context `title:` rename.** The `<Resource>Commands` / `<Resource>Queries` class names come from the commands/queries diagrams' class nodes; Table 1's Resource name comes from the `<<Aggregate Root>>` *class name*. A domain-`title:` change is byte-neutral. Tier 3 no-op.
- **Surface-marker changes** live in the commands/queries diagrams (the commands/queries-diagram axis above), not the domain diagram.
- **Code regen.** The per-surface serializer modules, endpoint modules, the FastAPI app wiring (`entrypoint.py`, `constants.py`, the aggregator `__init__.py` files, `api/auth.py`), the test fixtures (`tests/conftest.py`), and the integration tests are owned by `/rest-api-spec:generate-code`. They are out of scope for this updater. The `updates.md` emitted at Step 3 is the input contract a future `/rest-api-spec:update-code` will consume. (Several of those generation agents — `app-integrator`, `test-fixtures-preparer`, `tests-implementer`, the serializer implementers — are already additively idempotent, which eases the future code-updater.)
- **The Shared domain types registry** (`Pagination`, `PaginatedResultMetadataInfo`, `ResultSetInfo`) is hard-coded in `response-fields-writer` / `request-fields-writer` / `parameter-mapping-writer`. Changes to those types are plugin-source changes, not domain-diagram changes; they never appear in `updates.md` and are picked up only by re-running `/rest-api-spec:generate-specs` after a plugin upgrade.
- **Hand-edits inside a regenerated table.** Per the writer contract, the spec is regenerated from the diagrams, not curated. The Tables 4–6 `**Nested:**` sub-tables and `**Query Parameters:**` Descriptions are emitted mechanically; the user is expected to enrich Descriptions and Table 5 Validation prose by hand after generation — and a regen of the owning table discards those enrichments for *that table* (the other tables are byte-stable). The blast radius is small (a domain-only change re-runs at most three writers, each rewriting one table), but it is non-zero.
- **Concurrent updaters.** Two operators on parallel branches both re-running the updater produce a normal Git merge conflict on `spec.md`, resolved by standard merge tooling. Not an updater bug.

---

## Required artifacts

| Artifact | Status | Owns |
|---|---|---|
| `resource-spec-initializer` | unchanged | never re-runs for a domain-only change (no-op once Table 1 exists) |
| `endpoint-tables-writer` | unchanged | never re-runs for a domain-only change (Tables 1/2/3 are pure functions of the app-service diagrams + the `<<Aggregate Root>>` name) |
| `response-fields-writer` | unchanged | re-runs in Step 2 if `response_fields_dirty` |
| `request-fields-writer` | unchanged | re-runs in Step 2 if `request_fields_dirty` |
| `parameter-mapping-writer` | unchanged | re-runs in Step 2 if `parameter_mapping_dirty` |
| `rest-api-spec:rest-api-updates-writer` | **new agent** | runs in Step 3; emits `<stem>.rest-api/updates.md` |
| `rest-api-spec:updates-report-template` | **new skill** | report schema + rendering rules; auto-loaded by `rest-api-updates-writer` and (later) the `/rest-api-spec:update-code` consumer |
| `rest-api-spec:update-specs` (orchestrator skill) | **new skill** | the `SKILL.md` driving Steps 0–4 |
| `notes/updates-report.md` | **new design note** | sibling to this doc; owns the `<stem>.rest-api/updates.md` schema design rationale |

No existing agent's contract changes. The five existing writers keep their current input/output behaviour; the per-writer scoping the updater needs is given for free by each writer owning exactly one table and rewriting it in place. (If the Step-3 `updates.md` emission is dropped from the first cut, the three new `updates`-related artifacts are deferred too — the orchestrator skill alone is then the only new artifact.)

The persistence-spec / application-spec design split (schema-as-skill + design-as-note) is reused verbatim: the **skill** (`updates-report-template`) is a condensed contract document auto-loaded by both the producer agent and the future code-updater; the **note** (`updates-report.md`) is the *why* — design rationale, alternative-detector trade-offs, lifecycle/ownership, worked example.

---

## Alternatives considered

| Approach | Status | Why not |
|---|---|---|
| **A. Whole-pipeline regen** | rejected | Re-runs `resource-spec-initializer` (a no-op) and `endpoint-tables-writer` (Tables 1/2/3 can't move on a domain-only change) for nothing; rewrites all six tables across all surfaces; produces a noisy `git diff` for a one-field nested-type change. Equivalent to invoking `/rest-api-spec:generate-specs`. |
| **B. Per-sub-block splice** | rejected | The three table writers regenerate a whole table in one pass (no per-sub-block mode), so a splicer would have to diff fresh writer output against the live file at `**Nested:**` / `**Endpoint:**` granularity — significant new agent code (the rest-api analog of `spec-updater-approach-b.md`). The main payoff (preserving untouched content from regen drift) is small here — a domain-only change touches at most a handful of sub-blocks, and hand-edits aren't a preservation goal. Not worth the implementation cost. |
| **Per-writer regen (chosen)** | **accepted** | Reuses all three table writers verbatim — no contract changes; never re-runs the inventory writers; the unaffected tables are byte-stable. The new orchestration logic is preflight + tier dispatch + a cheap diagram scan for the referenced-type set — small, mechanical, regex-friendly. Accepts that a dirty writer rewrites its whole table (endpoints whose referenced types are unchanged get re-emitted byte-stable modulo LLM drift), the same drift-as-`git`-noise contract the persistence-spec and application-spec updaters already operate under. |

**Chaining (wired, domain-spec ≥ 0.29.0):** this updater runs as **Step 12 of domain `/update-specs`** — after the persistence Step 10 and application Step 11 chains, before the messaging Step 13 chain — reading the same `<stem>.domain/updates.md`. The cascade is unconditional (not file-presence-gated) and a missing `<stem>.rest-api/spec.md` (or input diagram) is a hard-fail that aborts the rest of the cascade — see the as-built "Chaining contract" in `persistence-spec/notes/spec-updater-approaches.md`. The chained step covers only the domain-driven axis; the commands/queries-diagram axis remains a separate trigger (the shared `application-spec:updates-detector` invocation discussed above, or a fresh `/rest-api-spec:generate-specs` run).
