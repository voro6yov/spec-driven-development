---
name: init-rest-api
description: "Initializes the project-wide REST API scaffolding. Invoke with: /rest-api-spec:init-rest-api"
allowed-tools: Bash, Write, Agent
---

You are the project-wide REST API initializer. Ensure that the current repository has the minimum directory structure and module set required for any subsequent `@rest-api-spec:code-generator` (or `/rest-api-spec:generate-rest-api`) run:

- the `api/` Python package (with a minimal `__init__.py` that satisfies the `from .X import *` + `__all__ = X.__all__ + ...` aggregation convention required by `@auth-integrator`),
- the shared serializer modules under `api/serializers/` (`error.py`, `configured_base_serializer.py`, `json_utils.py`) and their star-aggregator `serializers/__init__.py`, copied from this plugin's reference modules,
- `api/error_handlers.py` rendered from the domain exceptions defined under `<pkg>/domain/shared/exceptions.py`, with `register_error_handler(fastapi_app)` wired into `create_fastapi`,
- the `application/auth/` subpackage (`AuthCommands` + `UserData`), `api/auth.py` rendered from the auth-middleware skill template with `PUBLIC_ENDPOINTS` / `INTERNAL_ENDPOINTS_PREFIX` derived from `<pkg>/constants.py`, the `Singleton(AuthCommands)` provider in `containers.py`, and `register_auth(fastapi_app)` wired into `create_fastapi`,
- the standard API client + authentication fixtures (`app`, `client`, `containers`, `token_payload`, `request_headers`) added to `src/tests/conftest.py`.

This skill performs no per-resource work — per-surface package layout, endpoint modules, per-aggregate serializers, integration tests, top-level `endpoints/__init__.py`, and API-routing constants are still owned by the per-resource scaffolders and implementers run via `@rest-api-spec:code-generator`.

## Inputs

None. The skill operates entirely on the current working directory.

## Output discipline

This skill is **silent on success**. Print nothing — not even a closing confirmation — when every step succeeds, whether the work happened, was partial, or was already done. Print only on failure: a single `ERROR: ...` line naming the failure, then stop. Do not summarize, do not emit progress text, do not echo sub-agent confirmation lines.

## Workflow

### Step 1 — Discover src/ and the project package

Run `pwd` to obtain `<repo>`. Set `<src>` = `<repo>/src`.

Check `<src>` exists. If not, emit:

```
ERROR: src/ not found at <src>. Initialize a Python project under <repo>/src/ before running /rest-api-spec:init-rest-api.
```

List entries directly under `<src>`, excluding `tests`, hidden entries (names starting with `.`), and `__pycache__`:

```bash
ls -1 <src> 2>/dev/null | grep -v -E '^(tests|__pycache__|\..*)$'
```

Filter the output to directories only and bind the result. Exactly one directory must remain — bind it as `<pkg>`. Abort with `ERROR: ...` on any of these conditions:

- Zero directories remain:

  ```
  ERROR: no project package found under <src>. Expected exactly one directory (other than tests/). /rest-api-spec:init-rest-api does not bootstrap a project package; create src/<pkg>/ first.
  ```

- More than one directory remains:

  ```
  ERROR: ambiguous project package under <src>; found multiple candidates: <comma-separated list>. /rest-api-spec:init-rest-api requires exactly one src/<pkg>/.
  ```

Bind:

- `<pkg_dir>` = `<src>/<pkg>`
- `<containers_file>` = `<pkg_dir>/containers.py`
- `<constants_file>` = `<pkg_dir>/constants.py`
- `<entrypoint_file>` = `<pkg_dir>/entrypoint.py`
- `<api_pkg>` = `<pkg_dir>/api`
- `<api_init_file>` = `<api_pkg>/__init__.py`
- `<serializers_dir>` = `<api_pkg>/serializers`
- `<tests_dir>` = `<src>/tests`

### Step 2 — Pre-check containers.py exists

Check whether `<containers_file>` exists:

```bash
[ -f "<containers_file>" ]
```

If it does not exist, emit:

```
ERROR: containers.py not found at <containers_file>. /rest-api-spec:init-rest-api requires the project's containers.py to be in place — @auth-integrator registers an auth_commands provider in it. Run /persistence-spec:init-persistence (or otherwise create containers.py) before this skill.
```

and stop. Do not create the file. Do not proceed to any further step.

### Step 3 — Pre-check constants.py exists

Check whether `<constants_file>` exists:

```bash
[ -f "<constants_file>" ]
```

If it does not exist, emit:

```
ERROR: constants.py not found at <constants_file>. /rest-api-spec:init-rest-api requires the project's constants.py to be in place — @auth-integrator reads BASE_API_PREFIX (and any V<N>_API_PREFIX / INTERNAL_API_PREFIX) from it to render PUBLIC_ENDPOINTS. constants.py is created and patch-merged by `@app-integrator` during @rest-api-spec:code-generator; run that for your first resource before /rest-api-spec:init-rest-api, or hand-author constants.py with at least BASE_API_PREFIX defined.
```

and stop. Do not create the file. Do not proceed to any further step.

### Step 4 — Pre-check entrypoint.py exists

Check whether `<entrypoint_file>` exists:

```bash
[ -f "<entrypoint_file>" ]
```

If it does not exist, emit:

```
ERROR: entrypoint.py not found at <entrypoint_file>. /rest-api-spec:init-rest-api requires the project's entrypoint.py to be in place — @error-handlers-integrator and @auth-integrator patch register_error_handler(fastapi_app) and register_auth(fastapi_app) calls into create_fastapi. entrypoint.py is created by @app-integrator during @rest-api-spec:code-generator; run that for your first resource before /rest-api-spec:init-rest-api.
```

and stop. Do not create the file. Do not proceed to any further step.

### Step 5 — Pre-check tests/ exists

Check whether `<tests_dir>` exists:

```bash
[ -d "<tests_dir>" ]
```

If it does not exist, emit:

```
ERROR: tests/ not found at <tests_dir>. /rest-api-spec:init-rest-api requires the tests package to be in place — @test-fixtures-preparer creates <tests_dir>/conftest.py with the API client and authentication fixtures. Run /init-domain (or /application-spec:init-application) before this skill.
```

and stop. Do not create the directory. Do not proceed to any further step.

### Step 6 — Resolve target locations

Invoke `spec-core:target-locations-finder` with the prompt `rest-api`. Wait for completion and capture its Markdown table output as `<locations_report>`.

If the agent reports any error, surface it as a single `ERROR: ...` line and stop. Do not print the agent's success confirmation lines.

### Step 7 — Create the base api package

Run sequentially via `Bash`. Create the directory if it does not already exist:

```bash
mkdir -p <api_pkg>
```

Do **not** create `<api_init_file>` here — its content (a minimal aggregator that satisfies `@auth-integrator`'s convention check) is rendered in Step 9, after the shared serializer modules have been copied so that the `from .serializers import *` line resolves.

### Step 8 — Install shared serializer modules

Invoke `rest-api-spec:serializers-copier` with prompt `<locations_report>`. Wait for completion.

This copies `error.py`, `configured_base_serializer.py`, and `json_utils.py` from the plugin's `modules/serializers/` reference into `<serializers_dir>/`, then (re)writes `<serializers_dir>/__init__.py` as a star-aggregator over the root-level modules on disk. After this step `ErrorSerializer` is importable from `<pkg>.api.serializers`, which is a prerequisite for both `@error-handlers-integrator` (Step 10) and `@auth-integrator` (Step 11).

If the agent reports any error, surface it as a single `ERROR: ...` line and stop.

### Step 9 — Seed the api package `__init__.py`

Check whether `<api_init_file>` already exists:

```bash
[ -f "<api_init_file>" ]
```

If it does not exist, write the file with exactly this content (the minimum that satisfies `@auth-integrator`'s `from .X import *` + `__all__ = X.__all__ + ...` aggregation convention):

```python
from .serializers import *

__all__ = serializers.__all__
```

The file ends with a single trailing newline. `@auth-integrator` (Step 11) additively patches this file to insert `from .auth import *` among the existing star-import lines and append `+ auth.__all__` to the `__all__` aggregation.

If the file already exists, **do not modify it** — its content is owned downstream and `@auth-integrator` only inserts (never replaces) the auth-related lines.

### Step 10 — Wire error handlers

Invoke `rest-api-spec:error-handlers-integrator` with prompt `<locations_report>`. Wait for completion.

This discovers domain exceptions in `<pkg>/domain/shared/exceptions.py` (and infrastructure exceptions in `<pkg>/infrastructure/exceptions.py` when present), renders `<api_pkg>/error_handlers.py` (always regenerated), and additively patches `<pkg>/entrypoint.py` to call `register_error_handler(fastapi_app)` inside `create_fastapi`. The rendered `error_handlers.py` exports `json_error_handler` and `register_error_handler`, both of which are prerequisites for the next step.

If the agent reports any error (most commonly: `<pkg>/domain/shared/exceptions.py` missing or `DomainException` not defined), surface it as a single `ERROR: ...` line and stop. Do not proceed to Step 11.

### Step 11 — Wire authentication

Invoke `rest-api-spec:auth-integrator` with prompt `<locations_report>`. Wait for completion.

This scaffolds the `application/auth/` subpackage (`AuthCommands` + `UserData`), renders `<api_pkg>/auth.py` from the auth-middleware skill template, patches `<api_pkg>/__init__.py` to re-export the auth module, registers a `Singleton(AuthCommands)` provider in `containers.py`, and patches `<pkg>/entrypoint.py` to call `register_auth(fastapi_app)` inside `create_fastapi`. Depends on `<api_pkg>/error_handlers.py` (Step 10), the `<serializers_dir>/` shared modules (Step 8), the seeded `<api_init_file>` (Step 9), and the user-provided `<api_pkg>/fastapi_auth.py` (which the agent verifies and aborts on if missing).

If the agent reports any error (most commonly: `<api_pkg>/fastapi_auth.py` missing or `Forbidden`/`Unauthorized` not defined in domain), surface it as a single `ERROR: ...` line and stop. Do not proceed to Step 12.

### Step 12 — Prepare test fixtures

Invoke `rest-api-spec:test-fixtures-preparer` with prompt `<locations_report>`. Wait for completion.

This ensures the root `<tests_dir>/conftest.py` defines the API client and authentication fixtures (`app`, `client`, `containers`, `token_payload`, `request_headers`) required by every REST API integration test. Append-only and idempotent.

If the agent reports any error, surface it as a single `ERROR: ...` line and stop.

### Step 13 — Report

Emit no output. Silent success.
