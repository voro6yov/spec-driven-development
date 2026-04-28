---
name: generate-domain
description: Orchestrates end-to-end domain generation for an aggregate diagram by running domain-spec:generate-specs and then domain-spec:generate-code. Invoke with: /domain-spec:generate-domain <diagram_file>
argument-hint: <diagram_file>
allowed-tools: Read, Skill
---

You are a domain end-to-end orchestrator. Generate the domain spec and then the domain code for the aggregate diagram in `$ARGUMENTS` by chaining two skills sequentially.

## Inputs

- `$ARGUMENTS` — the path to the aggregate's Mermaid class diagram (`<dir>/<stem>.md`).

## Workflow

Run each skill in its own message and wait for it to complete before invoking the next.

### Step 1 — Generate the domain spec

Invoke skill `domain-spec:generate-specs` with args `$ARGUMENTS`.

If the skill reports a failure, abort the workflow and emit an `ERROR:` line naming the failure. Do not proceed to Step 2.

### Step 2 — Generate the domain code

Invoke skill `domain-spec:generate-code` with args `$ARGUMENTS`.

If the skill reports a failure, abort and emit an `ERROR:` line.

### Step 3 — Report

Do not emit an additional summary. Each invoked skill prints its own report.
