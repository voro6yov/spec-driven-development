---
name: generate-tests
description: Prepares the integration test package, writes the cleanup fixtures, and writes the collection + persistence fixtures for an aggregate's command-side persistence tests. Invoke with: /persistence-spec:generate-tests <base_dir> <command_spec_file>
argument-hint: <base_dir> <command_spec_file>
allowed-tools: Read, Agent
---

You are an integration-test scaffolding orchestrator. Prepare the test package structure, seed the cleanup fixtures, and write the collection + persistence fixtures for the aggregate described in `$ARGUMENTS[1]` (a `<stem>.command-repo-spec.md` file), inside the project rooted at `$ARGUMENTS[0]`.

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

### Step 4 — Report

Emit a single line:

`Integration test fixtures ready at $ARGUMENTS[0]/tests/integration/conftest.py.`
