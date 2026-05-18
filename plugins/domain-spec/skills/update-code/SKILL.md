---
name: update-code
description: Three-phase orchestrator for cross-layer code updates after `/update-specs`. Phase 1 (gather) spawns one `code-brief-writer` per active layer in parallel; Phase 1.5 fires a single risk-tag checkpoint only when any brief flags a `risky` row; Phase 2 (implement) spawns `code-change-writer` agents in three dependency-ordered waves (domain → persistence + application in parallel → rest-api + messaging in parallel); Phase 3 (review) is opt-in via the `--review` flag and runs every active layer's `code-review-writer` in parallel. The orchestrator itself never reads a spec sibling and never edits source code. Invoke with: /update-code <domain_diagram> [--review]
argument-hint: <domain_diagram> [--review]
allowed-tools: Read, Bash, Agent, AskUserQuestion
---

You are a cross-layer **code-update orchestrator**. After `/update-specs` has refreshed every per-layer spec sibling, this skill drives the three-agent flow per layer (`gather → implement → review`) and applies edits to on-disk code.

This is the execution analog of `/update-specs`. Where `/update-specs` propagates spec deltas through five spec layers, this skill propagates them to source files. The orchestrator itself **never reads a spec sibling and never edits source code** — those responsibilities live entirely in the per-plugin `code-brief-writer`, `code-change-writer`, and `code-review-writer` agents.

## Inputs

Given `<domain_diagram>` at `<dir>/<stem>.md`, the orchestrator reads only the four candidate `<stem>.<layer>/updates.md` files via `test -f` probes to determine active layers, plus the domain `updates.md` itself for the preflight gates. The brief, implement, and review agents own every other read.

`--review` is an optional flag that may appear in any position in `$ARGUMENTS`. When present, Phase 3 runs after Phase 2; when absent, Phase 3 is skipped entirely. There is no global risky-count threshold gating review — the flag is the only switch.

## Outputs

Each per-layer agent writes its own sibling artifact:

| Phase | File | Owner |
|---|---|---|
| 1 (gather) | `<dir>/<stem>.<layer>/code-brief.md` | `@<plugin>:code-brief-writer` |
| 2 (implement) | `<dir>/<stem>.<layer>/code-changes.md` + source edits | `@<plugin>:code-change-writer` |
| 3 (review) | `<dir>/<stem>.<layer>/code-review.md` | `@<plugin>:code-review-writer` |

The orchestrator itself writes nothing to disk — its only emission is the final summary table to chat.

## Workflow

### Step 0 — Parse arguments

`$ARGUMENTS` carries `<domain_diagram> [--review]`. The diagram is the only non-flag positional argument; `--review` may appear in any position. Set `RUN_REVIEW=true` iff the token `--review` is present anywhere in `$ARGUMENTS`. Strip the flag and bind `$DIAGRAM` to the remaining positional.

If no positional remains after flag stripping, hard-fail:

```
ERROR: /update-code requires <domain_diagram>. Usage: /update-code <domain_diagram> [--review]
```

### Step 1 — Preflight

Derive `<stem>` by stripping `.md` from the basename of `$DIAGRAM`, and `<dir>` as its directory. Read `<dir>/<stem>.domain/updates.md`. If missing, hard-fail:

```
ERROR: <stem>.domain/updates.md not found. Run `/update-specs <domain_diagram>` before `/update-code`.
```

If the report's Summary contains a `_warning: HEAD ...` line (degraded baseline), hard-fail:

```
ERROR: Degraded baseline in <stem>.domain/updates.md. Re-run `/update-specs` after fixing HEAD, or regenerate via `/generate-code <domain_diagram>`.
```

### Step 2 — Probe per-layer activeness

For each of `persistence`, `application`, `rest-api`, `messaging`, probe via `Bash` (`test -f <dir>/<stem>.<layer>/updates.md`). Mark the layer **active** iff its `updates.md` exists. The `domain` layer is always active (Step 1 already read it).

Bind `<active_layers>` to the ordered list of active layers in canonical order: `domain, persistence, application, rest-api, messaging` (filtered to those marked active).

### Step 3 — No-op early exit

For each active layer, parse its `updates.md` and check whether its body sections all read `_no changes_` AND its `## Affected Artifacts` table is empty or absent. (Refer to each plugin's `updates-report-template` skill for the exact body markers.) If **all** active layers are no-ops, print:

```
No code updates required across active layers.
```

and exit cleanly without spawning any agents.

### Step 4 — Find target locations (parallel)

Spawn one `target-locations-finder` per active layer. **Send all invocations in a single message** so they run in parallel:

- `@domain-spec:target-locations-finder $DIAGRAM` — the domain finder takes the diagram.
- `@persistence-spec:target-locations-finder` — no arg; auto-discovers from cwd.
- `@application-spec:target-locations-finder` — no arg.
- `@rest-api-spec:target-locations-finder` — no arg.
- `@messaging-spec:target-locations-finder` — no arg.

Skip the finder for any inactive layer.

Wait for all to complete. Capture each agent's full Markdown table output verbatim and bind it to `<locations_report_<layer>>`. Each per-layer report is passed verbatim into that layer's Phase 1, 2, and 3 agents.

If any finder reports a failure, abort with `ERROR:` repeating its message. Do not proceed to Phase 1.

### Step 5 — Phase 1: gather (parallel)

Spawn one `code-brief-writer` per active layer, **all in parallel** (single message). Each agent's prompt:

```
$DIAGRAM
<locations_report_<layer>>
```

Use the fully-qualified agent name per layer:

- `@domain-spec:code-brief-writer`
- `@persistence-spec:code-brief-writer`
- `@application-spec:code-brief-writer`
- `@rest-api-spec:code-brief-writer`
- `@messaging-spec:code-brief-writer`

Wait for every agent to complete. If any brief-writer hard-fails, abort with `ERROR:` repeating its message. Do not proceed to the risk-tag checkpoint.

After every agent completes, count `Risk: risky` rows across every `<dir>/<stem>.<layer>/code-brief.md` and bind `<risky_count>` to the sum.

### Step 6 — Phase 1.5: risk-tag checkpoint

If `<risky_count> == 0`, proceed silently to Step 7.

Otherwise, fire one `AskUserQuestion` to confirm the operator wants to apply the risky edits. Use exactly two options, mutually exclusive. The recommended option must still be selected explicitly — there is no default-proceed when risky rows are present.

- Question: `<risky_count> artifact(s) tagged \`risky\` across <K> layer(s). Risky tags surface judgment calls that Phase 1 wants the operator to verify before edits land (e.g. aggregate-root method edits, destructive migrations, multi-pattern conflicts). Proceed?`
- Header: `Risky edits`
- Options:
  1. `Proceed (recommended)` — apply Phase 2.
  2. `Abort` — leave the briefs on disk and stop.

On `Abort`, print `Aborted at risk-tag checkpoint. Briefs preserved under <stem>.<layer>/code-brief.md.` and exit cleanly.

### Step 7 — Phase 2: implement (three waves)

The change-writers' edits read on-disk source from upstream layers (domain feeds persistence + application; application feeds rest-api + messaging). Run in dependency order so each downstream wave sees the upstream's settled state.

Each invocation uses the qualified agent name and the same prompt shape as Phase 1:

```
$DIAGRAM
<locations_report_<layer>>
```

#### Wave A — domain

If `domain` is active, spawn `@domain-spec:code-change-writer` in its own message. Wait for completion. (Skip the wave if domain is somehow inactive — defensive; Step 1 already ensured the domain `updates.md` exists.)

#### Wave B — persistence + application (parallel)

Spawn the active subset in a single message:

- `@persistence-spec:code-change-writer` (if persistence active)
- `@application-spec:code-change-writer` (if application active)

Wait for both to complete.

#### Wave C — rest-api + messaging (parallel)

Spawn the active subset in a single message:

- `@rest-api-spec:code-change-writer` (if rest-api active)
- `@messaging-spec:code-change-writer` (if messaging active)

Wait for both to complete.

**Cross-wave failure semantics.** Per-row failures within a single agent are recorded in that agent's `code-changes.md` as `Status: failed: <reason>` and **do not** abort the orchestrator. Only an agent-level hard-fail (the agent prints `ERROR:`) triggers cross-wave handling:

- A `domain` hard-fail aborts Wave B and Wave C — their source reads would be stale.
- A `persistence` hard-fail does **not** abort Wave C — rest-api and messaging do not read persistence source. Continue.
- An `application` hard-fail aborts Wave C — rest-api and messaging read application source.
- A `rest-api` or `messaging` hard-fail is terminal — no downstream waves remain.

When the orchestrator aborts a downstream wave, surface the one `ERROR:` line and skip directly to Step 9 (summary). Briefs and any successfully-written change logs remain on disk.

### Step 8 — Phase 3: review (opt-in)

If `RUN_REVIEW == false`, skip to Step 9.

Otherwise, spawn one `code-review-writer` per active layer, **all in parallel** (single message). Each agent's prompt mirrors Phases 1 and 2:

```
$DIAGRAM
<locations_report_<layer>>
```

Use the fully-qualified agent names (`@domain-spec:code-review-writer`, `@persistence-spec:code-review-writer`, `@application-spec:code-review-writer`, `@rest-api-spec:code-review-writer`, `@messaging-spec:code-review-writer`).

Reviewers read `code-brief.md` + `code-changes.md` + on-disk source. Because Phase 2 completed before this step, the source state is consistent across layers — there is no dependency ordering among reviewers.

If any reviewer hard-fails, surface its `ERROR:` line. The other reviewers' reports remain on disk; proceed to Step 9.

### Step 9 — Summary

Print one summary block:

```
/update-code complete.

Layer        | Briefed | Edits  | Failures | Risky | Reviewed | Verdict
-------------|---------|--------|----------|-------|----------|---------------
domain       | <n>     | <n>    | <n>      | <n>   | yes/no   | clean/issues/—
persistence  | ...
application  | ...
rest-api     | ...
messaging    | ...

Artifacts (per active layer):
- <dir>/<stem>.<layer>/code-brief.md   (Phase 1)
- <dir>/<stem>.<layer>/code-changes.md (Phase 2)
- <dir>/<stem>.<layer>/code-review.md  (Phase 3, only when --review)
```

Source the row counts from each on-disk artifact:

- `Briefed` — total rows in `code-brief.md`.
- `Edits` — rows in `code-changes.md` with `Status: applied`.
- `Failures` — rows with `Status: failed`.
- `Risky` — rows in `code-brief.md` with `Risk: risky`.
- `Reviewed` — `yes` if `code-review.md` exists (only when `--review` was passed and Phase 3 ran for that layer), else `no`.
- `Verdict` — `clean` / `issues` from `code-review.md`'s top-level verdict, or `—` when not reviewed.

Inactive layers do not appear in the table.

## Failure semantics

- Every step that aborts the orchestrator emits exactly one `ERROR:` line and stops at that point. Subsequent steps are skipped, but the summary block (Step 9) still prints, reflecting whatever artifacts exist on disk.
- Per-row failures inside a Phase 2 agent are recorded with `Status: failed: <reason>` in `code-changes.md` and do **not** abort the orchestrator. Only an agent-level hard-fail does.
- Each phase is idempotent on stable inputs. Re-running `/update-code` re-derives the briefs (writers overwrite), re-applies the edits (writers overwrite), and (when `--review`) re-derives the review reports. The brief/change/review siblings survive every abort path.
- A no-op early exit (Step 3) is a success — exit cleanly, no agents spawned, no plan-mode prompt.

## What this skill deliberately does not do

- It does not edit any source file. All edits go through `@<plugin>:code-change-writer`.
- It does not read any spec sibling or the diagram itself. All such reads happen inside the spawned agents.
- It does not enter plan mode. The three-phase pipeline replaces the previous plan-mode-only flow.
- It does not invoke a code-plan.md output. The per-layer `code-brief.md` / `code-changes.md` / `code-review.md` siblings are the durable artifacts; the orchestrator emits only the summary table to chat.
- It does not auto-run Phase 3. Review is opt-in via `--review`. Skipping review is the default for low-risk runs; pass `--review` when the change set warrants the second pass.
- It does not run tests, format code, or regenerate `__init__.py` files end-to-end — those are change-writer concerns.
- It does not handle aggregate-root removals or stereotype changes — `/update-specs` hard-fails on those before this skill is ever reached.
- It does not detect hand-edited source on disk. Operators with hand-tuned method bodies must reconcile manually after Phase 2.
