---
name: update-code
description: "Application-layer code updater — the gather → implement → review flow that propagates commands/queries and ops deltas into the application service source. Invoke with: /application-spec:update-code <domain_diagram> [--review]"
argument-hint: <domain_diagram> [--review]
allowed-tools: Read, Bash, Agent, AskUserQuestion
---

You are the **application-layer code updater**. After `/update-specs` has refreshed `<stem>.application/updates.md` and `<stem>.application/ops-updates.md`, this skill propagates those deltas into the application package source via `gather → implement → review`.

This skill is **independently invocable** (`/application-spec:update-code <diagram> [--review]`) **and** is run as part of Wave 2 of `/spec-core:update-code` (in parallel with persistence). It reads settled domain source; it edits only the application package; it never invokes another plugin.

The **two-axis rule** — the application layer is a no-op only when *both* the commands/queries axis (`updates.md`) and the ops axis (`ops-updates.md`) are empty — lives entirely inside `@application-spec:code-brief-writer`, which reads both reports. This skill does not parse either body; it only checks whether the brief-writer produced a brief.

## Inputs & outputs

- Reads `<dir>/<stem>.application/updates.md` (preflight). Resolves locations via `@spec-core:target-locations-finder application`. The agents own every other read, including the optional `ops-updates.md`.
- The agents write the durable artifacts: `code-brief.md` (Phase 1), `code-changes.md` + source edits (Phase 2), `code-review.md` (Phase 3).

## Workflow

### Step 0 — Parse arguments

`$ARGUMENTS` carries `<domain_diagram> [--review]`. Set `RUN_REVIEW=true` iff `--review` is present anywhere; strip it and bind `$DIAGRAM` to the remaining positional. If none remains:

```
ERROR: /application-spec:update-code requires <domain_diagram>. Usage: /application-spec:update-code <domain_diagram> [--review]
```

### Step 1 — Preflight

Derive `<stem>`/`<dir>` per `spec-core:naming-conventions`. Read `<dir>/<stem>.application/updates.md`. If missing, hard-fail:

```
ERROR: <stem>.application/updates.md not found. Run `/update-specs <domain_diagram>` before `/update-code`.
```

(The ops-axis report `<stem>.application/ops-updates.md` is optional — its presence/absence is the brief-writer's concern, not a preflight gate here.)

### Step 2 — Resolve target locations

Invoke `@spec-core:target-locations-finder application`. Capture its table verbatim as `<locations_report>`. On failure, abort with `ERROR:` repeating its message.

### Step 3 — Phase 1: gather

Spawn `@application-spec:code-brief-writer` with prompt `$DIAGRAM` + `<locations_report>`. Wait. On hard-fail, abort with `ERROR:`. The brief-writer writes `code-brief.md` only when at least one axis contributed an artifact row; on a two-axis no-op it writes nothing. Probe `test -f <dir>/<stem>.application/code-brief.md`. **If absent, this run is a no-op** — print and exit:

```
No application code updates required.
```

### Step 4 — Risk-tag checkpoint

Count `Risk: risky` rows in `code-brief.md`. If zero, proceed to Step 5. Otherwise fire one `AskUserQuestion`:

- Question: `<risky_count> application artifact(s) tagged \`risky\` (e.g. service-signature or DI conflicts). Proceed?`
- Header: `Risky edits`
- Options: 1. `Proceed (recommended)` — apply Phase 2. 2. `Abort` — leave the brief on disk and stop.

On `Abort`, print and exit cleanly:

```
Aborted application at risk checkpoint. Brief preserved at <stem>.application/code-brief.md.
```

### Step 5 — Phase 2: implement

Spawn `@application-spec:code-change-writer` with the Phase-1 prompt shape. Wait. Per-artifact `Status: failed` rows do not abort; an agent-level hard-fail surfaces its `ERROR:` line and skips to Step 7.

### Step 6 — Phase 3: review (opt-in)

If `RUN_REVIEW == false`, skip to Step 7. Otherwise spawn `@application-spec:code-review-writer` with the Phase-1 prompt shape. On hard-fail, surface its `ERROR:` line and proceed.

### Step 7 — Outcome line

Print exactly one outcome line, sourced from the on-disk artifacts:

```
Updated application code: applied <A> edit(s)<failed_clause><review_clause>.
```

- `<A>` — `Status: applied` rows in `code-changes.md`.
- `<failed_clause>` — `; <F> failed` when any `Status: failed` rows exist, else empty.
- `<review_clause>` — `; reviewed: <clean|issues>` from `code-review.md` when `--review` ran, else empty.

## Failure semantics

- An `ERROR:` aborts the step and stops; on-disk artifacts survive. A no-op exit (Step 3) and a risk-gate abort (Step 4) are clean exits — but `/spec-core:update-code` treats an application abort/ERROR as "application did not settle" and skips rest-api and messaging (their change-writers read application source).
- Idempotent on stable inputs: re-running overwrites the brief/log and pre-checks edit post-state.

## What this skill deliberately does not do

- It does not edit outside the application package, read another layer's specs, or invoke another plugin. Cross-layer sequencing is owned by `/spec-core:update-code`.
- It does not parse `updates.md`/`ops-updates.md` bodies — no-op and two-axis detection are delegated to the brief-writer.
