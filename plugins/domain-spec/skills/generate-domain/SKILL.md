---
name: generate-domain
description: Orchestrates end-to-end domain generation for an aggregate diagram by running domain-spec:generate-specs and then domain-spec:generate-code. Invoke with: /domain-spec:generate-domain <domain_diagram>
argument-hint: <domain_diagram>
allowed-tools: Read, Skill
---

You are a domain end-to-end orchestrator. Generate the domain spec **and** the domain code for the aggregate diagram in `$ARGUMENTS` by chaining two skills sequentially.

## This is a TWO-PHASE skill

This skill is **not complete** until both phases finish:

1. **Phase 1** — `domain-spec:generate-specs` (writes `<stem>.domain/specs.md`, `exceptions.md`, `test-plan.md`)
2. **Phase 2** — `domain-spec:generate-code` (scaffolds the domain package, implements classes, writes fixtures and unit tests)

Phase 1 ends with its own confirmation line such as `Spec generation complete for ...`. **That message refers to Phase 1 only.** It is not the end of this skill — you MUST continue to Phase 2 immediately. The single most common failure mode of this skill is stopping after Phase 1; do not do that.

## Inputs

- `$ARGUMENTS` — the path to the aggregate's Mermaid class diagram (`<dir>/<stem>.md`).

All artifacts produced by Phase 1 land in `<dir>/<stem>.domain/` per `domain-spec:naming-conventions`; Phase 2 reads them from there.

## Workflow

Run each skill in its own message and wait for it to complete before invoking the next. Do not collapse them into a single message.

### Step 1 of 2 — Generate the domain spec

Invoke skill `domain-spec:generate-specs` with args `$ARGUMENTS`.

Failure handling: if the skill reports a failure, abort the workflow and emit an `ERROR:` line naming the failure. **Only** in that case do you stop before Step 2.

Success handling: if the skill returns its normal "Spec generation complete" confirmation (or any non-error completion), **proceed immediately to Step 2 of 2 in your very next message.** Do not summarize, do not pause, do not ask for confirmation — Phase 2 is mandatory and the user has already authorized it by invoking this umbrella.

### Step 2 of 2 — Generate the domain code

Invoke skill `domain-spec:generate-code` with args `$ARGUMENTS`.

If the skill reports a failure, abort and emit an `ERROR:` line.

### Step 3 — Report

Do not emit an additional summary. Each invoked skill prints its own report.
