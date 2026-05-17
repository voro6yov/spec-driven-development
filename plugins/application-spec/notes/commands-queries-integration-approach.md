# Commands / Queries Integration — Design

This note documents the design for integrating the two new app-service-axis detector reports (`commands-updates.md`, `queries-updates.md`) into the existing `/application-spec:update-specs` orchestrator, rather than creating a sibling skill for the app-service axis.

It supersedes the "out of scope" carve-out in [`spec-updater-approach.md`](spec-updater-approach.md) § "What this updater does NOT cover" → "Commands/queries-diagram changes are out of scope", and the "Future work" → "Extended `/application-spec:update-specs`" item in [`commands-queries-detectors-approach.md`](commands-queries-detectors-approach.md).

For the detector design, see [`commands-queries-detectors-approach.md`](commands-queries-detectors-approach.md).
For the catalog of app-service-axis update types, see [`commands-queries-update-types.md`](commands-queries-update-types.md).
For the report schema the detectors emit, see [`commands-queries-updates-report.md`](commands-queries-updates-report.md).
For the existing domain-axis updater design this note extends, see [`spec-updater-approach.md`](spec-updater-approach.md).

---

## Decision

**Integrate the two new reports into `/application-spec:update-specs`.** The orchestrator grows a second input axis: in addition to `<stem>.domain/updates.md`, it consumes `<stem>.application/commands-updates.md` and `<stem>.application/queries-updates.md`. The post-dispatch pipeline (writers → exceptions enricher → merger → services-finder → updates-writer) is unchanged.

Rejected alternative: a sibling skill `/application-spec:update-app-service-specs` for the app-service axis only.

---

## Why integrate, not create

### The new reports are pure dispatch inputs

Walking Steps 3–7 of the existing skill: the new reports are never read.

| Step | Agent | Reads |
|---|---|---|
| 3 | `commands-deps-writer`, `commands-methods-writer`, `queries-deps-writer`, `queries-methods-writer` | Domain diagram + side's app-service diagram. No `updates.md` of any kind. |
| 4 | `application-exceptions-specifier` | Fragments from Step 3 + domain diagram. No `updates.md`. |
| 5 | `specs-merger` | Fragments from Step 3+4. No `updates.md`. |
| 6 | `services-finder` | Merged specs + domain diagram. No `updates.md`. |
| 7 | `application-updates-writer` | Working-tree specs + `git HEAD` specs. (Reads `<stem>.domain/updates.md` only as an enrichment source for `Source delta` lookups; doesn't dispatch on it.) |

The writers regenerate from current diagrams. They don't know — and don't need to know — which axis triggered the run. The reports' only job is telling Step 2 "which side to regen."

A sibling skill would therefore duplicate the entire Step 3–7 orchestration just to swap in a different Step 0–2 prelude that does the same dispatch math with different inputs.

### Two skills would fight over one output file

Both the existing skill and the hypothetical sibling write to `<dir>/<stem>.application/updates.md`. `application-updates-writer` is a snapshot writer — it diffs working-tree specs against `git HEAD` and overwrites the report wholesale. If both skills ran sequentially on a both-axes edit, the second's report-write overwrites the first's, and the first run's pipeline work (writers + enricher + merger + services-finder) is duplicated for nothing.

Splitting the report into two files (e.g. `domain-application-updates.md` vs `app-service-application-updates.md`) would fix the coherence problem but propagate the fragmentation into the future `/application-spec:update-code` consumer's contract.

### Integration cost is small

The orchestrator changes amount to roughly 30 lines:

- **Step 0 verify**: 2 additional `test -f` checks for the app-service reports (or 2 detector invocations if Step 0 owns detection — see below).
- **Step 1 preflight**: 2–3 new gates from the app-service axis (anchor rename, stereotype change, degraded baseline), each scoped to its own axis so a domain-axis failure doesn't block app-service regen and vice versa.
- **Step 2 dispatch**: union the per-axis dirty-flag predicates. Each new report contributes triggers via its own `## Affected Categories` footer, OR'd into the existing `commands_dirty` / `queries_dirty` booleans.

Steps 3–7 are byte-identical.

---

## Detector invocation: where they run

The detectors are producers; the orchestrator is the consumer. Two ordering models for how the reports get onto disk:

| Model | Operator workflow | Pros | Cons |
|---|---|---|---|
| **A. Step 0 invokes detectors** | One command: `/application-spec:update-specs <domain_diagram>` | One-shot workflow; reports always fresh | Orchestrator owns detector lifecycle; Step 0 grows two parallel invocations |
| **B. Expect reports on disk** | `@commands-updates-detector …` + `@queries-updates-detector …` + `/application-spec:update-specs …` | Mirrors current "consume domain `updates.md` produced by prior step" contract; cleaner detection/consumption split | Operator runs three commands |

**Chosen: A.** Reasons:

- The existing skill already expects domain `updates.md` to be on disk (produced by domain `/update-specs` Step 0 or an explicit prior `@updates-detector` call). Symmetrically requiring the operator to invoke two more detectors for the app-service axis is an unnecessary asymmetry.
- The app-service detectors are cheap (no LLM creativity except for one prose-summary step per non-trivial section diff), so invoking them unconditionally at Step 0 is byte-stable on stable inputs and roughly free on a clean working tree.
- The domain-axis pre-step pattern is already established by domain `/update-specs` Step 0 invoking `domain-spec:updates-detector` — adopting the same pattern here keeps the mental model uniform across plugins.

Standalone invocability is preserved: `@commands-updates-detector` and `@queries-updates-detector` remain ad-hoc-runnable (their primary use case is ad-hoc inspection before a full update cycle).

---

## Step 0 — Verify inputs (extended)

Existing checks (0a–0f) are unchanged. Add detector invocations and report-presence checks.

Order of operations:

1. Verify input diagrams + existing specs on disk (existing 0b–0f).
2. Verify domain `<stem>.domain/updates.md` on disk (existing 0a).
3. **Invoke `application-spec:commands-updates-detector` and `application-spec:queries-updates-detector` in parallel** with prompt `$ARGUMENTS[0]`. Wait for both to return. Each detector writes its own report or hard-fails (see detector hard-fail conditions in their agent files).
4. If either detector hard-fails, abort the orchestrator with that detector's `ERROR:` line repeated verbatim. The other detector's output (if it completed) is left on disk for the next run.
5. Read the three reports (`<stem>.domain/updates.md`, `<stem>.application/commands-updates.md`, `<stem>.application/queries-updates.md`) into the Step 1 working set.

Rationale for parallel detector invocation: the two detectors are independent (no shared file, no shared state) and the only shared resource is the per-plugin folder, which `mkdir -p` handles idempotently. Same parallel pattern the four Step 3 writers already use.

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
| 1.dom.d | `<<Repository>>` lifecycle change in domain | Set `domain_axis_disabled = true` |

Each disabled gate prints a `WARNING:` line (not `ERROR:`) describing what was skipped and directing the operator to `/application-spec:generate-specs` for the domain axis if the app-service regen alone isn't enough.

### 1.app — App-service-axis gates

New, mirroring the detector hard-fails:

| Gate | Trigger | Action |
|---|---|---|
| 1.app.a | Commands `_warning: HEAD ..._` line in Summary | Set `commands_axis_disabled = true` |
| 1.app.b | Queries `_warning: HEAD ..._` line in Summary | Set `queries_axis_disabled = true` |

(The detectors themselves hard-fail on stereotype change, anchor rename, multi-anchor — those never reach the orchestrator. The orchestrator only sees a `_warning:_` if HEAD was degraded.)

### 1.all — Total-abort gate

If `domain_axis_disabled` AND `commands_axis_disabled` AND `queries_axis_disabled` → abort the orchestrator with an aggregated `ERROR:` summarizing what got disabled and pointing the operator to `/application-spec:generate-specs <domain_diagram>`.

---

## Step 2 — Dispatch (three-way union)

The existing dispatch:

```
commands_dirty = (affected_categories ∩ {aggregates, value-objects, repositories-services}) != ∅
              or per_class_changes
queries_dirty  = (affected_categories ∩ {data-structures, repositories-services}) != ∅
              or per_class_changes
```

becomes:

```
# Domain axis (existing rules, but axis-gated)
domain_commands_triggers = domain_axis_disabled ? ∅ :
    (domain.affected_categories ∩ {aggregates, value-objects, repositories-services}) ∪
    (domain.per_class_changes ? {prose-proxy} : ∅)
domain_queries_triggers = domain_axis_disabled ? ∅ :
    (domain.affected_categories ∩ {data-structures, repositories-services}) ∪
    (domain.per_class_changes ? {prose-proxy} : ∅)

# Commands axis (new)
commands_axis_triggers = commands_axis_disabled ? ∅ :
    commands_updates.affected_categories
    # subset: {methods, dependencies, raised-exceptions, external-interfaces, ...}
    # — every category that drives application-spec regen on the commands side

# Queries axis (new)
queries_axis_triggers = queries_axis_disabled ? ∅ :
    queries_updates.affected_categories
    # subset: {methods, dependencies, raised-exceptions, external-interfaces, ...}

# Union
commands_dirty = (domain_commands_triggers ∪ commands_axis_triggers) != ∅
queries_dirty  = (domain_queries_triggers  ∪ queries_axis_triggers ) != ∅
```

The exact mapping from app-service `affected_categories` to dirty-side dispatch is owned by [`commands-queries-update-types.md`](commands-queries-update-types.md) § "Mapping `## Affected Categories` → consumer impact" — every commands-axis category drives `commands_dirty`; every queries-axis category drives `queries_dirty`. The `surface-markers` and `messaging-markers` categories from the commands axis don't drive application-spec regen (they're REST / messaging axes' concerns), so they don't contribute to `commands_dirty` — but they don't block the run either; they're simply ignored by this orchestrator.

If neither flag is true → Tier 4 no-op (skip Steps 3–6, still run Step 7 to emit a `_no changes_` report).

---

## Steps 3–7 — Unchanged

Verbatim from [`spec-updater-approach.md`](spec-updater-approach.md):

- **Step 3** — per-side regen (parallel where both sides fire). Writers regenerate from current diagrams.
- **Step 4** — `application-exceptions-specifier` (auto-skips sides whose `.exceptions.md` is absent).
- **Step 5** — `specs-merger` per dirty side (parallel).
- **Step 6** — `services-finder` (always runs after Step 5 regardless of which sides were dirty).
- **Step 7** — `application-updates-writer` (always runs, even on Tier 4 no-op).

No agent contract changes. No new writer. No new merger. The exceptions specifier's existing per-side disk-presence skip continues to provide per-side scoping for free.

---

## Step 8 — Report (extended summary line)

The existing one-line summary needs to surface which axis (or axes) drove the regen. Suggested shape:

```
Updated <stem>.application/{<files>} (<dispatch_clause>; triggers: <axis_summary>) and emitted <stem>.application/updates.md.
```

Where `<axis_summary>` is one of:

- `domain` — only domain-axis triggers fired
- `commands-diagram` — only commands-axis triggers fired
- `queries-diagram` — only queries-axis triggers fired
- `domain + commands-diagram` — both
- ... (any combination of the three)

For Tier 4 no-op (no triggers from any axis), keep the existing no-op messages.

If any preflight axis was disabled by a 1.dom or 1.app gate, prepend the `WARNING:` line(s) before the summary so the operator sees what got skipped.

---

## Failure semantics (extended)

Existing semantics: orchestrator does not roll back partial writes; re-running is the supported recovery path.

New cases:

- **Step 0 detector hard-fail** — orchestrator aborts with the detector's `ERROR:` line repeated verbatim. The other detector's report (if it completed) is left on disk. Re-running after fixing the trigger re-runs both detectors.
- **Total preflight abort (1.all)** — no writes; operator runs `/application-spec:generate-specs`.
- **Partial preflight disable (1.dom xor 1.app)** — the enabled axis regenerates as normal; the disabled axis's WARNING is surfaced in Step 8.

Step 3 writer aborts (the existing 2-abort case) remain unchanged. They're triggered by the writers detecting unreconcilable conditions in the diagrams; the operator reconciles the indicated diagram and re-runs.

---

## What this does NOT change

- **Existing skill contract for the domain axis** — every existing gate, dispatch rule, and writer invocation continues to apply. A domain-only edit produces the same output as before (modulo the detector invocations at Step 0, which are no-ops on a clean app-service working tree).
- **Existing agent contracts** — `application-updates-writer`, the writers, the merger, the exceptions specifier, `services-finder`: all unchanged. The only modification is to the orchestrator skill (`update-specs/SKILL.md`).
- **`<dir>/<stem>.application/updates.md` schema** — still produced by `application-updates-writer` snapshot-style; the report describes spec deltas, not which axis triggered them. (The new `Source delta` enrichment may eventually want a "triggered by app-service axis" annotation, but that's a follow-up — the v1 schema is sufficient.)
- **REST and messaging downstream consumers** — they each face the same integrate-vs-create decision when extending to the app-service axis. This note recommends integration for application-spec; the precedent extends to REST and messaging when those extensions land, but each plugin makes its own decision.

---

## What this DOES change

| File | Change |
|---|---|
| `plugins/application-spec/skills/update-specs/SKILL.md` | Extend Step 0 to invoke both app-service detectors; extend Step 1 to per-axis-scoped gates; extend Step 2 to three-way union dispatch; extend Step 8 summary line; update the frontmatter `description` to reflect the new scope (no longer "domain-driven axis only") |
| `plugins/application-spec/notes/spec-updater-approach.md` | Drop the "Commands/queries-diagram changes are out of scope" item from § "What this updater does NOT cover"; add a back-reference to this note |
| `plugins/application-spec/notes/commands-queries-detectors-approach.md` | Mark "Extended `/application-spec:update-specs`" in § "Future work" as done; back-reference this note |
| `plugins/application-spec/.claude-plugin/plugin.json` | Bump `version` (user-visible orchestrator behaviour change) |

No new skill file. No new agent file. The two detector agents already exist.

---

## Alternatives considered

| Approach | Status | Why not |
|---|---|---|
| **Sibling skill `/application-spec:update-app-service-specs` for the app-service axis only** | rejected | Duplicates Steps 3–7 orchestration just to swap in a different Step 0–2 prelude. Both skills write to the same `<dir>/<stem>.application/updates.md`; sequential runs on both-axes edits make the first run's pipeline work redundant. Forces operator to run two commands when both axes are touched. |
| **Sibling skill + per-axis report files** (`domain-application-updates.md` vs `app-service-application-updates.md`) | rejected | Solves the report-coherence problem but propagates the fragmentation into the future `/application-spec:update-code` consumer's contract — that consumer now has to read both files and merge them, which is exactly the work the integrated orchestrator does. |
| **Umbrella skill that chains domain + app-service updaters** | rejected | Same duplicated Step 3–7 pipeline cost as the sibling skill, plus a third skill to maintain. |
| **Integrate into `/application-spec:update-specs` (chosen)** | **accepted** | Reports are pure dispatch inputs; Steps 3–7 are byte-identical; one output file means one coherent report per run; one operator command for any combination of axes touched. |

---

## Open questions

- **Should domain `/update-specs` (the cascading orchestrator) also invoke the app-service detectors at its Step 0**, so that when `/update-specs` cascades into `/application-spec:update-specs` at Step 11 the detector reports are already on disk? Or should we let the application skill's Step 0 own all detector invocations regardless of how it was entered? Leaning toward the latter for simplicity (the application skill is self-sufficient; the cascading orchestrator stays domain-axis-scoped). Decide when implementing.
- **Does REST and messaging follow the same integration pattern?** Likely yes — same structural argument applies (reports are pure dispatch inputs for those orchestrators too). But each plugin's update-specs skill is a separate decision; track as follow-up work.
- **`Source delta` enrichment** — should the app-service-axis triggers contribute to `application-updates-writer`'s per-section `Source delta` lookups? Currently the writer reads only `<stem>.domain/updates.md` for source attribution. The app-service axis would benefit from analogous attribution (e.g. "Method `find_by_code` changed → commands-updates.md anchor-method `method_changed`"). Not blocking for v1, but worth a follow-up.

---

## Out of scope for this note

- **The `<stem>.application/updates.md` schema** — owned by [`updates-report.md`](updates-report.md). No schema change is required for the integration.
- **REST and messaging extensions** — each plugin's update-specs will face the same decision; track as separate notes when those land.
- **Code-axis updaters** (`/application-spec:update-code` and downstream) — consume `<stem>.application/updates.md`; their contract is unaffected by the integration.
