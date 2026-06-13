---
name: init-application
description: "Initializes the project-wide application-layer scaffolding (project package discovery, src/<pkg>/application/, src/<pkg>/infrastructure/, src/<pkg>/infrastructure/services/, src/tests/fakes/, and a minimal src/tests/conftest.py). Invoke with: /application-spec:init-application"
allowed-tools: Bash, Agent
---

You are the project-wide application-layer initializer. Ensure that the current repository has the minimum directory structure required for any subsequent `/application-spec:generate-code` (or `/application-spec:generate-application`) run:

- the `application/` Python package (empty aggregator; populated per-aggregate by `@application-files-scaffolder`),
- the `infrastructure/` and `infrastructure/services/` Python packages (empty aggregators; populated per-aggregate),
- the `tests/fakes/` Python package (empty aggregator; populated per-service by `@service-implementer`),
- a `tests/conftest.py` file with a minimal `import pytest` preamble (additively patched per-aggregate by `@service-implementer` and `@commands-implementer`).

This skill performs no aggregate-specific work — per-aggregate stub modules, service packages, exception classes, DI providers, and conftest fixtures are still owned by the per-aggregate scaffolders and implementers.

This skill performs no `containers.py` wiring — every application-spec provider (settings, exceptions, services, commands, queries) is aggregate-specific. The only `containers.py`-related work here is the existence pre-check in Step 2; this skill assumes `/persistence-spec:init-persistence` (or the project owner) has already created the file.

## Inputs

None. The skill operates entirely on the current working directory.

## Output discipline

This skill is **silent on success**. Print nothing — not even a closing confirmation — when every step succeeds, whether the work happened or was already done. Print only on failure: a single `ERROR: ...` line naming the failure, then stop. Do not summarize, do not emit progress text, do not echo sub-agent confirmation lines.

## Workflow

### Step 1 — Discover src/ and the project package

Run `pwd` to obtain `<repo>`. Set `<src>` = `<repo>/src`.

Check `<src>` exists. If not, emit:

```
ERROR: src/ not found at <src>. Initialize a Python project under <repo>/src/ before running /application-spec:init-application.
```

List entries directly under `<src>`, excluding `tests`, hidden entries (names starting with `.`), and `__pycache__`:

```bash
ls -1 <src> 2>/dev/null | grep -v -E '^(tests|__pycache__|\..*)$'
```

Filter the output to directories only and bind the result. Exactly one directory must remain — bind it as `<pkg>`. Abort with `ERROR: ...` on any of these conditions:

- Zero directories remain:

  ```
  ERROR: no project package found under <src>. Expected exactly one directory (other than tests/). /application-spec:init-application does not bootstrap a project package; create src/<pkg>/ first.
  ```

- More than one directory remains:

  ```
  ERROR: ambiguous project package under <src>; found multiple candidates: <comma-separated list>. /application-spec:init-application requires exactly one src/<pkg>/.
  ```

Bind:

- `<pkg_dir>` = `<src>/<pkg>`
- `<containers_file>` = `<pkg_dir>/containers.py`
- `<constants_file>` = `<pkg_dir>/constants.py`
- `<tests_dir>` = `<src>/tests`
- `<app_pkg>` = `<pkg_dir>/application`
- `<infra_pkg>` = `<pkg_dir>/infrastructure`
- `<services_dir>` = `<infra_pkg>/services`
- `<fakes_dir>` = `<tests_dir>/fakes`
- `<conftest_file>` = `<tests_dir>/conftest.py`

### Step 2 — Pre-check containers.py exists

Check whether `<containers_file>` exists:

```bash
[ -f "<containers_file>" ]
```

If it does not exist, emit:

```
ERROR: containers.py not found at <containers_file>. /application-spec:init-application requires the project's containers.py to be in place — every per-aggregate application service registers a provider in it. Run /persistence-spec:init-persistence (or otherwise create containers.py) before this skill.
```

and stop. Do not create the file. Do not proceed to any further step.

### Step 3 — Pre-check constants.py exists

Check whether `<constants_file>` exists:

```bash
[ -f "<constants_file>" ]
```

If it does not exist, emit:

```
ERROR: constants.py not found at <constants_file>. /application-spec:init-application requires the project's constants.py to be in place — @application-files-scaffolder appends one <UPPER_AGGREGATE>_DESTINATION = "<Plural>" line per aggregate into it. constants.py is hand-authored; this skill does not create it.
```

and stop. Do not create the file. Do not proceed to any further step.

### Step 4 — Resolve target locations

Invoke `spec-core:target-locations-finder` with the prompt `application`. Wait for completion and capture its Markdown table output as `<locations_report>`.

If the agent reports any error, surface it as a single `ERROR: ...` line and stop. Do not print the agent's success confirmation lines.

The report is captured for parity with `/persistence-spec:init-persistence` (which feeds the report into downstream scaffolders); this skill does not consume any row beyond the existence check performed above. The bindings derived in Step 1 are authoritative for Steps 5-7.

### Step 5 — Create the base application package

Run sequentially via `Bash`. Create the directory and an empty `__init__.py` if it does not already exist:

```bash
mkdir -p <app_pkg> && [ -f <app_pkg>/__init__.py ] || touch <app_pkg>/__init__.py
```

Never overwrite an existing `<app_pkg>/__init__.py` — its content is owned by `@application-files-scaffolder` Step 6b (which rewrites it from on-disk aggregate subpackages on every per-aggregate run).

### Step 6 — Create the base infrastructure packages

Run sequentially via `Bash`. For each of the two directories, create the directory and an empty `__init__.py` if they do not already exist:

```bash
mkdir -p <infra_pkg>    && [ -f <infra_pkg>/__init__.py ]    || touch <infra_pkg>/__init__.py
mkdir -p <services_dir> && [ -f <services_dir>/__init__.py ] || touch <services_dir>/__init__.py
```

Never overwrite an existing `__init__.py`. The `<services_dir>/__init__.py` is rewritten on every per-aggregate run by `@application-files-scaffolder` Step 6, but the initial zero-byte file keeps the package importable until the first aggregate is scaffolded.

### Step 7 — Create the tests packages and conftest.py preamble

Run sequentially via `Bash`. Create both test directories and their `__init__.py` files if missing:

```bash
mkdir -p <tests_dir>  && [ -f <tests_dir>/__init__.py ]  || touch <tests_dir>/__init__.py
mkdir -p <fakes_dir>  && [ -f <fakes_dir>/__init__.py ]  || touch <fakes_dir>/__init__.py
```

Never overwrite an existing `__init__.py`. The `<fakes_dir>/__init__.py` is rewritten on every per-service run by `@service-implementer` Step 8, but the initial zero-byte file keeps the package importable until the first service is wired.

Then check whether `<conftest_file>` already exists:

```bash
[ -f "<conftest_file>" ]
```

If it does not exist, write the file with exactly this content (the minimal preamble shared by `@service-implementer` and `@commands-implementer`):

```python
import pytest
```

If it already exists, do not modify it — its content is owned downstream and per-aggregate agents only append (never replace) imports and fixtures.

Note: the `tests/__init__.py` created above is intentionally zero-byte. The persistence-spec pipeline's `@integration-test-package-preparer` (run by `/persistence-spec:init-persistence`) creates `<tests_dir>/integration/__init__.py` and `<tests_dir>/integration/conftest.py` separately; this skill does not touch the integration subpackage.

### Step 8 — Report

Emit no output. Silent success.
