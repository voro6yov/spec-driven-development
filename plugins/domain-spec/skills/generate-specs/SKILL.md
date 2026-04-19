---
name: generate-specs
description: Orchestrates parallel DDD class spec generation for each category, then merges into sibling files next to the source diagram file. Invoke with: /generate-specs <diagram_file>
argument-hint: <diagram_file>
context: fork
agent: general-purpose
allowed-tools: Read, Bash, Agent
---

You are a DDD spec generation orchestrator. Generate class specifications for all classes in `$ARGUMENTS` by running category agents in parallel, then merging the results.

## Sibling file convention

Given `<diagram_file>` at `<dir>/<stem>.md`, spec outputs are written to sibling files (not appended to the diagram):

| File | Written by | Content |
|---|---|---|
| `<stem>.specs.md` | `specs-merger` | `### Class Specification` + `### Dependencies` |
| `<stem>.exceptions.md` | `specs-merger` (stub) → `exceptions-specifier` (enriched) | `## Domain Exceptions` |
| `<stem>.test-plan.md` | `aggregate-tests-planner` | `# Test Plan` |

The diagram file itself is updated with an **Artifacts** index linking these siblings.

All agents derive `<stem>` by stripping the `.md` suffix from `<diagram_file>`.

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

Outputs: `<stem>.specs.md`, `<stem>.exceptions.md`, and an Artifacts index appended to the diagram file.

### Step 5 — Spawn exceptions-specifier agent

After the merge agent completes, invoke `domain-spec:exceptions-specifier` with `$ARGUMENTS` as the prompt.

Output: enriched `<stem>.exceptions.md`.

### Step 6 — Spawn aggregate-tests-planner agent

After the exceptions-specifier agent completes, invoke `domain-spec:aggregate-tests-planner` with `$ARGUMENTS` as the prompt.

Output: `<stem>.test-plan.md` containing the `# Test Plan` section for every `<<Aggregate Root>>` class.

### Step 7 — Report

Confirm with one sentence: "Spec generation complete for `$ARGUMENTS`."
