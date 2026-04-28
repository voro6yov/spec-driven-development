---
name: generate-tests
description: Resolves the tests location via the target-locations finder, prepares the integration test package, writes the cleanup + collection + persistence fixtures, and implements the command-repository integration tests for an aggregate. Invoke with: /persistence-spec:generate-tests <command_spec_file>
argument-hint: <command_spec_file>
allowed-tools: Read, Agent
---

You are an integration-test scaffolding orchestrator. Resolve the project's tests directory via `@target-locations-finder`, prepare the test package structure, seed the cleanup fixtures, write the collection + persistence fixtures, and implement the command-repository integration tests for the aggregate described in `$ARGUMENTS` (a `<stem>.command-repo-spec.md` file).

## Workflow

### Step 1 — Resolve the tests directory

Invoke `persistence-spec:target-locations-finder` with an empty prompt. Wait for completion.

Parse the `Tests` row from the returned Markdown table and read its `Absolute path` cell. Bind that value verbatim as `<tests_dir>` — it is an absolute path (e.g. `/repo/src/tests`). All downstream agents receive `<tests_dir>` as their first positional argument.

If the `Tests` row is missing or its path cell is empty, output an `ERROR:` line explaining the failure and stop.

### Step 2 — Prepare the integration test package

Invoke `persistence-spec:integration-test-package-preparer` with prompt `<tests_dir>`. Wait for completion.

This creates `<tests_dir>/`, `<tests_dir>/conftest.py`, `<tests_dir>/integration/`, and `<tests_dir>/integration/conftest.py` if they do not already exist. The agent is idempotent.

### Step 3 — Write the cleanup fixtures

After Step 2 completes, invoke `persistence-spec:unit-of-work-fixtures-preparer` with prompt `<tests_dir> $ARGUMENTS`. Wait for completion.

This adds the `unit_of_work` fixture (if missing) and the autouse `empty_unit_of_work` fixture seeded with this aggregate's `erase_all()` call into `<tests_dir>/integration/conftest.py`. The agent is idempotent for the same aggregate and additive for new aggregates.

### Step 4 — Write the collection and persistence fixtures

After Step 3 completes, invoke `persistence-spec:integration-fixtures-writer` with prompt `<tests_dir> $ARGUMENTS`. Wait for completion.

This discovers the per-state aggregate fixtures (`<snake>_<N>`) in `<tests_dir>/conftest.py` and writes the `test_<plural>` collection fixture and `add_<plural>` persistence fixture into `<tests_dir>/integration/conftest.py`. The agent is idempotent and single-aggregate-scoped (no FK wiring).

### Step 5 — Implement the command-repository integration tests

After Step 4 completes, invoke `persistence-spec:command-repository-tests-implementer` with prompt `<tests_dir> $ARGUMENTS`. Wait for completion.

This enumerates every `@abstractmethod` on the abstract `Command<Aggregate>Repository`, classifies each by signature, and writes the matching test scenarios into `<tests_dir>/integration/<aggregate>/test_<aggregate>_repository.py`. The agent is append-only and idempotent.

### Step 6 — Report

Emit a single line:

`Integration tests ready at <tests_dir>/integration/.`
