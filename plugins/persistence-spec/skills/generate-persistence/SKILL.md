---
name: generate-persistence
description: Orchestrates end-to-end persistence generation for an aggregate diagram by spawning the persistence-spec:specs-generator and then persistence-spec:code-generator agents. Invoke with: /persistence-spec:generate-persistence <domain_diagram>
argument-hint: <domain_diagram>
allowed-tools: Read, Agent
---

You are a persistence end-to-end orchestrator. Generate the persistence spec **and** the persistence code for the aggregate diagram in `$ARGUMENTS` by chaining two orchestrator agents sequentially. Each agent runs the heavy fan-out in its own isolated context and returns only a one-line report — this umbrella stays lean.

## This is a TWO-PHASE skill

This skill is **not complete** until both phases finish:

1. **Phase 1** — `persistence-spec:specs-generator` agent (writes `command-repo-spec.md`)
2. **Phase 2** — `persistence-spec:code-generator` agent (implements tables, mappers, repositories, integrations, and tests)

Phase 1 ends with its own confirmation line such as `Persistence spec generation complete for ...`. **That message refers to Phase 1 only.** It is not the end of this skill — you MUST continue to Phase 2 immediately. The single most common failure mode of this skill is stopping after Phase 1; do not do that.

## Inputs

- `$ARGUMENTS` — the path to the aggregate's Mermaid class diagram (`<dir>/<stem>.md`).

Both spawned agents derive the command-side spec sibling at `<dir>/<stem>.persistence/command-repo-spec.md` internally per `spec-core:naming-conventions`. This umbrella only forwards the domain diagram path.

## Workflow

Spawn each agent in its own message (via the `Agent` tool) and wait for it to complete before spawning the next. Do not collapse them into a single message.

### Step 1 of 2 — Generate the persistence spec

Spawn the `persistence-spec:specs-generator` agent with prompt `$ARGUMENTS`.

Failure handling: if the agent reports a failure, abort the workflow and emit an `ERROR:` line naming the failure. **Only** in that case do you stop before Step 2.

Success handling: if the agent returns its normal "Persistence spec generation complete" confirmation (or any non-error completion), **proceed immediately to Step 2 of 2 in your very next message.** Do not summarize, do not pause, do not ask for confirmation — Phase 2 is mandatory and the user has already authorized it by invoking this umbrella.

### Step 2 of 2 — Generate the persistence code

Spawn the `persistence-spec:code-generator` agent with prompt `$ARGUMENTS`.

If the agent reports a failure, abort and emit an `ERROR:` line.

### Step 3 — Report

Do not emit an additional summary. Each spawned agent prints its own report.
