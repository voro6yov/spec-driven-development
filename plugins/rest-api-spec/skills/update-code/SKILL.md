---
name: update-code
description: "REST-API-layer code updater — the gather → implement → review flow that propagates resource deltas into the API endpoint/serializer source. Invoke with: /rest-api-spec:update-code <domain_diagram> [--review]"
argument-hint: <domain_diagram> [--review]
allowed-tools: Read, Bash, Agent, AskUserQuestion
---

You are the **rest-api-layer code updater**. After `/update-specs` has refreshed `<stem>.rest-api/updates.md`, this skill propagates that delta into the REST API package source via `gather → implement → review`.

This skill is **independently invocable** (`/rest-api-spec:update-code <diagram> [--review]`) **and** is run as part of Wave 3 of `/spec-core:update-code` (in parallel with messaging, after application). It reads settled application source; it edits only the API package; it never invokes another plugin.

## Inputs & outputs

- Reads `<dir>/<stem>.rest-api/updates.md` (preflight). Resolves locations via `@spec-core:target-locations-finder rest-api`. The agents own every other read.
- The agents write the durable artifacts: `code-brief.md` (Phase 1), `code-changes.md` + source edits (Phase 2), `code-review.md` (Phase 3).

## Workflow

### Step 0 — Parse arguments

`$ARGUMENTS` carries `<domain_diagram> [--review]`. Set `RUN_REVIEW=true` iff `--review` is present anywhere; strip it and bind `$DIAGRAM` to the remaining positional. If none remains:

```
ERROR: /rest-api-spec:update-code requires <domain_diagram>. Usage: /rest-api-spec:update-code <domain_diagram> [--review]
```

### Step 1 — Preflight

Derive `<stem>`/`<dir>` per `spec-core:naming-conventions`. Read `<dir>/<stem>.rest-api/updates.md`. If missing, hard-fail:

```
ERROR: <stem>.rest-api/updates.md not found. Run `/update-specs <domain_diagram>` before `/update-code`.
```

### Step 2 — Resolve target locations

Invoke `@spec-core:target-locations-finder rest-api`. Capture its table verbatim as `<locations_report>`. On failure, abort with `ERROR:` repeating its message.

### Step 3 — Phase 1: gather

Spawn `@rest-api-spec:code-brief-writer` with prompt `$DIAGRAM` + `<locations_report>`. Wait. On hard-fail, abort with `ERROR:`. The brief-writer writes `code-brief.md` only when it gathered at least one artifact row. Probe `test -f <dir>/<stem>.rest-api/code-brief.md`. **If absent, this run is a no-op** — print and exit:

```
No rest-api code updates required.
```

### Step 4 — Risk-tag checkpoint

Count `Risk: risky` rows in `code-brief.md`. If zero, proceed to Step 5. Otherwise fire one `AskUserQuestion`:

- Question: `<risky_count> rest-api artifact(s) tagged \`risky\` (e.g. surface cascades, spec/report drift). Proceed?`
- Header: `Risky edits`
- Options: 1. `Proceed (recommended)` — apply Phase 2. 2. `Abort` — leave the brief on disk and stop.

On `Abort`, print and exit cleanly:

```
Aborted rest-api at risk checkpoint. Brief preserved at <stem>.rest-api/code-brief.md.
```

### Step 5 — Phase 2: implement

Spawn `@rest-api-spec:code-change-writer` with the Phase-1 prompt shape. Wait. Per-artifact `Status: failed` rows do not abort; an agent-level hard-fail surfaces its `ERROR:` line and skips to Step 7.

### Step 6 — Phase 3: review (opt-in)

If `RUN_REVIEW == false`, skip to Step 7. Otherwise spawn `@rest-api-spec:code-review-writer` with the Phase-1 prompt shape. On hard-fail, surface its `ERROR:` line and proceed.

### Step 7 — Outcome line

Print exactly one outcome line, sourced from the on-disk artifacts:

```
Updated rest-api code: applied <A> edit(s)<failed_clause><review_clause>.
```

- `<A>` — `Status: applied` rows in `code-changes.md`.
- `<failed_clause>` — `; <F> failed` when any `Status: failed` rows exist, else empty.
- `<review_clause>` — `; reviewed: <clean|issues>` from `code-review.md` when `--review` ran, else empty.

## Failure semantics

- An `ERROR:` aborts the step and stops; on-disk artifacts survive. A no-op exit (Step 3) and a risk-gate abort (Step 4) are clean exits. rest-api is a Wave-3 leaf — nothing downstream reads its source, so its outcome never gates another layer.
- Idempotent on stable inputs: re-running overwrites the brief/log and pre-checks edit post-state.

## What this skill deliberately does not do

- It does not edit outside the API package, read another layer's specs, or invoke another plugin. Cross-layer sequencing is owned by `/spec-core:update-code`.
