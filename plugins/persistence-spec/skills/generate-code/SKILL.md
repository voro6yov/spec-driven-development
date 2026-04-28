---
name: generate-code
description: Implements the command-side and query-side persistence package for an aggregate from its command-repo-spec, then prepares the integration test package and writes the repository integration tests. Resolves target locations once, runs scaffolders in parallel, runs implementers in dependency order, wires the aggregate into the per-context unit of work and query context, and finally generates fixtures and tests. Invoke with: /persistence-spec:generate-code <command_spec_file>
argument-hint: <command_spec_file>
allowed-tools: Read, Agent
---

You are a persistence implementation orchestrator. Generate the command-side and query-side persistence code AND their integration tests for the aggregate described in `$ARGUMENTS` (a `<stem>.command-repo-spec.md` file).

## Workflow

### Step 1 — Find target locations

Invoke `persistence-spec:target-locations-finder` with an empty prompt. Wait for completion.

Capture the agent's full Markdown table output verbatim as `<locations_report_text>`. This text is the second argument passed to every downstream code-phase agent in Steps 2–4. Pass it verbatim — do not trim, summarize, or reformat it.

Parse two values from the report:

- **`<skip_uow_scaffolder>`** — read the `Context Integration` row's `Status` cell. If the status is `exists`, set this flag to true; otherwise false. The `unit-of-work-scaffolder` is aggregate-agnostic and only needs to run once per context — skip it on subsequent runs as a caller-side optimization. The agent itself is idempotent, so re-running is safe; the skip just avoids redundant work. **Do not reuse this flag for `query-context-scaffolder`.** The locations report's `Context Integration` row tracks only the `unit_of_work` directory; the sibling `query_context/` directory may be missing even when `unit_of_work/` exists. The query-context scaffolder is idempotent, so always invoke it and let it no-op when the package is already in place.
- **`<tests_dir>`** — read the `Absolute path` cell of the `Tests` row. Bind that value verbatim — it is an absolute path (e.g. `/repo/src/tests`). If the `Tests` row is missing or its path cell is empty, output an `ERROR:` line explaining the failure and stop before any code generation.

### Step 2 — Spawn scaffolders in parallel

In a single message, invoke the following agents in parallel. Do not wait between them.

- `persistence-spec:repositories-scaffolder` with prompt `$ARGUMENTS <locations_report_text>`
- `persistence-spec:mappers-scaffolder` with prompt `$ARGUMENTS <locations_report_text>`
- `persistence-spec:migrations-scaffolder` with prompt `$ARGUMENTS <locations_report_text>`
- `persistence-spec:table-scaffolder` with prompt `$ARGUMENTS <locations_report_text>`
- `persistence-spec:unit-of-work-scaffolder` with prompt `<locations_report_text>` — **skip this invocation entirely** if `<skip_uow_scaffolder>` is true.
- `persistence-spec:query-context-scaffolder` with prompt `<locations_report_text>` — always invoke; the agent is idempotent and the locations report cannot distinguish a present `query_context/` from a missing one.

Each agent parses `<locations_report_text>` for the rows it needs and ignores the others.

Wait for all invocations to complete before proceeding.

### Step 3 — Run implementers (two phases)

#### Phase 3a — Parallel implementers

In a single message, invoke the following agents in parallel:

- `persistence-spec:table-implementer` with prompt `$ARGUMENTS <locations_report_text>`
- `persistence-spec:migrations-implementer` with prompt `$ARGUMENTS <locations_report_text>`
- `persistence-spec:mappers-implementer` with prompt `$ARGUMENTS <locations_report_text>`

Wait for all three to complete.

#### Phase 3b — Repository implementers

After Phase 3a completes, invoke the following agents in parallel in a single message:

- `persistence-spec:command-repository-implementer` with prompt `$ARGUMENTS <locations_report_text>`
- `persistence-spec:query-repository-implementer` with prompt `$ARGUMENTS <locations_report_text>`

Wait for both to complete. The command repository depends on mappers being implemented, so it must run after Phase 3a. The query repository has no mapper dependency but is grouped here for symmetry and because Step 4 needs both repositories implemented.

### Step 4 — Integrate unit of work and query context

In a single message, invoke the following agents in parallel:

- `persistence-spec:unit-of-work-integrator` with prompt `$ARGUMENTS <locations_report_text>`
- `persistence-spec:query-context-integrator` with prompt `$ARGUMENTS <locations_report_text>`

Both steps always run — they are per-aggregate wiring and idempotent, so they are safe regardless of whether the scaffolders were skipped in Step 2.

Wait for both to complete.

### Step 5 — Prepare the integration test package

Invoke `persistence-spec:integration-test-package-preparer` with prompt `<tests_dir>`. Wait for completion.

This creates `<tests_dir>/`, `<tests_dir>/conftest.py`, `<tests_dir>/integration/`, and `<tests_dir>/integration/conftest.py` if they do not already exist. The agent is idempotent.

### Step 6 — Write the cleanup fixtures

Invoke `persistence-spec:unit-of-work-fixtures-preparer` with prompt `<tests_dir> $ARGUMENTS`. Wait for completion.

This adds the `unit_of_work` fixture (if missing) and the autouse `empty_unit_of_work` fixture seeded with this aggregate's `erase_all()` call into `<tests_dir>/integration/conftest.py`. The agent is idempotent for the same aggregate and additive for new aggregates.

### Step 7 — Write the collection and persistence fixtures

Invoke `persistence-spec:integration-fixtures-writer` with prompt `<tests_dir> $ARGUMENTS`. Wait for completion.

This discovers the per-state aggregate fixtures (`<snake>_<N>`) in `<tests_dir>/conftest.py` and writes the `test_<plural>` collection fixture and `add_<plural>` persistence fixture into `<tests_dir>/integration/conftest.py`. The agent is idempotent and single-aggregate-scoped (no FK wiring).

### Step 8 — Implement the repository integration tests

In a single message, invoke the following agents in parallel:

- `persistence-spec:command-repository-tests-implementer` with prompt `<tests_dir> $ARGUMENTS`
- `persistence-spec:query-repository-tests-implementer` with prompt `<tests_dir> $ARGUMENTS`

Wait for both to complete.

The command-side agent enumerates every `@abstractmethod` on `Command<Aggregate>Repository`, classifies each by signature, and writes scenarios into `<tests_dir>/integration/<aggregate>/test_<aggregate>_repository.py`. The query-side agent does the same for `Query<Aggregate>Repository` and writes into `<tests_dir>/integration/<aggregate>/test_query_<aggregate>_repository.py`. Both agents are append-only and idempotent.

If any test-phase agent (Steps 5–8) fails, abort the workflow and report the failure.

### Step 9 — Report

Emit a phased Markdown summary grouping bullets by phase:

- **Scaffolding** — one bullet per scaffolder invoked in Step 2 with its top-line outcome. If `unit-of-work-scaffolder` was skipped, list it with `skipped (Context Integration already exists)`.
- **Implementation** — one bullet per implementer invoked in Step 3 (Phase 3a and 3b combined, including `query-repository-implementer`) with its top-line outcome.
- **Integration** — one bullet each for `unit-of-work-integrator` and `query-context-integrator` with their top-line outcomes.
- **Tests** — one bullet each for `integration-test-package-preparer`, `unit-of-work-fixtures-preparer`, `integration-fixtures-writer`, `command-repository-tests-implementer`, and `query-repository-tests-implementer` with their top-line outcomes.

End with: `Persistence code generation complete for $ARGUMENTS.`
