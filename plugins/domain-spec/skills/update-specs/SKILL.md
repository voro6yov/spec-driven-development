---
name: update-specs
description: "Surgically updates DDD class specs after a diagram change by detecting deltas, regenerating only affected categories, splicing them into the existing siblings, refreshing exceptions, and conditionally replanning tests. Invoke with: /update-specs <domain_diagram>"
argument-hint: <domain_diagram>
allowed-tools: Read, Bash, Agent, Skill
---

You are a DDD spec **update** orchestrator. Given a diagram whose working-tree differs from `git HEAD`, regenerate only the affected slices of the existing sibling spec artifacts in-place — do not rerun the full `/generate-specs` pipeline, do not touch class blocks unrelated to the change, and do not ask for confirmation before writing.

This skill is the surgical analog of `/generate-specs`. It implements **Approach B** from `notes/spec-updater-approach-b.md`: pre-prune what was removed, fan out per-category regen, splice into the live spec, then refresh exceptions and conditionally replan tests.

After the domain-side update completes successfully — and **only** then; a no-op early-exit (Step 1d) or any hard-fail/abort `return`s before the cascade — this skill **fans out two downstream spec updaters in parallel** (Step 10): `/persistence-spec:update-specs` and `/application-spec:update-specs`. Persistence is domain-driven. The application updater additionally **owns the app-service-axis subtree**: it produces the shared `<stem>.application/commands-updates.md` / `queries-updates.md` detector reports itself (at its own Step 0) and, after refreshing its own specs, re-cascades to `/rest-api-spec:update-specs` and `/messaging-spec:update-specs`. A single `/update-specs` thereby propagates one domain diagram change through every spec layer — domain → {persistence, application → {rest-api, messaging}}. Each downstream updater consumes the `<stem>.domain/updates.md` this skill just wrote in Step 0. The cascade **assumes those layers have already been generated**: a downstream updater whose spec artifact is missing hard-fails (`ERROR:`), but that ERROR does not abort its sibling — persistence and application run to completion independently and each prints its own report. There is no opt-out flag — the cascade is always attempted on the success path. This orchestrator emits no consolidated cascade summary.

## Output path convention

Given `<domain_diagram>` at `<dir>/<stem>.md`, the orchestrator reads and writes the same per-plugin folder used by `/generate-specs`:

| File | Touched by | Operation |
|---|---|---|
| `<dir>/<stem>.domain/updates.md` | `updates-detector` | Always (re)written at Step 0 |
| `<dir>/<stem>.domain/specs.md` | `spec-pruner`, `spec-splicer` | Surgical edit |
| `<dir>/<stem>.domain/exceptions.md` | `spec-splicer` (stub refresh), `exceptions-specifier` (enrichment) | Replaced |
| `<dir>/<stem>.domain/test-plan.md` | `aggregate-tests-planner` | Conditionally replaced (blast-radius gate) |

All agents derive `<stem>` by stripping the `.md` suffix from `<domain_diagram>`. Per-category regen scratch lives at `<dir>/<stem>.domain/.specs-tmp/<category>.md`; the orchestrator owns its lifecycle and removes it on success. See `spec-core:naming-conventions` for the canonical layout.

Step 10 writes the downstream per-plugin folders — `<dir>/<stem>.persistence/` and `<dir>/<stem>.application/` (and, via the application updater's own re-cascade, `<dir>/<stem>.rest-api/` and `<dir>/<stem>.messaging/`) — and their `updates.md` reports. The `<dir>/<stem>.application/commands-updates.md` / `queries-updates.md` detector reports are produced by the application updater at its own Step 0, **not here**. All those writes are owned entirely by the chained `/…-spec:update-specs` skills; see each one's own path-convention section for the per-file detail. This orchestrator invokes the two downstream updaters with `$ARGUMENTS[0]` (no flag) and surfaces every `ERROR:` line that returns.

## Category → Stereotype mapping

Same as `/generate-specs`. Used when iterating affected categories in canonical order:

| Category | Stereotypes |
|---|---|
| `data-structures` | `<<TypedDict>>` |
| `value-objects` | `<<Value Object>>` |
| `domain-events` | `<<Event>>` / `<<Domain Event>>` (alias) or inferred events (`-->` with `: emits`) |
| `commands` | `<<Command>>` or inferred commands (`--()` with `: emits`) |
| `aggregates` | `<<Aggregate Root>>`, `<<Entity>>` |
| `repositories-services` | `<<Repository>>`, `<<Service>>`, `<<Interface>>` (alias of `<<Service>>`) |

Canonical order for fan-out, dispatch, and reporting:

1. `data-structures`
2. `value-objects`
3. `domain-events`
4. `commands`
5. `aggregates`
6. `repositories-services`

## Workflow

### Step 0 — Detect updates

Invoke `domain-spec:updates-detector` with prompt `$ARGUMENTS` and wait for the agent to finish before reading the report. This step is sequential (one agent call); Steps 3 and 4 are the only parallel fan-outs in the workflow.

The detector compares the working tree against `git HEAD` and (re)writes `<dir>/<stem>.domain/updates.md`. It is always invoked unconditionally — any prior `<stem>.domain/updates.md` is clobbered. Manual edits to the report are not preserved.

If the agent reports a failure, abort and emit a single `ERROR:` line repeating its message.

### Step 1 — Preflight

Read `<dir>/<stem>.domain/updates.md`. The report is the orchestrator's single source of truth for everything in this step. Do not re-derive any of its inputs from the diagram.

Use `Bash` (`grep`) and `Read` to extract and **persist for the rest of the workflow**:

- **`degraded_baseline: bool`** — whether the Summary contains a line beginning `_warning: HEAD ` (zero or many Mermaid blocks at HEAD).
- **`stereotype_changed: list[str]`** — class names listed under `## Class Lifecycle → Stereotype Changed`.
- **`removed_classes: list[(name, stereotype)]`** — bullets under `## Class Lifecycle → Removed`. Capture `(class_name, stereotype)` from the bullet form `` - `ClassName` `<<Stereotype>>` ``.
- **`affected_categories: list[str]`** — bullets under `## Affected Categories` in the order they appear (the detector emits them in canonical order). The literal body `_None._` means empty.
- **`orphan_prose: bool`** — whether `## Orphan Prose Changes` is present with a non-empty body. The synthetic `### Preamble` block counts as a non-empty body. Step 1d's exit message and Step 9's success summary both consume this flag — extract it once here, do not re-grep later.

Apply the gates below **in order**. The first one that fires terminates Step 1 — later gates are not evaluated.

#### 1a. Hard-fail: degraded baseline (handles **C5**)

If the Summary contains a `_warning: HEAD ...` line, hard-fail:

```
ERROR: HEAD baseline is degraded (multiple or missing Mermaid blocks at HEAD). The surgical updater
cannot operate against a degraded baseline. Run `/generate-specs <domain_diagram>` to regenerate the
specs from scratch, or fix the HEAD revision before retrying `/update-specs`.
```

Do not invoke any downstream agent.

#### 1b. Hard-fail: stereotype change (handles **L3**)

If `## Class Lifecycle → Stereotype Changed` has at least one bullet, hard-fail with the offending names enumerated:

```
ERROR: Class(es) <names> have stereotype changes in <stem>.domain/updates.md. Stereotype changes require
the spec body to be re-rendered under the new category's template; the surgical updater cannot
perform the cross-category move. Run `/generate-specs <domain_diagram>` to regenerate the specs
from scratch.
```

#### 1c. Hard-fail: aggregate-root removal (defensive)

If any bullet under `## Class Lifecycle → Removed` has stereotype `<<Aggregate Root>>`, hard-fail:

```
ERROR: Aggregate root `<ClassName>` is listed under `## Class Lifecycle → Removed` in
<stem>.domain/updates.md. Aggregate roots cannot be removed; the diagram or the report is malformed.
```

This is a defensive check — `spec-pruner` enforces the same contract — but the orchestrator surfaces it earlier so the operator gets a single clean failure instead of a partial pipeline.

Surface every offending name (not just the first) so the operator can fix everything in one pass.

#### 1d. No-op exit: nothing actionable

Early exit (with success) when `affected_categories` is empty (`_None._` body).

By the report-template's footer-computation contract, an empty `## Affected Categories` implies empty `## Class Lifecycle → Added`, empty `## Class Lifecycle → Removed`, no class blocks under `## Per-Class Changes`, and an empty `## Orphan Relationship Changes` — every one of those would otherwise contribute a category. The only content the report can carry on this exit path is orphan prose changes (`Preamble`, `Notes`, `Glossary`, …) which by design do not feed category dispatch. The malformed-report guard at Step 3 catches the inverse — `affected_categories` empty but lifecycle/per-class/orphan-rel content present.

Print one summary line:

- If `orphan_prose` is true: `No structural updates required. Orphan prose changes detected — review <stem>.domain/updates.md.`
- Otherwise: `No structural updates required.`

#### 1e. Hard-fail: incomplete footer (footer ⊉ body)

Reached only when `affected_categories` is non-empty (1d did not fire). This gate is a safety net against a detector that emits a `## Affected Categories` footer missing a category its own body implies — `updates-detector` now computes the footer deterministically (its Step 7b), so in normal operation this gate never fires; it exists to convert any regression or hand-edit into a loud failure instead of a silent splice skip. (The orchestrator dispatches both the Step 3 fan-out and the splice off the footer, so a class whose category is absent from the footer is silently dropped even though its `## Per-Class Changes` block exists — exactly the corruption this gate guards.)

Recompute the **implied category set** from the report body, independently of the footer, using the inverse of the Category → Stereotype mapping table above:

- For every bullet under `## Class Lifecycle → Added` and `→ Removed`, map its inline `<<Stereotype>>` to a category.
- For every `### \`ClassName\` \`<<Stereotype>>\`` heading under `## Per-Class Changes`, map its stereotype to a category.

(Stereotype-changed classes are already rejected by 1b; orphan-relationship contributions are not re-derived here — this gate is a per-class/lifecycle completeness net, not a full footer recomputation, so it never over-fires on footer entries it cannot see.)

If `implied_categories ⊄ affected_categories`, hard-fail:

```
ERROR: <stem>.domain/updates.md has an incomplete `## Affected Categories` footer — categories
<missing> are implied by `## Per-Class Changes` / `## Class Lifecycle` but absent from the footer.
The surgical updater dispatches fan-out and splice off the footer, so an incomplete footer would
silently skip those classes. Re-run `@updates-detector <domain_diagram>` to regenerate the report
(its footer is computed deterministically), then retry `/update-specs`.
```

Surface every missing category. Do not invoke any downstream agent.

### Step 2 — Prune removed classes

Invoke `domain-spec:spec-pruner` with prompt `$ARGUMENTS`. Wait for completion.

The pruner is idempotent: if `## Class Lifecycle → Removed` is empty, it prints `No removals to prune.` and exits cleanly. If the report and the spec are out of sync (e.g. a previous prune already ran), it reports `0` and writes back unchanged content. Either outcome is success — proceed.

If the pruner exits non-zero, abort and emit a single `ERROR:` line repeating its message. Do not run downstream agents.

### Step 3 — Fan out class-specifiers (parallel)

Use the `affected_categories` list captured in Step 1.

#### 3a. Malformed-report guard

If `affected_categories` is empty at this point, the report is malformed: Step 1d would have early-exited on a clean empty footer, so reaching Step 3 with an empty footer means lifecycle, per-class, or orphan-relationship content is present without contributing a category — a contract violation by `updates-detector`. Hard-fail:

```
ERROR: <stem>.domain/updates.md is malformed — `## Affected Categories` is empty but
`## Class Lifecycle`, `## Per-Class Changes`, or `## Orphan Relationship Changes`
contain entries. Re-run `@updates-detector <domain_diagram>` to regenerate the report,
or inspect the file for hand-edits that broke the footer.
```

Do not invoke any downstream agent. Without this guard, the splicer would early-exit on the empty footer and skip its exceptions-stub refresh, leaving stale entries in `<stem>.domain/exceptions.md` after the pruner removed the underlying class block — a silent, hard-to-diagnose corruption.

#### 3b. Spawn class-specifier per affected category

For each `<cat>` in `affected_categories`, spawn `domain-spec:class-specifier` with prompt `$ARGUMENTS <cat>`.

Send **all** agent invocations in a single message so they run in parallel. Wait for every one to complete before proceeding. Each agent (re)writes `<dir>/<stem>.domain/.specs-tmp/<cat>.md` with the fresh per-category content plus a `### Partial Dependencies` footer.

If any agent reports a failure, abort and emit a single `ERROR:` line. Do not invoke `pattern-assigner` or `spec-splicer` against partial temp files.

### Step 4 — Fan out pattern-assigners (parallel)

After every `class-specifier` finishes, for the same `affected_categories` set spawn `domain-spec:pattern-assigner` with prompt `$ARGUMENTS <cat>`.

Send all invocations in a single message so they run in parallel. Wait for every one to complete before proceeding.

If any agent reports a failure, abort and emit a single `ERROR:` line.

### Step 5 — Splice

Invoke `domain-spec:spec-splicer` with prompt `$ARGUMENTS`. Wait for completion.

The splicer surgically merges the temp blocks into `<stem>.domain/specs.md` (insert / replace / skip per the report) and refreshes the `## Domain Exceptions` stub in `<stem>.domain/exceptions.md`. It does not enrich the exceptions and does not clean up the temp directory.

If the splicer hard-fails (e.g. a missing temp file, a stereotype-change report it received in error), abort and emit a single `ERROR:` line.

### Step 6 — Enrich exceptions

Invoke `domain-spec:exceptions-specifier` with prompt `$ARGUMENTS`. Wait for completion.

Always run this step after Step 5 — the splicer always rewrites the `## Domain Exceptions` stub (including emitting a `_(none)_` body when no `▪ Raises:` lines exist), so the enricher always has a fresh stub to consume.

If it fails, abort and emit a single `ERROR:` line. Note that `<stem>.domain/specs.md` and the exceptions stub are already on disk by this point — the failure leaves a clean partial state that re-running the orchestrator on top of unchanged inputs will idempotently complete.

### Step 7 — Test-plan replan (conditional)

Compute the **blast-radius gate**:

```
blast_radius = {"data-structures", "value-objects", "domain-events", "aggregates"}
should_replan = bool(set(affected_categories) & blast_radius)
```

These four categories are the aggregate root's blast radius — changes to any of them can shift state keys, mutation paths, emitted events, or return shapes that the test plan references. Pure `commands` or `repositories-services` changes are outside the blast radius and cannot affect aggregate unit tests.

- If `should_replan` is **true**: invoke `domain-spec:aggregate-tests-planner` with prompt `$ARGUMENTS`. The planner overwrites `<stem>.domain/test-plan.md` from scratch by reading the spliced `<stem>.domain/specs.md`. If it fails, abort and emit a single `ERROR:` line.
- If `should_replan` is **false**: skip the planner. `<stem>.domain/test-plan.md` is left byte-identical.

There is no per-aggregate filter — the working-tree invariant is that every diagram has exactly one `<<Aggregate Root>>` (enforced by `spec-pruner`'s removal guard and `updates-detector`'s validation), so the planner always operates over a single aggregate when it runs.

### Step 8 — Clean up

Remove the per-category scratch directory:

```bash
rm -rf <dir>/<stem>.domain/.specs-tmp
```

This mirrors what `specs-merger` does at the end of `/generate-specs`. The cleanup removes only the transient `.specs-tmp/` subdirectory; the rest of `<stem>.domain/` (the spliced spec, exceptions stub, and test plan) is preserved. Removal happens only on the success path (i.e. after Step 7 either ran successfully or was skipped) — when an earlier step aborted, leave the temp directory in place so the operator can inspect it.

### Step 9 — Report

Print one summary line indicating which sibling files were updated and whether the test plan was replanned:

```
Updated <stem>.domain/specs.md and <stem>.domain/exceptions.md (categories: <list>)<test_plan_clause><orphan_prose_clause>.
```

Where:

- `<list>` is `affected_categories` (captured in Step 1) joined by `, ` in canonical order. By construction `affected_categories` is non-empty on this code path — Step 1d exits before Step 9 on the empty footer, and Step 3a hard-fails before Step 9 on the malformed-empty-footer case.
- `<test_plan_clause>` is `; replanned <stem>.domain/test-plan.md` when Step 7 ran, otherwise empty.
- `<orphan_prose_clause>` is `; orphan prose changes detected — review <stem>.domain/updates.md` when `orphan_prose` (captured in Step 1) is true, otherwise empty.

Do not emit additional commentary. Each invoked agent already prints its own per-step report.

Step 10 (the parallel downstream cascade) runs after this. Its per-skill reports follow Step 9's summary line; this orchestrator adds nothing more.

### Step 10 — Cascade downstream spec updaters (parallel)

This step is reached **only on the success path**. Step 1d's no-op early-exit and every Step 1a–1c / mid-pipeline hard-fail `return` before this point, so Step 10 runs exactly when the domain-side specs were (re)generated — never on a no-op and never on an abort.

In a single message, invoke the two downstream `/…-spec:update-specs` skills in parallel:

- `persistence-spec:update-specs` with args `$ARGUMENTS[0]`
- `application-spec:update-specs` with args `$ARGUMENTS[0]`

Neither receives a flag. Persistence is domain-driven and invokes no app-service detector. The application updater **owns the app-service-axis subtree**: at its own Step 0 it produces the shared `<dir>/<stem>.application/commands-updates.md` / `queries-updates.md` detector reports, and after refreshing its own specs it re-cascades in parallel to `/rest-api-spec:update-specs` and `/messaging-spec:update-specs` (handing them `--detectors-fresh` so they reuse the reports it just produced). This orchestrator does **not** invoke rest-api or messaging directly, and no longer pre-produces the detector reports — there is no contention to hoist away, because application is the single producer feeding the two read-only consumers in its own subtree.

Wait for both to complete. Each prints its own report (and the application updater's report is followed by the rest-api / messaging reports from its re-cascade).

**No skill aborts the other** — persistence and application run independently regardless of sibling outcome. Surface each skill's `ERROR:` line as it returns; do not halt the fan-out. The two have disjoint reads (persistence consumes `<stem>.domain/updates.md` + its own per-plugin folder; application consumes `<stem>.domain/updates.md` + the app-service diagrams + its own folder), so a failure in one does not poison the other.

Note: because the rest-api / messaging updaters are now nested inside the application updater's tail (not siblings here), an application-side hard-fail aborts before that re-cascade — rest-api and messaging are then **not** run. This is the accepted coupling of routing the app-service-axis subtree through application; re-run `/update-specs` (or `/application-spec:update-specs`) after reconciling the application-side trigger to propagate to rest-api / messaging. See the application updater's own failure semantics for detail.

After both return, the workflow is done. Do not print a consolidated cascade summary — each chained skill already printed its own outcome line.

## Failure semantics

- Every step that aborts emits exactly one `ERROR:` line and exits the workflow. Do not chain further agents on top of a failed step.
- The orchestrator does not roll back partial writes. **Re-running `/update-specs` after fixing the trigger is the supported recovery path** — every step is idempotent on stable inputs:
  - **Step 0** (`updates-detector`) regenerates the report from HEAD-vs-working-tree on every call.
  - **Step 2** (`spec-pruner`) is explicitly idempotent and prints `0` when there is nothing left to prune.
  - **Steps 3 / 4** overwrite per-category temp files in `.specs-tmp/`.
  - **Step 5** (`spec-splicer`) yields byte-identical output on byte-identical inputs.
  - **Step 6** (`exceptions-specifier`) is pure derivation from the spec.
  - **Step 7** (`aggregate-tests-planner`) overwrites `<stem>.domain/test-plan.md` from scratch.
  - **Step 8** (cleanup) is destructive but only runs after a clean Step 7 / skipped-Step-7 success path.
  - **Step 10** (the parallel downstream `/…-spec:update-specs` cascade) fans out two independently idempotent skills — `persistence-spec:update-specs` and `application-spec:update-specs` (the latter produces the app-service detector reports at its own Step 0 and re-cascades to rest-api / messaging from its own tail). Re-running re-derives every downstream report from disk + git. A downstream `ERROR:` does **not** abort the sibling (persistence and application run to completion) and does not retroactively fail the domain-side update (Steps 0–9 already completed and were reported by Step 9). Re-running `/update-specs` after fixing the downstream trigger re-runs Steps 0–9 (byte-stable modulo LLM drift) and then re-fans-out Step 10 from scratch.
- The only failures `/update-specs` cannot retry through are degraded-baseline (1a) and stereotype-change (1b) conditions — both gates will fire again on re-run. The error messages explicitly direct the operator to `/generate-specs <domain_diagram>` for those cases. (Note: a degraded baseline or stereotype change hard-fails *before* Step 10, so the downstream updaters — which would each independently hard-fail on the same condition — are never reached.)
- A downstream Step-10 skill that hard-fails because its spec layer was never generated (e.g. `<stem>.persistence/command-repo-spec.md` missing) is the operator's signal to run that layer's `/…-spec:generate-specs` first. The cascade assumes the downstream layers exist; run `/update-specs` only once the full spec set (and code) has been generated for the aggregate. (rest-api / messaging are reached transitively through the application updater's re-cascade — a missing `<stem>.rest-api/spec.md` surfaces there, not here.)

## What this skill deliberately does not do

- It does not regenerate `<stem>.domain/specs.md` end-to-end — that is `/generate-specs`.
- It does not touch the diagram file itself or its Artifacts index — those siblings are already linked from the original `/generate-specs` run.
- It does not preserve manual edits inside a touched class block in `<stem>.domain/specs.md`. Untouched class blocks survive byte-identical (the splicer's load-bearing invariant); touched blocks are wholesale-replaced.
- It does not handle stereotype changes or degraded baselines — those route to a `/generate-specs` re-run via the operator-instruction failures in Steps 1a / 1b.
- It does not handle aggregate-root removals — those are a malformed-report condition (1c).
- It does not auto-update generated code or test bodies in any layer — the domain code-side updater (Approach C, see `notes/code-updater-approach-c.md`) and the per-plugin `…-spec:update-code` skills are separate concerns. Step 10 cascades only the downstream **spec** updates, never their code.
- It does not run the cascade (Step 10) on a no-op early-exit (Step 1d) or after any hard-fail/abort — only a successful domain-side regen, reaching the end of Step 9, triggers the Step-10 fan-out.
- It does not invoke `/rest-api-spec:update-specs` or `/messaging-spec:update-specs` directly, and it no longer produces the `<stem>.application/{commands,queries}-updates.md` detector reports — both responsibilities now belong to the `/application-spec:update-specs` subtree it fans out in Step 10.
- It has no flag to suppress the cascade — the two downstream updaters are always attempted on the success path, run in parallel (one Step-10 batch). To refresh only the domain side, invoke the underlying domain agents (`@updates-detector`, `@spec-splicer`, …) directly; "domain-only `/update-specs`" is not a supported mode.
