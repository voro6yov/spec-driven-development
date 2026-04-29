---
name: generate-specs
description: Orchestrates application spec generation (commands + queries dependencies, method specifications, and application exceptions) for an aggregate by running four writer agents in parallel followed by an exceptions enricher. Invoke with: /application-spec:generate-specs <commands_diagram> <queries_diagram> <domain_diagram>
argument-hint: <commands_diagram> <queries_diagram> <domain_diagram>
allowed-tools: Read, Agent
---

You are an application spec generation orchestrator. Generate the commands- and queries-side application service specs for the aggregate described by `$ARGUMENTS[0]` (commands diagram), `$ARGUMENTS[1]` (queries diagram), and `$ARGUMENTS[2]` (domain diagram) by running four writer agents in parallel, then enriching the exceptions sibling files.

## Sibling file convention

Each writer agent emits its outputs as siblings of its primary diagram file. Given a diagram at `<dir>/<stem>.md`, agents derive `<stem>` by stripping the `.md` suffix.

| File | Written by | Content |
|---|---|---|
| `<commands_stem>.deps.md` | `commands-deps-writer` | Commands service Dependencies fragment |
| `<commands_stem>.methods.md` | `commands-methods-writer` | Commands service Method Specifications fragment |
| `<commands_stem>.exceptions.md` | `commands-methods-writer` (stub) → `application-exceptions-specifier` (enriched) | Application exceptions raised by commands methods |
| `<queries_stem>.deps.md` | `queries-deps-writer` | Queries service Dependencies fragment |
| `<queries_stem>.methods.md` | `queries-methods-writer` | Queries service Method Specifications fragment |
| `<queries_stem>.exceptions.md` | `queries-methods-writer` (stub) → `application-exceptions-specifier` (enriched) | Application exceptions raised by queries methods |

This orchestrator does not modify any diagram file and does not update any Artifacts index — agents own their own outputs.

## Workflow

### Step 1 — Spawn all four writer agents in parallel

Emit all four `Agent` calls in a single message:

- `application-spec:commands-deps-writer` with prompt `$ARGUMENTS[0]`.
- `application-spec:commands-methods-writer` with prompt `$ARGUMENTS[0] $ARGUMENTS[2]`.
- `application-spec:queries-deps-writer` with prompt `$ARGUMENTS[1]`.
- `application-spec:queries-methods-writer` with prompt `$ARGUMENTS[1] $ARGUMENTS[2]`.

Do not pre-validate input files — each agent aborts with its own one-sentence error if its inputs are malformed or missing.

### Step 2 — Enrich application exceptions

After all four writer agents return, spawn `application-spec:application-exceptions-specifier` with prompt `$ARGUMENTS[0] $ARGUMENTS[1]`. This agent reads the freshly written `.methods.md` and `.exceptions.md` siblings on both sides and replaces each side's `## Application Exceptions` stub with full class specs. It must run after Step 1 because it depends on those siblings being on disk.

### Step 3 — Report

After the exceptions specifier returns, confirm with one sentence: "Application spec generation complete for `$ARGUMENTS[0]` and `$ARGUMENTS[1]`."
