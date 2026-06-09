---
name: generate-specs
description: "Orchestrates application spec generation (commands + queries dependencies, method specifications, and application exceptions) for an aggregate. Invoke with: /application-spec:generate-specs <domain_diagram>"
argument-hint: <domain_diagram>
allowed-tools: Read, Bash, Agent, Skill
---

You are an application spec generation orchestrator. Generate the commands- and queries-side application service specs for the aggregate described by `$ARGUMENTS[0]` (the domain diagram) by running the writer agents in parallel, then enriching the exceptions sibling files. Sibling diagram paths (`<commands_diagram>`, `<queries_diagram>`) are derived internally per `spec-core:naming-conventions`; agents accept only `<domain_diagram>` (plus an `<op-name>` discriminator for ops services) and derive the rest themselves.

The commands and queries sides are always generated. The **ops track** is opt-in per aggregate: it is generated only when the aggregate declares at least one `<dir>/<stem>.ops.<op-name>.md` diagram. An aggregate with no such diagrams behaves exactly as today — no ops agents are spawned and no `ops.*` artifacts are written.

## Sibling file convention

Per `spec-core:naming-conventions`. From `$ARGUMENTS[0]` (the domain diagram) at `<dir>/<stem>.md`:

- `<dir>` = directory containing the diagrams
- `<stem>` = the canonical aggregate stem (domain filename with `.md` stripped)
- `<commands_diagram>` = `<dir>/<stem>.commands.md`
- `<queries_diagram>` = `<dir>/<stem>.queries.md`
- `<ops_diagrams>` = the result of globbing `<dir>/<stem>.ops.*.md` — zero or more hand-authored ops diagrams, one per service
- For each ops diagram, `<op-name>` = its basename split on the literal `.ops.` (both `<stem>` and `<op-name>` are dot-free kebab, so the split is unambiguous) — left part is `<stem>`, right part minus `.md` is `<op-name>`
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
| `<plugin_dir>/ops.<op-name>.deps.md` | `ops-deps-writer` | Ops service Dependencies fragment (consumed by merger) — one per `<op-name>` |
| `<plugin_dir>/ops.<op-name>.methods.md` | `ops-methods-writer` | Ops service Method Specifications fragment (consumed by merger) — one per `<op-name>` |
| `<plugin_dir>/ops.<op-name>.exceptions.md` | `ops-methods-writer` (stub) → `application-exceptions-specifier` (enriched) | Application exceptions raised by this ops service's methods (consumed by merger) — one per `<op-name>` |
| `<plugin_dir>/ops.<op-name>.specs.md` | `specs-merger` | Final ops spec (deps + methods + exceptions merged), top heading `# <X>` — one per `<op-name>` |
| `<plugin_dir>/services.md` | `services-finder` | Reconciled list of services the application layer must implement |

Every writer agent (the four fixed ones plus each `ops-deps-writer` / `ops-methods-writer` pair) `mkdir -p`s the per-plugin folder on first use, so no separate scaffolder step is required. The merger deletes the three fragment files (`.deps.md`, `.methods.md`, `.exceptions.md`) on each side after writing the consolidated `<side>.specs.md` — for the ops track the side is keyed by `<op-name>`, so each merger run cleans up only its own `ops.<op-name>.*` fragments. This orchestrator does not modify any diagram file and does not update any Artifacts index — agents own their own outputs.

## Workflow

### Step 1 — Discover ops services, then spawn all writer agents in parallel

First, glob `<dir>/<stem>.ops.*.md` to enumerate the aggregate's ops services. For each match, derive `<op-name>` by splitting the basename on the literal `.ops.` (left part is `<stem>`, right part minus `.md` is `<op-name>`). Let N be the number of matches (possibly zero).

Then emit **all** `Agent` calls in a single message — the four fixed writers plus 2×N ops writers (so the fan-out grows by 2×N). Pass only `$ARGUMENTS[0]` (the domain diagram) to the four fixed writers and `$ARGUMENTS[0] <op-name>` to each ops writer — the agents derive their own sibling diagrams via `spec-core:naming-conventions`:

- `application-spec:commands-deps-writer` with prompt `$ARGUMENTS[0]`.
- `application-spec:commands-methods-writer` with prompt `$ARGUMENTS[0]`.
- `application-spec:queries-deps-writer` with prompt `$ARGUMENTS[0]`.
- `application-spec:queries-methods-writer` with prompt `$ARGUMENTS[0]`.
- For each `<op-name>`: `application-spec:ops-deps-writer` with prompt `$ARGUMENTS[0] <op-name>`.
- For each `<op-name>`: `application-spec:ops-methods-writer` with prompt `$ARGUMENTS[0] <op-name>`.

When N is zero, this is exactly the four fixed writers — identical to the pre-ops behavior. Do not pre-validate input files — each agent aborts with its own one-sentence error if its inputs are malformed or missing.

### Step 2 — Enrich application exceptions

After all writer agents return, spawn `application-spec:application-exceptions-specifier` with prompt `$ARGUMENTS[0]`. This agent reads the freshly written `commands.methods.md` / `commands.exceptions.md` and `queries.methods.md` / `queries.exceptions.md` files inside `<plugin_dir>` and replaces each side's `## Application Exceptions` stub with full class specs. The same single run also self-discovers and enriches every `ops.<op-name>.exceptions.md` stub in `<plugin_dir>` (it globs the ops files itself — no extra invocation per `<op-name>` is needed). It must run after Step 1 because it depends on those siblings being on disk.

### Step 3 — Merge fragments per side in parallel

After the exceptions specifier returns, spawn the `application-spec:specs-merger` agents in parallel (single message, 2 + N `Agent` calls — the two fixed sides plus one per `<op-name>`):

- `application-spec:specs-merger` with prompt `$ARGUMENTS[0] commands`.
- `application-spec:specs-merger` with prompt `$ARGUMENTS[0] queries`.
- For each `<op-name>`: `application-spec:specs-merger` with prompt `$ARGUMENTS[0] ops <op-name>`.

Each commands/queries merger consolidates its side's `<side>.deps.md`, `<side>.methods.md`, and `<side>.exceptions.md` files inside `<plugin_dir>` into `<plugin_dir>/<side>.specs.md` and deletes the consumed fragments. Each ops merger does the same for its `ops.<op-name>.{deps,methods,exceptions}.md` fragments, writing `<plugin_dir>/ops.<op-name>.specs.md` with top heading `# <X>` (the verbatim braced class name, read from `<dir>/<stem>.ops.<op-name>.md`, not suffix-derived). When N is zero only the two fixed mergers run. Step 3 must wait for Step 2 because the merger trusts whatever is on disk and copies the exceptions body verbatim.

### Step 4 — Enumerate services

After all mergers return, spawn `application-spec:services-finder` with prompt `$ARGUMENTS[0]`. It reads the freshly merged `<plugin_dir>/commands.specs.md`, `<plugin_dir>/queries.specs.md`, and every `<plugin_dir>/ops.<op-name>.specs.md` plus the domain diagram and writes `<plugin_dir>/services.md`. Step 4 must wait for Step 3 because the finder reads the consolidated specs.

### Step 5 — Report

After the services finder returns, confirm with one sentence: "Application spec generation complete for `$ARGUMENTS[0]` (commands, queries, and N ops services)." — state the ops count N; when N is zero, drop the ops clause: "Application spec generation complete for `$ARGUMENTS[0]`."
