---
name: generate-specs
description: Orchestrates application spec generation (commands + queries dependencies, method specifications, and application exceptions) for an aggregate by running four writer agents in parallel, an exceptions enricher, then per-side mergers that consolidate the fragments into final `<stem>.specs.md` files. Invoke with: /application-spec:generate-specs <commands_diagram> <queries_diagram> <domain_diagram>
argument-hint: <commands_diagram> <queries_diagram> <domain_diagram>
allowed-tools: Read, Agent
---

You are an application spec generation orchestrator. Generate the commands- and queries-side application service specs for the aggregate described by `$ARGUMENTS[0]` (commands diagram), `$ARGUMENTS[1]` (queries diagram), and `$ARGUMENTS[2]` (domain diagram) by running four writer agents in parallel, then enriching the exceptions sibling files.

## Sibling file convention

Each writer agent emits its outputs as siblings of its primary diagram file. Given a diagram at `<dir>/<stem>.md`, agents derive `<stem>` by stripping the `.md` suffix.

| File | Written by | Content |
|---|---|---|
| `<commands_stem>.deps.md` | `commands-deps-writer` | Commands service Dependencies fragment (consumed by merger) |
| `<commands_stem>.methods.md` | `commands-methods-writer` | Commands service Method Specifications fragment (consumed by merger) |
| `<commands_stem>.exceptions.md` | `commands-methods-writer` (stub) → `application-exceptions-specifier` (enriched) | Application exceptions raised by commands methods (consumed by merger) |
| `<commands_stem>.specs.md` | `specs-merger` | Final commands spec (deps + methods + exceptions merged) |
| `<queries_stem>.deps.md` | `queries-deps-writer` | Queries service Dependencies fragment (consumed by merger) |
| `<queries_stem>.methods.md` | `queries-methods-writer` | Queries service Method Specifications fragment (consumed by merger) |
| `<queries_stem>.exceptions.md` | `queries-methods-writer` (stub) → `application-exceptions-specifier` (enriched) | Application exceptions raised by queries methods (consumed by merger) |
| `<queries_stem>.specs.md` | `specs-merger` | Final queries spec (deps + methods + exceptions merged) |
| `<domain_stem>.services.md` | `services-finder` | Reconciled list of services the application layer must implement |

The merger deletes the three fragment files (`.deps.md`, `.methods.md`, `.exceptions.md`) on each side after writing the consolidated `.specs.md`. This orchestrator does not modify any diagram file and does not update any Artifacts index — agents own their own outputs.

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

### Step 3 — Merge fragments per side in parallel

After the exceptions specifier returns, spawn two `application-spec:specs-merger` agents in parallel (single message, two `Agent` calls):

- `application-spec:specs-merger` with prompt `$ARGUMENTS[0]`.
- `application-spec:specs-merger` with prompt `$ARGUMENTS[1]`.

Each merger consolidates its side's `.deps.md`, `.methods.md`, and `.exceptions.md` siblings into `<stem>.specs.md` and deletes the consumed fragments. Step 3 must wait for Step 2 because the merger trusts whatever is on disk and copies the exceptions body verbatim.

### Step 4 — Enumerate services

After both mergers return, spawn `application-spec:services-finder` with prompt `$ARGUMENTS[2] $ARGUMENTS[0] $ARGUMENTS[1]`. It reads the freshly merged `.specs.md` siblings on both sides plus the domain diagram and writes `<domain_stem>.services.md` next to the domain diagram. Step 4 must wait for Step 3 because the finder reads the consolidated specs.

### Step 5 — Report

After the services finder returns, confirm with one sentence: "Application spec generation complete for `$ARGUMENTS[0]` and `$ARGUMENTS[1]`."
