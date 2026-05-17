# Commands / Queries Integration — Design (REST API)

This note documents the design for integrating the two new app-service-axis detector reports (`commands-updates.md`, `queries-updates.md`) into the existing `/rest-api-spec:update-specs` orchestrator, rather than creating a sibling skill for the app-service axis.

It supersedes the "Commands/queries-diagram changes are out of scope" item in [`spec-updater-approach.md`](spec-updater-approach.md) § "What this updater does NOT cover" and partially supersedes related call-outs about "the dominant axis" being out of scope.

For the detector design, see [`../../application-spec/notes/commands-queries-detectors-approach.md`](../../application-spec/notes/commands-queries-detectors-approach.md).
For the catalog of app-service-axis update types and the per-category dispatch table (including the REST API row), see [`../../application-spec/notes/commands-queries-update-types.md`](../../application-spec/notes/commands-queries-update-types.md).
For the report schema the detectors emit, see [`../../application-spec/notes/commands-queries-updates-report.md`](../../application-spec/notes/commands-queries-updates-report.md).
For the application-spec integration this note is modelled on, see [`../../application-spec/notes/commands-queries-integration-approach.md`](../../application-spec/notes/commands-queries-integration-approach.md).
For the existing domain-axis updater design this note extends, see [`spec-updater-approach.md`](spec-updater-approach.md).

---

## Decision

**Integrate the two new reports into `/rest-api-spec:update-specs`.** The orchestrator grows two additional input axes: in addition to `<stem>.domain/updates.md`, it consumes `<stem>.application/commands-updates.md` and `<stem>.application/queries-updates.md`. The cross-plugin path is deliberate — the detector reports are owned by application-spec and **shared** across application-spec, rest-api-spec, and messaging-spec consumers without duplication.

Rejected alternatives:

- A sibling skill `/rest-api-spec:update-app-service-rest-specs` for the app-service axis only.
- A rest-api-spec-local pair of detectors that re-diff the same two diagrams.

---

## Why integrate, not create

### The new reports are pure dispatch inputs

The existing skill is structured as Step 0 (verify inputs) → Step 1 (preflight) → Step 2 (dispatch tier) → Step 3 (table-writer regen) → Step 4 (updates writer) → Step 5 (report). The new reports are read **only** by Steps 0–2; Steps 3–4 are byte-identical regardless of which axis triggered them.

Per-step input audit:

| Step | Agent / logic | Reads |
|---|---|---|
| 3 | `response-fields-writer`, `request-fields-writer`, `parameter-mapping-writer` | `<stem>.md`, `<stem>.commands.md`, `<stem>.queries.md`, `<stem>.rest-api/spec.md`. No `updates.md` of any kind. |
| 3 (new) | `resource-spec-initializer`, `endpoint-tables-writer` | Same diagram inputs. No `updates.md`. |
| 4 | `rest-api-updates-writer` | Working-tree `spec.md` + `git HEAD`. (Reads `<stem>.domain/updates.md` only as a `Source delta` enrichment source; doesn't dispatch on it.) |

The writers regenerate from current diagrams. They don't know — and don't need to know — which axis triggered the run. The reports' only job is telling Step 2 *which writers* to fan out.

A sibling skill would therefore duplicate the entire Step 3–4 orchestration just to swap in a different Step 0–2 prelude that does the same dispatch math with different inputs.

### Two skills would fight over one output file

Both the existing skill and the hypothetical sibling write to `<dir>/<stem>.rest-api/updates.md`. `rest-api-updates-writer` is a snapshot writer — it diffs working-tree `spec.md` against `git HEAD` and overwrites the report wholesale. If both skills ran sequentially on a both-axes edit, the second's report-write overwrites the first's, and the first run's pipeline work (Tables 4/5/6 regen) is duplicated for nothing.

Splitting the report into two files (`domain-rest-api-updates.md` vs `app-service-rest-api-updates.md`) would fix the coherence problem but propagate the fragmentation into the future `/rest-api-spec:update-code` consumer's contract.

### Integration cost is bigger than application-spec's, but the structure is the same

The orchestrator changes amount to roughly 80 lines (vs. ~30 for application-spec — the difference is because the REST orchestrator must add agents to its repertoire, not just expand its dispatch math):

- **Step 0 verify**: 2 additional `test -f` checks on the app-service reports (or 2 detector invocations if Step 0 owns detection — see *Detector invocation* below).
- **Step 1 preflight**: per-axis-scoped gates (existing 1a–1c become 1.dom.a–1.dom.c; new 1.cmd.a / 1.qry.a for degraded baselines; new 1.all total-abort gate). The existing 1d (abort-and-reconcile for a renamed/removed referenced data type) stays as a domain-axis gate.
- **Step 2 dispatch**: union the per-axis dirty-flag predicates with new categories. Up to four new writers join the repertoire (see *Step 2 — Dispatch* below).
- **Step 3 ordering**: add `resource-spec-initializer` → `endpoint-tables-writer` *before* the existing Tables 4/5/6 writers (since 4/5/6 are scoped per-endpoint and consume Tables 2/3's row list).
- **Step 5 report**: extended summary line surfacing which axis (or axes) drove the regen.

Steps 4 (updates writer) is byte-identical.

---

## Cross-plugin path policy

The detector outputs live at `<dir>/<stem>.application/commands-updates.md` and `<dir>/<stem>.application/queries-updates.md` — paths owned by the application-spec plugin's per-aggregate folder convention. This orchestrator reads them but never writes there.

Rationale for keeping the reports in `<stem>.application/`, not moving them to a neutral location or duplicating into `<stem>.rest-api/`:

- They already exist on disk in `<stem>.application/` once the application detectors run.
- Moving them disrupts the application-spec orchestrator that already consumes them.
- The detectors describe the diagrams (`<stem>.commands.md`, `<stem>.queries.md`) — those diagrams sit in `<dir>/`, not under any plugin folder; the `<stem>.application/` location is incidental, chosen because the application-spec plugin "owns" the application-service diagrams as its primary input.
- All three consumer orchestrators (application, rest-api, messaging) reading **one shared report** per detector is strictly better than three plugin-local copies that could drift.

This cross-plugin dependency is unidirectional (rest-api-spec reads application-spec's plugin folder; application-spec never reads rest-api-spec's). Document the convention in `rest-api-spec:naming-conventions` so it's not an implicit contract.

---

## Detector invocation: where they run

The detectors are producers; this orchestrator is one of three consumers. Two ordering models for how the reports get onto disk:

| Model | Operator workflow | Pros | Cons |
|---|---|---|---|
| **A. Step 0 invokes detectors** | One command: `/rest-api-spec:update-specs <domain_diagram>` | One-shot workflow; reports always fresh | Up to triple invocation during the domain `/update-specs` cascade (each downstream skill re-invokes); orchestrator owns detector lifecycle |
| **B. Expect reports on disk** | `@commands-updates-detector …` + `@queries-updates-detector …` + `/rest-api-spec:update-specs …` | No redundant detector runs in the cascade; mirrors the current "consume domain `updates.md` produced by prior step" contract | Operator runs three commands; cascade entry path needs the cascade orchestrator to invoke them |

**Chosen: A.** Reasons:

- Matches the application-spec integration's choice (uniform mental model across the three plugins).
- The detectors are byte-stable on stable inputs — triple invocation during the cascade is wasted CPU, not a correctness problem.
- Standalone invocability stays trivial: the operator doesn't need to remember a separate detector step.
- The cascade-deduplication concern is real but is best addressed later by having the cascade orchestrator (`domain-spec:update-specs`) invoke the detectors once before the per-layer fan-out and have each downstream skill check for a fresh on-disk report. That is a follow-up, not a v1 requirement.

Standalone invocability is preserved: `@commands-updates-detector` and `@queries-updates-detector` remain ad-hoc-runnable.

---

## Step 0 — Verify inputs (extended)

Existing checks (0a–0d) are unchanged. Add detector invocations.

Order of operations:

1. Verify input diagrams + existing `spec.md` on disk (existing 0a–0d).
2. **Invoke `application-spec:commands-updates-detector` and `application-spec:queries-updates-detector` in parallel** with prompt `$ARGUMENTS[0]`. Wait for both to return.
3. If either detector hard-fails, abort the orchestrator with that detector's `ERROR:` line repeated verbatim. The other detector's output (if it completed) is left on disk.
4. `Read` the three reports (`<stem>.domain/updates.md`, `<stem>.application/commands-updates.md`, `<stem>.application/queries-updates.md`) into the Step 1 working set.

Rationale for parallel detector invocation: the two detectors are independent (no shared file, no shared state). Same parallel pattern application-spec already uses.

---

## Step 1 — Preflight (per-axis-scoped)

The existing skill's preflight (1a–1d) gates the **whole orchestrator**: any one fires → abort, no writes. With three reports in play this is too coarse — a degraded domain baseline shouldn't block app-service-axis regen if the app-service reports are clean.

Restructure the preflight into per-axis sub-blocks:

### 1.dom — Domain-axis gates

Existing 1a–1d, but each gate **disables only domain-axis dispatch** rather than aborting:

| Gate | Trigger | Action |
|---|---|---|
| 1.dom.a | Domain `_warning: HEAD ..._` line in Summary | Set `domain_axis_disabled = true` |
| 1.dom.b | `stereotype_changed` non-empty in domain | Set `domain_axis_disabled = true` |
| 1.dom.c | Aggregate-root removed in domain | Set `domain_axis_disabled = true` |
| 1.dom.d | `removed_or_renamed_data_types ∩ referenced_types` non-empty (existing abort-and-reconcile) | Set `domain_axis_disabled = true` |

Each disabled gate prints a `WARNING:` line (not `ERROR:`) describing what was skipped. 1.dom.d retains its existing abort-and-reconcile message — the operator must reconcile the application-service diagram and re-run, but only the domain axis is held back; commands/queries-axis triggers can still proceed.

### 1.cmd — Commands-axis gates

| Gate | Trigger | Action |
|---|---|---|
| 1.cmd.a | Commands `_warning: HEAD ..._` line in Summary | Set `commands_axis_disabled = true` |

(The commands detector itself hard-fails on stereotype change, anchor rename, multi-anchor — those never reach the orchestrator. The orchestrator only sees a `_warning:_` if HEAD was degraded.)

### 1.qry — Queries-axis gates

| Gate | Trigger | Action |
|---|---|---|
| 1.qry.a | Queries `_warning: HEAD ..._` line in Summary | Set `queries_axis_disabled = true` |

### 1.all — Total-abort gate

If all three `*_axis_disabled` flags are true → abort the orchestrator with an aggregated `ERROR:` summarizing what got disabled and pointing the operator to `/rest-api-spec:generate-specs <domain_diagram>`.

---

## Step 2 — Dispatch tier (three-way union)

The existing dispatch produces three booleans (`response_fields_dirty`, `request_fields_dirty`, `parameter_mapping_dirty`) keyed off `data-structures`, `value-objects`, and `commands` categories on the domain axis.

Expanded dispatch:

```
# Domain axis (existing rules, but axis-gated)
domain_response_fields_dirty   = ∅ if domain_axis_disabled else <existing rule>
domain_request_fields_dirty    = ∅ if domain_axis_disabled else <existing rule>
domain_parameter_mapping_dirty = ∅ if domain_axis_disabled else <existing rule>

# Commands-axis triggers (new)
commands_axis_triggers = ∅ if commands_axis_disabled else
    set(commands.affected_categories) & {"methods", "surface-markers"}
    # — categories from `commands-updates.md` that drive REST regen

# Queries-axis triggers (new)
queries_axis_triggers = ∅ if queries_axis_disabled else
    set(queries.affected_categories) & {"methods", "surface-markers"}
```

Per-category mapping to REST writers (cross-reference [`../../application-spec/notes/commands-queries-update-types.md`](../../application-spec/notes/commands-queries-update-types.md) § "Mapping `## Affected Categories` → consumer impact"):

| Category | Axis | Writer(s) it drives |
|---|---|---|
| `methods` | commands | `endpoint-tables-writer` (Table 3 add/remove rows); Tables 4/5/6 writers (refresh affected endpoint) |
| `methods` | queries | `endpoint-tables-writer` (Table 2 add/remove rows); Tables 4/5/6 writers (refresh affected endpoint) |
| `surface-markers` | commands or queries | `resource-spec-initializer` (Table 1 `Surfaces` row); `endpoint-tables-writer` (materialize / drop `## Surface:` sections; relocate endpoints between surfaces); Tables 4/5/6 writers (per-surface scoping) |
| `dependencies` / `raised-exceptions` / `external-interfaces` / `external-domain-events` / `messaging-markers` | either axis | Silently ignored — not REST-relevant |

Computed writer flags:

```
table_1_dirty           = ("surface-markers" in commands_axis_triggers ∪ queries_axis_triggers)
                          # Table 1's `Surfaces` row reflects the union of marker sets across both diagrams

tables_2_3_dirty        = ("methods" in commands_axis_triggers ∪ queries_axis_triggers)
                       or ("surface-markers" in commands_axis_triggers ∪ queries_axis_triggers)
                          # endpoint inventory + per-surface section set

response_fields_dirty   = domain_response_fields_dirty
                       or ("methods" in commands_axis_triggers ∪ queries_axis_triggers)
                       or ("surface-markers" in commands_axis_triggers ∪ queries_axis_triggers)

request_fields_dirty    = domain_request_fields_dirty
                       or ("methods" in commands_axis_triggers ∪ queries_axis_triggers)
                       or ("surface-markers" in commands_axis_triggers ∪ queries_axis_triggers)

parameter_mapping_dirty = domain_parameter_mapping_dirty
                       or ("methods" in commands_axis_triggers ∪ queries_axis_triggers)
                       or ("surface-markers" in commands_axis_triggers ∪ queries_axis_triggers)
```

Tier 3 no-op (every dirty flag false) → skip Step 3, still run Step 4 to emit a `_no changes_` report, then Step 5.

### Why `surface-markers` fans out to nearly every writer

A surface added (S1) materializes a brand-new `## Surface: <name>` section in `spec.md` — every table in that section (Tables 2/3 + per-endpoint Tables 4/5/6) must be filled. A surface removed (S2) symmetrically drops the section. A method moved between surfaces (S3) relocates its row in Tables 2/3 *and* its per-endpoint Tables 4/5/6 entries.

This is by design: the writer ownership of `## Surface: <name>` sections is monolithic — when a surface appears or disappears, all surface-scoped writers run.

---

## Step 3 — Per-writer regen (sequential, expanded repertoire)

The existing skill runs three writers (Tables 4/5/6) sequentially. The expanded skill adds two more, **in this order**:

| Order | Writer | When | Owns |
|---|---|---|---|
| 1 | `resource-spec-initializer` | `table_1_dirty` | Table 1 `Surfaces` row; per-surface `## Surface:` H2 headings (materialization / removal) |
| 2 | `endpoint-tables-writer` | `tables_2_3_dirty` | Tables 2 (Query Endpoints) + 3 (Command Endpoints) per surface |
| 3 | `response-fields-writer` | `response_fields_dirty` | Table 4 (Response Fields) per surface per endpoint |
| 4 | `request-fields-writer` | `request_fields_dirty` | Table 5 (Request Fields) per surface per endpoint |
| 5 | `parameter-mapping-writer` | `parameter_mapping_dirty` | Table 6 (Parameter Mapping) per surface per endpoint |

**Why sequential, not parallel.** All writers edit the single `spec.md` in place. Same constraint the existing skill already operates under. Additionally, `endpoint-tables-writer` must run before Tables 4/5/6 writers because the latter scope per-endpoint and need the freshly written Tables 2/3 to know which endpoints exist; `resource-spec-initializer` must run before `endpoint-tables-writer` because the per-surface `## Surface:` sections it materializes are where `endpoint-tables-writer` writes Tables 2/3.

Each writer parses the diagrams fresh and re-renders its owned table(s) in place. The writers do not read any `updates.md`; they have no per-axis dispatch — re-running on identical diagrams produces byte-identical output modulo LLM nondeterminism.

### Abort-and-reconcile (runtime)

A table writer can abort at runtime even though gate 1.dom.d passed — specifically when a renamed/removed type is referenced *transitively* (a referenced type's field, or that field's field). The existing abort flow surfaces `Cannot resolve …` and produces no edit; the orchestrator emits a single `ERROR:` line and exits. Earlier-sequenced writers may have already edited `spec.md`; those edits are left in place, and re-running idempotently overwrites them.

The new writers (`resource-spec-initializer`, `endpoint-tables-writer`) can also abort — e.g. a surface marker name that's not a valid kebab-case identifier, or a method signature the parser can't tokenize. The orchestrator surfaces those aborts verbatim per the same pattern.

---

## Steps 4–5 — Unchanged Step 4; extended Step 5 summary

**Step 4** — `rest-api-updates-writer` always runs (even on Tier 3 no-op).

> *Follow-up:* the updates writer currently reads only `<stem>.domain/updates.md` for `Source delta` attribution. Extending it to also read `<stem>.application/{commands,queries}-updates.md` for app-service-axis attribution is a v2 enhancement — not blocking for this integration.

**Step 5 — extended summary line.** The summary needs to surface which axis (or axes) drove the regen. Suggested shape:

```
Updated <stem>.rest-api/spec.md (<regen_clause>; triggers: <axis_summary>) and emitted <stem>.rest-api/updates.md.
```

Where:

- `<regen_clause>` names exactly the tables whose writer ran, in writer-order (e.g. `regenerated Table 1 + Tables 2/3 + Tables 4, 5 & 6`, or the existing-style `regenerated Tables 4, 5 & 6`).
- `<axis_summary>` is one of `domain`, `commands-diagram`, `queries-diagram`, `domain + commands-diagram`, ..., or any combination — same vocabulary as the application-spec integration.

If any preflight axis was disabled by a 1.dom / 1.cmd / 1.qry gate, prepend the `WARNING:` line(s) before the summary.

---

## Failure semantics (extended)

Existing semantics: orchestrator does not roll back partial writes; re-running is the supported recovery path.

New cases:

- **Step 0 detector hard-fail** — orchestrator aborts with the detector's `ERROR:` line verbatim. The other detector's report (if completed) is left on disk. Re-running re-runs both detectors.
- **Total preflight abort (1.all)** — no writes; operator runs `/rest-api-spec:generate-specs`.
- **Partial preflight disable (1.dom xor 1.cmd xor 1.qry)** — the enabled axes regenerate as normal; the disabled axis's WARNING is surfaced in Step 5.
- **Step 3 writer aborts** — existing behaviour: surface the aborting writer's message verbatim; earlier-sequenced writers' edits are left in place; re-running is idempotent.

---

## What this does NOT change

- **Existing skill contract for the domain axis** — every existing gate, dispatch rule, and writer invocation continues to apply. A domain-only edit produces the same output as before (modulo the detector invocations at Step 0, which are no-ops on a clean app-service working tree).
- **Existing writer contracts** — `response-fields-writer`, `request-fields-writer`, `parameter-mapping-writer`: unchanged. `rest-api-updates-writer`: unchanged in this integration (extension to app-service-axis source attribution is a follow-up).
- **New writer contracts** — `resource-spec-initializer` and `endpoint-tables-writer` already exist (used by `/rest-api-spec:generate-specs`). They are idempotent on stable inputs; no contract change needed to integrate them into the updater repertoire.
- **`<dir>/<stem>.rest-api/spec.md` schema** — unchanged.
- **`<dir>/<stem>.rest-api/updates.md` schema** — still produced by `rest-api-updates-writer` snapshot-style; the report describes spec deltas, not which axis triggered them.
- **Application-spec orchestrator** — unaffected. The shared detectors are write-once-read-many.

---

## What this DOES change

| File | Change |
|---|---|
| `plugins/rest-api-spec/skills/update-specs/SKILL.md` | Extend Step 0 to invoke both app-service detectors; extend Step 1 to per-axis-scoped gates; extend Step 2 to three-way union dispatch with new writer flags; extend Step 3 to add `resource-spec-initializer` and `endpoint-tables-writer` to the sequenced repertoire; extend Step 5 summary line; update the frontmatter `description` to drop "domain-driven axis only" |
| `plugins/rest-api-spec/notes/spec-updater-approach.md` | Drop the "Commands/queries-diagram changes are out of scope — and they are the dominant axis" item from § "What this updater does NOT cover"; soften the "domain diagram's contribution is so narrow that the median domain change leaves `spec.md` byte-identical" claim in the Goal section (still true for *domain-only* edits, no longer true generally); add a back-reference to this note |
| `plugins/rest-api-spec/skills/naming-conventions/SKILL.md` | Document the cross-plugin path convention: `<stem>.application/commands-updates.md` and `<stem>.application/queries-updates.md` are consumed by this plugin even though they live under application-spec's per-aggregate folder |
| `plugins/rest-api-spec/.claude-plugin/plugin.json` | Bump `version` (user-visible orchestrator behaviour change) |

No new skill file. No new agent file. The two detector agents already exist in application-spec; the two newly-recruited writer agents already exist in rest-api-spec.

---

## Alternatives considered

| Approach | Status | Why not |
|---|---|---|
| **Sibling skill `/rest-api-spec:update-app-service-rest-specs` for the app-service axis only** | rejected | Same arguments as application-spec made: duplicates Steps 3–4 orchestration; two skills fight over one output file; forces operator to run two commands on both-axes edits. |
| **Sibling skill + per-axis report files** (`domain-rest-api-updates.md` vs `app-service-rest-api-updates.md`) | rejected | Solves report coherence but propagates fragmentation into the future `/rest-api-spec:update-code` consumer's contract. |
| **rest-api-spec-local pair of detectors** that re-diff `<stem>.commands.md` and `<stem>.queries.md` | rejected | Duplicates the application-spec detectors' work; produces redundant reports; same diff math performed three times across the three downstream plugins. The shared-detector design is exactly what `commands-queries-detectors-approach.md` chose to avoid. |
| **Umbrella skill that chains all per-layer updaters** | rejected | Doesn't address the orchestrator's own consumption path — still needs the per-layer dispatch to know what to regenerate. The umbrella is orthogonal. |
| **Integrate into `/rest-api-spec:update-specs` (chosen)** | **accepted** | Reports are pure dispatch inputs; Step 3 adds new writers to an existing repertoire (not a parallel pipeline); one output file means one coherent report per run; one operator command for any combination of axes touched. |

---

## Open questions

- **`Source delta` enrichment in `rest-api-updates-writer`** — currently reads only `<stem>.domain/updates.md`. Extending to also read the app-service-axis reports for per-section attribution is a clean follow-up. Not blocking for v1.
- **Cascade-deduplication** — when domain `/update-specs` cascades through application → rest-api → messaging, each downstream skill re-invokes the detectors. Byte-stable on stable inputs, but wasteful. Best fix is to have the cascade orchestrator invoke detectors once and have downstream skills detect the fresh on-disk reports — defer until measured.
- **Should `resource-spec-initializer` ever re-run for Table 1 fields other than `Surfaces`?** A change to the `<<Aggregate Root>>` class name is a hard-fail (1.dom.c) — no regen path. A change to the resource's plural lives in the application-service diagrams (Table 1's `Plural` row), which is a separate consideration. Currently the dispatch only re-runs the initializer for `surface-markers` triggers; if `Plural` also becomes axis-driven, this dispatch widens. Decide when implementing.
- **Surface-marker churn diff granularity.** A surface added is a coarse signal — every endpoint in the new surface fans out through Tables 2/3/4/5/6. A surface renamed (which the detector reports as removed + added) over-regenerates. Worth a v2 narrowing once we see how often surfaces get renamed in practice.

---

## Out of scope for this note

- **The `<stem>.rest-api/updates.md` schema** — owned by [`updates-report.md`](updates-report.md). No schema change is required for the integration.
- **The detector agents themselves** — owned by application-spec. This note treats them as a stable external dependency.
- **Code-axis updaters** (`/rest-api-spec:update-code` and downstream) — consume `<stem>.rest-api/updates.md`; their contract is unaffected by the integration.
- **Cross-plugin scheduling** — when both application-spec and rest-api-spec consume the same detector reports, do they need to coordinate? No: the detectors are pure producers and the consumers' writes never collide (application-spec writes `<stem>.application/{commands,queries}.specs.md` + `services.md`; rest-api-spec writes `<stem>.rest-api/spec.md`). Independent.
