---
name: temp-update-code
description: "Application-only variant of `update-code` for testing. Runs the three-phase flow (gather → implement → review) against the application layer alone. Invoke with: /application-spec:temp-update-code <domain_diagram> [--review]"
argument-hint: <domain_diagram> [--review]
allowed-tools: Read, Bash, Agent, AskUserQuestion
---

You are an **application-only code-update orchestrator**. This is a testing variant of `/update-code` that exercises the three-agent flow (`gather → implement → review`) **only** for the application layer. Domain, persistence, REST API, and messaging layers are ignored entirely, even if their `updates.md` siblings exist.

The orchestrator itself **never reads a spec sibling and never edits source code** — those responsibilities live entirely in the `@application-spec:code-brief-writer`, `@application-spec:code-change-writer`, and `@application-spec:code-review-writer` agents.

## Inputs

Given `<domain_diagram>` at `<dir>/<stem>.md`, the orchestrator reads only `<dir>/<stem>.application/updates.md` for the preflight gate and the no-op early-exit check. The brief, implement, and review agents own every other read.

`--review` is an optional flag that may appear in any position in `$ARGUMENTS`. When present, Phase 3 runs after Phase 2; when absent, Phase 3 is skipped entirely.

## Outputs

The application-spec agents write these sibling artifacts:

| Phase | File | Owner |
|---|---|---|
| 1 (gather) | `<dir>/<stem>.application/code-brief.md` | `@application-spec:code-brief-writer` |
| 2 (implement) | `<dir>/<stem>.application/code-changes.md` + source edits | `@application-spec:code-change-writer` |
| 3 (review) | `<dir>/<stem>.application/code-review.md` | `@application-spec:code-review-writer` |

The orchestrator itself writes nothing to disk — its only emission is the final summary block to chat.

## Workflow

### Step 0 — Parse arguments

`$ARGUMENTS` carries `<domain_diagram> [--review]`. The diagram is the only non-flag positional argument; `--review` may appear in any position. Set `RUN_REVIEW=true` iff the token `--review` is present anywhere in `$ARGUMENTS`. Strip the flag and bind `$DIAGRAM` to the remaining positional.

If no positional remains after flag stripping, hard-fail:

```
ERROR: /application-spec:temp-update-code requires <domain_diagram>. Usage: /application-spec:temp-update-code <domain_diagram> [--review]
```

### Step 1 — Preflight

Derive `<stem>` by stripping `.md` from the basename of `$DIAGRAM`, and `<dir>` as its directory. Read `<dir>/<stem>.application/updates.md`. If missing, hard-fail:

```
ERROR: <stem>.application/updates.md not found. Run `/application-spec:update-specs <domain_diagram>` (or `/application-spec:temp-update-specs <domain_diagram>`) before `/application-spec:temp-update-code`.
```

### Step 2 — No-op early exit

Parse `<dir>/<stem>.application/updates.md` and check whether all four body sections (`## Commands Methods Changes`, `## Queries Methods Changes`, `## Application Exceptions Changes`, `## Services Changes`) read `_no changes_` AND its `## Affected Artifacts` table is empty or absent. (Refer to `application-spec:updates-report-template` for the exact body markers.)

If all sections are `_no changes_` AND the Affected Artifacts table has no data rows, print:

```
No application code updates required.
```

and exit cleanly without spawning any agents.

Otherwise proceed to Step 3.

### Step 3 — Find target locations

Spawn `@application-spec:target-locations-finder` (no arg — auto-discovers from cwd per the agent's contract) and wait for completion. Capture the agent's full Markdown table output verbatim and bind it to `<locations_report>`. This report is passed verbatim into Phases 1, 2, and 3.

If the finder reports a failure, abort with `ERROR:` repeating its message.

### Step 4 — Phase 1: gather

Spawn `@application-spec:code-brief-writer` with prompt:

```
$DIAGRAM
<locations_report>
```

Wait for completion. If it hard-fails, abort with `ERROR:` repeating its message.

After the agent completes, count `Risk: risky` rows in `<dir>/<stem>.application/code-brief.md` and bind `<risky_count>` to that count.

### Step 5 — Phase 1.5: risk-tag checkpoint

If `<risky_count> == 0`, proceed silently to Step 6.

Otherwise, fire one `AskUserQuestion` to confirm the operator wants to apply the risky edits.

- Question: `<risky_count> artifact(s) tagged \`risky\` in the application brief. Risky tags surface judgment calls that Phase 1 wants the operator to verify before edits land (e.g. aggregate-root method renames, service interface flips, exception-class lifecycle). Proceed?`
- Header: `Risky edits`
- Options:
  1. `Proceed (recommended)` — apply Phase 2.
  2. `Abort` — leave the brief on disk and stop.

On `Abort`, print `Aborted at risk-tag checkpoint. Brief preserved at <stem>.application/code-brief.md.` and exit cleanly.

### Step 6 — Phase 2: implement

Spawn `@application-spec:code-change-writer` with the same prompt shape as Phase 1:

```
$DIAGRAM
<locations_report>
```

Wait for completion. Per-row failures inside the agent are recorded in `code-changes.md` as `Status: failed: <reason>` and **do not** abort the orchestrator. Only an agent-level hard-fail (the agent prints `ERROR:`) is terminal — surface its line and skip to Step 8.

### Step 7 — Phase 3: review (opt-in)

If `RUN_REVIEW == false`, skip to Step 8.

Otherwise, spawn `@application-spec:code-review-writer` with the same prompt:

```
$DIAGRAM
<locations_report>
```

The reviewer reads `code-brief.md` + `code-changes.md` + on-disk source. If it hard-fails, surface its `ERROR:` line; proceed to Step 8.

### Step 8 — Summary

Print one summary block:

```
/application-spec:temp-update-code complete.

Layer       | Briefed | Edits | Failures | Risky | Reviewed | Verdict
------------|---------|-------|----------|-------|----------|---------------
application | <n>     | <n>   | <n>      | <n>   | yes/no   | clean/issues/—

Artifacts:
- <dir>/<stem>.application/code-brief.md   (Phase 1)
- <dir>/<stem>.application/code-changes.md (Phase 2)
- <dir>/<stem>.application/code-review.md  (Phase 3, only when --review)
```

Source the row counts from each on-disk artifact:

- `Briefed` — total rows in `code-brief.md`.
- `Edits` — rows in `code-changes.md` with `Status: applied`.
- `Failures` — rows with `Status: failed`.
- `Risky` — rows in `code-brief.md` with `Risk: risky`.
- `Reviewed` — `yes` if `code-review.md` exists (only when `--review` was passed and Phase 3 ran), else `no`.
- `Verdict` — `clean` / `issues` from `code-review.md`'s top-level verdict, or `—` when not reviewed.

## Failure semantics

- Every step that aborts the orchestrator emits exactly one `ERROR:` line and stops at that point. The summary block (Step 8) still prints, reflecting whatever artifacts exist on disk.
- Per-row failures inside the Phase 2 agent are recorded with `Status: failed: <reason>` in `code-changes.md` and do **not** abort the orchestrator. Only an agent-level hard-fail does.
- Each phase is idempotent on stable inputs. Re-running `/application-spec:temp-update-code` re-derives the brief (writer overwrites), re-applies the edits (writer overwrites), and (when `--review`) re-derives the review report.
- A no-op early exit (Step 2) is a success — exit cleanly, no agents spawned.

## What this skill deliberately does not do

- It does not touch domain, persistence, rest-api, or messaging layers, even if their `updates.md` siblings exist. Use `/update-code` for cross-layer orchestration.
- It does not edit any source file. All edits go through `@application-spec:code-change-writer`.
- It does not read any spec sibling or the diagram itself. All such reads happen inside the spawned agents.
- It does not auto-run Phase 3. Review is opt-in via `--review`.
- It does not run tests, format code, or regenerate `__init__.py` files end-to-end — those are change-writer concerns.
- It does not handle aggregate-root removals, stereotype changes, or repository lifecycle gates — `/application-spec:update-specs` (or `/application-spec:temp-update-specs`) surfaces those as `WARNING:` lines on the relevant axis before this skill is ever reached.
- It does not detect hand-edited source on disk. Operators with hand-tuned application service methods, service implementations, or exception classes must reconcile manually after Phase 2.
