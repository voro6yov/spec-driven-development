---
name: update-specs
description: "Surgically updates the application service specs (`commands.specs.md`, `queries.specs.md`, `services.md`) from domain/diagram changes. Invoke with: /application-spec:update-specs <domain_diagram>"
argument-hint: <domain_diagram>
allowed-tools: Read, Bash, Agent, Skill
---

You are an application spec **update** orchestrator. Given a domain diagram and its sibling commands/queries application-service diagrams, refresh the existing `<dir>/<stem>.application/commands.specs.md`, `<dir>/<stem>.application/queries.specs.md`, and `<dir>/<stem>.application/services.md` in place — invoke the two app-service-axis update detectors, re-run only the dirty side's writers, re-enrich application exceptions, re-run `services-finder`, and emit `<dir>/<stem>.application/updates.md`. Then **re-cascade the app-service-axis change** to `/rest-api-spec:update-specs` and `/messaging-spec:update-specs` in parallel (Step 9). Do not rerun the full `/application-spec:generate-specs` pipeline, do not touch the diagram files, and do not ask for confirmation before writing.

This skill is the application-side counterpart to `/update-specs` (domain) and `/persistence-spec:update-specs`. Design rationale lives in `notes/spec-updater-approach.md`, `notes/update-types.md`, `notes/updates-report.md`, `notes/commands-queries-detectors-approach.md`, `notes/commands-queries-update-types.md`, `notes/commands-queries-updates-report.md`, and `notes/commands-queries-integration-approach.md`; the load-bearing idea is **per-side snapshot regen** — every section of `<side>.specs.md` is a pure snapshot, so the surgical unit of work is one full side, not one method block. Commands and queries are independent; a delta on any of the three input axes touches at most one or both.

The orchestrator consumes three update reports — one per axis — and unions their dispatch signals:

- **Domain axis** — `<dir>/<stem>.domain/updates.md`, produced by `domain-spec:updates-detector` (consumed **if present**; **absent ⇒ the domain axis is treated as no-change** per Step 0a — never invoked or produced here).
- **Commands-diagram axis** — `<dir>/<stem>.application/commands-updates.md`, produced by `application-spec:commands-updates-detector` (invoked at Step 0 below).
- **Queries-diagram axis** — `<dir>/<stem>.application/queries-updates.md`, produced by `application-spec:queries-updates-detector` (invoked at Step 0 below).

The orchestrator never re-diffs any diagram itself.

This skill is also the **owner of the app-service-axis cascade**. After refreshing its own specs it fans out `/rest-api-spec:update-specs` and `/messaging-spec:update-specs` in parallel (Step 9), handing them `--detectors-fresh` so they reuse the two detector reports this skill produced at Step 0. It is invoked two ways, with **identical behaviour** either way: standalone (for a commands/queries-diagram-only change, where it is the entry point) and as one of the two downstream skills fanned out by domain `/update-specs`'s Step 10 (alongside `/persistence-spec:update-specs`). Domain no longer pre-produces the detector reports or invokes rest-api / messaging directly — that whole subtree is rooted here.

## Output path convention

Per `application-spec:naming-conventions`, given `<domain_diagram>` at `<dir>/<stem>.md`:

- `<dir>` = directory containing the diagrams.
- `<stem>` = the canonical aggregate stem (domain filename with `.md` stripped).
- `<plugin_dir>` = `<dir>/<stem>.application` — the per-plugin folder for application-spec.

| File | Role | Touched by |
|---|---|---|
| `<dir>/<stem>.domain/updates.md` | input — domain delta report (**optional** — absent ⇒ domain axis treated as no-change, see Step 0a) | not modified |
| `<dir>/<stem>.commands.md` | input — hand-authored commands diagram (must already exist) | not modified |
| `<dir>/<stem>.queries.md` | input — hand-authored queries diagram (must already exist) | not modified |
| `<plugin_dir>/commands-updates.md` | input — commands-diagram delta report | produced by `commands-updates-detector` at Step 0 |
| `<plugin_dir>/queries-updates.md` | input — queries-diagram delta report | produced by `queries-updates-detector` at Step 0 |
| `<plugin_dir>/commands.specs.md` | spec being updated (must already exist) | `commands-deps-writer` + `commands-methods-writer` (per-side fragments) → `application-exceptions-specifier` → `specs-merger commands` (when commands dirty) |
| `<plugin_dir>/queries.specs.md` | spec being updated (must already exist) | `queries-deps-writer` + `queries-methods-writer` (per-side fragments) → `application-exceptions-specifier` → `specs-merger queries` (when queries dirty) |
| `<plugin_dir>/services.md` | spec being updated (must already exist) | `services-finder` (when at least one side was dirty) |
| `<plugin_dir>/updates.md` | output — application delta report | `application-updates-writer` |

`<domain_diagram>`, `<commands_diagram>`, and `<queries_diagram>` are read by the invoked agents; this orchestrator never modifies them. Every agent derives `<dir>` / `<stem>` from `$ARGUMENTS[0]` per `application-spec:naming-conventions` — pass `$ARGUMENTS[0]` verbatim as the prompt to each.

This skill keeps no runtime state between agents. The updates writer recovers the pre-update specs via `git show HEAD:<spec_file>` for each of the three spec files and reads the three on-disk delta reports for axis-tagged source attribution, so there is nothing for the orchestrator to capture or hand along.

The Step-9 re-cascade additionally writes the downstream `<dir>/<stem>.rest-api/` and `<dir>/<stem>.messaging/` per-plugin folders and their `updates.md` reports — those writes are owned entirely by the chained `/rest-api-spec:update-specs` / `/messaging-spec:update-specs` skills; see each one's own path-convention section for the per-file detail.

## Workflow

### Step 0 — Verify inputs and produce the app-service-axis reports

Derive `<dir>` and `<stem>` from `$ARGUMENTS[0]` per `application-spec:naming-conventions`. `<stem>` must satisfy `^[a-z][a-z0-9-]*$`. Using `Bash` (`test -f`), verify the input files in this order:

- **0a.** If `<dir>/<stem>.domain/updates.md` is missing → **do not hard-fail**. The domain report is an **optional** input: set `domain_report_absent = true`, emit the `WARNING` below, and continue with the commands/queries-diagram axes only. This skill never produces the domain report itself (it does not invoke `domain-spec:updates-detector`), so absence is handled by **suppressing the domain axis**, not by synthesizing the file:

  ```
  WARNING: <dir>/<stem>.domain/updates.md absent — domain axis treated as no-change. The
  commands/queries-diagram axes still drive this update. If the domain diagram actually changed,
  run `@updates-detector <domain_diagram>` (or `/update-specs <domain_diagram>`) first so
  domain-driven application changes are not silently skipped.
  ```

  When `domain_report_absent` is true: skip the domain-axis extraction in Step 1, bind every domain-axis value to its empty default (`domain.affected_categories = []`, `domain.per_class_changes = false`, all `## Class Lifecycle` lists empty, `domain.degraded_baseline = false`, `domain.orphan_prose = false`), and the domain-axis gates (1.dom.a–d) cannot fire. The downstream `application-updates-writer` (Step 7) already tolerates an absent domain report — its domain-axis `Source delta` probe is skipped and the Summary's `Domain updates source` renders `_none_`.

- **0b.** If `<dir>/<stem>.application/commands.specs.md` is missing → hard-fail:

  ```
  ERROR: <dir>/<stem>.application/commands.specs.md not found. The application updater is not the
  first-run pipeline. Run `/application-spec:generate-specs <domain_diagram>` to create the spec.
  ```

- **0c.** If `<dir>/<stem>.application/queries.specs.md` is missing → hard-fail:

  ```
  ERROR: <dir>/<stem>.application/queries.specs.md not found. The application updater is not the
  first-run pipeline. Run `/application-spec:generate-specs <domain_diagram>` to create the spec.
  ```

- **0d.** If `<dir>/<stem>.application/services.md` is missing → hard-fail:

  ```
  ERROR: <dir>/<stem>.application/services.md not found. The application updater is not the
  first-run pipeline. Run `/application-spec:generate-specs <domain_diagram>` to create the spec.
  ```

- **0e.** If `<dir>/<stem>.commands.md` is missing → hard-fail:

  ```
  ERROR: <dir>/<stem>.commands.md not found. The commands application-service diagram is a required
  hand-authored input. Restore the file or run `/application-spec:generate-specs <domain_diagram>`
  after authoring it.
  ```

- **0f.** If `<dir>/<stem>.queries.md` is missing → hard-fail:

  ```
  ERROR: <dir>/<stem>.queries.md not found. The queries application-service diagram is a required
  hand-authored input. Restore the file or run `/application-spec:generate-specs <domain_diagram>`
  after authoring it.
  ```

Do not synthesize any of these files.

#### 0g. Invoke the two app-service-axis detectors in parallel

After 0a–0f run (0a never aborts — it only records `domain_report_absent`; 0b–0f hard-fail on a missing input), fan out the two detectors in a single message so they run concurrently. Pass `$ARGUMENTS[0]` (the domain diagram path) as the prompt to each — the detectors derive their own sibling diagrams via `application-spec:naming-conventions`.

- `application-spec:commands-updates-detector` with prompt `$ARGUMENTS[0]`.
- `application-spec:queries-updates-detector` with prompt `$ARGUMENTS[0]`.

Each detector writes its own report (`<plugin_dir>/commands-updates.md`, `<plugin_dir>/queries-updates.md`) or hard-fails with an `ERROR:` line. The detectors share `<plugin_dir>` only — both use `mkdir -p` idempotently, so the parallel pattern is safe.

This skill is the **single producer** of these two reports: whether invoked standalone or fanned out by domain `/update-specs`'s Step 10, it always produces them here, then hands them down to the Step-9 re-cascade via `--detectors-fresh`. There is no concurrent producer to race with — domain no longer pre-produces them, and rest-api / messaging only read them — so there is **no cascade-mode shortcut**; the detectors run on every invocation. (A stray `--detectors-fresh` token in `$ARGUMENTS` is harmless: this orchestrator only ever reads `$ARGUMENTS[0]`, so the flag is simply ignored and the detectors run anyway.)

If either detector hard-fails, abort the orchestrator with that detector's `ERROR:` line repeated verbatim. The other detector's output (if it completed) is left on disk for the next run; no rollback is performed. The same `/application-spec:generate-specs <domain_diagram>` recovery path the detectors themselves direct to applies here.

Wait for both detectors to return successfully before proceeding to Step 1.

### Step 1 — Preflight (per-axis-scoped)

`Read` all three reports — `<dir>/<stem>.domain/updates.md`, `<plugin_dir>/commands-updates.md`, `<plugin_dir>/queries-updates.md`. They are the orchestrator's single source of truth for this step — do not re-derive anything from any diagram. When `domain_report_absent` (Step 0a) is true, **skip the domain report read entirely** and bind every domain-axis value below to its empty default (the 1.dom gates then cannot fire); the commands/queries reports are still read. Use `Bash` (`grep`) and `Read` to extract, per axis:

**Domain axis** (from `<stem>.domain/updates.md`):

- **`domain.degraded_baseline`** — whether the `## Summary` block contains a line beginning `_warning: HEAD `.
- **`domain.stereotype_changed`** — class names listed under `## Class Lifecycle → Stereotype Changed` (one bullet per class; the exact bullet format is owned by `domain-spec:updates-report-template`). Empty when the heading is absent or its body is `_None._`-style.
- **`domain.removed_classes`** — bullets under `## Class Lifecycle → Removed`, each `` - `ClassName` `<<Stereotype>>` ``. Capture `(class_name, stereotype)` per bullet.
- **`domain.added_classes`** — bullets under `## Class Lifecycle → Added`, each `` - `ClassName` `<<Stereotype>>` `` (the `— <N> attributes, <N> methods` suffix is informational; ignore for dispatch). Capture `(class_name, stereotype)` per bullet.
- **`domain.affected_categories`** — bullets under `## Affected Categories`, in the order they appear. The literal body `_None._` means empty.
- **`domain.per_class_changes`** — whether `## Per-Class Changes` is present with at least one `### `-style class block. Used for the dispatch step's prose-or-member proxy.
- **`domain.orphan_prose`** — whether `## Orphan Prose Changes` is present with a non-empty body (the synthetic `### Preamble` block counts). Used only to colour the no-op message.
- **`domain.repo_class_lifecycle`** — whether any bullet under `## Class Lifecycle → Added` or `→ Removed` carries the stereotype `<<Repository>>`.

**Commands-diagram axis** (from `<plugin_dir>/commands-updates.md`):

- **`commands.degraded_baseline`** — whether the `## Summary` block contains a line beginning `_warning: HEAD `.
- **`commands.affected_categories`** — bullets under `## Affected Categories`, in the order they appear. The vocabulary is owned by `application-spec:application-updates-report-template`. The literal body `_None._` means empty.

**Queries-diagram axis** (from `<plugin_dir>/queries-updates.md`):

- **`queries.degraded_baseline`** — whether the `## Summary` block contains a line beginning `_warning: HEAD `.
- **`queries.affected_categories`** — bullets under `## Affected Categories`. The literal body `_None._` means empty.

The structural hard-fails the detectors themselves enforce (anchor missing/renamed, multi-anchor, stereotype change inside the app-service diagram) never reach the orchestrator — the detector aborts at Step 0 and the orchestrator surfaces its `ERROR:` verbatim. The orchestrator only sees a `_warning:_` on an app-service axis when HEAD was degraded.

Apply the gates below per axis. Each gate sets a per-axis disable flag (`domain_axis_disabled`, `commands_axis_disabled`, `queries_axis_disabled`) and emits a `WARNING:` line describing what was skipped; the run continues if any other axis is still enabled. Only the aggregated 1.all gate aborts the orchestrator.

#### 1.dom — Domain-axis gates

Each gate **disables only the domain axis** and emits a `WARNING:` (not `ERROR:`).

| Gate | Trigger | Action |
|---|---|---|
| 1.dom.a | `domain.degraded_baseline` true | Set `domain_axis_disabled = true`; emit `WARNING: domain axis disabled — HEAD baseline is degraded (multiple or missing Mermaid blocks at HEAD per <stem>.domain/updates.md). Run /application-spec:generate-specs <domain_diagram> to regenerate the domain-driven half from scratch.` |
| 1.dom.b | `domain.stereotype_changed` non-empty | Set `domain_axis_disabled = true`; emit `WARNING: domain axis disabled — class(es) <names> have stereotype changes in <stem>.domain/updates.md. A stereotype change moves a class to a different pattern catalog. Run /application-spec:generate-specs <domain_diagram> to regenerate from scratch.` (surface every offending name) |
| 1.dom.c | Any bullet in `domain.removed_classes` has stereotype `<<Aggregate Root>>` | Set `domain_axis_disabled = true`; emit `WARNING: domain axis disabled — aggregate root <ClassName> is listed under Class Lifecycle → Removed in <stem>.domain/updates.md. The <AggregateRoot>Commands / <AggregateRoot>Queries services lose their anchor; an aggregate-root rename also moves the diagram filenames. Rename the diagrams (<stem>.md, <stem>.commands.md, <stem>.queries.md) and the <stem>.application/ folder, then run /application-spec:generate-specs <domain_diagram>.` |
| 1.dom.d | `domain.repo_class_lifecycle` true | Set `domain_axis_disabled = true`; emit `WARNING: domain axis disabled — a <<Repository>> interface was added or removed per <stem>.domain/updates.md. A new repository requires a fresh dependency selection. Run /application-spec:generate-specs <domain_diagram>.` |

Only one of 1.dom.a–1.dom.d fires per run (whichever is first); evaluate in order and stop at the first match.

Note: the orchestrator does not pre-check the narrower cases the methods writers also abort on (a missing `save(...)` on the command repo, an aggregate-root method renamed/removed under the application diagrams' canonical shape, a domain `<<Service>>` removed/stereotype-changed while still referenced by the commands diagram, a query-side external-interface operation renamed/removed, a query-repo finder rename that breaks the same-name match). The methods writers themselves abort on these and surface a one-sentence error directing the operator to reconcile the relevant application-service diagram. The orchestrator surfaces that error verbatim from Step 3.

#### 1.cmd — Commands-axis gates

Each gate **disables only the commands axis** and emits a `WARNING:`.

| Gate | Trigger | Action |
|---|---|---|
| 1.cmd.a | `commands.degraded_baseline` true | Set `commands_axis_disabled = true`; emit `WARNING: commands-diagram axis disabled — HEAD baseline is degraded (multiple or missing Mermaid blocks at HEAD per <stem>.application/commands-updates.md). Commands-diagram-driven dispatch is skipped for this run.` |

#### 1.qry — Queries-axis gates

Each gate **disables only the queries axis** and emits a `WARNING:`.

| Gate | Trigger | Action |
|---|---|---|
| 1.qry.a | `queries.degraded_baseline` true | Set `queries_axis_disabled = true`; emit `WARNING: queries-diagram axis disabled — HEAD baseline is degraded (multiple or missing Mermaid blocks at HEAD per <stem>.application/queries-updates.md). Queries-diagram-driven dispatch is skipped for this run.` |

#### 1.all — Total-abort gate

If `domain_axis_disabled` AND `commands_axis_disabled` AND `queries_axis_disabled` are all true, abort the orchestrator with:

```
ERROR: all three input axes are disabled by preflight gates (see WARNING lines above). The orchestrator
cannot regenerate any side. Resolve the underlying conditions or run /application-spec:generate-specs
<domain_diagram> to rebuild the application specs from scratch.
```

No writes; no downstream agents are invoked.

### Step 2 — Dispatch tier (three-way union)

Compute two booleans from the values captured in Step 1, treating disabled axes as contributing the empty set:

```
# Domain axis (existing rules, but axis-gated; absent report ⇒ empty contribution)
domain_commands_triggers = ∅ if (domain_axis_disabled or domain_report_absent) else
    (set(domain.affected_categories) & {"aggregates", "value-objects", "repositories-services"}) ∪
    ({"prose-proxy"} if domain.per_class_changes else ∅)
domain_queries_triggers  = ∅ if (domain_axis_disabled or domain_report_absent) else
    (set(domain.affected_categories) & {"data-structures", "repositories-services"}) ∪
    ({"prose-proxy"} if domain.per_class_changes else ∅)

# Commands-diagram axis (per-side by construction — commands report only describes the commands side)
commands_axis_triggers = ∅ if commands_axis_disabled else
    set(commands.affected_categories) & {"methods", "dependencies", "raised-exceptions", "external-interfaces"}

# Queries-diagram axis (per-side by construction — queries report only describes the queries side)
queries_axis_triggers  = ∅ if queries_axis_disabled else
    set(queries.affected_categories)  & {"methods", "dependencies", "raised-exceptions", "external-interfaces"}

# Union
commands_dirty = (domain_commands_triggers ∪ commands_axis_triggers) != ∅
queries_dirty  = (domain_queries_triggers  ∪ queries_axis_triggers ) != ∅
```

Rationale (category-level dispatch):

**Domain axis:**

- **`aggregates`** and **`value-objects`** can only affect the commands side (factory seeded-fields, postcondition prose, `Requires Aggregate State`, child-collection re-index). Queries methods go through DTOs and are byte-neutral on these.
- **`data-structures`** can only affect the queries side (Returns shape-hint prose at most). Command methods always return `<AggregateRoot>` and never name a TypedDict.
- **`repositories-services`** can affect either side — `Command<X>Repository` finder churn and referenced-`<<Service>>` method-signature changes drive the commands side; `Query<X>Repository` finder churn and query-side external-interface operation churn drive the queries side. Without finer-grained class identification we mark both sides dirty; the unaffected side's regen is byte-stable on stable inputs and only contributes diff noise.
- **`per_class_changes`** non-empty is treated as a prose proxy — the methods writers re-read the domain diagram's surrounding prose as advisory description, and a class-keyed prose change might nudge a Purpose / postcondition / collaborator-hint / status-gating / External-Interface-hint clause. We err on the side of regenerating both sides; the typical outcome is byte-stable output modulo LLM prose drift.
- **`domain-events`** and **`commands`** (the domain-message-dataclass category) never appear in application method specs — `domain.affected_categories ⊆ {domain-events, commands}` alone leaves both flags false.

**App-service axes (per-side by construction):**

- **Commands-diagram axis** drives only the commands side, because the commands report describes the commands diagram. `methods` / `dependencies` / `raised-exceptions` / `external-interfaces` all map to commands-side regen.
- **Queries-diagram axis** drives only the queries side, symmetrically.
- The `surface-markers` and `messaging-markers` categories that may appear on a commands report are owned by `/rest-api-spec:update-specs` and `/messaging-spec:update-specs` respectively; this orchestrator silently ignores them (no `commands_dirty` contribution, no log line).

If neither flag is true → **Tier 4 no-op**. Skip Steps 3–6 and jump straight to Step 7 (emit the report) so a `<stem>.application/updates.md` always exists after a successful run; the writer sees the working-tree specs unchanged versus HEAD and emits an all-`_no changes_` report. Then run Step 8 (the no-op summary line) **and Step 9 (the rest-api / messaging re-cascade — which still runs on a no-op**, because a domain-axis change that is byte-neutral for the application specs can still be live for rest-api or messaging: a pure domain-event attribute change is a Tier-4 no-op here but fires the messaging updater, and a domain `<<Command>>` parameter-type change is a no-op here but can fire the rest-api request-fields writer). Then exit.

If at least one flag is true, proceed to Step 3.

### Step 3 — Per-side regen (parallel where both sides fire)

For each dirty side, fan out the writer agents in parallel. **Emit all selected agent calls in a single message** so they run concurrently. Pass `$ARGUMENTS[0]` (the domain diagram path) as the prompt to each — the writers derive their own sibling diagrams via `application-spec:naming-conventions`.

If `commands_dirty`:

- `application-spec:commands-deps-writer` with prompt `$ARGUMENTS[0]`.
- `application-spec:commands-methods-writer` with prompt `$ARGUMENTS[0]`.

If `queries_dirty`:

- `application-spec:queries-deps-writer` with prompt `$ARGUMENTS[0]`.
- `application-spec:queries-methods-writer` with prompt `$ARGUMENTS[0]`.

When both sides are dirty, all four writers fan out together in a single message — the same parallel pattern `/application-spec:generate-specs` uses today. Wait for every selected writer to complete before proceeding.

Each writer regenerates its fragment from current inputs (the domain diagram + its side's application-service diagram) and writes `<plugin_dir>/<side>.deps.md` / `<plugin_dir>/<side>.methods.md` / `<plugin_dir>/<side>.exceptions.md` (stub) inside `<dir>/<stem>.application/`. The writers do not read the prior `<side>.specs.md`. A side's `## Dependencies` is byte-stable on any domain-only change (it's a pure function of the application-service diagram); re-running the deps writer is an LLM-drift cost we accept rather than a correctness requirement, but is required because the merger consumes the on-disk fragment.

#### Abort-and-reconcile

The methods writers may abort with a one-sentence error rather than producing a fragment. The conditions are:

- `commands-methods-writer` aborts when an aggregate-root method that a command method resolves to has been renamed/removed (Step 5c match fails), when the chosen load-step finder has no remaining subset (Step 5d), or when a domain `<<Service>>` referenced by the commands diagram is missing/stereotype-changed (Step 4).
- `queries-methods-writer` aborts when a `Query<AggregateRoot>Repository` finder a query method needs has been renamed/removed (Step 5e same-name match fails), or when an external-interface operation a hint references no longer resolves (Step 5a).

If any writer reports a failure, abort the workflow and emit a single `ERROR:` line repeating its message verbatim. Do not run downstream agents — the spec is left partially regenerated and re-running `/application-spec:update-specs` after the operator reconciles the indicated application-service diagram idempotently completes the update. The other side's writers (if launched in parallel) may have completed; their fragments are left on disk to be re-consumed (or replaced) on a subsequent successful run.

### Step 4 — Enrich application exceptions

After all Step 3 writers return successfully, invoke `application-spec:application-exceptions-specifier` with prompt `$ARGUMENTS[0]`. The agent processes both sides in one call but auto-skips a side whose `<side>.exceptions.md` is absent (its existing disk-presence contract).

Because Step 3 only writes fragments for the dirty side, the unaffected side's `<side>.exceptions.md` is not on disk (deleted by the prior `generate-specs` run's merger), and the enricher leaves the unaffected side's `<side>.specs.md` untouched. This is the load-bearing reason per-side regen requires no contract change to existing agents — the disk-presence check the enricher already performs is exactly the per-side scoping the updater needs.

If the enricher reports a failure, abort and emit a single `ERROR:` line repeating its message.

### Step 5 — Merge fragments per dirty side (parallel)

After the enricher returns, fan out the merger(s) in parallel for the dirty side(s) only. Emit the selected `Agent` calls in a single message:

- `application-spec:specs-merger` with prompt `$ARGUMENTS[0] commands` (if `commands_dirty`).
- `application-spec:specs-merger` with prompt `$ARGUMENTS[0] queries` (if `queries_dirty`).

Each merger consolidates its side's `<side>.deps.md` + `<side>.methods.md` + `<side>.exceptions.md` into `<plugin_dir>/<side>.specs.md` (overwriting the prior file) and deletes the consumed fragments. The unaffected side's `<side>.specs.md` is left byte-identical.

If a merger reports a failure, abort and emit a single `ERROR:` line repeating its message. The other merger (if running in parallel) may complete; the orchestrator does not roll back.

### Step 6 — Re-run services-finder

After all merger(s) return, invoke `application-spec:services-finder` with prompt `$ARGUMENTS[0]`. It re-reads the freshly merged specs plus the domain diagram and rewrites `<plugin_dir>/services.md`.

This step always runs after Step 5 (regardless of which sides were dirty). Reasons:

- A commands-side regen may add or drop a `## Dependencies → Domain Services` bullet, which changes the services report.
- A queries-side regen may add or drop a `## Dependencies → External Interfaces` bullet on the queries side.
- A domain `<<Service>>` lifecycle that *was* validated against the application diagrams in Tier 1 may still need the report regenerated to drop or re-include the service.

`services-finder` is a pure function of the merged specs + the domain diagram; re-running it on a stable input is byte-stable modulo LLM drift in prose summaries.

If the agent reports a failure, abort and emit a single `ERROR:` line repeating its message.

### Step 7 — Emit the application updates report

Invoke `application-spec:application-updates-writer` with prompt `$ARGUMENTS[0]`. It diffs the working-tree specs (`commands.specs.md`, `queries.specs.md`, `services.md`) against `git HEAD`, classifies the per-section deltas, reads the three on-disk delta reports (`<stem>.domain/updates.md`, `<plugin_dir>/commands-updates.md`, `<plugin_dir>/queries-updates.md`) for axis-tagged `Source delta` enrichment, derives the `## Affected Artifacts` table mechanically, and writes `<dir>/<stem>.application/updates.md` (always — even on Tier 4 no-op, where every section after `## Summary` renders `_no changes_` and the Affected Artifacts table has no data rows).

The writer recovers everything it needs from disk + git + the three sibling delta reports; the orchestrator passes nothing else.

This step runs **on every successful run**, including the Tier 4 no-op early-exit case (Step 2). The consumer's contract (`/update-code`, the cross-layer `domain-spec:update-code` orchestrator) requires the report to always exist after a successful run.

If the writer reports a failure, abort and emit a single `ERROR:` line repeating its message. The application specs are already in their final post-update state by this point — re-running the orchestrator (or just the updates writer agent standalone) idempotently produces the report.

### Step 8 — Report

Print one summary line. The shape depends on the dispatch outcome.

Build `<axis_summary>` first — a comma-separated list (in canonical order: `domain`, `commands-diagram`, `queries-diagram`) of axes that contributed at least one trigger to a dirty-side flag. An axis whose flag-contribution was the empty set (either disabled, or its triggers all resolved to empty) does not appear in `<axis_summary>`.

- **Tier 4 no-op**:
  - If `domain.orphan_prose` is true: `No application spec updates required. Orphan prose changes detected — review <stem>.domain/updates.md. Emitted <stem>.application/updates.md.`
  - Otherwise: `No application spec updates required (no application-relevant changes on any axis). Emitted <stem>.application/updates.md.`

- **At least one side dirty**:
  ```
  Updated <stem>.application/{<files>} (<dispatch_clause>; triggers: <axis_summary>) and emitted <stem>.application/updates.md.
  ```
  Where:
  - `<files>` is a comma-separated list, in canonical order: `commands.specs.md` (when commands_dirty), `queries.specs.md` (when queries_dirty), `services.md` (always — Step 6 always runs).
  - `<dispatch_clause>` is one of `regenerated commands side`, `regenerated queries side`, or `regenerated both sides`, matching the dirty-flag combination.
  - `<axis_summary>` examples: `domain`, `commands-diagram`, `queries-diagram`, `domain + commands-diagram`, `commands-diagram + queries-diagram`, `domain + commands-diagram + queries-diagram`. Use ` + ` (space-plus-space) as the separator.

If any preflight axis was disabled (Step 1.dom / 1.cmd / 1.qry fired), the `WARNING:` line(s) for those gates are emitted before the summary so the operator sees what got skipped. The summary itself still runs.

Do not emit additional commentary — each invoked agent already printed its own per-step report.

### Step 9 — Re-cascade to rest-api + messaging (parallel)

This step is reached on **every successful run** — a dirty-side regen, a partial-preflight-disable run, **and** the Tier-4 no-op (Step 2) — but **not** after any hard-fail/abort (the Step 0 missing-input cases, the 1.all total-abort, and any Step 3–7 agent failure all `return` before here). It runs unconditionally on success because a domain-axis change can be byte-neutral for the application specs yet still live for rest-api or messaging: a pure domain-event attribute change is a Tier-4 no-op here but fires the messaging updater, and a domain `<<Command>>` parameter-type change is a no-op here but can fire the rest-api request-fields writer. Gating the cascade on this skill's own dirtiness would silently drop those.

In a single message, invoke both downstream skills in parallel:

- `rest-api-spec:update-specs` with args `$ARGUMENTS[0] --detectors-fresh`
- `messaging-spec:update-specs` with args `$ARGUMENTS[0] --detectors-fresh`

The literal `--detectors-fresh` token (second positional arg) tells each updater that the two app-service-axis detector reports are already on disk and byte-stable from this skill's Step 0g; they skip their own internal detector invocation and read the reports directly. (rest-api reads both reports; messaging reads only `commands-updates.md`.) Both reports are guaranteed present because Step 0g produced them on this very run.

Wait for both to complete. Each prints its own report.

**No skill aborts the other** — rest-api and messaging run independently regardless of sibling outcome, and a downstream `ERROR:` does not retroactively fail the application-side update (Steps 0–8 already completed and were reported by Step 8). Surface each skill's `ERROR:` line as it returns; do not halt the fan-out. They have disjoint reads (each consumes `<stem>.domain/updates.md` + the shared detector reports + its own per-plugin folder) and disjoint writes (`<stem>.rest-api/` vs `<stem>.messaging/`), so a failure in one does not poison the other.

A downstream updater whose spec layer was never generated surfaces it here: rest-api hard-fails on a missing `<stem>.rest-api/spec.md`; messaging prints a clean "nothing to update" when `<stem>.messaging/` is absent or empty (it never hard-fails on that account). The cascade assumes those layers exist where applicable; this skill surfaces the `ERROR:` and continues. Re-run after generating the missing layer.

This orchestrator does not print a consolidated cascade summary — each chained skill already printed its own outcome line.

## Failure semantics

- **Step 0 detector hard-fail** (0g): orchestrator aborts with the detector's `ERROR:` line repeated verbatim. The other detector's report (if it completed) is left on disk. Re-running after fixing the trigger re-runs both detectors. No rollback.
- **Total preflight abort (1.all)**: no writes; the WARNING lines for each disabled axis are emitted before the aggregated ERROR. Operator runs `/application-spec:generate-specs`.
- **Partial preflight disable (1.dom xor 1.cmd xor 1.qry)**: the enabled axis (or axes) regenerate as normal; the disabled axis's WARNING is surfaced before the Step 8 summary. This is a success path, so the Step 9 re-cascade still runs.
- **Step 3+ agent failure**: every step that aborts emits exactly one `ERROR:` line and exits the workflow. Do not chain further agents on top of a failed step. The orchestrator does not roll back partial writes.
- **Step 9 cascade**: reached only on the application-side success path. An application-side hard-fail (the Step 0 missing-input cases, the 1.all total-abort, or any Step 3–7 agent abort) `return`s before Step 9, so **rest-api and messaging are not run** on that invocation — the accepted coupling of rooting the app-service-axis subtree here. Within Step 9 the two downstream skills are independent: one's `ERROR:` neither aborts the other nor fails the already-completed application-side update. Re-run `/application-spec:update-specs` after reconciling the application-side trigger to propagate to rest-api / messaging.
- **Re-running `/application-spec:update-specs` after fixing the trigger is the supported recovery path** — every step is idempotent on stable inputs:
  - **Step 0 detectors** regenerate their reports wholesale on every call (output stable modulo LLM nondeterminism in prose-summary blocks).
  - **Step 3** writers regenerate their fragments wholesale from current diagrams on every call (output stable modulo LLM nondeterminism).
  - **Step 4** (`application-exceptions-specifier`) is deterministic from method flows + raising-method identity params; idempotent on stable input.
  - **Step 5** (`specs-merger`) is mechanical — concatenates fragments in a fixed order, deletes consumed fragments. Re-running on identical fragments yields identical output.
  - **Step 6** (`services-finder`) regenerates `services.md` from current inputs; byte-stable on stable inputs modulo LLM prose drift.
  - **Step 7** (`application-updates-writer`) is a pure HEAD-vs-working-tree diff and overwrites `updates.md` from scratch; reads the three delta reports for source attribution.
  - **Step 9** (the rest-api / messaging re-cascade) fans out two independently idempotent skills; re-running re-derives their reports from disk + git. A downstream `ERROR:` does not abort the sibling or fail the application-side update.
- The only failures `/application-spec:update-specs` cannot retry through are the Step 0 missing-input cases (**0b–0f**; 0a is no longer a failure — an absent domain report degrades the domain axis to no-change with a `WARNING`) and the total-abort gate (1.all). Each error message directs the operator to the correct fix — diagram-restore-or-rename for the missing input diagrams, `/application-spec:generate-specs` for everything else.

## Idempotency

Re-running `/application-spec:update-specs` against unchanged inputs (working-tree specs unchanged versus HEAD, same domain `updates.md`, same `<stem>.commands.md` / `<stem>.queries.md`) produces:

- Fresh, byte-stable (modulo LLM drift) commands-updates.md / queries-updates.md from Step 0.
- A no-op through Step 2 (skipping Steps 3–6) when every axis's flag-contribution is empty — but Step 7 (report), Step 8 (summary), and Step 9 (the rest-api / messaging re-cascade) still run.
- Otherwise, byte-identical fragments, merged specs, services report, and updates report — modulo LLM prose drift in the deps / methods / services-finder agents (`git diff` noise, not a correctness failure).

There are no sentinel comments in `<plugin_dir>/updates.md` beyond those the writer emits per `application-spec:updates-report-template`. Unlike persistence-spec's `<!-- appended-from updates-hash:<hash> -->` (which guards the append-only migrations log), every section here is a snapshot — re-running over unchanged inputs simply reproduces the same content.

## What this skill deliberately does not do

- It does not regenerate `<stem>.application/{commands,queries}.specs.md` or `services.md` end-to-end — that is `/application-spec:generate-specs`. In particular it does not invoke a scaffolder (the files already exist).
- It does not re-diff `<domain_diagram>` and does not invoke (or produce) `domain-spec:updates-detector`'s report — the domain `updates.md` is consumed **if present**, and an absent report degrades the domain axis to no-change (Step 0a, with a `WARNING`) rather than hard-failing.
- It does not touch the diagram files (`<stem>.md`, `<stem>.commands.md`, `<stem>.queries.md`) or any Artifacts index — those siblings are linked from the original `/application-spec:generate-specs` run.
- It does not itself act on the `surface-markers` or `messaging-markers` categories that may appear on the commands-diagram updates report — those drive `/rest-api-spec:update-specs` and `/messaging-spec:update-specs` respectively. This orchestrator ignores them for its *own* dispatch (no `commands_dirty` contribution) but **delegates** them by re-cascading to both skills at Step 9.
- It does not pre-check the narrower abort conditions of the methods writers (a missing `save(...)` on the command repo, an aggregate-root method renamed under the application diagrams' canonical shape, a referenced `<<Service>>` removed, a query-repo finder rename that breaks a same-name match, an external-interface operation rename). The methods writers abort with their own one-sentence errors and the orchestrator surfaces them verbatim from Step 3.
- It does not preserve hand-edits inside the spec — the writer/merger contract is that the spec is regenerated from the diagrams, not curated. The unaffected side's `<side>.specs.md` is preserved byte-identically (the chosen approach's main payoff); inside a regenerated side, manual edits are wholesale replaced.
- It does not auto-update generated application code (`<aggregate>_commands.py`, `<aggregate>_queries.py`, infrastructure stubs, test fakes, DI providers, conftest fixtures, application exception classes appended to the domain aggregate's `exceptions.py`, integration tests) — that is the cross-layer `/update-code` skill (`domain-spec:update-code`), which consumes the `<stem>.application/updates.md` this skill emits.
- It is independently invocable (the entry point for a commands/queries-diagram-only change), **and** is one of the two downstream skills fanned out in parallel by domain `/update-specs`'s Step 10 (alongside `/persistence-spec:update-specs`). Its behaviour is **identical** either way: it always produces the two app-service-axis detector reports at Step 0g and always re-cascades to rest-api / messaging at Step 9. It does **not** receive `--detectors-fresh` (it is the producer), but it does **pass** `--detectors-fresh` down to rest-api / messaging. Domain no longer pre-produces the detector reports and no longer invokes rest-api / messaging directly — that subtree is rooted here.
