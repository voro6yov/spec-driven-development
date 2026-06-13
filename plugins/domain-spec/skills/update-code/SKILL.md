---
name: update-code
description: "Domain-layer code updater — the gather → implement → review flow that propagates `<stem>.domain/updates.md` into the domain package source. Invoke with: /domain-spec:update-code <domain_diagram> [--review]"
argument-hint: <domain_diagram> [--review]
allowed-tools: Read, Bash, Agent, AskUserQuestion
---

You are the **domain-layer code updater**. After `/update-specs` has refreshed `<stem>.domain/updates.md`, this skill propagates that delta into the domain package source via the three-agent flow `gather → implement → review`. It is the execution analog of `/domain-spec:update-specs`, scoped to one layer.

This skill is **independently invocable** (`/domain-spec:update-code <diagram> [--review]` to update only the domain source) **and** is run as Wave 1 of the cross-layer `/spec-core:update-code` cascade. It edits only the domain package; it never touches another layer, and it never invokes another plugin.

## Inputs & outputs

- Reads `<dir>/<stem>.domain/updates.md` (preflight gates only). Resolves its target locations via `@spec-core:target-locations-finder domain <domain_diagram>`. Every other read happens inside the spawned agents.
- The agents write the durable artifacts: `code-brief.md` (Phase 1), `code-changes.md` + source edits (Phase 2), `code-review.md` (Phase 3). This skill writes nothing to disk — it emits only its risk-gate prompt and a final outcome line.

## Workflow

### Step 0 — Parse arguments

`$ARGUMENTS` carries `<domain_diagram> [--review]`. The diagram is the only non-flag positional; `--review` may appear in any position. Set `RUN_REVIEW=true` iff the token `--review` is present anywhere; strip it and bind `$DIAGRAM` to the remaining positional. If no positional remains, hard-fail:

```
ERROR: /domain-spec:update-code requires <domain_diagram>. Usage: /domain-spec:update-code <domain_diagram> [--review]
```

### Step 1 — Preflight

Derive `<stem>` by stripping `.md` from the basename of `$DIAGRAM`, and `<dir>` as its directory (per `spec-core:naming-conventions`). Read `<dir>/<stem>.domain/updates.md`. If missing, hard-fail:

```
ERROR: <stem>.domain/updates.md not found. Run `/update-specs <domain_diagram>` before `/update-code`.
```

If the report's Summary contains a `_warning: HEAD ...` line (degraded baseline), hard-fail:

```
ERROR: Degraded baseline in <stem>.domain/updates.md. Re-run `/update-specs` after fixing HEAD, or regenerate via `@domain-spec:code-generator <domain_diagram>`.
```

### Step 2 — Resolve target locations

Invoke `@spec-core:target-locations-finder domain $DIAGRAM`. Capture its full Markdown table verbatim as `<locations_report>`. If it reports a failure, abort with `ERROR:` repeating its message.

### Step 3 — Phase 1: gather

Spawn `@domain-spec:code-brief-writer` with prompt:

```
$DIAGRAM
<locations_report>
```

Wait for it to complete. If it hard-fails, abort with `ERROR:` repeating its message.

The brief-writer writes `<dir>/<stem>.domain/code-brief.md` **only when it gathered at least one artifact row**; on a no-op it writes nothing and emits a no-op payload. Probe `test -f <dir>/<stem>.domain/code-brief.md`. **If absent, this run is a no-op** — print and exit cleanly:

```
No domain code updates required.
```

### Step 4 — Risk-tag checkpoint

Count `Risk: risky` rows in `<dir>/<stem>.domain/code-brief.md` and bind `<risky_count>`. If `<risky_count> == 0`, proceed silently to Step 5.

Otherwise fire one `AskUserQuestion` to confirm before edits land (the recommended option must still be selected explicitly — there is no default-proceed when risky rows are present):

- Question: `<risky_count> domain artifact(s) tagged \`risky\`. Risky tags surface judgment calls Phase 1 wants verified before edits land (e.g. aggregate-root method edits, multi-pattern conflicts). Proceed?`
- Header: `Risky edits`
- Options: 1. `Proceed (recommended)` — apply Phase 2. 2. `Abort` — leave the brief on disk and stop.

On `Abort`, print and exit cleanly:

```
Aborted domain at risk checkpoint. Brief preserved at <stem>.domain/code-brief.md.
```

### Step 5 — Phase 2: implement

Spawn `@domain-spec:code-change-writer` with the same prompt shape as Phase 1 (`$DIAGRAM` + `<locations_report>`). Wait for completion. It reads `code-brief.md`, applies the edits, and writes `code-changes.md`. Per-artifact failures are recorded as `Status: failed: <reason>` and do **not** abort; only an agent-level hard-fail does — surface its `ERROR:` line and skip to Step 7.

### Step 6 — Phase 3: review (opt-in)

If `RUN_REVIEW == false`, skip to Step 7. Otherwise spawn `@domain-spec:code-review-writer` with the same prompt shape. It reads `code-brief.md` + `code-changes.md` + on-disk source and writes `code-review.md`. If it hard-fails, surface its `ERROR:` line and proceed to Step 7.

### Step 7 — Outcome line

Print exactly one outcome line, sourced from the on-disk artifacts:

```
Updated domain code: applied <A> edit(s)<failed_clause><review_clause>.
```

- `<A>` — rows in `code-changes.md` with `Status: applied`.
- `<failed_clause>` — `; <F> failed` when any `Status: failed` rows exist, else empty.
- `<review_clause>` — `; reviewed: <clean|issues>` from `code-review.md`'s top-level verdict when `--review` ran, else empty.

This line is what `/spec-core:update-code` classifies into the cascade topology (`updated` / `no-op` / `aborted` / `ERROR`). Do not print a multi-row table — the artifacts are the durable detail.

## Failure semantics

- Every step that aborts emits exactly one `ERROR:` line and stops. The brief / change / review artifacts that exist on disk at that point survive.
- A no-op early exit (Step 3) and a risk-gate abort (Step 4) are both clean exits, not errors — but `/spec-core:update-code` treats a risk-gate abort as "domain did not settle" and skips downstream waves (their change-writers read domain source).
- Each phase is idempotent on stable inputs: re-running re-derives the brief, re-applies the edits (writers overwrite; edits pre-check post-state), and (when `--review`) re-derives the review.

## What this skill deliberately does not do

- It does not edit any source outside the domain package, read any other layer's specs, or invoke another plugin's skill. Cross-layer sequencing is owned by `/spec-core:update-code`.
- It does not enter plan mode, run tests, or format code — those are change-writer concerns.
- It does not handle aggregate-root removals or stereotype changes — `/update-specs` hard-fails on those before this skill is reached.
