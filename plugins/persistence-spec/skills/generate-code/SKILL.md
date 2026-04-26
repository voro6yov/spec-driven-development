---
name: generate-code
description: Implements the command-side persistence package for an aggregate from its command-repo-spec. Resolves target locations in the current repo, then runs the per-aggregate and per-context scaffolders in parallel. Invoke with: /persistence-spec:generate-code <command_spec_file>
argument-hint: <command_spec_file>
allowed-tools: Read, Agent
---

You are a persistence implementation orchestrator. Scaffold the command-side persistence code for the aggregate described in `$ARGUMENTS` (a `<stem>.command-repo-spec.md` file).

## Workflow

### Step 1 — Find target locations

Invoke `persistence-spec:target-locations-finder` with an empty prompt. Wait for completion.

Capture the agent's full Markdown table output verbatim as `<locations_report_text>`. This text is the second argument to the scaffolders in Step 2.

Parse the `Context Integration` row's `Status` cell from the report. If the status is `exists`, set `<skip_uow>` to true; otherwise false. The `unit-of-work-scaffolder` is aggregate-agnostic and only needs to run once per context — skip it on subsequent runs as a caller-side optimization. The agent itself is idempotent, so re-running is safe; the skip just avoids redundant work.

### Step 2 — Spawn scaffolders in parallel

In a single message, invoke the following agents in parallel. Do not wait between them.

- `persistence-spec:command-repo-files-scaffolder` with prompt `$ARGUMENTS <locations_report_text>`
- `persistence-spec:migrations-scaffolder` with prompt `$ARGUMENTS <locations_report_text>`
- `persistence-spec:unit-of-work-scaffolder` with prompt `<locations_report_text>` — **skip this invocation entirely** if `<skip_uow>` is true.

Each scaffolder parses `<locations_report_text>` for the rows it needs and ignores the others. Pass the report verbatim — do not trim, summarize, or reformat it.

Wait for all invocations to complete.

### Step 3 — Report

Emit a concise Markdown summary that lists each scaffolder invoked and its top-line outcome (one bullet per agent). If `unit-of-work-scaffolder` was skipped, note `skipped (Context Integration already exists)`.

End with: `Persistence code scaffolding complete for $ARGUMENTS.`
