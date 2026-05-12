---
name: update-specs
description: Surgically updates the application service specs (`commands.specs.md`, `queries.specs.md`, `services.md`) after a domain diagram change — regenerates only the dirty side(s) from the current diagrams, refreshes application exceptions, re-runs the services finder, and emits the application updates report. Consumes the domain `updates.md`; never re-diffs the diagram. Invoke with: /application-spec:update-specs <domain_diagram>
argument-hint: <domain_diagram>
allowed-tools: Read, Bash, Agent
---

You are an application spec **update** orchestrator. Given a domain diagram whose `<dir>/<stem>.domain/updates.md` report describes a change, refresh the existing `<dir>/<stem>.application/commands.specs.md`, `<dir>/<stem>.application/queries.specs.md`, and `<dir>/<stem>.application/services.md` in place — re-run only the dirty side's writers, re-enrich application exceptions, re-run `services-finder`, and emit `<dir>/<stem>.application/updates.md`. Do not rerun the full `/application-spec:generate-specs` pipeline, do not touch the diagram files, and do not ask for confirmation before writing.

This skill is the application-side counterpart to `/update-specs` (domain) and `/persistence-spec:update-specs`. Design rationale lives in `notes/spec-updater-approach.md`, `notes/update-types.md`, and `notes/updates-report.md`; the load-bearing idea is **per-side snapshot regen** — every section of `<side>.specs.md` is a pure snapshot, so the surgical unit of work is one full side, not one method block. Commands and queries are independent; a domain delta touches at most one or both.

This skill **does not** detect domain-level deltas — it consumes the `<dir>/<stem>.domain/updates.md` report that `domain-spec:updates-detector` (Step 0 of domain `/update-specs`, or an explicit prior invocation) already wrote. It never re-diffs the diagram and never invokes `domain-spec:updates-detector`.

This skill covers only the **domain-driven axis**. Changes that originate in `<stem>.commands.md` / `<stem>.queries.md` (the application-service diagrams) are out of scope here — see *What this skill deliberately does not do* below.

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
| `<plugin_dir>/commands.specs.md` | spec being updated (must already exist) | `commands-deps-writer` + `commands-methods-writer` (per-side fragments) → `application-exceptions-specifier` → `specs-merger commands` (when commands dirty) |
| `<plugin_dir>/queries.specs.md` | spec being updated (must already exist) | `queries-deps-writer` + `queries-methods-writer` (per-side fragments) → `application-exceptions-specifier` → `specs-merger queries` (when queries dirty) |
| `<plugin_dir>/services.md` | spec being updated (must already exist) | `services-finder` (when at least one side was dirty) |
| `<plugin_dir>/updates.md` | output — application delta report | `application-updates-writer` |

`<domain_diagram>`, `<commands_diagram>`, and `<queries_diagram>` are read by the invoked agents; this orchestrator never modifies them. Every agent derives `<dir>` / `<stem>` from `$ARGUMENTS[0]` per `application-spec:naming-conventions` — pass `$ARGUMENTS[0]` verbatim as the prompt to each.

This skill keeps no runtime state between agents. The updates writer recovers the pre-update specs via `git show HEAD:<spec_file>` for each of the three spec files, so there is nothing for the orchestrator to capture or hand along.

## Workflow

### Step 0 — Verify inputs

Derive `<dir>` and `<stem>` from `$ARGUMENTS[0]` per `application-spec:naming-conventions`. `<stem>` must satisfy `^[a-z][a-z0-9-]*$`. Using `Bash` (`test -f`):

- **0a.** If `<dir>/<stem>.domain/updates.md` is missing → hard-fail:

  ```
  ERROR: <dir>/<stem>.domain/updates.md not found. The application updater consumes the domain
  updates report; it is not the first-run pipeline. Run `/update-specs <domain_diagram>` (or
  `@updates-detector <domain_diagram>`) first, or run `/application-spec:generate-specs <domain_diagram>`
  to regenerate the application specs from scratch.
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

Do not synthesize any of these files. Do not invoke any agent.

### Step 1 — Preflight

`Read` `<dir>/<stem>.domain/updates.md`. It is the orchestrator's single source of truth for this step — do not re-derive anything from the diagram. Use `Bash` (`grep`) and `Read` to extract:

- **`degraded_baseline`** — whether the `## Summary` block contains a line beginning `_warning: HEAD `.
- **`stereotype_changed`** — class names listed under `## Class Lifecycle → Stereotype Changed` (one bullet per class; the exact bullet format is owned by `domain-spec:updates-report-template`). Empty when the heading is absent or its body is `_None._`-style.
- **`removed_classes`** — bullets under `## Class Lifecycle → Removed`, each `` - `ClassName` `<<Stereotype>>` ``. Capture `(class_name, stereotype)` per bullet.
- **`added_classes`** — bullets under `## Class Lifecycle → Added`, each `` - `ClassName` `<<Stereotype>>` `` (the `— <N> attributes, <N> methods` suffix is informational; ignore for dispatch). Capture `(class_name, stereotype)` per bullet.
- **`affected_categories`** — bullets under `## Affected Categories`, in the order they appear. The literal body `_None._` means empty.
- **`per_class_changes`** — whether `## Per-Class Changes` is present with at least one `### `-style class block. Used for the dispatch step's prose-or-member proxy.
- **`orphan_prose`** — whether `## Orphan Prose Changes` is present with a non-empty body (the synthetic `### Preamble` block counts). Used only to colour the no-op message.
- **`repo_class_lifecycle`** — whether any bullet under `## Class Lifecycle → Added` or `→ Removed` carries the stereotype `<<Repository>>`.

Apply the gates below **in order**. The first one that fires terminates Step 1 — later gates are not evaluated.

#### 1a. Hard-fail: degraded baseline

If `degraded_baseline` is true:

```
ERROR: HEAD baseline is degraded (multiple or missing Mermaid blocks at HEAD per <stem>.domain/updates.md).
The surgical application updater cannot operate against a degraded baseline. Run
`/application-spec:generate-specs <domain_diagram>` to regenerate the application specs from scratch.
```

#### 1b. Hard-fail: stereotype change

If `stereotype_changed` is non-empty:

```
ERROR: Class(es) <names> have stereotype changes in <stem>.domain/updates.md. A stereotype change moves a
class to a different pattern catalog (e.g. a value object becoming a child entity), which means the
application spec is no longer addressing the right kind of class. Run
`/application-spec:generate-specs <domain_diagram>` to regenerate from scratch.
```

Surface every offending name, not just the first.

#### 1c. Hard-fail: aggregate-root removal

If any bullet in `removed_classes` has stereotype `<<Aggregate Root>>`:

```
ERROR: Aggregate root `<ClassName>` is listed under `## Class Lifecycle → Removed` in
<stem>.domain/updates.md. The `<AggregateRoot>Commands` / `<AggregateRoot>Queries` services lose their
anchor; an aggregate-root rename also moves the diagram filenames (a coordinated multi-file rename the
updater cannot perform). Rename the diagrams (`<stem>.md`, `<stem>.commands.md`, `<stem>.queries.md`)
and the `<stem>.application/` folder, then run `/application-spec:generate-specs <domain_diagram>`.
```

#### 1d. Hard-fail: `<<Repository>>` interface lifecycle change

If `repo_class_lifecycle` is true (a `<<Repository>>`-stereotyped class added or removed):

```
ERROR: A `<<Repository>>` interface was added or removed per <stem>.domain/updates.md. A domain aggregate
without its `Command<X>Repository` / `Query<X>Repository` cannot back an application service, and a new
repository requires a fresh dependency selection. Run `/application-spec:generate-specs <domain_diagram>`.
```

Note: the orchestrator does not pre-check the narrower cases the methods writers also abort on (a missing
`save(...)` on the command repo, an aggregate-root method renamed/removed under the application diagrams'
canonical shape, a domain `<<Service>>` removed/stereotype-changed while still referenced by the commands
diagram, a query-side external-interface operation renamed/removed, a query-repo finder rename that breaks
the same-name match). The methods writers themselves abort on these and surface a one-sentence error
directing the operator to reconcile the relevant application-service diagram. The orchestrator surfaces
that error verbatim from Step 2.

### Step 2 — Dispatch tier

Compute two booleans from the values captured in Step 1:

```
commands_dirty = (set(affected_categories) & {"aggregates", "value-objects", "repositories-services"}) != set()
              or per_class_changes

queries_dirty  = (set(affected_categories) & {"data-structures", "repositories-services"}) != set()
              or per_class_changes
```

Rationale (category-level dispatch):

- **`aggregates`** and **`value-objects`** can only affect the commands side (factory seeded-fields, postcondition prose, `Requires Aggregate State`, child-collection re-index). Queries methods go through DTOs and are byte-neutral on these.
- **`data-structures`** can only affect the queries side (Returns shape-hint prose at most). Command methods always return `<AggregateRoot>` and never name a TypedDict.
- **`repositories-services`** can affect either side — `Command<X>Repository` finder churn and referenced-`<<Service>>` method-signature changes drive the commands side; `Query<X>Repository` finder churn and query-side external-interface operation churn drive the queries side. Without finer-grained class identification we mark both sides dirty; the unaffected side's regen is byte-stable on stable inputs and only contributes diff noise.
- **`per_class_changes`** non-empty is treated as a prose proxy — the methods writers re-read the domain diagram's surrounding prose as advisory description, and a class-keyed prose change might nudge a Purpose / postcondition / collaborator-hint / status-gating / External-Interface-hint clause. We err on the side of regenerating both sides; the typical outcome is byte-stable output modulo LLM prose drift.
- **`domain-events`** and **`commands`** (the domain-message-dataclass category) never appear in application method specs — `affected_categories ⊆ {domain-events, commands}` alone leaves both flags false.

If neither flag is true → **Tier 4 no-op**. Skip Steps 3–6 and jump straight to Step 7 (emit the report) so a `<stem>.application/updates.md` always exists after a successful run; the writer sees the working-tree specs unchanged versus HEAD and emits an all-`_no changes_` report. Then run Step 8 (which renders the no-op summary line) and exit.

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

Invoke `application-spec:application-updates-writer` with prompt `$ARGUMENTS[0]`. It diffs the working-tree specs (`commands.specs.md`, `queries.specs.md`, `services.md`) against `git HEAD`, classifies the per-section deltas, derives the `## Affected Artifacts` table mechanically, and writes `<dir>/<stem>.application/updates.md` (always — even on Tier 4 no-op, where every section after `## Summary` renders `_no changes_` and the Affected Artifacts table has no data rows).

The writer recovers everything it needs from disk + git + the sibling domain `updates.md`; the orchestrator passes nothing else.

This step runs **on every successful run**, including the Tier 4 no-op early-exit case (Step 2). The consumer's contract (`/application-spec:update-code`, future) requires the report to always exist after a successful run.

If the writer reports a failure, abort and emit a single `ERROR:` line repeating its message. The application specs are already in their final post-update state by this point — re-running the orchestrator (or just the updates writer agent standalone) idempotently produces the report.

### Step 8 — Report

Print one summary line. The shape depends on the dispatch outcome:

- **Tier 4 no-op**:
  - If `orphan_prose` is true: `No application spec updates required. Orphan prose changes detected — review <stem>.domain/updates.md. Emitted <stem>.application/updates.md.`
  - Otherwise: `No application spec updates required (no application-relevant domain changes). Emitted <stem>.application/updates.md.`

- **At least one side dirty**:
  ```
  Updated <stem>.application/{<files>} (<dispatch_clause>) and emitted <stem>.application/updates.md.
  ```
  Where:
  - `<files>` is a comma-separated list, in canonical order: `commands.specs.md` (when commands_dirty), `queries.specs.md` (when queries_dirty), `services.md` (always — Step 6 always runs).
  - `<dispatch_clause>` is one of `regenerated commands side`, `regenerated queries side`, or `regenerated both sides`, matching the dirty-flag combination.

Do not emit additional commentary — each invoked agent already printed its own per-step report.

## Failure semantics

- Every step that aborts emits exactly one `ERROR:` line and exits the workflow. Do not chain further agents on top of a failed step.
- The orchestrator does not roll back partial writes. **Re-running `/application-spec:update-specs` after fixing the trigger is the supported recovery path** — every step is idempotent on stable inputs:
  - **Step 3** writers regenerate their fragments wholesale from current diagrams on every call (output stable modulo LLM nondeterminism).
  - **Step 4** (`application-exceptions-specifier`) is deterministic from method flows + raising-method identity params; idempotent on stable input.
  - **Step 5** (`specs-merger`) is mechanical — concatenates fragments in a fixed order, deletes consumed fragments. Re-running on identical fragments yields identical output.
  - **Step 6** (`services-finder`) regenerates `services.md` from current inputs; byte-stable on stable inputs modulo LLM prose drift.
  - **Step 7** (`application-updates-writer`) is a pure HEAD-vs-working-tree diff and overwrites `updates.md` from scratch.
- The only failures `/application-spec:update-specs` cannot retry through are the Step 0 missing-input cases (0a–0f) and the Step 1 preflight hard-fails (1a–1d). Each error message directs the operator to the correct fix — `/update-specs` / `@updates-detector` for the missing domain report, diagram-restore-or-rename for the missing input diagrams, `/application-spec:generate-specs` for everything else.

## Idempotency

Re-running `/application-spec:update-specs` against unchanged inputs (working-tree specs unchanged versus HEAD, same domain `updates.md`) produces:

- A no-op early-exit through Step 2 when `affected_categories` and per-class blocks are empty enough to leave both dirty flags false.
- Otherwise, byte-identical fragments, merged specs, services report, and updates report — modulo LLM prose drift in the deps / methods / services-finder agents (`git diff` noise, not a correctness failure).

There are no sentinel comments. Unlike persistence-spec's `<!-- appended-from updates-hash:<hash> -->` (which guards the append-only migrations log), every section here is a snapshot — re-running over an unchanged domain `updates.md` simply reproduces the same content.

## What this skill deliberately does not do

- It does not regenerate `<stem>.application/{commands,queries}.specs.md` or `services.md` end-to-end — that is `/application-spec:generate-specs`. In particular it does not invoke a scaffolder (the files already exist).
- It does not re-diff `<domain_diagram>` and does not invoke `domain-spec:updates-detector` — the domain `updates.md` is expected on disk before this skill runs.
- It does not touch the diagram files (`<stem>.md`, `<stem>.commands.md`, `<stem>.queries.md`) or any Artifacts index — those siblings are linked from the original `/application-spec:generate-specs` run.
- It does not handle commands-/queries-diagram changes (a method added/removed, a method signature changed, a collaborator added/dropped, multi-tenancy added). Those originate in the application-service diagrams, are not captured by `<stem>.domain/updates.md`, and require either a future `application-spec:updates-detector` analog or a fresh `/application-spec:generate-specs` run.
- It does not handle aggregate-root removal/rename, stereotype changes, `<<Repository>>` interface lifecycle changes, or a degraded baseline — those route to `/application-spec:generate-specs` via the Step 1 hard-fails.
- It does not pre-check the narrower abort conditions of the methods writers (a missing `save(...)` on the command repo, an aggregate-root method renamed under the application diagrams' canonical shape, a referenced `<<Service>>` removed, a query-repo finder rename that breaks a same-name match, an external-interface operation rename). The methods writers abort with their own one-sentence errors and the orchestrator surfaces them verbatim from Step 3.
- It does not preserve hand-edits inside the spec — the writer/merger contract is that the spec is regenerated from the diagrams, not curated. The unaffected side's `<side>.specs.md` is preserved byte-identically (the chosen approach's main payoff); inside a regenerated side, manual edits are wholesale replaced.
- It does not auto-update generated application code (`<aggregate>_commands.py`, `<aggregate>_queries.py`, infrastructure stubs, test fakes, DI providers, conftest fixtures, application exception classes appended to the domain aggregate's `exceptions.py`, integration tests) — that is the future `/application-spec:update-code` skill, which consumes the `<stem>.application/updates.md` this skill emits.
- It is independently invocable, **and** is chained as **Step 11** of domain `/update-specs` — after the persistence Step 10 chain, before the rest-api Step 12 chain. A missing-spec-file hard-fail (Steps 0b–0f) when invoked from that chain aborts the rest of the cascade; run `/application-spec:generate-specs` (and `/application-spec:generate-code`) before relying on the domain-level cascade.
