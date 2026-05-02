---
name: generate-specs
description: Orchestrates REST API resource spec generation by running the rest-api-spec agents in sequence to populate Tables 1–6 of the `<domain_stem>.rest-api.md` sibling file. Use when the user asks to generate a REST API spec from Mermaid command/query/domain diagrams. Invoke with: /generate-specs <commands_diagram> <queries_diagram> <domain_diagram>
argument-hint: <commands_diagram> <queries_diagram> <domain_diagram>
allowed-tools: Read, Agent
---

You are a REST API spec generation orchestrator. Populate the `<domain_stem>.rest-api.md` sibling file by running the rest-api-spec agents in sequence.

## Arguments

- `$ARGUMENTS[0]` — `<commands_diagram>`: Mermaid `<Resource>Commands` application-service class diagram.
- `$ARGUMENTS[1]` — `<queries_diagram>`: Mermaid `<Resource>Queries` application-service class diagram.
- `$ARGUMENTS[2]` — `<domain_diagram>`: Mermaid domain class diagram for the aggregate.

## Output

A single sibling file `<domain_stem>.rest-api.md`, located next to `<domain_diagram>`, where `<domain_stem>` is `<domain_diagram>` with the `.md` suffix stripped. Each step below populates a different set of tables in this file.

The artifact is structured as Table 1 (Resource Basics, including a `Surfaces` row) followed by one `## Surface: <name>` H2 section per surface, each containing Tables 2–6 scoped to that surface. Surfaces are auto-derived from `%% <name>` markers inside the commands and queries class bodies — see the `rest-api-spec:surface-markers` skill. Diagrams without markers default to a single `v1` surface, so existing single-surface diagrams keep working unchanged.

## Workflow

Run agents one at a time using the Agent tool. Wait for each to complete before invoking the next.

### Step 1 — Initialize the resource spec (Table 1)

Use the Agent tool to invoke `rest-api-spec:resource-spec-initializer` with `$ARGUMENTS[2]` as the prompt.

Populates: Table 1 (Resource Basics).

### Step 2 — Write endpoint tables (Tables 2 & 3)

Use the Agent tool to invoke `rest-api-spec:endpoint-tables-writer` with `$ARGUMENTS[0] $ARGUMENTS[1] $ARGUMENTS[2]` as the prompt.

Populates: Tables 2 (Query Endpoints) and 3 (Command Endpoints).

### Step 3 — Write response fields (Table 4)

Use the Agent tool to invoke `rest-api-spec:response-fields-writer` with `$ARGUMENTS[0] $ARGUMENTS[1] $ARGUMENTS[2]` as the prompt.

Populates: Table 4 (Response Fields).

### Step 4 — Write request fields (Table 5)

Use the Agent tool to invoke `rest-api-spec:request-fields-writer` with `$ARGUMENTS[0] $ARGUMENTS[1] $ARGUMENTS[2]` as the prompt.

Populates: Table 5 (Request Fields).

### Step 5 — Write parameter mapping (Table 6)

Use the Agent tool to invoke `rest-api-spec:parameter-mapping-writer` with `$ARGUMENTS[0] $ARGUMENTS[1] $ARGUMENTS[2]` as the prompt.

Populates: Table 6 (Parameter Mapping).

### Step 6 — Report

Confirm with one sentence: "REST API spec generation complete for `$ARGUMENTS[2]`."
