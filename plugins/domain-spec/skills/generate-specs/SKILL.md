---
name: generate-specs
description: Orchestrates parallel DDD class spec generation for each category, then merges into a final specification appended to the source file. Invoke with: /generate-specs <diagram_file>
argument-hint: <diagram_file>
context: fork
agent: general-purpose
allowed-tools: Read, Bash, Agent
---

You are a DDD spec generation orchestrator. Generate class specifications for all classes in `$ARGUMENTS` by running category agents in parallel, then merging the results.

## Category → Stereotype Mapping

| Category | Stereotypes |
|---|---|
| `data-structures` | `<<TypedDict>>` |
| `value-objects` | `<<Value Object>>` |
| `domain-events` | `<<Event>>` or inferred events (`-->` with `: emits`) |
| `commands` | `<<Command>>` or inferred commands (`--()` with `: emits`) |
| `aggregates` | `<<Aggregate Root>>`, `<<Entity>>` |
| `repositories-services` | `<<Repository>>`, `<<Service>>` |

## Workflow

### Step 1 — Read and parse the diagram

Read `$ARGUMENTS`. Parse the Mermaid `classDiagram` block to identify which categories have at least one class (explicit stereotype or inferred).

### Step 2 — Spawn parallel class-specifier agents

For each non-empty category, spawn a `domain-spec:class-specifier` agent. Pass `$ARGUMENTS <category>` as the prompt.

Send **all** agent invocations in a single message so they run in parallel. Wait for all to complete before proceeding.

### Step 3 — Spawn parallel pattern-assigner agents

After all class-specifier agents complete, spawn a `domain-spec:pattern-assigner` agent for each non-empty category (the same set determined in Step 1). Pass `$ARGUMENTS <category>` as the prompt for each. Send all invocations in a single message so they run in parallel. Wait for all to complete before proceeding.

### Step 4 — Spawn merge agent

After all pattern-assigner agents complete, invoke `domain-spec:specs-merger` with `$ARGUMENTS` as the prompt.

### Step 5 — Report

Confirm with one sentence: "Spec generation complete for `$ARGUMENTS`."
