---
name: generate-code
description: Implements the messaging consumer package for a single consumer from its `<dir>/<stem>.messaging/<consumer_name>.md` spec file and the derived `<dir>/<stem>.commands.md` Mermaid commands diagram. Resolves target locations once, scaffolds the per-consumer submodule, fills external event dataclasses + handler functions + the dispatcher factory, wires the dispatcher into containers/entrypoint/__main__, and finally prepares the test fixtures and writes the handler integration tests. Invoke with: /messaging-spec:generate-code <domain_diagram> <consumer_name>
argument-hint: <domain_diagram> <consumer_name>
allowed-tools: Bash, Agent
---

You are a messaging implementation orchestrator. Implement the messaging code AND its handler integration tests for the consumer named `$ARGUMENTS[1]` (`<consumer_name>`), scoped to the aggregate whose domain diagram is `$ARGUMENTS[0]`. Sibling diagram and spec paths (`<commands_diagram>`, `<consumer_spec_file>`) are derived internally per `messaging-spec:naming-conventions`; downstream agents accept only `<commands_diagram>` (or `<consumer_name>`) plus non-derivable extras and derive the rest themselves.

The skill consumes the consumer spec — it does not regenerate it. If the spec is missing required tables (Table 1 / Table 2 / Table 3) or the path shape is malformed, downstream agents abort with their own one-sentence errors — this orchestrator does not pre-validate.

## Sibling file convention

Per `messaging-spec:naming-conventions`. From `$ARGUMENTS[0]` (the domain diagram) at `<dir>/<stem>.md` and `$ARGUMENTS[1]` (the consumer name, kebab-case matching `^[a-z][a-z0-9-]*$`):

- `<dir>` = directory containing the diagrams
- `<stem>` = the canonical aggregate stem (domain filename with `.md` stripped)
- `<commands_diagram>` = `<dir>/<stem>.commands.md` — the Mermaid commands class diagram (source of external event class declarations)
- `<consumer_spec_file>` = `<dir>/<stem>.messaging/<consumer_name>.md` — the per-consumer spec consumed by the messaging agents

## Workflow

The pipeline is fully sequential — each step waits for its predecessor to complete before invoking the next agent. If any agent reports an error, abort the pipeline and propagate the failure in the Step 10 report; do not run subsequent steps.

### Step 1 — Derive sibling paths

From `$ARGUMENTS[0]` (the domain diagram) and `$ARGUMENTS[1]` (the consumer name), derive the two sibling paths used downstream:

- Let `<dir>` = `dirname($ARGUMENTS[0])`
- Let `<stem>` = `basename($ARGUMENTS[0])` with the trailing `.md` stripped
- Let `<consumer_name>` = `$ARGUMENTS[1]` (must satisfy `^[a-z][a-z0-9-]*$`; if it does not, abort with a one-sentence error)
- Let `<commands_diagram>` = `<dir>/<stem>.commands.md`
- Let `<consumer_spec_file>` = `<dir>/<stem>.messaging/<consumer_name>.md`

These bindings are used by Step 10's report and as a sanity reference; downstream agents derive the same values from their own input arguments.

### Step 2 — Find target locations

Invoke `messaging-spec:target-locations-finder` with an empty prompt. Wait for completion.

Capture the agent's full Markdown table output verbatim as `<locations_report_text>`. This text is the locations argument passed to every downstream agent in Steps 3–9. Pass it verbatim — do not trim, summarize, or reformat it.

### Step 3 — Scaffold the per-consumer submodule

Invoke `messaging-spec:consumer-scaffolder` with prompt `<commands_diagram> <consumer_name> <locations_report_text>`. Wait for completion.

This emits the `<messaging_pkg>/<consumer_name_snake>/` directory with stub modules for `__init__.py`, `dispatcher.py`, `handlers.py`, and (conditionally) `events.py`; additively patches the root `messaging/__init__.py` aggregator; and appends destination + queue constants to `<pkg>/constants.py`. Subsequent steps assume these stubs exist on disk.

If the scaffolder aborts, propagate the failure and stop — do not proceed to Step 4.

### Step 4 — Implement external event classes

Invoke `messaging-spec:external-events-implementer` with prompt `<commands_diagram> <consumer_name> <locations_report_text>`. Wait for completion.

This walks Table 2 of the consumer spec, looks up each `external` event class on the Mermaid commands diagram, and renders each as a `@dataclass` extending `DomainEvent` in `<messaging_pkg>/<consumer_name_snake>/events.py`. Per-class additive — upgrades the scaffolder's bare `class X: pass` stubs in place; preserves user-implemented classes byte-identical.

If Table 2 has zero `external` rows, the agent prints a no-op line and returns without writing — the expected outcome for internal-only consumers.

If the implementer aborts, propagate the failure and stop — do not proceed to Step 5.

### Step 5 — Implement event handlers

Invoke `messaging-spec:event-handlers-implementer` with prompt `<commands_diagram> <consumer_name> <locations_report_text>`. Wait for completion.

This walks Tables 2 and 3 of the consumer spec and renders one `@inject`-decorated handler function per unique (Event Name, Source Destination) tuple in `<messaging_pkg>/<consumer_name_snake>/handlers.py`. Per-handler additive — upgrades the scaffolder's bare `def x(): pass` stubs in place; preserves user-implemented handlers byte-identical.

If the implementer aborts, propagate the failure and stop — do not proceed to Step 6.

### Step 6 — Implement the dispatcher factory

Invoke `messaging-spec:dispatcher-implementer` with prompt `<commands_diagram> <consumer_name> <locations_report_text>`. Wait for completion.

This auto-selects the single-aggregate or multi-aggregate dispatcher template based on the count of distinct Source Destinations in Table 2 and renders the `make_<consumer_name_snake>_dispatcher(...)` factory body in `<messaging_pkg>/<consumer_name_snake>/dispatcher.py`. Verifies that `dispatcher.py`, every expected handler in `handlers.py`, every required destination + queue constant in `constants.py`, and every internal-event aggregate subpackage are present before writing. Always regenerates `dispatcher.py` (full-file overwrite).

If the implementer aborts, propagate the failure and stop — do not proceed to Step 7.

### Step 7 — Wire the dispatcher into the service

Invoke `messaging-spec:dispatch-integrator` with prompt `<consumer_name> <locations_report_text>`. Wait for completion.

This patches `<pkg>/containers.py` (registers a `<consumer>_dispatcher: providers.Singleton[IMessageConsumer]` provider plus the supporting imports), `<pkg>/entrypoint.py` (defines a `run_<consumer>_dispatcher()` runner), and `<pkg>/__main__.py` (adds a `dispatch_<consumer>` Click command and registers it with the CLI group). Per-substep, line-level idempotent — partial wiring across files is repaired without wholesale skips.

If the integrator aborts, propagate the failure and stop — do not proceed to Step 8.

### Step 8 — Prepare test fixtures

Invoke `messaging-spec:test-fixtures-preparer` with prompt `<commands_diagram> <consumer_name> <locations_report_text>`. Wait for completion.

This ensures the root `<tests_dir>/conftest.py` defines the canonical `make_event_envelope` helper and one `@pytest.fixture` per Table 2 handler entry. Append-only and idempotent — preserves any existing fixture body byte-identical.

If the preparer aborts, propagate the failure and stop — do not proceed to Step 9.

### Step 9 — Implement handler integration tests

Invoke `messaging-spec:tests-implementer` with prompt `<commands_diagram> <consumer_name> <locations_report_text>`. Wait for completion.

This emits one test module per consumer at `<tests_dir>/integration/messaging/<consumer_name_snake>/test_<consumer_name_snake>_handlers.py` containing one `test_<handler_name>__success` function per Table 2 row. Each test constructs the event via the `make_event_envelope` helper, invokes the handler, and emits no assertions (handler-doesn't-raise contract). Append-only and idempotent.

If the implementer aborts, propagate the failure and stop.

### Step 10 — Report

Emit a phased Markdown summary grouping bullets by phase:

- **Scaffolding** — one bullet for `consumer-scaffolder` reporting its top-line outcome.
- **Implementation** — one bullet each for `external-events-implementer`, `event-handlers-implementer`, and `dispatcher-implementer` with their top-line outcomes.
- **Integration** — one bullet for `dispatch-integrator` with its top-line outcome.
- **Tests** — one bullet each for `test-fixtures-preparer` and `tests-implementer` with their top-line outcomes.

End with: `Messaging code generation complete for $ARGUMENTS[0] consumer $ARGUMENTS[1].`
