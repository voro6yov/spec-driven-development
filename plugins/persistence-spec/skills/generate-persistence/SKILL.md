---
name: generate-persistence
description: Orchestrates end-to-end persistence generation for an aggregate diagram by running persistence-spec:generate-specs and then persistence-spec:generate-code. Invoke with: /persistence-spec:generate-persistence <domain_diagram>
argument-hint: <domain_diagram>
allowed-tools: Read, Skill
---

You are a persistence end-to-end orchestrator. Generate the persistence spec and then the persistence code for the aggregate diagram in `$ARGUMENTS` by chaining two skills sequentially.

## Inputs

- `$ARGUMENTS` — the path to the aggregate's Mermaid class diagram (`<dir>/<stem>.md`).

Both invoked skills derive the command-side spec sibling at `<dir>/<stem>.persistence/command-repo-spec.md` internally per `persistence-spec:naming-conventions`. This umbrella only forwards the domain diagram path.

## Workflow

Run each skill in its own message and wait for it to complete before invoking the next.

### Step 1 — Generate the persistence spec

Invoke skill `persistence-spec:generate-specs` with args `$ARGUMENTS`.

If the skill reports a failure, abort the workflow and emit an `ERROR:` line naming the failure. Do not proceed to Step 2.

### Step 2 — Generate the persistence code

Invoke skill `persistence-spec:generate-code` with args `$ARGUMENTS`.

If the skill reports a failure, abort and emit an `ERROR:` line.

### Step 3 — Report

Do not emit an additional summary. Each invoked skill prints its own report.
