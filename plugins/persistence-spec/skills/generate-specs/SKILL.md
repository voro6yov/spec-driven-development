---
name: generate-specs
description: "Orchestrates persistence spec generation (command repository spec) for an aggregate diagram by running scaffolder, pattern-selector, migrations-writer, and schema-writer agents in sequence. Invoke with: /persistence-spec:generate-specs <domain_diagram>"
argument-hint: <domain_diagram>
allowed-tools: Read, Agent, Skill
---

You are a persistence spec generation orchestrator. Generate the command-side repository spec for the aggregate(s) in `$ARGUMENTS` by running agents strictly sequentially.

## Sibling-folder convention

Per `persistence-spec:naming-conventions`, given `<domain_diagram>` at `<dir>/<stem>.md`, the persistence-spec plugin owns the per-aggregate folder `<dir>/<stem>.persistence/` and writes its single artifact inside it:

| File | Written/enriched by | Content |
|---|---|---|
| `<dir>/<stem>.persistence/command-repo-spec.md` | `command-repo-spec-scaffolder` (scaffold + folder creation) → `command-repo-spec-pattern-selector` (Sections 1–2 except Migrations) → `command-repo-spec-migrations-writer` (§2 Migrations) → `command-repo-spec-schema-writer` (Section 3) | Command repository spec |

The scaffolder agent creates the per-plugin folder on first run and updates the diagram's `## Artifacts` section itself. This orchestrator does not modify the diagram file.

All agents derive `<stem>` by stripping the `.md` suffix from `<domain_diagram>` and locate the spec in `<dir>/<stem>.persistence/command-repo-spec.md`.

## Workflow

Run each agent in its own message and wait for it to complete before invoking the next. Pass `$ARGUMENTS` as the prompt to every agent.

### Step 1 — Command repo spec scaffolder

Invoke `persistence-spec:command-repo-spec-scaffolder`.

### Step 2 — Command repo spec pattern selector

Invoke `persistence-spec:command-repo-spec-pattern-selector`.

### Step 3 — Command repo spec migrations writer

Invoke `persistence-spec:command-repo-spec-migrations-writer`.

### Step 4 — Command repo spec schema writer

Invoke `persistence-spec:command-repo-spec-schema-writer`.

### Step 5 — Report

Confirm with one sentence: "Persistence spec generation complete for `$ARGUMENTS`."
