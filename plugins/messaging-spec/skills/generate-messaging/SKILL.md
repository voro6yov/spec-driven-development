---
name: generate-messaging
description: Orchestrates end-to-end messaging generation for a single consumer by running messaging-spec:generate-specs and then messaging-spec:generate-code. Invoke with: /messaging-spec:generate-messaging <domain_diagram> <consumer_name>
argument-hint: <domain_diagram> <consumer_name>
allowed-tools: Read, Skill
---

You are a messaging end-to-end orchestrator. Generate the messaging consumer spec **and** the messaging code for the consumer named `$ARGUMENTS[1]` (`<consumer_name>`), scoped to the aggregate whose domain diagram is `$ARGUMENTS[0]`, by chaining two skills sequentially.

## This is a TWO-PHASE skill

This skill is **not complete** until both phases finish:

1. **Phase 1** — `messaging-spec:generate-specs` (writes `<stem>.messaging/<consumer_name>.md` with Tables 1, 2, and 3)
2. **Phase 2** — `messaging-spec:generate-code` (scaffolds the per-consumer messaging submodule, implements external events, handlers, and the dispatcher factory, wires the dispatcher into containers/entrypoint/__main__, prepares test fixtures, and writes handler integration tests)

Phase 1 ends with its own confirmation line such as `Messaging spec generation complete for ...`. **That message refers to Phase 1 only.** It is not the end of this skill — you MUST continue to Phase 2 immediately. The single most common failure mode of this skill is stopping after Phase 1; do not do that.

## Inputs

- `$ARGUMENTS[0]` — the path to the aggregate's Mermaid domain class diagram (`<dir>/<stem>.md`).
- `$ARGUMENTS[1]` — the kebab-case consumer name (matching `^[a-z][a-z0-9-]*$`), as it appears in the `%% Messaging - <consumer_name>` marker inside the commands diagram.

All artifacts produced by Phase 1 land in `<dir>/<stem>.messaging/<consumer_name>.md` per `spec-core:naming-conventions`; Phase 2 reads from there. The sibling commands diagram (`<commands_diagram>`) is derived internally by each invoked skill; this umbrella only forwards the domain diagram path and the consumer name.

## Workflow

Run each skill in its own message and wait for it to complete before invoking the next. Do not collapse them into a single message.

### Step 1 of 2 — Generate the messaging consumer spec

Invoke skill `messaging-spec:generate-specs` with args `$ARGUMENTS`.

Failure handling: if the skill reports a failure, abort the workflow and emit an `ERROR:` line naming the failure. **Only** in that case do you stop before Step 2.

Success handling: if the skill returns its normal "Messaging spec generation complete" confirmation (or any non-error completion), **proceed immediately to Step 2 of 2 in your very next message.** Do not summarize, do not pause, do not ask for confirmation — Phase 2 is mandatory and the user has already authorized it by invoking this umbrella.

### Step 2 of 2 — Generate the messaging code

Invoke skill `messaging-spec:generate-code` with args `$ARGUMENTS`.

If the skill reports a failure, abort and emit an `ERROR:` line.

### Step 3 — Report

Do not emit an additional summary. Each invoked skill prints its own report.
