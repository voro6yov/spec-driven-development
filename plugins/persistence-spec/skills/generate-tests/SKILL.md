---
name: generate-tests
description: Prepares the integration test package, writes the cleanup + collection + persistence fixtures, and implements the command-repository integration tests for an aggregate. Invoke with: /persistence-spec:generate-tests <base_dir> <command_spec_file>
argument-hint: <base_dir> <command_spec_file>
allowed-tools: Read, Agent
---

You are an integration-test scaffolding orchestrator. Prepare the test package structure, seed the cleanup fixtures, write the collection + persistence fixtures, and implement the command-repository integration tests for the aggregate described in `$ARGUMENTS[1]` (a `<stem>.command-repo-spec.md` file), inside the project rooted at `$ARGUMENTS[0]`.

## Workflow

### Step 1 — Prepare the integration test package

Invoke `persistence-spec:integration-test-package-preparer` with prompt `$ARGUMENTS[0]`. Wait for completion.

This creates `tests/`, `tests/conftest.py`, `tests/integration/`, and `tests/integration/conftest.py` under `$ARGUMENTS[0]` if they do not already exist. The agent is idempotent.

### Step 2 — Write the cleanup fixtures

After Step 1 completes, invoke `persistence-spec:unit-of-work-fixtures-preparer` with prompt `$ARGUMENTS[0] $ARGUMENTS[1]`. Wait for completion.

This adds the `unit_of_work` fixture (if missing) and the autouse `empty_unit_of_work` fixture seeded with this aggregate's `erase_all()` call into `tests/integration/conftest.py`. The agent is idempotent for the same aggregate and additive for new aggregates.

### Step 3 — Write the collection and persistence fixtures

After Step 2 completes, invoke `persistence-spec:integration-fixtures-writer` with prompt `$ARGUMENTS[0] $ARGUMENTS[1]`. Wait for completion.

This discovers the per-state aggregate fixtures (`<snake>_<N>`) in `tests/conftest.py` and writes the `test_<plural>` collection fixture and `add_<plural>` persistence fixture into `tests/integration/conftest.py`. The agent is idempotent and single-aggregate-scoped (no FK wiring).

### Step 4 — Implement the command-repository integration tests

After Step 3 completes, invoke `persistence-spec:command-repository-tests-implementer` with prompt `$ARGUMENTS[0] $ARGUMENTS[1]`. Wait for completion.

This enumerates every `@abstractmethod` on the abstract `Command<Aggregate>Repository`, classifies each by signature, and writes the matching test scenarios into `tests/integration/<aggregate>/test_<aggregate>_repository.py`. The agent is append-only and idempotent.

### Step 5 — Report

Emit a single line:

`Integration tests ready at $ARGUMENTS[0]/tests/integration/.`
