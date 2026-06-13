---
name: generate-specs
description: "Orchestrates messaging consumer spec generation for a single consumer. Invoke with: /messaging-spec:generate-specs <domain_diagram> <consumer_name>"
argument-hint: <domain_diagram> <consumer_name>
allowed-tools: Bash, Agent
---

You are a messaging consumer-spec generation orchestrator. Generate the consumer spec file for the consumer named `$ARGUMENTS[1]` (`<consumer_name>`), scoped to the aggregate whose domain diagram is `$ARGUMENTS[0]`. Sibling diagram and spec paths (`<commands_diagram>`, `<consumer_spec_file>`) are derived internally per `spec-core:naming-conventions`; downstream agents accept only `<commands_diagram>` (or `<consumer_name>`) plus non-derivable extras and derive the rest themselves.

This skill only writes the spec — it does not implement messaging code. Implementation is handled by `messaging-spec:generate-code` (or the umbrella `messaging-spec:generate-messaging`).

## Sibling file convention

Per `spec-core:naming-conventions`. From `$ARGUMENTS[0]` (the domain diagram) at `<dir>/<stem>.md` and `$ARGUMENTS[1]` (the consumer name, kebab-case matching `^[a-z][a-z0-9-]*$`):

- `<dir>` = directory containing the diagrams
- `<stem>` = the canonical aggregate stem (domain filename with `.md` stripped)
- `<commands_diagram>` = `<dir>/<stem>.commands.md` — the Mermaid commands class diagram (source of consumer markers and external event class declarations)
- `<consumer_spec_file>` = `<dir>/<stem>.messaging/<consumer_name>.md` — the per-consumer spec written by this skill

## Workflow

The pipeline is fully sequential — each step waits for its predecessor to complete before invoking the next agent. If any agent reports an error, abort the pipeline and propagate the failure in the Step 6 report; do not run subsequent steps.

### Step 1 — Derive sibling paths

From `$ARGUMENTS[0]` (the domain diagram) and `$ARGUMENTS[1]` (the consumer name), derive the two sibling paths used downstream:

- Let `<dir>` = `dirname($ARGUMENTS[0])`
- Let `<stem>` = `basename($ARGUMENTS[0])` with the trailing `.md` stripped
- Let `<consumer_name>` = `$ARGUMENTS[1]` (must satisfy `^[a-z][a-z0-9-]*$`; if it does not, abort with a one-sentence error)
- Let `<commands_diagram>` = `<dir>/<stem>.commands.md`
- Let `<consumer_spec_file>` = `<dir>/<stem>.messaging/<consumer_name>.md`

These bindings are used by Step 6's report and as a sanity reference; downstream agents derive the same values from their own input arguments.

### Step 2 — Find target locations

Invoke `spec-core:target-locations-finder` with the prompt `messaging`. Wait for completion.

Capture the agent's full Markdown table output verbatim as `<locations_report_text>`. This text is the locations argument passed to the initializer in Step 3. Pass it verbatim — do not trim, summarize, or reformat it.

### Step 3 — Initialize the consumer spec (Table 1)

Invoke `messaging-spec:consumer-spec-initializer` with prompt `<commands_diagram> <consumer_name> <locations_report_text>`. Wait for completion.

This validates the presence of a `%% Messaging - <consumer_name>` marker in the commands diagram, derives the service prefix from the project's Python package name, and creates `<consumer_spec_file>` initialized with Table 1 (Consumer Basics). Idempotent — leaves an existing Table 1 intact.

If the initializer aborts, propagate the failure and stop — do not proceed to Step 4.

### Step 4 — Fill Table 2 (Events to Consume)

Invoke `messaging-spec:event-tables-writer` with prompt `<commands_diagram> <consumer_name>`. Wait for completion.

This parses the `%% Messaging - <consumer_name>` block(s) inside the Mermaid commands class diagram **and every sibling ops diagram** (`<dir>/<stem>.ops.*.md`, auto-discovered by the writer) and writes one row per `<HandlerClass> <arrow> <Event> : handles (<Source>, <method>)` line into Table 2 of `<consumer_spec_file>` — a `<X>Commands.on_<event>` binding from the commands diagram or a free-form ops-service binding from an ops diagram. Replaces any existing Table 2 in place. Idempotent. An aggregate with zero ops diagrams behaves exactly as before.

If the writer aborts, propagate the failure and stop — do not proceed to Step 5.

### Step 5 — Fill Table 3 (Event Parameter Mapping)

Invoke `messaging-spec:event-fields-writer` with prompt `<commands_diagram> <consumer_name>`. Wait for completion.

This walks every row of the Table 2 written in Step 4, matches the bound handler's parameters (resolved from the commands diagram for a `<X>Commands.on_<event>` handler, or from the sibling ops diagram for a `<OpsClass>.<method>` handler) against the source event class's attributes, and emits one per-event sub-block into Table 3. Replaces any existing Table 3 in place. Idempotent.

If the writer aborts, propagate the failure and stop.

### Step 6 — Report

Emit a phased Markdown summary grouping bullets by phase:

- **Initialization** — one bullet for `consumer-spec-initializer` reporting its top-line outcome.
- **Tables** — one bullet each for `event-tables-writer` and `event-fields-writer` with their top-line outcomes.

End with: `Messaging spec generation complete for $ARGUMENTS[0] consumer $ARGUMENTS[1].`
