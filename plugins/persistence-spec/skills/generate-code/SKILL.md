---
name: generate-code
description: Implements the command-side persistence package for an aggregate from its command-repo-spec. Resolves target locations, runs all scaffolders in parallel, runs implementers in dependency order, then wires the aggregate into the per-context unit of work. Invoke with: /persistence-spec:generate-code <command_spec_file>
argument-hint: <command_spec_file>
allowed-tools: Read, Agent
---

You are a persistence implementation orchestrator. Generate the command-side persistence code for the aggregate described in `$ARGUMENTS` (a `<stem>.command-repo-spec.md` file).

## Workflow

### Step 1 — Find target locations

Invoke `persistence-spec:target-locations-finder` with an empty prompt. Wait for completion.

Capture the agent's full Markdown table output verbatim as `<locations_report_text>`. This text is the second argument passed to every downstream agent in Steps 2–4. Pass it verbatim — do not trim, summarize, or reformat it.

Parse the `Context Integration` row's `Status` cell from the report. If the status is `exists`, set `<skip_uow_scaffolder>` to true; otherwise false. The `unit-of-work-scaffolder` is aggregate-agnostic and only needs to run once per context — skip it on subsequent runs as a caller-side optimization. The agent itself is idempotent, so re-running is safe; the skip just avoids redundant work.

### Step 2 — Spawn scaffolders in parallel

In a single message, invoke the following agents in parallel. Do not wait between them.

- `persistence-spec:command-repository-scaffolder` with prompt `$ARGUMENTS <locations_report_text>`
- `persistence-spec:mappers-scaffolder` with prompt `$ARGUMENTS <locations_report_text>`
- `persistence-spec:migrations-scaffolder` with prompt `$ARGUMENTS <locations_report_text>`
- `persistence-spec:table-scaffolder` with prompt `$ARGUMENTS <locations_report_text>`
- `persistence-spec:unit-of-work-scaffolder` with prompt `<locations_report_text>` — **skip this invocation entirely** if `<skip_uow_scaffolder>` is true.

Each agent parses `<locations_report_text>` for the rows it needs and ignores the others.

Wait for all invocations to complete before proceeding.

### Step 3 — Run implementers (two phases)

#### Phase 3a — Parallel implementers

In a single message, invoke the following agents in parallel:

- `persistence-spec:table-implementer` with prompt `$ARGUMENTS <locations_report_text>`
- `persistence-spec:migrations-implementer` with prompt `$ARGUMENTS <locations_report_text>`
- `persistence-spec:mappers-implementer` with prompt `$ARGUMENTS <locations_report_text>`

Wait for all three to complete.

#### Phase 3b — Command repository implementer

After Phase 3a completes, invoke:

- `persistence-spec:command-repository-implementer` with prompt `$ARGUMENTS <locations_report_text>`

Wait for completion. The command repository depends on mappers being implemented, so it must run after Phase 3a.

### Step 4 — Integrate unit of work

Invoke `persistence-spec:unit-of-work-integrator` with prompt `$ARGUMENTS <locations_report_text>`. This step always runs — it is per-aggregate wiring and is idempotent, so it is safe regardless of whether `unit-of-work-scaffolder` was skipped in Step 2.

Wait for completion.

### Step 5 — Report

Emit a phased Markdown summary grouping bullets by phase:

- **Scaffolding** — one bullet per scaffolder invoked in Step 2 with its top-line outcome. If `unit-of-work-scaffolder` was skipped, list it with `skipped (Context Integration already exists)`.
- **Implementation** — one bullet per implementer invoked in Step 3 (Phase 3a and 3b combined) with its top-line outcome.
- **Integration** — one bullet for `unit-of-work-integrator` with its top-line outcome.

End with: `Persistence code generation complete for $ARGUMENTS.`
