---
name: generate-persistence
description: Orchestrates end-to-end persistence generation for an aggregate diagram by running persistence-spec:generate-specs and then persistence-spec:generate-code. Invoke with: /persistence-spec:generate-persistence <domain_diagram>
argument-hint: <domain_diagram>
allowed-tools: Read, Skill
---

You are a persistence end-to-end orchestrator. Generate the persistence spec **and** the persistence code for the aggregate diagram in `$ARGUMENTS` by chaining two skills sequentially.

## This is a TWO-PHASE skill

This skill is **not complete** until both phases finish:

1. **Phase 1** — `persistence-spec:generate-specs` (writes `command-repo-spec.md`)
2. **Phase 2** — `persistence-spec:generate-code` (implements tables, mappers, repositories, integrations, and tests)

Phase 1 ends with its own confirmation line such as `Persistence spec generation complete for ...`. **That message refers to Phase 1 only.** It is not the end of this skill — you MUST continue to Phase 2 immediately. The single most common failure mode of this skill is stopping after Phase 1; do not do that.

## Inputs

- `$ARGUMENTS` — the path to the aggregate's Mermaid class diagram (`<dir>/<stem>.md`).

Both invoked skills derive the command-side spec sibling at `<dir>/<stem>.persistence/command-repo-spec.md` internally per `spec-core:naming-conventions`. This umbrella only forwards the domain diagram path.

## Workflow

Run each skill in its own message and wait for it to complete before invoking the next. Do not collapse them into a single message.

### Step 1 of 2 — Generate the persistence spec

Invoke skill `persistence-spec:generate-specs` with args `$ARGUMENTS`.

Failure handling: if the skill reports a failure, abort the workflow and emit an `ERROR:` line naming the failure. **Only** in that case do you stop before Step 2.

Success handling: if the skill returns its normal "Persistence spec generation complete" confirmation (or any non-error completion), **proceed immediately to Step 2 of 2 in your very next message.** Do not summarize, do not pause, do not ask for confirmation — Phase 2 is mandatory and the user has already authorized it by invoking this umbrella.

### Step 2 of 2 — Generate the persistence code

Invoke skill `persistence-spec:generate-code` with args `$ARGUMENTS`.

If the skill reports a failure, abort and emit an `ERROR:` line.

### Step 3 — Report

Do not emit an additional summary. Each invoked skill prints its own report.
