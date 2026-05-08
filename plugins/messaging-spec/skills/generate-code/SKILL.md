---
name: generate-code
description: Implements the messaging consumer package for a single consumer from its `<consumer_name>.messaging.md` spec sibling and a Mermaid commands class diagram. Resolves target locations once, scaffolds the per-consumer submodule, fills external event dataclasses + handler functions + the dispatcher factory, wires the dispatcher into containers/entrypoint/__main__, and finally prepares the test fixtures and writes the handler integration tests. Invoke with: /messaging-spec:generate-code <consumer_spec_file> <commands_diagram>
argument-hint: <consumer_spec_file> <commands_diagram>
allowed-tools: Agent
---

You are a messaging implementation orchestrator. Implement the messaging code AND its handler integration tests for the consumer described by `$ARGUMENTS[0]` (a `<consumer_name>.messaging.md` consumer spec) using the Mermaid commands class diagram at `$ARGUMENTS[1]` as the source of external event class declarations.

The skill consumes the consumer spec sibling — it does not regenerate it. If the spec is missing required tables (Table 1 / Table 2 / Table 3) or the file basename is malformed, downstream agents abort with their own one-sentence errors — this orchestrator does not pre-validate.

## Sibling file convention

For the consumer spec at `<dir>/<consumer_name>.messaging.md` (passed as `$ARGUMENTS[0]`), derive `<consumer_name>` by taking the final path segment (basename) of `$ARGUMENTS[0]` and stripping the trailing `.messaging.md` suffix. The result is a kebab-case identifier (e.g. `profile-reconciliation`) consumed by Steps 3, 5, and 6.

If `$ARGUMENTS[0]` does not end with `.messaging.md`, the downstream agents will abort on their own filename validation — do not pre-check.

## Workflow

The pipeline is fully sequential — each step waits for its predecessor to complete before invoking the next agent. If any agent reports an error, abort the pipeline and propagate the failure in the Step 9 report; do not run subsequent steps.

### Step 1 — Find target locations

Invoke `messaging-spec:target-locations-finder` with an empty prompt. Wait for completion.

Capture the agent's full Markdown table output verbatim as `<locations_report_text>`. This text is the locations argument passed to every downstream agent in Steps 2–8. Pass it verbatim — do not trim, summarize, or reformat it.

### Step 2 — Scaffold the per-consumer submodule

Invoke `messaging-spec:consumer-scaffolder` with prompt `$ARGUMENTS[0] <locations_report_text>`. Wait for completion.

This emits the `<messaging_pkg>/<consumer_name_snake>/` directory with stub modules for `__init__.py`, `dispatcher.py`, `handlers.py`, and (conditionally) `events.py`; additively patches the root `messaging/__init__.py` aggregator; and appends destination + queue constants to `<pkg>/constants.py`. Subsequent steps assume these stubs exist on disk.

If the scaffolder aborts, propagate the failure and stop — do not proceed to Step 3.

### Step 3 — Implement external event classes

Invoke `messaging-spec:external-events-implementer` with prompt `$ARGUMENTS[1] <consumer_name> <locations_report_text>`. Wait for completion.

This walks Table 2 of the consumer spec, looks up each `external` event class on the Mermaid commands diagram, and renders each as a `@dataclass` extending `DomainEvent` in `<messaging_pkg>/<consumer_name_snake>/events.py`. Per-class additive — upgrades the scaffolder's bare `class X: pass` stubs in place; preserves user-implemented classes byte-identical.

If Table 2 has zero `external` rows, the agent prints a no-op line and returns without writing — the expected outcome for internal-only consumers.

If the implementer aborts, propagate the failure and stop — do not proceed to Step 4.

### Step 4 — Implement event handlers

Invoke `messaging-spec:event-handlers-implementer` with prompt `$ARGUMENTS[0] <locations_report_text>`. Wait for completion.

This walks Tables 2 and 3 of the consumer spec and renders one `@inject`-decorated handler function per unique (Event Name, Source Destination) tuple in `<messaging_pkg>/<consumer_name_snake>/handlers.py`. Per-handler additive — upgrades the scaffolder's bare `def x(): pass` stubs in place; preserves user-implemented handlers byte-identical.

If the implementer aborts, propagate the failure and stop — do not proceed to Step 5.

### Step 5 — Implement the dispatcher factory

Invoke `messaging-spec:dispatcher-implementer` with prompt `<consumer_name> <locations_report_text>`. Wait for completion.

This auto-selects the single-aggregate or multi-aggregate dispatcher template based on the count of distinct Source Destinations in Table 2 and renders the `make_<consumer_name_snake>_dispatcher(...)` factory body in `<messaging_pkg>/<consumer_name_snake>/dispatcher.py`. Verifies that `dispatcher.py`, every expected handler in `handlers.py`, every required destination + queue constant in `constants.py`, and every internal-event aggregate subpackage are present before writing. Always regenerates `dispatcher.py` (full-file overwrite).

If the implementer aborts, propagate the failure and stop — do not proceed to Step 6.

### Step 6 — Wire the dispatcher into the service

Invoke `messaging-spec:dispatch-integrator` with prompt `<consumer_name> <locations_report_text>`. Wait for completion.

This patches `<pkg>/containers.py` (registers a `<consumer>_dispatcher: providers.Singleton[IMessageConsumer]` provider plus the supporting imports), `<pkg>/entrypoint.py` (defines a `run_<consumer>_dispatcher()` runner), and `<pkg>/__main__.py` (adds a `dispatch_<consumer>` Click command and registers it with the CLI group). Per-substep, line-level idempotent — partial wiring across files is repaired without wholesale skips.

If the integrator aborts, propagate the failure and stop — do not proceed to Step 7.

### Step 7 — Prepare test fixtures

Invoke `messaging-spec:test-fixtures-preparer` with prompt `$ARGUMENTS[0] <locations_report_text>`. Wait for completion.

This ensures the root `<tests_dir>/conftest.py` defines the canonical `make_event_envelope` helper and one `@pytest.fixture` per Table 2 handler entry. Append-only and idempotent — preserves any existing fixture body byte-identical.

If the preparer aborts, propagate the failure and stop — do not proceed to Step 8.

### Step 8 — Implement handler integration tests

Invoke `messaging-spec:tests-implementer` with prompt `$ARGUMENTS[0] <locations_report_text>`. Wait for completion.

This emits one test module per consumer at `<tests_dir>/integration/messaging/<consumer_name_snake>/test_<consumer_name_snake>_handlers.py` containing one `test_<handler_name>__success` function per Table 2 row. Each test constructs the event via the `make_event_envelope` helper, invokes the handler, and emits no assertions (handler-doesn't-raise contract). Append-only and idempotent.

If the implementer aborts, propagate the failure and stop.

### Step 9 — Report

Emit a phased Markdown summary grouping bullets by phase:

- **Scaffolding** — one bullet for `consumer-scaffolder` reporting its top-line outcome.
- **Implementation** — one bullet each for `external-events-implementer`, `event-handlers-implementer`, and `dispatcher-implementer` with their top-line outcomes.
- **Integration** — one bullet for `dispatch-integrator` with its top-line outcome.
- **Tests** — one bullet each for `test-fixtures-preparer` and `tests-implementer` with their top-line outcomes.

End with: `Messaging code generation complete for $ARGUMENTS[0].`
