---
name: generate-specs
description: "Orchestrates application spec generation (commands + queries dependencies, method specifications, and application exceptions) for an aggregate. Invoke with: /application-spec:generate-specs <domain_diagram>"
argument-hint: <domain_diagram>
allowed-tools: Read, Agent, Skill
---

You are an application spec generation orchestrator. Generate the commands- and queries-side application service specs for the aggregate described by `$ARGUMENTS[0]` (the domain diagram) by running four writer agents in parallel, then enriching the exceptions sibling files. Sibling diagram paths (`<commands_diagram>`, `<queries_diagram>`) are derived internally per `application-spec:naming-conventions`; agents accept only `<domain_diagram>` and derive the rest themselves.

## Sibling file convention

Per `application-spec:naming-conventions`. From `$ARGUMENTS[0]` (the domain diagram) at `<dir>/<stem>.md`:

- `<dir>` = directory containing the diagrams
- `<stem>` = the canonical aggregate stem (domain filename with `.md` stripped)
- `<commands_diagram>` = `<dir>/<stem>.commands.md`
- `<queries_diagram>` = `<dir>/<stem>.queries.md`
- `<plugin_dir>` = `<dir>/<stem>.application` — the per-plugin folder for application-spec

Every spec artifact lives inside `<plugin_dir>`:

| File | Written by | Content |
|---|---|---|
| `<plugin_dir>/commands.deps.md` | `commands-deps-writer` | Commands service Dependencies fragment (consumed by merger) |
| `<plugin_dir>/commands.methods.md` | `commands-methods-writer` | Commands service Method Specifications fragment (consumed by merger) |
| `<plugin_dir>/commands.exceptions.md` | `commands-methods-writer` (stub) → `application-exceptions-specifier` (enriched) | Application exceptions raised by commands methods (consumed by merger) |
| `<plugin_dir>/commands.specs.md` | `specs-merger` | Final commands spec (deps + methods + exceptions merged) |
| `<plugin_dir>/queries.deps.md` | `queries-deps-writer` | Queries service Dependencies fragment (consumed by merger) |
| `<plugin_dir>/queries.methods.md` | `queries-methods-writer` | Queries service Method Specifications fragment (consumed by merger) |
| `<plugin_dir>/queries.exceptions.md` | `queries-methods-writer` (stub) → `application-exceptions-specifier` (enriched) | Application exceptions raised by queries methods (consumed by merger) |
| `<plugin_dir>/queries.specs.md` | `specs-merger` | Final queries spec (deps + methods + exceptions merged) |
| `<plugin_dir>/services.md` | `services-finder` | Reconciled list of services the application layer must implement |

The four writer agents each `mkdir -p` the per-plugin folder on first use, so no separate scaffolder step is required. The merger deletes the three fragment files (`.deps.md`, `.methods.md`, `.exceptions.md`) on each side after writing the consolidated `<side>.specs.md`. This orchestrator does not modify any diagram file and does not update any Artifacts index — agents own their own outputs.

## Workflow

### Step 1 — Spawn all four writer agents in parallel

Emit all four `Agent` calls in a single message, passing only `$ARGUMENTS[0]` (the domain diagram) to each — the agents derive their own sibling diagrams via `application-spec:naming-conventions`:

- `application-spec:commands-deps-writer` with prompt `$ARGUMENTS[0]`.
- `application-spec:commands-methods-writer` with prompt `$ARGUMENTS[0]`.
- `application-spec:queries-deps-writer` with prompt `$ARGUMENTS[0]`.
- `application-spec:queries-methods-writer` with prompt `$ARGUMENTS[0]`.

Do not pre-validate input files — each agent aborts with its own one-sentence error if its inputs are malformed or missing.

### Step 2 — Enrich application exceptions

After all four writer agents return, spawn `application-spec:application-exceptions-specifier` with prompt `$ARGUMENTS[0]`. This agent reads the freshly written `commands.methods.md` / `commands.exceptions.md` and `queries.methods.md` / `queries.exceptions.md` files inside `<plugin_dir>` and replaces each side's `## Application Exceptions` stub with full class specs. It must run after Step 1 because it depends on those siblings being on disk.

### Step 3 — Merge fragments per side in parallel

After the exceptions specifier returns, spawn two `application-spec:specs-merger` agents in parallel (single message, two `Agent` calls):

- `application-spec:specs-merger` with prompt `$ARGUMENTS[0] commands`.
- `application-spec:specs-merger` with prompt `$ARGUMENTS[0] queries`.

Each merger consolidates its side's `<side>.deps.md`, `<side>.methods.md`, and `<side>.exceptions.md` files inside `<plugin_dir>` into `<plugin_dir>/<side>.specs.md` and deletes the consumed fragments. Step 3 must wait for Step 2 because the merger trusts whatever is on disk and copies the exceptions body verbatim.

### Step 4 — Enumerate services

After both mergers return, spawn `application-spec:services-finder` with prompt `$ARGUMENTS[0]`. It reads the freshly merged `<plugin_dir>/commands.specs.md` and `<plugin_dir>/queries.specs.md` plus the domain diagram and writes `<plugin_dir>/services.md`. Step 4 must wait for Step 3 because the finder reads the consolidated specs.

### Step 5 — Report

After the services finder returns, confirm with one sentence: "Application spec generation complete for `$ARGUMENTS[0]`."
