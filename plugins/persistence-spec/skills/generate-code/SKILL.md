---
name: generate-code
description: Implements the command-side and query-side persistence package for an aggregate from its command-repo-spec and writes its repository integration tests. Assumes `/persistence-spec:init-persistence` has prepared the project-wide scaffolding. Resolves target locations once, runs per-aggregate scaffolders in parallel, runs implementers in dependency order, wires the aggregate into the per-context unit of work and query context, and finally generates fixtures and tests. Invoke with: /persistence-spec:generate-code <domain_diagram>
argument-hint: <domain_diagram>
allowed-tools: Read, Agent
---

You are a persistence implementation orchestrator. Generate the command-side and query-side persistence code AND their integration tests for the aggregate described by `$ARGUMENTS[0]` (the domain diagram). The skill consumes the `<dir>/<stem>.persistence/command-repo-spec.md` sibling that `/persistence-spec:generate-specs` produces — it does not regenerate it. Spec-file paths are derived internally per `persistence-spec:naming-conventions`; downstream agents accept only `<domain_diagram>` plus non-derivable extras and derive the rest themselves.

## Precondition

Project-wide persistence scaffolding (`infrastructure/`, `infrastructure/repositories/`, `infrastructure/repositories/tables/`, `infrastructure/unit_of_work/`, `infrastructure/query_context/`, `extras/database_session/`, `etc/migrator/migrations/master.yaml`, and the `tests/integration/` package) must already be in place. Run `/persistence-spec:init-persistence` once per project before this skill. This skill does **not** scaffold any aggregate-agnostic artifact; per-aggregate scaffolders below will fail loudly if their parent packages are missing.

## Sibling file convention

Per `persistence-spec:naming-conventions`. From `$ARGUMENTS[0]` (the domain diagram) at `<dir>/<stem>.md`:

- `<dir>` = directory containing the domain diagram
- `<stem>` = the canonical aggregate stem (domain filename with `.md` stripped)
- `<plugin_dir>` = `<dir>/<stem>.persistence` — the per-plugin folder for persistence-spec
- Command repository spec = `<plugin_dir>/command-repo-spec.md`

If the command repository spec is missing the downstream agents abort with their own one-sentence errors — this orchestrator does not pre-validate.

## Workflow

### Step 1 — Find target locations

Invoke `persistence-spec:target-locations-finder` with an empty prompt. Wait for completion.

Capture the agent's full Markdown table output verbatim as `<locations_report_text>`. This text is the locations argument passed to every downstream code-phase agent in Steps 2–4. Pass it verbatim — do not trim, summarize, or reformat it.

Parse one value from the report:

- **`<tests_dir>`** — read the `Absolute path` cell of the `Tests` row. Bind that value verbatim — it is an absolute path (e.g. `/repo/src/tests`). If the `Tests` row is missing or its path cell is empty, output an `ERROR:` line explaining the failure and stop before any code generation.

### Step 2 — Spawn aggregate scaffolders in parallel

In a single message, invoke the following agents in parallel. Do not wait between them.

- `persistence-spec:repositories-scaffolder` with prompt `$ARGUMENTS[0] <locations_report_text>`
- `persistence-spec:mappers-scaffolder` with prompt `$ARGUMENTS[0] <locations_report_text>`
- `persistence-spec:migrations-scaffolder` with prompt `$ARGUMENTS[0] <locations_report_text>`
- `persistence-spec:table-scaffolder` with prompt `$ARGUMENTS[0] <locations_report_text>`

Each agent parses `<locations_report_text>` for the rows it needs and ignores the others. The aggregate-agnostic `unit-of-work-scaffolder`, `query-context-scaffolder`, and `database-session-scaffolder` are not invoked here — `/persistence-spec:init-persistence` owns them.

Wait for all invocations to complete before proceeding.

### Step 3 — Run implementers (two phases)

#### Phase 3a — Parallel implementers

In a single message, invoke the following agents in parallel:

- `persistence-spec:table-implementer` with prompt `$ARGUMENTS[0] <locations_report_text>`
- `persistence-spec:migrations-implementer` with prompt `$ARGUMENTS[0] <locations_report_text>`
- `persistence-spec:mappers-implementer` with prompt `$ARGUMENTS[0] <locations_report_text>`

Wait for all three to complete.

#### Phase 3b — Repository implementers

After Phase 3a completes, invoke the following agents in parallel in a single message:

- `persistence-spec:command-repository-implementer` with prompt `$ARGUMENTS[0] <locations_report_text>`
- `persistence-spec:query-repository-implementer` with prompt `$ARGUMENTS[0] <locations_report_text>`

Wait for both to complete. The command repository depends on mappers being implemented, so it must run after Phase 3a. The query repository has no mapper dependency but is grouped here for symmetry and because Step 4 needs both repositories implemented.

### Step 4 — Integrate unit of work and query context

In a single message, invoke the following agents in parallel:

- `persistence-spec:unit-of-work-integrator` with prompt `$ARGUMENTS[0] <locations_report_text>`
- `persistence-spec:query-context-integrator` with prompt `$ARGUMENTS[0] <locations_report_text>`

Both steps always run — they are per-aggregate wiring and idempotent.

Wait for both to complete.

### Step 5 — Write the cleanup fixtures

Invoke `persistence-spec:unit-of-work-fixtures-preparer` with prompt `$ARGUMENTS[0] <tests_dir>`. Wait for completion.

This adds the `unit_of_work` fixture (if missing) and the autouse `empty_unit_of_work` fixture seeded with this aggregate's `erase_all()` call into `<tests_dir>/integration/conftest.py`. The agent is idempotent for the same aggregate and additive for new aggregates.

### Step 6 — Write the collection and persistence fixtures

Invoke `persistence-spec:integration-fixtures-writer` with prompt `$ARGUMENTS[0] <tests_dir>`. Wait for completion.

This discovers the per-state aggregate fixtures (`<snake>_<N>`) in `<tests_dir>/conftest.py` and writes the `test_<plural>` collection fixture and `add_<plural>` persistence fixture into `<tests_dir>/integration/conftest.py`. The agent is idempotent and single-aggregate-scoped (no FK wiring).

### Step 7 — Implement the repository integration tests

In a single message, invoke the following agents in parallel:

- `persistence-spec:command-repository-tests-implementer` with prompt `$ARGUMENTS[0] <tests_dir>`
- `persistence-spec:query-repository-tests-implementer` with prompt `$ARGUMENTS[0] <tests_dir>`

Wait for both to complete.

The command-side agent enumerates every `@abstractmethod` on `Command<Aggregate>Repository`, classifies each by signature, and writes scenarios into `<tests_dir>/integration/<aggregate>/test_<aggregate>_repository.py`. The query-side agent does the same for `Query<Aggregate>Repository` and writes into `<tests_dir>/integration/<aggregate>/test_query_<aggregate>_repository.py`. Both agents are append-only and idempotent.

If any test-phase agent (Steps 5–7) fails, abort the workflow and report the failure.

### Step 8 — Report

Emit a phased Markdown summary grouping bullets by phase:

- **Scaffolding** — one bullet per scaffolder invoked in Step 2 (`repositories-scaffolder`, `mappers-scaffolder`, `migrations-scaffolder`, `table-scaffolder`) with its top-line outcome.
- **Implementation** — one bullet per implementer invoked in Step 3 (Phase 3a and 3b combined, including `query-repository-implementer`) with its top-line outcome.
- **Integration** — one bullet each for `unit-of-work-integrator` and `query-context-integrator` with their top-line outcomes.
- **Tests** — one bullet each for `unit-of-work-fixtures-preparer`, `integration-fixtures-writer`, `command-repository-tests-implementer`, and `query-repository-tests-implementer` with their top-line outcomes.

End with: `Persistence code generation complete for $ARGUMENTS[0].`
