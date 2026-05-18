---
name: generate-code
description: Implements the REST API layer for a resource from its `<dir>/<stem>.rest-api/spec.md` resource spec sibling. Resolves target locations once, scaffolds the per-surface package layout, implements query and command serializers in sequence (so they don't race on shared aggregators), implements endpoint modules, and finally wires everything into the FastAPI app. Invoke with: /rest-api-spec:generate-code <domain_diagram>
argument-hint: <domain_diagram>
allowed-tools: Agent, Skill
---

You are a REST API implementation orchestrator. Implement the REST API layer for the resource whose domain diagram is at `$ARGUMENTS[0]`. The skill consumes the resource spec sibling that `/rest-api-spec:generate-specs` produces — it does not regenerate it. Spec-file paths are derived internally per `rest-api-spec:naming-conventions`; downstream agents accept only `<domain_diagram>` plus `<locations_report_text>` and derive the rest themselves.

## Sibling file convention

Per `rest-api-spec:naming-conventions`. From `$ARGUMENTS[0]` (the domain diagram) at `<dir>/<stem>.md`:

- `<dir>` = directory containing the domain diagram
- `<stem>` = domain filename with the `.md` suffix stripped
- `<plugin_dir>` = `<dir>/<stem>.rest-api` — the per-plugin folder for rest-api-spec
- Resource input spec = `<plugin_dir>/spec.md` (derived inside each agent)

If the resource input spec is missing the downstream agents abort with their own one-sentence errors — this orchestrator does not pre-validate.

## Workflow

### Step 1 — Find target locations

Invoke `rest-api-spec:target-locations-finder` with an empty prompt. Wait for completion.

Capture the agent's full Markdown table output verbatim as `<locations_report_text>`. This text is the locations argument passed to every downstream agent in Steps 2–7. Pass it verbatim — do not trim, summarize, or reformat it.

Test fixtures (`app`, `client`, `containers`, `token_payload`, `request_headers`) in `<tests_dir>/conftest.py` are project-wide and assumed already in place — `/rest-api-spec:init-rest-api` owns that step. If you have not yet run `/rest-api-spec:init-rest-api` for this project, do so before invoking this skill; otherwise `@tests-implementer` (Step 7) will produce test modules whose required fixtures are not defined.

### Step 2 — Scaffold the per-surface package layout

Invoke `rest-api-spec:rest-api-scaffolder` with prompt `$ARGUMENTS[0] <locations_report_text>`. Wait for completion.

This emits the `endpoints/` and `serializers/` sub-packages and the per-surface sub-directories under each. Subsequent steps assume these stubs exist on disk. The shared serializer modules (`error.py`, `configured_base_serializer.py`, `json_utils.py`) and the root `serializers/__init__.py` aggregator are **not** owned by this step — they are project-wide dependencies installed once by `/rest-api-spec:init-rest-api`. Run that skill before this one if it has not yet been run for this project.

If the scaffolder aborts, propagate the failure and stop — do not proceed to Step 3.

### Step 3 — Implement query serializers

Invoke `rest-api-spec:query-serializers-implementer` with prompt `$ARGUMENTS[0] <locations_report_text>`. Wait for completion.

This emits one Python module per query endpoint under `api/serializers/<surface>/<aggregate>/<operation>.py`, generates the shared `result_set.py` and `paginated_result_metadata.py` if any endpoint is paginated, and (re)writes the per-aggregate `__init__.py` as a star-aggregator.

If the implementer aborts, propagate the failure and stop — do not proceed to Step 4.

### Step 4 — Implement command serializers

Invoke `rest-api-spec:command-serializers-implementer` with prompt `$ARGUMENTS[0] <locations_report_text>`. Wait for completion.

This emits one Python module per command endpoint under `api/serializers/<surface>/<aggregate>/<operation>.py` (with `to_domain()` on nested sub-serializers whose target type is a domain TypedDict) and (re)writes the per-aggregate `__init__.py`.

**Do not run Steps 3 and 4 in parallel.** Both agents (re)write the same per-aggregate `__init__.py` based on a disk scan; running them concurrently risks a write race where one agent's aggregator clobbers the other's freshly-written modules. Sequencing query → command guarantees the final aggregator reflects both sets.

If the implementer aborts, propagate the failure and stop — do not proceed to Step 5.

### Step 5 — Implement endpoints

Invoke `rest-api-spec:endpoints-implementer` with prompt `$ARGUMENTS[0] <locations_report_text>`. Wait for completion.

This emits one router module per surface at `api/endpoints/<surface>/<plural>.py` containing the surface's `<plural>_router` plus one endpoint function per Table 2 / Table 3 row. The endpoints reference the serializer classes emitted in Steps 3–4 via the per-aggregate aggregator imports (`...serializers.<surface>.<aggregate>`).

If the implementer aborts, propagate the failure and stop — do not proceed to Step 6.

### Step 6 — Integrate into the FastAPI app

Invoke `rest-api-spec:app-integrator` with prompt `$ARGUMENTS[0] <locations_report_text>`. Wait for completion.

This regenerates the per-surface `endpoints/<surface>/__init__.py` aggregators and the top-level `endpoints/__init__.py` from a disk scan, patch-merges the API routing constants into `<pkg>/constants.py`, creates `<pkg>/entrypoint.py` (or additively patches `create_fastapi`'s `include_router` lines if the file already exists), and — when an `internal` surface is present — additively patches `<pkg>/api/auth.py` to skip auth on internal paths.

If the integrator aborts, propagate the failure and stop.

### Step 7 — Implement REST API tests

Invoke `rest-api-spec:tests-implementer` with prompt `$ARGUMENTS[0] <locations_report_text>`. Wait for completion.

This writes one integration test module per surface at `<tests_dir>/integration/<resource>/test_<plural>_<surface>_api.py`, with success / not_found / already_exists / missing_required_field scenarios dispatched per endpoint shape. Append-only and idempotent. Relies on the API client + authentication fixtures (`app`, `client`, `containers`, `token_payload`, `request_headers`) installed once per project by `/rest-api-spec:init-rest-api`.

If the implementer aborts, propagate the failure and stop.

### Step 8 — Report

Emit a single completion line:

```
REST API code generation complete for $ARGUMENTS[0].
```
