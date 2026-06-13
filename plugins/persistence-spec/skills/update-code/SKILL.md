---
name: update-code
description: "Persistence-layer code updater — the gather → implement → review flow that propagates domain/persistence deltas into the command-side repository source, plus the query-side repository patches. Invoke with: /persistence-spec:update-code <domain_diagram> [--review]"
argument-hint: <domain_diagram> [--review]
allowed-tools: Read, Bash, Agent, AskUserQuestion
---

You are the **persistence-layer code updater**. After `/update-specs` has refreshed `<stem>.persistence/updates.md` (and `<stem>.domain/updates.md`), this skill propagates those deltas into the persistence package source via `gather → implement → review`, plus a query-side phase the command-side chain never sees.

This skill is **independently invocable** (`/persistence-spec:update-code <diagram> [--review]`) **and** is run as part of Wave 2 of `/spec-core:update-code` (in parallel with application). It reads settled domain source; it edits only the persistence package; it never invokes another plugin.

## Inputs & outputs

- Reads `<dir>/<stem>.persistence/updates.md` (preflight) and resolves locations via `@spec-core:target-locations-finder persistence`. The agents own every other read.
- Two implement tracks write durable artifacts:
  - **Command-side** — `@persistence-spec:code-change-writer` writes `code-changes.md` + source edits (driven by `code-brief.md`).
  - **Query-side** — `@persistence-spec:query-code-change-writer` writes `query-code-changes.md` + source edits, driven by `<stem>.domain/updates.md` directly. It runs **whenever this skill runs** (the persistence layer is active by definition), detects the query signal itself, and records a clean no-op when the domain report carries no `Query<X>Repository` delta. The command-side brief/change chain has no input signal for query-repo concrete methods or invariant clauses — that is this track's job.

## Workflow

### Step 0 — Parse arguments

`$ARGUMENTS` carries `<domain_diagram> [--review]`. Set `RUN_REVIEW=true` iff `--review` is present anywhere; strip it and bind `$DIAGRAM` to the remaining positional. If none remains:

```
ERROR: /persistence-spec:update-code requires <domain_diagram>. Usage: /persistence-spec:update-code <domain_diagram> [--review]
```

### Step 1 — Preflight

Derive `<stem>`/`<dir>` per `spec-core:naming-conventions`. Read `<dir>/<stem>.persistence/updates.md`. If missing, hard-fail:

```
ERROR: <stem>.persistence/updates.md not found. Run `/update-specs <domain_diagram>` before `/update-code`.
```

The query-side track also requires `<dir>/<stem>.domain/updates.md`; if it is missing, hard-fail with the same "run /update-specs first" guidance naming the domain report.

### Step 2 — Resolve target locations

Invoke `@spec-core:target-locations-finder persistence`. Capture its table verbatim as `<locations_report>`. On failure, abort with `ERROR:` repeating its message.

### Step 3 — Phase 1: gather (command-side)

Spawn `@persistence-spec:code-brief-writer` with prompt `$DIAGRAM` + `<locations_report>`. Wait. On hard-fail, abort with `ERROR:`. Probe `test -f <dir>/<stem>.persistence/code-brief.md` and bind `<command_changed>` to its presence (the brief-writer writes nothing on a command-side no-op).

### Step 4 — Risk-tag checkpoint

If `<command_changed>` is false, skip to Step 5. Otherwise count `Risk: risky` rows in `code-brief.md`. If zero, proceed. If non-zero, fire one `AskUserQuestion`:

- Question: `<risky_count> persistence artifact(s) tagged \`risky\` (e.g. destructive migrations, pattern flips). Proceed?`
- Header: `Risky edits`
- Options: 1. `Proceed (recommended)` — apply Phase 2. 2. `Abort` — leave the brief on disk and stop.

On `Abort`, print and exit cleanly (the query-side track does **not** run on an abort — a declined checkpoint stops the whole layer):

```
Aborted persistence at risk checkpoint. Brief preserved at <stem>.persistence/code-brief.md.
```

### Step 5 — Phase 2: implement (command-side)

If `<command_changed>`, spawn `@persistence-spec:code-change-writer` with the Phase-1 prompt shape. Wait. Per-artifact `Status: failed` rows do not abort; an agent-level hard-fail surfaces its `ERROR:` line (continue to Step 5.5 — the query track is independent).

### Step 5.5 — Phase 2.5: implement (query-side)

Always — whether or not the command side changed — spawn `@persistence-spec:query-code-change-writer` with prompt `$DIAGRAM` + `<locations_report>`, **after** Step 5 has settled (Step 5 may have touched the same `SqlAlchemyQuery<X>Repository` file; the query track must see that settled state before layering its surgical patches). It reads `<stem>.domain/updates.md`, applies structural method deltas then invariant-clause patches, and always writes `query-code-changes.md` (a clean no-op log when there is no query-repo delta). Per-delta failures are logged as `Status: failed`; only an agent-level hard-fail surfaces an `ERROR:` line.

### Step 6 — Phase 3: review (opt-in)

If `RUN_REVIEW` and `<command_changed>`, spawn `@persistence-spec:code-review-writer` with the Phase-1 prompt shape (it reviews the aggregate persistence file set, including the query repo). On hard-fail, surface its `ERROR:` line. (A query-only run with no command-side brief is not separately reviewed — the reviewer reads `code-brief.md`/`code-changes.md`, which a command-side no-op never produced.)

### Step 7 — Outcome line

Bind `<A_cmd>` = `Status: applied` rows in `code-changes.md` (0 if absent); `<A_qry>` = `Status: applied` rows in `query-code-changes.md`. **If `<command_changed>` is false AND `<A_qry> == 0`**, print and exit:

```
No persistence code updates required.
```

Otherwise print exactly one outcome line:

```
Updated persistence code: applied <A_cmd> command + <A_qry> query edit(s)<failed_clause><review_clause>.
```

`<failed_clause>` = `; <F> failed` summing failed rows across both logs when any exist; `<review_clause>` = `; reviewed: <clean|issues>` from `code-review.md` when `--review` ran and the command side was reviewed, else empty.

## Failure semantics

- An `ERROR:` aborts the step and stops; on-disk artifacts survive. A no-op exit (Step 7) and a risk-gate abort (Step 4) are clean exits — but `/spec-core:update-code` treats a persistence abort/ERROR as not affecting rest-api/messaging (nothing reads persistence source).
- The command-side and query-side tracks are independent: a command-side hard-fail still lets the query track run, and vice versa. Both may touch `SqlAlchemyQuery<X>Repository`; the Step 5-before-5.5 ordering plus the query track's per-method idempotence pre-check (`def <name>(` present → no-op) is the load-bearing safety against double-adding.
- Idempotent on stable inputs: re-running overwrites briefs/logs and pre-checks edit post-state.

## What this skill deliberately does not do

- It does not edit outside the persistence package, read another layer's specs, or invoke another plugin. Cross-layer sequencing is owned by `/spec-core:update-code`.
- It does not run migrations, run tests, or format code — those are change-writer concerns.
