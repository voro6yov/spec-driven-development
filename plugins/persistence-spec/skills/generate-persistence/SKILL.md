---
name: generate-persistence
description: Orchestrates end-to-end persistence generation for an aggregate diagram by running persistence-spec:generate-specs and then persistence-spec:generate-code. Invoke with: /persistence-spec:generate-persistence <diagram_file>
argument-hint: <diagram_file>
allowed-tools: Read, Skill
---

You are a persistence end-to-end orchestrator. Generate the persistence spec and then the persistence code for the aggregate diagram in `$ARGUMENTS` by chaining two skills sequentially.

## Inputs

- `$ARGUMENTS` — the path to the aggregate's Mermaid class diagram (`<dir>/<stem>.md`).

The command-side spec sibling file is `<dir>/<stem>.command-repo-spec.md` per the persistence-spec sibling-file convention. Derive it by stripping the `.md` suffix from `$ARGUMENTS` and appending `.command-repo-spec.md`.

## Workflow

Run each skill in its own message and wait for it to complete before invoking the next.

### Step 1 — Generate the persistence spec

Invoke skill `persistence-spec:generate-specs` with args `$ARGUMENTS`.

If the skill reports a failure, abort the workflow and emit an `ERROR:` line naming the failure. Do not proceed to Step 2.

### Step 2 — Generate the persistence code

Invoke skill `persistence-spec:generate-code` with args `<dir>/<stem>.command-repo-spec.md` (the derived sibling path).

If the skill reports a failure, abort and emit an `ERROR:` line.

### Step 3 — Report

Do not emit an additional summary. Each invoked skill prints its own report.
