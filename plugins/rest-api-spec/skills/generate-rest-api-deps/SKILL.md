---
name: generate-rest-api-deps
description: Bootstraps the project-wide REST API dependencies that every per-resource code-generation run assumes are already in place — copies the shared serializer modules into `<api_pkg>/serializers/`, wires exception-to-HTTP error handlers, and wires JWT-style request authentication. Idempotent. Run once per project (not per resource). Invoke with `/rest-api-spec:generate-rest-api-deps`.
argument-hint:
allowed-tools: Agent
---

You are a REST API dependency-bootstrap orchestrator. Install the project-wide pieces of the REST API layer that are independent of any individual resource: the shared serializer modules, the FastAPI exception handlers, and the request-authentication middleware. The skill is idempotent — re-running it is safe and converges on the same end state. It does **not** scaffold per-resource endpoints, serializers, or test files; that work belongs to `/rest-api-spec:generate-code`.

This skill takes no arguments.

## Workflow

### Step 1 — Find target locations

Invoke `rest-api-spec:target-locations-finder` with an empty prompt. Wait for completion.

Capture the agent's full Markdown table output verbatim as `<locations_report_text>`. This text is the locations argument passed to every downstream agent in Steps 2–4. Pass it verbatim — do not trim, summarize, or reformat it.

### Step 2 — Install shared serializer modules

Invoke `rest-api-spec:serializers-copier` with prompt `<locations_report_text>`. Wait for completion.

This copies `error.py`, `configured_base_serializer.py`, and `json_utils.py` from the plugin's `modules/serializers/` reference into `<api_pkg>/serializers/`, then (re)writes `<api_pkg>/serializers/__init__.py` as a star-aggregator over the root-level modules on disk. After this step `ErrorSerializer` is importable from `<pkg>.api.serializers`.

If the copier aborts, propagate the failure and stop — do not proceed to Step 3.

### Step 3 — Wire error handlers

Invoke `rest-api-spec:error-handlers-integrator` with prompt `<locations_report_text>`. Wait for completion.

This discovers domain exceptions in `<pkg>/domain/shared/exceptions.py` (and infrastructure exceptions in `<pkg>/infrastructure/exceptions.py` when present), renders `<api_pkg>/error_handlers.py` (always regenerated), and additively patches `<pkg>/entrypoint.py` to call `register_error_handler(fastapi_app)` inside `create_fastapi`. The rendered `error_handlers.py` exports `json_error_handler` and `register_error_handler`, both of which are prerequisites for the next step.

If the integrator aborts, propagate the failure and stop — do not proceed to Step 4.

### Step 4 — Wire authentication

Invoke `rest-api-spec:auth-integrator` with prompt `<locations_report_text>`. Wait for completion.

This scaffolds the `application/auth/` subpackage (`AuthCommands` + `UserData`), renders `<api_pkg>/auth.py` from the auth-middleware skill template, patches `<api_pkg>/__init__.py` to re-export the auth module, registers a `Singleton(AuthCommands)` provider in `containers.py`, and patches `<pkg>/entrypoint.py` to call `register_auth(fastapi_app)` inside `create_fastapi`. Depends on `<api_pkg>/error_handlers.py` (Step 3), `<api_pkg>/serializers/` shared modules (Step 2), and the user-provided `<api_pkg>/fastapi_auth.py` (which the agent verifies and aborts on if missing).

If the integrator aborts, propagate the failure and stop.

### Step 5 — Report

Emit a single completion line:

```
REST API dependencies installed.
```
