---
name: generate-application
description: Orchestrates end-to-end application generation for an aggregate diagram by spawning the application-spec:specs-generator and then application-spec:code-generator agents. Invoke with: /application-spec:generate-application <domain_diagram>
argument-hint: <domain_diagram>
allowed-tools: Read, Agent
---

You are an application end-to-end orchestrator. Generate the application spec **and** the application code for the aggregate diagram in `$ARGUMENTS` by chaining two orchestrator agents sequentially. Each agent runs the heavy fan-out in its own isolated context and returns only a one-line report — this umbrella stays lean.

## This is a TWO-PHASE skill

This skill is **not complete** until both phases finish:

1. **Phase 1** — `application-spec:specs-generator` agent (writes `commands.specs.md`, `queries.specs.md`, and `services.md`)
2. **Phase 2** — `application-spec:code-generator` agent (scaffolds the application/infrastructure packages, implements services, exceptions, settings, the commands and queries application services, and writes integration tests)

Phase 1 ends with its own confirmation line such as `Application spec generation complete for ...`. **That message refers to Phase 1 only.** It is not the end of this skill — you MUST continue to Phase 2 immediately. The single most common failure mode of this skill is stopping after Phase 1; do not do that.

## Inputs

- `$ARGUMENTS` — the path to the aggregate's Mermaid class diagram (`<dir>/<stem>.md`).

All artifacts produced by Phase 1 land in `<dir>/<stem>.application/` per `spec-core:naming-conventions`; Phase 2 reads them from there. Sibling diagrams (`<commands_diagram>`, `<queries_diagram>`) are derived internally by each spawned agent; this umbrella only forwards the domain diagram path.

## Workflow

Spawn each agent in its own message (via the `Agent` tool) and wait for it to complete before spawning the next. Do not collapse them into a single message.

### Step 1 of 2 — Generate the application spec

Spawn the `application-spec:specs-generator` agent with prompt `$ARGUMENTS`.

Failure handling: if the agent reports a failure, abort the workflow and emit an `ERROR:` line naming the failure. **Only** in that case do you stop before Step 2.

Success handling: if the agent returns its normal "Application spec generation complete" confirmation (or any non-error completion), **proceed immediately to Step 2 of 2 in your very next message.** Do not summarize, do not pause, do not ask for confirmation — Phase 2 is mandatory and the user has already authorized it by invoking this umbrella.

### Step 2 of 2 — Generate the application code

Spawn the `application-spec:code-generator` agent with prompt `$ARGUMENTS`.

If the agent reports a failure, abort and emit an `ERROR:` line.

### Step 3 — Report

Do not emit an additional summary. Each spawned agent prints its own report.
