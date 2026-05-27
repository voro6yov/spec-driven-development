---
name: temp-update-specs
description: "Application-only variant of `update-specs` for testing. Refreshes `<stem>.application/{commands.specs.md, queries.specs.md, services.md}` from the current domain diagram + sibling app-service diagrams and emits `<stem>.application/updates.md`. Invoke with: /application-spec:temp-update-specs <domain_diagram>"
argument-hint: <domain_diagram>
allowed-tools: Read, Bash, Agent
---

You are an application-spec **update** orchestrator running in testing mode. This is a thin variant of `/application-spec:update-specs` — invoke it when iterating on the application updater alone so the test cadence and slash-command namespace stay isolated from the layer-cascading `/update-specs` flow.

The behaviour is byte-identical to `/application-spec:update-specs`: invoke the two app-service-axis detectors, refresh the dirty sides of `<dir>/<stem>.application/{commands.specs.md, queries.specs.md}` and re-run `services-finder` to refresh `<dir>/<stem>.application/services.md`, then emit `<dir>/<stem>.application/updates.md`. Do not rerun the full `/application-spec:generate-specs` pipeline, do not touch the diagram files, and do not ask for confirmation before writing.

This skill **does not** detect domain-level deltas — it consumes the `<dir>/<stem>.domain/updates.md` report that `domain-spec:updates-detector` (Step 0 of domain `/update-specs` or `/temp-update-specs`, or an explicit prior invocation) already wrote. It never re-diffs the domain diagram and never invokes `domain-spec:updates-detector`.

Unlike `/application-spec:update-specs`, this skill **does not** accept the `--detectors-fresh` cascade-mode shortcut — it is invoked standalone for testing and always runs the two app-service-axis detectors itself at Step 0g.

## Output path convention

Per `application-spec:naming-conventions`, given `<domain_diagram>` at `<dir>/<stem>.md`:

- `<dir>` = directory containing the diagrams.
- `<stem>` = the canonical aggregate stem (domain filename with `.md` stripped).
- `<plugin_dir>` = `<dir>/<stem>.application` — the per-plugin folder for application-spec.

| File | Role | Touched by |
|---|---|---|
| `<dir>/<stem>.domain/updates.md` | input — domain delta report (must already exist) | not modified |
| `<dir>/<stem>.commands.md` | input — hand-authored commands diagram (must already exist) | not modified |
| `<dir>/<stem>.queries.md` | input — hand-authored queries diagram (must already exist) | not modified |
| `<plugin_dir>/commands-updates.md` | input — commands-diagram delta report | produced by `commands-updates-detector` at Step 0g |
| `<plugin_dir>/queries-updates.md` | input — queries-diagram delta report | produced by `queries-updates-detector` at Step 0g |
| `<plugin_dir>/commands.specs.md` | spec being updated (must already exist) | `commands-deps-writer` + `commands-methods-writer` (per-side fragments) → `application-exceptions-specifier` → `specs-merger commands` (when commands dirty) |
| `<plugin_dir>/queries.specs.md` | spec being updated (must already exist) | `queries-deps-writer` + `queries-methods-writer` (per-side fragments) → `application-exceptions-specifier` → `specs-merger queries` (when queries dirty) |
| `<plugin_dir>/services.md` | spec being updated (must already exist) | `services-finder` (when at least one side was dirty) |
| `<plugin_dir>/updates.md` | output — application delta report | `application-updates-writer` |

Every agent derives `<dir>` / `<stem>` from `$ARGUMENTS[0]` per `application-spec:naming-conventions` — pass `$ARGUMENTS[0]` verbatim as the prompt to each.

## Workflow

### Step 0 — Verify inputs and produce the app-service-axis reports

Derive `<dir>` and `<stem>` from `$ARGUMENTS[0]` per `application-spec:naming-conventions`. `<stem>` must satisfy `^[a-z][a-z0-9-]*$`. Using `Bash` (`test -f`), verify the input files in this order:

- **0a.** If `<dir>/<stem>.domain/updates.md` is missing → hard-fail:

  ```
  ERROR: <dir>/<stem>.domain/updates.md not found. The application updater consumes the domain
  updates report; it is not the first-run pipeline. Run `/update-specs <domain_diagram>` (or
  `/temp-update-specs <domain_diagram>` from domain-spec, or `@updates-detector <domain_diagram>`)
  first, or run `/application-spec:generate-specs <domain_diagram>` to regenerate the application
  specs from scratch.
  ```

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

After 0a–0f pass, fan out the two detectors in a single message so they run concurrently. Pass `$ARGUMENTS[0]` (the domain diagram path) as the prompt to each — the detectors derive their own sibling diagrams via `application-spec:naming-conventions`.

- `application-spec:commands-updates-detector` with prompt `$ARGUMENTS[0]`.
- `application-spec:queries-updates-detector` with prompt `$ARGUMENTS[0]`.

Each detector writes its own report (`<plugin_dir>/commands-updates.md`, `<plugin_dir>/queries-updates.md`) or hard-fails with an `ERROR:` line. The detectors share `<plugin_dir>` only — both use `mkdir -p` idempotently, so the parallel pattern is safe.

If either detector hard-fails, abort the orchestrator with that detector's `ERROR:` line repeated verbatim. The other detector's output (if it completed) is left on disk for the next run; no rollback is performed. The same `/application-spec:generate-specs <domain_diagram>` recovery path the detectors themselves direct to applies here.

Wait for both detectors to return successfully before proceeding to Step 1.

### Step 1 — Preflight (per-axis-scoped)

`Read` all three reports — `<dir>/<stem>.domain/updates.md`, `<plugin_dir>/commands-updates.md`, `<plugin_dir>/queries-updates.md`. They are the orchestrator's single source of truth for this step — do not re-derive anything from any diagram. Use `Bash` (`grep`) and `Read` to extract, per axis:

**Domain axis** (from `<stem>.domain/updates.md`):

- **`domain.degraded_baseline`** — whether the `## Summary` block contains a line beginning `_warning: HEAD `.
- **`domain.stereotype_changed`** — class names listed under `## Class Lifecycle → Stereotype Changed`. Empty when the heading is absent or its body is `_None._`-style.
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

#### 1.cmd — Commands-axis gates

| Gate | Trigger | Action |
|---|---|---|
| 1.cmd.a | `commands.degraded_baseline` true | Set `commands_axis_disabled = true`; emit `WARNING: commands-diagram axis disabled — HEAD baseline is degraded (multiple or missing Mermaid blocks at HEAD per <stem>.application/commands-updates.md). Commands-diagram-driven dispatch is skipped for this run.` |

#### 1.qry — Queries-axis gates

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
# Domain axis (existing rules, but axis-gated)
domain_commands_triggers = ∅ if domain_axis_disabled else
    (set(domain.affected_categories) & {"aggregates", "value-objects", "repositories-services"}) ∪
    ({"prose-proxy"} if domain.per_class_changes else ∅)
domain_queries_triggers  = ∅ if domain_axis_disabled else
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

If neither flag is true → **Tier 4 no-op**. Skip Steps 3–6 and jump straight to Step 7 (emit the report) so a `<stem>.application/updates.md` always exists after a successful run; the writer sees the working-tree specs unchanged versus HEAD and emits an all-`_no changes_` report. Then run Step 8 (which renders the no-op summary line) and exit.

If at least one flag is true, proceed to Step 3.

### Step 3 — Per-side regen (parallel where both sides fire)

For each dirty side, fan out the writer agents in parallel. **Emit all selected agent calls in a single message** so they run concurrently. Pass `$ARGUMENTS[0]` (the domain diagram path) as the prompt to each.

If `commands_dirty`:

- `application-spec:commands-deps-writer` with prompt `$ARGUMENTS[0]`.
- `application-spec:commands-methods-writer` with prompt `$ARGUMENTS[0]`.

If `queries_dirty`:

- `application-spec:queries-deps-writer` with prompt `$ARGUMENTS[0]`.
- `application-spec:queries-methods-writer` with prompt `$ARGUMENTS[0]`.

When both sides are dirty, all four writers fan out together in a single message. Wait for every selected writer to complete before proceeding.

If any writer reports a failure, abort the workflow and emit a single `ERROR:` line repeating its message verbatim. Do not run downstream agents.

### Step 4 — Enrich application exceptions

After all Step 3 writers return successfully, invoke `application-spec:application-exceptions-specifier` with prompt `$ARGUMENTS[0]`. The agent processes both sides in one call but auto-skips a side whose `<side>.exceptions.md` is absent.

If the enricher reports a failure, abort and emit a single `ERROR:` line repeating its message.

### Step 5 — Merge fragments per dirty side (parallel)

After the enricher returns, fan out the merger(s) in parallel for the dirty side(s) only. Emit the selected `Agent` calls in a single message:

- `application-spec:specs-merger` with prompt `$ARGUMENTS[0] commands` (if `commands_dirty`).
- `application-spec:specs-merger` with prompt `$ARGUMENTS[0] queries` (if `queries_dirty`).

Each merger consolidates its side's `<side>.deps.md` + `<side>.methods.md` + `<side>.exceptions.md` into `<plugin_dir>/<side>.specs.md` (overwriting the prior file) and deletes the consumed fragments. The unaffected side's `<side>.specs.md` is left byte-identical.

If a merger reports a failure, abort and emit a single `ERROR:` line repeating its message.

### Step 6 — Re-run services-finder

After all merger(s) return, invoke `application-spec:services-finder` with prompt `$ARGUMENTS[0]`. It re-reads the freshly merged specs plus the domain diagram and rewrites `<plugin_dir>/services.md`.

This step always runs after Step 5 (regardless of which sides were dirty).

If the agent reports a failure, abort and emit a single `ERROR:` line repeating its message.

### Step 7 — Emit the application updates report

Invoke `application-spec:application-updates-writer` with prompt `$ARGUMENTS[0]`. It diffs the working-tree specs against `git HEAD`, classifies the per-section deltas, reads the three on-disk delta reports for axis-tagged `Source delta` enrichment, derives the `## Affected Artifacts` table mechanically, and writes `<dir>/<stem>.application/updates.md` (always — even on Tier 4 no-op).

This step runs **on every successful run**, including the Tier 4 no-op early-exit case (Step 2).

If the writer reports a failure, abort and emit a single `ERROR:` line repeating its message.

### Step 8 — Report

Print one summary line. The shape depends on the dispatch outcome.

Build `<axis_summary>` first — a comma-separated list (in canonical order: `domain`, `commands-diagram`, `queries-diagram`) of axes that contributed at least one trigger to a dirty-side flag.

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

## Failure semantics

- Every step that aborts emits exactly one `ERROR:` line and exits the workflow.
- Re-running `/application-spec:temp-update-specs` after fixing the trigger is the supported recovery path — every step is idempotent on stable inputs.
- The only failures this skill cannot retry through are the Step 0 missing-input cases (0a–0f) and the total-abort gate (1.all). Each error message directs the operator to the correct fix.

## What this skill deliberately does not do

- It does not chain to `/persistence-spec:update-specs`, `/rest-api-spec:update-specs`, or `/messaging-spec:update-specs`. The application layer's `update-specs` never cascaded, so the "temp" prefix here is purely a testing namespace that keeps this invocation off the layer-cascading `/update-specs` path.
- It does not accept the `--detectors-fresh` cascade-mode shortcut. It is invoked standalone for testing and always runs the two app-service-axis detectors itself at Step 0g.
- It does not regenerate `<stem>.application/{commands,queries}.specs.md` or `services.md` end-to-end — that is `/application-spec:generate-specs`.
- It does not re-diff `<domain_diagram>` and does not invoke `domain-spec:updates-detector` — the domain `updates.md` is expected on disk before this skill runs.
- It does not touch the diagram files (`<stem>.md`, `<stem>.commands.md`, `<stem>.queries.md`) or any Artifacts index.
- It does not act on the `surface-markers` or `messaging-markers` categories that may appear on the commands-diagram updates report — those drive `/rest-api-spec:update-specs` and `/messaging-spec:update-specs` respectively. This orchestrator silently ignores them.
- It does not preserve hand-edits inside the spec — the writer/merger contract is that the spec is regenerated from the diagrams, not curated.
- It does not auto-update generated application code — pair this skill with `/application-spec:temp-update-code <domain_diagram>` for the application-only code-update analog.
