---
name: init-persistence
description: Initializes the project-wide persistence scaffolding. Invoke with: /init-persistence
allowed-tools: Bash, Agent
---

You are the project-wide persistence initializer. Ensure that the current repository has the minimum directory structure required for any subsequent `@persistence-spec:code-generator` (or `/persistence-spec:generate-persistence`) run:

- the `infrastructure/`, `infrastructure/repositories/`, and `infrastructure/repositories/tables/` Python packages,
- the `infrastructure/unit_of_work/` and `infrastructure/query_context/` packages copied from the `spec-core:modules` umbrella (with `containers.py` providers wired),
- the `extras/database_session/` package copied from the `spec-core:modules` umbrella and re-exported through `extras/__init__.py`,
- `etc/migrator/migrations/` with an empty Liquibase `master.yaml` stub,
- `tests/` and `tests/integration/` test packages with empty `conftest.py` files (plus the `query_context` integration fixture).

This skill performs no aggregate-specific work — per-aggregate sub-packages, tables, mappers, migrations, and repositories are still owned by the per-aggregate scaffolders.

## Inputs

None. The skill operates entirely on the current working directory.

## Output discipline

This skill is **silent on success**. Print nothing — not even a closing confirmation — when every step succeeds, whether the work happened, was partial, or was already done. Print only on failure: a single `ERROR: ...` line naming the failure, then stop. Do not summarize, do not emit progress text, do not echo sub-agent confirmation lines.

## Workflow

### Step 1 — Discover src/ and the project package

Invoke `@spec-core:project-package-finder` with prompt `/init-persistence`. Wait for completion. If it returns a line beginning `ERROR:`, surface that line verbatim and stop.

Otherwise parse its report table and bind `<repo>` = the `Repo` value, `<src>` = the `Src` value, and `<pkg>` = the `Package` value.

Bind:

- `<pkg_dir>` = `<src>/<pkg>`
- `<containers_file>` = `<pkg_dir>/containers.py`
- `<tests_dir>` = `<src>/tests`
- `<infra_dir>` = `<pkg_dir>/infrastructure`
- `<repos_dir>` = `<infra_dir>/repositories`
- `<tables_dir>` = `<repos_dir>/tables`
- `<migrations_dir>` = `<repo>/etc/migrator/migrations`
- `<master_yaml>` = `<migrations_dir>/master.yaml`

### Step 2 — Pre-check containers.py exists

Check whether `<containers_file>` exists:

```bash
[ -f "<containers_file>" ]
```

If it does not exist, emit:

```
ERROR: containers.py not found at <containers_file>. /init-persistence requires the project's containers.py to be in place before wiring unit_of_work and query_context providers.
```

and stop. Do not create the file. Do not proceed to any further step.

### Step 3 — Resolve target locations

Invoke `spec-core:target-locations-finder` with the prompt `persistence`. Wait for completion and capture its Markdown table output as `<locations_report>`.

If the agent reports any error, surface it as a single `ERROR: ...` line and stop.

### Step 4 — Create the base infrastructure packages

Run sequentially via `Bash`. For each of the three directories, create the directory and an empty `__init__.py` if they do not already exist:

```bash
mkdir -p <infra_dir>  && [ -f <infra_dir>/__init__.py ]  || touch <infra_dir>/__init__.py
mkdir -p <repos_dir>  && [ -f <repos_dir>/__init__.py ]  || touch <repos_dir>/__init__.py
mkdir -p <tables_dir> && [ -f <tables_dir>/__init__.py ] || touch <tables_dir>/__init__.py
```

Never overwrite an existing `__init__.py`.

### Step 5 — Create the migrations directory and master.yaml stub

Run:

```bash
mkdir -p <migrations_dir>
```

Then check whether `<master_yaml>` already exists:

```bash
[ -f "<master_yaml>" ]
```

If it does not exist, write the file with exactly this content (a minimal valid Liquibase changelog):

```yaml
databaseChangeLog: []
```

If it already exists, do not modify it.

### Step 6 — Scaffold the database_session package

Invoke `persistence-spec:database-session-scaffolder` with prompt `<locations_report>`. Wait for completion.

If the agent reports any error, surface it as a single `ERROR: ...` line and stop. Do not print the agent's success confirmation lines.

### Step 7 — Prepare the integration test package

Ensure `<tests_dir>` exists as a Python package containing a `conftest.py`, an `integration` sub-package, and an `integration/conftest.py`. Each created file is empty — fixture content is added by downstream agents. This is idempotent: create every missing level, never overwrite an existing file.

Run sequentially via `Bash`:

```bash
mkdir -p <tests_dir>             && [ -f <tests_dir>/__init__.py ]                  || touch <tests_dir>/__init__.py
[ -f <tests_dir>/conftest.py ]                                                      || touch <tests_dir>/conftest.py
mkdir -p <tests_dir>/integration && [ -f <tests_dir>/integration/__init__.py ]      || touch <tests_dir>/integration/__init__.py
[ -f <tests_dir>/integration/conftest.py ]                                          || touch <tests_dir>/integration/conftest.py
```

Never overwrite an existing file. If any command fails, surface it as a single `ERROR: ...` line and stop.

### Step 8 — Scaffold the unit_of_work package and wire containers.py

Invoke `persistence-spec:context-package-scaffolder` with prompt `unit_of_work <locations_report>`. Wait for completion.

If the agent reports any error, surface it as a single `ERROR: ...` line and stop.

### Step 9 — Scaffold the query_context package, wire containers.py, and add the integration fixture

Invoke `persistence-spec:context-package-scaffolder` with prompt `query_context <locations_report>`. Wait for completion.

This MUST run **after** Step 8 and **after** Step 7: the `query_context` axis derives its install directory as the sibling of the `unit_of_work/` package, asserts that leaf is exactly `unit_of_work`, and anchors its `query_context` conftest fixture immediately after the `def unit_of_work(` fixture in `<tests_dir>/integration/conftest.py`. Never invoke this before Step 8, and never combine the two invocations into one call.

If the agent reports any error, surface it as a single `ERROR: ...` line and stop.

### Step 10 — Report

Emit no output. Silent success.
