---
name: generate-specs
description: "Orchestrates REST API resource spec generation from a domain diagram. Use when the user asks to generate a REST API spec from a Mermaid domain class diagram. Invoke with: /generate-specs <domain_diagram>"
argument-hint: <domain_diagram>
allowed-tools: Read, Agent, Skill
---

You are a REST API spec generation orchestrator. Populate the `<output>` sibling file by running the rest-api-spec agents in sequence. Sibling diagram paths (`<commands_diagram>`, `<queries_diagram>`) are derived internally per `spec-core:naming-conventions`; agents accept only `<domain_diagram>` and derive the rest themselves.

## Arguments

- `$ARGUMENTS[0]` — `<domain_diagram>`: Mermaid domain class diagram for the aggregate at `<dir>/<stem>.md`.

## Sibling file convention

Per `spec-core:naming-conventions`. From `$ARGUMENTS[0]` (the domain diagram) at `<dir>/<stem>.md`:

- `<dir>` = directory containing the domain diagram
- `<stem>` = the canonical aggregate stem (domain filename with `.md` stripped)
- `<commands_diagram>` (derived inside agents) = `<dir>/<stem>.commands.md`
- `<queries_diagram>` (derived inside agents) = `<dir>/<stem>.queries.md`
- `<plugin_dir>` = `<dir>/<stem>.rest-api` — the per-plugin folder for rest-api-spec
- `<output>` = `<plugin_dir>/spec.md` — the resource input spec, populated incrementally by each step below

## Output

A single sibling file `<output>`, located inside the per-plugin folder next to `<domain_diagram>`. Each step below populates a different set of tables in this file.

The artifact is structured as Table 1 (Resource Basics, including a `Surfaces` row) followed by one `## Surface: <name>` H2 section per surface, each containing Tables 2, 3, 3o, and 4–6 scoped to that surface. Surfaces are auto-derived from `%% <name>` markers inside the commands, queries, **and any ops** class bodies — see the `rest-api-spec:surface-markers` skill. Diagrams without markers default to a single `v1` surface, so existing single-surface diagrams keep working unchanged.

**Ops endpoints.** When the aggregate declares one or more `<dir>/<stem>.ops.<op-name>.md` diagrams, each public ops method additionally becomes a `Table 3o` (Ops Endpoints) POST action endpoint, with its request/response/parameter detail filled into Tables 4–6 by the same writers. An aggregate with no ops diagrams produces no Table 3o rows and behaves exactly as today — the writers self-discover ops diagrams by glob, so the pipeline below is unchanged.

## Workflow

Run agents one at a time using the Agent tool. Wait for each to complete before invoking the next. Pass `$ARGUMENTS[0]` (the domain diagram) as the prompt to every agent — each agent derives its own sibling diagrams via `spec-core:naming-conventions`.

### Step 1 — Initialize the resource spec (Table 1 + Surface section headings)

Use the Agent tool to invoke `rest-api-spec:resource-spec-initializer` with `$ARGUMENTS[0]` as the prompt.

Populates: Table 1 (Resource Basics) and one empty `## Surface: <name>` H2 heading per discovered surface (auto-derived from the `%% <name>` markers in the commands and queries diagrams; defaults to a single `v1` surface when no markers are present).

### Step 2 — Write endpoint tables (Tables 2 & 3)

Use the Agent tool to invoke `rest-api-spec:endpoint-tables-writer` with `$ARGUMENTS[0]` as the prompt.

Populates: Tables 2 (Query Endpoints), 3 (Command Endpoints), and 3o (Ops Endpoints).

### Step 3 — Write response fields (Table 4)

Use the Agent tool to invoke `rest-api-spec:response-fields-writer` with `$ARGUMENTS[0]` as the prompt.

Populates: Table 4 (Response Fields).

### Step 4 — Write request fields (Table 5)

Use the Agent tool to invoke `rest-api-spec:request-fields-writer` with `$ARGUMENTS[0]` as the prompt.

Populates: Table 5 (Request Fields).

### Step 5 — Write parameter mapping (Table 6)

Use the Agent tool to invoke `rest-api-spec:parameter-mapping-writer` with `$ARGUMENTS[0]` as the prompt.

Populates: Table 6 (Parameter Mapping).

### Step 6 — Report

Confirm with one sentence: "REST API spec generation complete for `$ARGUMENTS[0]`."
