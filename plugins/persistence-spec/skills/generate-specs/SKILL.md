---
name: generate-specs
description: Orchestrates persistence spec generation (command repository spec) for an aggregate diagram by running scaffolder, pattern-selector, and schema-writer agents in sequence. Invoke with: /persistence-spec:generate-specs <diagram_file>
argument-hint: <diagram_file>
allowed-tools: Read, Agent
---

You are a persistence spec generation orchestrator. Generate the command-side repository spec for the aggregate(s) in `$ARGUMENTS` by running agents strictly sequentially.

## Sibling file convention

Given `<diagram_file>` at `<dir>/<stem>.md`, spec outputs are written to sibling files (not appended to the diagram):

| File | Written/enriched by | Content |
|---|---|---|
| `<stem>.command-repo-spec.md` | `command-repo-spec-scaffolder` (scaffold) → `command-repo-spec-pattern-selector` (Sections 1–2) → `command-repo-spec-schema-writer` (Section 3) | Command repository spec |

The scaffolder agent updates the diagram's `## Artifacts` section itself. This orchestrator does not modify the diagram file.

All agents derive `<stem>` by stripping the `.md` suffix from `<diagram_file>`.

## Workflow

Run each agent in its own message and wait for it to complete before invoking the next. Pass `$ARGUMENTS` as the prompt to every agent.

### Step 1 — Command repo spec scaffolder

Invoke `persistence-spec:command-repo-spec-scaffolder`.

### Step 2 — Command repo spec pattern selector

Invoke `persistence-spec:command-repo-spec-pattern-selector`.

### Step 3 — Command repo spec schema writer

Invoke `persistence-spec:command-repo-spec-schema-writer`.

### Step 4 — Report

Confirm with one sentence: "Persistence spec generation complete for `$ARGUMENTS`."
