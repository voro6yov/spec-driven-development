# Commands Integration — Design (Messaging)

This note documents the design for integrating the new app-service-axis commands-detector report (`commands-updates.md`) into the existing `/messaging-spec:update-specs` orchestrator, rather than building a messaging-spec-local commands-diagram detector.

It supersedes the "commands-diagram trigger axis" item in [`spec-updater-approach.md`](spec-updater-approach.md) § "Out of scope (deliberate)" / "What this updater does NOT cover" — that section explicitly anticipated this integration as the future fix.

Only the **commands** report is consumed: messaging is command-side only — there is no per-consumer subscription to query-side operations, no `<Resource>Queries`-driven messaging artifact. The queries-updates report is irrelevant here.

For the detector design, see [`../../application-spec/notes/commands-queries-detectors-approach.md`](../../application-spec/notes/commands-queries-detectors-approach.md).
For the catalog of app-service-axis update types and the per-category dispatch table (including the messaging row), see [`../../application-spec/notes/commands-queries-update-types.md`](../../application-spec/notes/commands-queries-update-types.md).
For the report schema the detector emits, see [`../../application-spec/notes/commands-queries-updates-report.md`](../../application-spec/notes/commands-queries-updates-report.md).
For the application-spec integration this note is modelled on, see [`../../application-spec/notes/commands-queries-integration-approach.md`](../../application-spec/notes/commands-queries-integration-approach.md).
For the existing domain-axis updater design this note extends, see [`spec-updater-approach.md`](spec-updater-approach.md).

---

## Decision

**Integrate `commands-updates.md` into `/messaging-spec:update-specs`.** The orchestrator grows a second input axis: in addition to `<stem>.domain/updates.md`, it consumes `<stem>.application/commands-updates.md`. The cross-plugin path is deliberate — the detector report is owned by application-spec and **shared** across application-spec, rest-api-spec, and messaging-spec consumers without duplication.

Rejected alternatives:

- A messaging-spec-local commands-diagram detector (the `messaging-spec:updates-detector` placeholder mentioned in [`spec-updater-approach.md`](spec-updater-approach.md) § "Out of scope (deliberate)" item 4 and § "Adjacent designs deliberately not adopted yet" item 1).
- A sibling skill `/messaging-spec:update-app-service-messaging-specs` for the commands-axis only.

---

## Why integrate, not create

### The new report is a pure dispatch input

Walking the existing skill's steps: the new report is read only by Steps 0–4; Steps 5–6 are byte-identical regardless of which axis triggered them.

Per-step input audit:

| Step | Agent / logic | Reads |
|---|---|---|
| 0 | file-presence checks; consumer enumeration | `<stem>.domain/updates.md`, `<stem>.commands.md`, `<stem>.messaging/*.md`. No commands-axis report. |
| 5 | `event-tables-writer`, `event-fields-writer` | `<stem>.commands.md`, `<stem>.md`, `<stem>.messaging/<C>.md`. No `updates.md` of any kind. |
| 6 | `messaging-updates-writer` | Working-tree consumer specs + `git HEAD` + `<stem>.domain/updates.md` (for source attribution). |

The writers regenerate from current diagrams. They don't know — and don't need to know — which axis triggered the run. The report's only job is telling Steps 2–4 which consumers and which lifecycle transitions to dispatch.

### A messaging-spec-local detector would duplicate work

The application-spec commands-updates-detector already diffs `<stem>.commands.md` and emits everything messaging needs:

- `messaging-markers` category — consumer add/remove (X1/X2); per-consumer row add/remove/change (X3/X4); arrow flip (X5).
- `external-domain-events` category — external event lifecycle (L1/L2) and attribute changes (M7).
- `methods` category — `on_<event>` handler signature changes (M4) bound by a `%% Messaging` row.

A messaging-spec-local detector would re-implement the same Mermaid parsing logic against the same diagram and produce a strict subset of the same information. Wasteful; risks drift between the two parsers.

The shared-detector design ([`commands-queries-detectors-approach.md`](../../application-spec/notes/commands-queries-detectors-approach.md)) explicitly anticipates this — its report schema includes the `messaging-markers` and `external-domain-events` categories specifically so messaging-spec can dispatch on them.

### One output file per run

Both this skill (after integration) and `messaging-updates-writer` write to `<dir>/<stem>.messaging/updates.md`. Keeping the single skill means a single coherent report per run; a sibling skill would either fight over the file or fragment the report.

### Integration cost is moderate

The orchestrator changes amount to roughly 50 lines:

- **Step 0 verify**: 1 additional detector invocation (only the commands detector — queries is irrelevant for messaging).
- **Step 1 preflight**: 4 existing domain-axis gates become per-axis-scoped (1.dom.a–1.dom.d); new 1.cmd.a (commands degraded). New 1.all total-abort gate.
- **Step 2 consumer enumeration**: extended — must consider commands-axis X1 (consumer added) as a *signal* but defer the actual consumer-spec init to `/messaging-spec:generate-code` (see *Step 2 — Consumer enumeration* below).
- **Steps 3–4 affected-set computation**: union the per-axis dispatch signals. Commands-axis contributes via `messaging-markers`, `external-domain-events`, and a filtered `methods` (only handlers bound by a `%% Messaging` row).
- **Step 7 report**: extended summary line surfacing which axis (or axes) drove the regen.

Step 5 (writer fan-out) and Step 6 (updates writer) are byte-identical.

---

## Cross-plugin path policy

The detector output lives at `<dir>/<stem>.application/commands-updates.md` — a path owned by the application-spec plugin's per-aggregate folder convention. This orchestrator reads it but never writes there.

Same rationale as the rest-api-spec integration (see [`../../rest-api-spec/notes/commands-queries-integration-approach.md`](../../rest-api-spec/notes/commands-queries-integration-approach.md) § "Cross-plugin path policy"):

- The report already exists on disk in `<stem>.application/` once the application detector runs.
- All three consumer orchestrators reading **one shared report** is strictly better than three plugin-local copies.
- The cross-plugin dependency is unidirectional (messaging-spec reads application-spec's plugin folder; never the reverse).

Document the convention in `messaging-spec:naming-conventions`.

---

## Detector invocation: where it runs

Same trade-off as application-spec and rest-api-spec. **Chosen: Step 0 invokes the detector.** Reasons:

- Matches the application-spec and rest-api-spec integrations (uniform mental model across the three plugins).
- The detector is byte-stable on stable inputs — triple invocation during the cascade is wasted CPU, not a correctness problem.
- Standalone invocability stays trivial.

Only the **commands** detector is invoked — the queries detector is irrelevant to messaging and would be wasted work.

Standalone invocability is preserved: `@commands-updates-detector` remains ad-hoc-runnable.

---

## Step 0 — Verify inputs (extended)

Existing checks (0a–0c) are unchanged. Add detector invocation.

Order of operations:

1. Verify domain `updates.md`, commands diagram, and enumerate consumer specs (existing 0a–0c). The "no consumer specs → true no-op" exit (0c) needs revisiting — see *Step 2 — Consumer enumeration* below.
2. **Invoke `application-spec:commands-updates-detector`** with prompt `$ARGUMENTS[0]`.
3. If the detector hard-fails, abort the orchestrator with its `ERROR:` line repeated verbatim.
4. `Read` both reports (`<stem>.domain/updates.md`, `<stem>.application/commands-updates.md`) into the Step 1 working set.

### Reconsidering the Step 0c "no consumers" early exit

Existing behaviour: if `<stem>.messaging/` is absent or holds no consumer specs, the skill prints "nothing to update" and exits.

With the commands-axis integration, a new consideration: the commands diagram may now declare a `%% Messaging - <C>` block for a consumer that **does not yet have** a consumer spec on disk — this is X1 (consumer added) from the detector's perspective. Two reasonable responses:

| Response | Pros | Cons |
|---|---|---|
| **A. Route X1 to `/messaging-spec:generate-code`** (current Step 0c stays; X1 is a `WARNING:` in the report, not an action) | Keeps the skill focused on *updating existing* specs; consumer-spec init is interview-driven via `consumer-spec-initializer`, which `/messaging-spec:generate-code` already orchestrates | Operator runs two commands for a "new consumer + domain edit" workflow |
| **B. Invoke `consumer-spec-initializer` + `consumer-scaffolder`** for each new X1 consumer | One-shot workflow | Significantly expands the skill's repertoire; `consumer-scaffolder` requires a target-locations report (a code-side concern); the orchestrator grows a new "init" mode beyond "update" |

**Chosen: A.** Reasons:

- The existing Step 0c "no consumers → no-op exit" matches the chained-cascade-safety contract (the skill is wired into domain `/update-specs` as Step 13 and must not abort the cascade when the messaging layer doesn't exist).
- `/messaging-spec:generate-code` already owns the init path end-to-end (consumer-spec-initializer → scaffolder → implementers → tests). Reusing it for X1 is cleaner than duplicating its first half here.
- The X1 signal is still **surfaced** — `messaging-updates-writer` records the new-consumer-needs-init notice in `updates.md` (Step 6 enhancement), and Step 7's summary line emits a `WARNING:` per X1 consumer with the operator instruction.

So Step 0c stays as-is for the *absent-folder* case (true no-op). When the folder exists but a new `%% Messaging - <C>` block declares a consumer for which no spec exists yet, the orchestrator proceeds through Steps 1–6 normally for the existing consumers and surfaces the X1 consumer as a `WARNING:` in Step 7.

### Symmetric handling of X2 (consumer removed)

The detector also signals consumer removal — a `%% Messaging - <C>` block disappeared from the commands diagram while the consumer spec `<stem>.messaging/<C>.md` is still on disk. The orchestrator does **not** silently delete the consumer spec — the operator's contract is "the skill writes inside specs, not deletes spec files". The X2 signal becomes a `WARNING:` in the report and the summary line, recommending the operator delete the now-orphaned consumer spec file (and run `/messaging-spec:generate-code` to reconcile the code side).

---

## Step 1 — Preflight (per-axis-scoped)

The existing skill's preflight (1a–1d) gates the **whole orchestrator**: any one fires → abort, no writes. With two reports in play this is too coarse — a degraded domain baseline shouldn't block commands-axis regen if the commands report is clean (and vice versa).

Restructure the preflight into per-axis sub-blocks:

### 1.dom — Domain-axis gates

Existing 1a–1d, but each gate **disables only domain-axis dispatch**:

| Gate | Trigger | Action |
|---|---|---|
| 1.dom.a | Domain `_warning: HEAD ..._` line in Summary | Set `domain_axis_disabled = true` |
| 1.dom.b | Aggregate root removed or stereotype-demoted | Set `domain_axis_disabled = true` |
| 1.dom.c | Aggregate root renamed | Set `domain_axis_disabled = true` |
| 1.dom.d | Any other stereotype change | Set `domain_axis_disabled = true` |

Note: domain-axis hard-fails are reasonably severe for messaging (an aggregate-root rename cascades into the `<stem>.messaging/` folder name, the import root, the `%% Messaging` markers' `<Source>` cells), so the existing hard-fail messages stay as the WARNING text — the operator should reconcile and re-run rather than proceed half-blind.

### 1.cmd — Commands-axis gates

| Gate | Trigger | Action |
|---|---|---|
| 1.cmd.a | Commands `_warning: HEAD ..._` line in Summary | Set `commands_axis_disabled = true` |

The commands detector itself hard-fails on stereotype change, anchor rename, multi-anchor — those never reach the orchestrator.

### 1.all — Total-abort gate

If both `domain_axis_disabled` AND `commands_axis_disabled` → abort the orchestrator with an aggregated `ERROR:` pointing the operator to `/messaging-spec:generate-code <domain_diagram> <consumer>` per consumer.

---

## Step 2 — Consumer enumeration (unchanged, but referenced from Step 4)

Existing Step 2 enumerates consumers from `<stem>.messaging/*.md` and parses each consumer's Table 2 to get `internal_subs[C]`. No structural change — the consumer-enumeration source remains the on-disk consumer-spec set, not the commands report.

Reason: the consumer-spec file *is* the unit being updated. A new consumer declared in the commands diagram but not yet initialized is handled per *Reconsidering the Step 0c …* above (Step 7 surfaces a WARNING; no spec-file-init here).

---

## Step 3 — Abort-and-reconcile gate (extended)

Existing Step 3 computes `dangling[C] := internal_subs[C] ∩ removed_or_renamed_events` (domain axis) — a consumer subscribing to an internal event the domain diagram no longer declares.

Extended: also consider the commands-axis signal that the `%% Messaging - <C>` block referencing the dangling internal event was *also* dropped or renamed in the working tree. If yes, the operator already reconciled the commands diagram and the regen will succeed; this consumer drops out of the aborted set.

The check:

```
dangling[C] = internal_subs[C] ∩ removed_or_renamed_events  # existing
            - rows_already_removed_from_commands[C]          # new: from commands.messaging-markers
```

Where `rows_already_removed_from_commands[C]` is the set of internal-event names removed from the `%% Messaging - <C>` block per the commands report's `## Messaging Markers → ### <C>` block.

This converts an "abort-and-reconcile" into a clean regen when the operator's edit covered both diagrams. The existing per-consumer WARNING text still surfaces for truly-dangling consumers.

---

## Step 4 — Compute affected consumers (three-way union)

Existing dispatch:

```
affected := { C ∉ aborted : internal_subs[C] ∩ keys(event_attr_deltas) ≠ ∅ }
```

Extended:

```
# Domain-axis contribution (existing rule, axis-gated)
domain_affected = ∅ if domain_axis_disabled else
    { C ∉ aborted : internal_subs[C] ∩ keys(event_attr_deltas) ≠ ∅ }

# Commands-axis contribution (new)
commands_affected = ∅ if commands_axis_disabled else (
    # X3/X4/X5: row added/removed/changed inside any existing consumer
    { C : C ∈ existing_consumers ∧ commands_report.messaging_markers[C].rows_changed ≠ ∅ }
    ∪
    # M4 filtered: `methods` triggered by an on_<event> handler change bound by C
    { C : ∃ handler bound by %% Messaging - C whose signature changed }
    ∪
    # M7: external event attribute change ripples into Table 3 of every consumer
    # whose Table 2 has an `external` row referencing the changed event
    { C : ∃ external-row in Table 2(C) referencing changed_external_events }
)

# Union
affected = domain_affected ∪ commands_affected
```

Tier-3 no-op (every set empty) → skip Step 5, still run Step 6 to emit `updates.md`, then Step 7 with the no-op summary.

### Per-category mapping

Cross-reference [`../../application-spec/notes/commands-queries-update-types.md`](../../application-spec/notes/commands-queries-update-types.md) § "Mapping `## Affected Categories` → consumer impact":

| Commands-axis category | Effect |
|---|---|
| `messaging-markers` X1 (consumer added) | Step 7 WARNING — route to `/messaging-spec:generate-code` |
| `messaging-markers` X2 (consumer removed) | Step 7 WARNING — orphaned consumer spec; operator deletes file + re-runs |
| `messaging-markers` X3/X4/X5 (row changes within existing consumer) | Add to `commands_affected` — Tables 2/3 regen via existing Step 5 |
| `external-domain-events` (external event attribute change) | Add affected consumers — every consumer with an `external` Table 2 row referencing the event |
| `methods` (anchor public method change) | Add affected consumers — but only those whose changed method is bound by a `%% Messaging` row (filter against `internal_subs[C]` row's `command_method` column) |
| `dependencies` / `raised-exceptions` / `external-interfaces` / `surface-markers` | Silently ignored — not messaging-relevant |

The filter on `methods` is important — most anchor method changes are not handler changes, so most `methods` signals don't fire messaging-axis dispatch.

---

## Step 5 — Regenerate Tables 2–3 per affected consumer (unchanged)

Existing two-round parallel fan-out:

1. Round 1 — `event-tables-writer` per consumer in parallel (refreshes Table 2 from current `%% Messaging` markers).
2. Round 2 — `event-fields-writer` per consumer in parallel (rebuilds Table 3 wholesale from current handler signatures + event class attribute lists).

No structural change. Both writers are byte-stable on stable inputs and already handle the commands-axis-driven cases (Table 2 row add/remove from `event-tables-writer`; Table 3 regen from `event-fields-writer`).

---

## Step 6 — Emit the messaging updates report (extended scope)

`messaging-updates-writer` already runs unconditionally per successful run. Extension scope:

- The writer should additionally read `<stem>.application/commands-updates.md` for source attribution and to render `X1` (consumer-needs-init) and `X2` (orphaned consumer) advisory blocks in the report body.
- The per-consumer status vocabulary (`updated` / `aborted` / `unaffected`) gains two new outcomes: `needs-init` (X1) and `orphaned` (X2). Both render a recommended action.

> *Follow-up:* this writer extension is desirable but not strictly required for v1. A simpler v1 surfaces X1/X2 only in Step 7's WARNING lines and leaves `updates.md` describing existing-consumer transitions only.

---

## Step 7 — Report (extended summary line)

Existing one-line summary needs to surface which axis drove the regen and the new X1/X2 outcomes.

Suggested shape:

```
Processed <stem>.messaging/ — <k> consumer(s) regenerated (<names>), <f> failed (<names>),
<m> aborted (<names>), <n> unaffected, <i> need init (<names>), <o> orphaned (<names>);
triggers: <axis_summary>; emitted <stem>.messaging/updates.md.
```

Where:

- `<i>` = `needs-init` count (new X1 consumers); each accompanied by a `WARNING:` line directing the operator to `/messaging-spec:generate-code <domain_diagram> <C>`.
- `<o>` = `orphaned` count (X2 consumers); each accompanied by a `WARNING:` line recommending `rm <stem>.messaging/<C>.md` and a `/messaging-spec:generate-code` follow-up.
- `<axis_summary>` is `domain`, `commands-diagram`, or `domain + commands-diagram` — same vocabulary as the application-spec integration.

Drop any clause whose count is zero.

If any preflight axis was disabled by a 1.dom / 1.cmd gate, prepend the `WARNING:` line(s) before the summary.

---

## Failure semantics (extended)

Existing semantics: orchestrator does not roll back partial writes; re-running is the supported recovery path.

New cases:

- **Step 0 detector hard-fail** — orchestrator aborts with the detector's `ERROR:` line verbatim. Re-running re-invokes the detector.
- **Total preflight abort (1.all)** — no writes; operator runs `/messaging-spec:generate-code <domain_diagram> <consumer>` per consumer.
- **Partial preflight disable (1.dom xor 1.cmd)** — the enabled axis regenerates as normal; the disabled axis's WARNING is surfaced in Step 7.
- **X1 / X2 advisory** — never a failure; surfaced as WARNING + recorded in the updates report. Operator-action items, not blockers.

The existing per-consumer abort (Step 3) and per-consumer writer failure (Step 5) semantics are unchanged.

---

## What this does NOT change

- **Existing skill contract for the domain axis** — every existing gate, dispatch rule, and writer invocation continues to apply. A domain-only edit produces the same output as before (modulo the detector invocation at Step 0, which is a no-op on a clean commands working tree).
- **Existing writer contracts** — `event-tables-writer`, `event-fields-writer`: unchanged. `messaging-updates-writer`: the writer extension (X1/X2 advisory blocks; commands-axis source attribution) is a follow-up; v1 of the integration can defer it and surface X1/X2 only in Step 7 WARNING lines.
- **`<dir>/<stem>.messaging/<consumer>.md` schema** — unchanged.
- **`<dir>/<stem>.messaging/updates.md` schema** — extended *if* the v1 cut includes the writer extension above; otherwise unchanged.
- **Application-spec and rest-api-spec orchestrators** — unaffected. The shared detector is write-once-read-many.
- **Consumer-spec init / scaffold flow** — owned by `/messaging-spec:generate-code`. This skill never invokes `consumer-spec-initializer` or `consumer-scaffolder`. X1 consumers are surfaced as WARNINGs that direct the operator to the init pipeline.

---

## What this DOES change

| File | Change |
|---|---|
| `plugins/messaging-spec/skills/update-specs/SKILL.md` | Extend Step 0 to invoke `commands-updates-detector`; extend Step 1 to per-axis-scoped gates; extend Step 3 to deduct already-reconciled rows from the dangling set; extend Step 4 to three-way union dispatch (`messaging-markers` X3/X4/X5, `external-domain-events`, filtered `methods`); extend Step 7 summary line with X1/X2 outcomes + axis trigger; update the frontmatter `description` to drop "domain-diagram axis only" |
| `plugins/messaging-spec/notes/spec-updater-approach.md` | Drop "The commands-diagram trigger axis" item from § "Out of scope (deliberate)"; supersede the "Adjacent designs deliberately not adopted yet → messaging-spec:updates-detector" item with a back-reference to this note; add a back-reference to this note |
| `plugins/messaging-spec/skills/naming-conventions/SKILL.md` | Document the cross-plugin path convention: `<stem>.application/commands-updates.md` is consumed by this plugin even though it lives under application-spec's per-aggregate folder |
| `plugins/messaging-spec/agents/messaging-updates-writer.md` *(v2 — see [`messaging-updates-writer-commands-axis.md`](messaging-updates-writer-commands-axis.md))* | Read `<stem>.application/commands-updates.md` for source attribution; render X1 (needs-init) and X2 (orphaned) advisory blocks |
| `plugins/messaging-spec/skills/updates-report-template/SKILL.md` *(v2 — see [`messaging-updates-writer-commands-axis.md`](messaging-updates-writer-commands-axis.md))* | Add `needs-init` and `orphaned` status to the per-consumer status vocabulary; document the advisory block shapes; document the axis-tagged `Source delta` grammar; document the `## Operator Actions` H2 placement |
| `plugins/messaging-spec/.claude-plugin/plugin.json` | Bump `version` (user-visible orchestrator behaviour change) |

No new skill file. No new agent file. The detector agent already exists in application-spec.

---

## Alternatives considered

| Approach | Status | Why not |
|---|---|---|
| **A messaging-spec-local `commands-updates-detector`** | rejected | Duplicates the application-spec detector's parsing logic against the same diagram; produces a strict subset of the same information; the shared-detector design ([`commands-queries-detectors-approach.md`](../../application-spec/notes/commands-queries-detectors-approach.md)) explicitly chose the cross-plugin sharing pattern. |
| **Sibling skill `/messaging-spec:update-app-service-messaging-specs` for the commands-axis only** | rejected | Same arguments as application-spec made: duplicates Steps 5–6 orchestration; two skills fight over `<stem>.messaging/updates.md`; forces operator to run two commands on both-axes edits. |
| **Have the skill auto-init X1 consumers** (invoke `consumer-spec-initializer` + `consumer-scaffolder`) | rejected | Expands the skill's repertoire across a fundamentally different mode (init vs update); `consumer-scaffolder` requires a target-locations report (a code-side concern this update-specs skill avoids); a one-shot operator command is a Step-7 WARNING away. Routing to `/messaging-spec:generate-code` keeps update-specs focused. |
| **Auto-delete X2 orphaned consumer specs** | rejected | Violates the operator-controls-the-file-system principle; an orphaned spec file may carry hand-authored notes worth preserving before deletion. Surface as WARNING, let the operator decide. |
| **Integrate into `/messaging-spec:update-specs` (chosen)** | **accepted** | Report is a pure dispatch input; Steps 5–6 are byte-identical; one output file means one coherent report per run; one operator command for any combination of axes touched. |

---

## Open questions

- **`messaging-updates-writer` extension for X1/X2 advisory blocks** — *Resolved by [`messaging-updates-writer-commands-axis.md`](messaging-updates-writer-commands-axis.md).* The v2 design lands the `needs-init` and `orphaned` per-consumer statuses, the axis-tagged `Source delta` grammar, the `## Operator Actions` H2 between `## Consumer Changes` and `## Affected Artifacts`, the two-line `(domain-updates-hash, commands-updates-hash)` sentinel block, and the commands-updates source missing + race-condition warnings. The writer reads `<dir>/<stem>.application/commands-updates.md` as a non-fatal sibling input (same posture as the existing missing-`<domain_updates_file>` rule) and never opens the Mermaid commands diagram itself — it consumes the detector's report.
- **Filtered `methods` dispatch precision** — the filter "anchor method bound by a `%% Messaging` row" requires the orchestrator to cross-reference the commands report's `## Per-Method Changes` against each consumer's Table 2 `command_method` column. This is a straightforward join but adds parsing surface. Worth measuring whether the simpler "any `methods` signal triggers all consumers with internal subscriptions" over-regenerates noticeably in practice — if not, simplify.
- **Cascade-deduplication** — same concern as application-spec and rest-api-spec; defer.
- **X2 conflict with the existing per-consumer abort (Step 3)** — an internal event removed in the domain diagram *and* the `%% Messaging` block referencing it dropped from the commands diagram in the same operator edit. Step 3's new "deduct already-reconciled rows" rule handles this correctly: the consumer is no longer dangling, but may now be X2 (the whole `%% Messaging - <C>` block dropped) — surface as X2 WARNING, skip regen. Worth a worked example in the SKILL.md.

---

## Out of scope for this note

- **The `<stem>.messaging/updates.md` schema baseline** — owned by [`updates-report.md`](updates-report.md). The X1/X2 advisory extension is documented here as a v2 enhancement; the baseline schema is unchanged.
- **The detector agent itself** — owned by application-spec. This note treats it as a stable external dependency.
- **The command-handler side of a consumer** — Table 1's *Commands queue name* is the only consumer-spec trace of the command side; domain `<<Command>>` changes ripple into generated `command-handlers` / `command-replies` / `command-dispatchers` code only, reconciled by `/messaging-spec:generate-code`. This integration does not change the modeling gap flagged in `spec-updater-approach.md` § "Out of scope (deliberate)" item 5.
- **Code-axis updaters** (`/messaging-spec:update-code` and downstream) — consume `<stem>.messaging/updates.md`; their contract is largely unaffected (the X1/X2 status values, if added, would be informational for them too).
- **Cross-plugin scheduling** — when application-spec, rest-api-spec, and messaging-spec all consume the same commands report, do they need to coordinate? No: the detector is a pure producer and the consumers' writes never collide (each writes inside its own per-plugin folder).
