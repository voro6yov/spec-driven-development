---
name: generate-code
description: Implements the REST API layer for a resource from its `<domain_stem>.rest-api.md` spec sibling. Resolves target locations once, scaffolds the per-surface package layout, implements query and command serializers in sequence (so they don't race on shared aggregators), implements endpoint modules, and finally wires everything into the FastAPI app. Invoke with: /rest-api-spec:generate-code <domain_diagram>
argument-hint: <domain_diagram>
allowed-tools: Agent
---

You are a REST API implementation orchestrator. Implement the REST API layer for the resource whose domain diagram is at `$ARGUMENTS[0]`. The skill consumes the `<domain_stem>.rest-api.md` sibling artifact that `/rest-api-spec:generate-specs` produces — it does not regenerate it.

## Sibling file convention

For the domain diagram at `<dir>/<domain_stem>.md`, derive `<domain_stem>` by stripping the trailing `.md`. The sibling artifact consumed here is:

| Diagram | Sibling artifact | Bound to |
|---|---|---|
| `$ARGUMENTS[0]` | `<domain_stem>.rest-api.md` | `<rest_api_spec_file>` |

If the artifact is missing the downstream agents abort with their own one-sentence errors — this orchestrator does not pre-validate.

## Workflow

### Step 1 — Compute sibling path

Derive `<rest_api_spec_file>` by string substitution on the domain diagram argument: take `$ARGUMENTS[0]` and replace the trailing `.md` with `.rest-api.md`. If the argument does not end in `.md`, fall back to appending `.rest-api.md` unchanged.

Do not shell-expand — substitute this string directly when constructing prompts in subsequent steps. It is passed verbatim to downstream agents.

### Step 2 — Find target locations

Invoke `rest-api-spec:target-locations-finder` with an empty prompt. Wait for completion.

Capture the agent's full Markdown table output verbatim as `<locations_report_text>`. This text is the locations argument passed to every downstream agent in Steps 3–7. Pass it verbatim — do not trim, summarize, or reformat it.

### Step 3 — Scaffold the per-surface package layout

Invoke `rest-api-spec:rest-api-scaffolder` with prompt `<locations_report_text> <rest_api_spec_file>`. Wait for completion.

This emits the `endpoints/` and `serializers/` sub-packages, the per-surface sub-directories under each, the shared serializer modules (`error.py`, `configured_base_serializer.py`, `json_utils.py`) at `serializers/` root, and the root `serializers/__init__.py` aggregator. Subsequent steps assume these stubs exist on disk.

If the scaffolder aborts, propagate the failure and stop — do not proceed to Step 4.

### Step 4 — Implement query serializers

Invoke `rest-api-spec:query-serializers-implementer` with prompt `<locations_report_text> <rest_api_spec_file>`. Wait for completion.

This emits one Python module per query endpoint under `api/serializers/<surface>/<operation>.py`, generates the shared `result_set.py` and `paginated_result_metadata.py` if any endpoint is paginated, and (re)writes the per-surface `__init__.py` plus the root `serializers/__init__.py` as star-aggregators.

If the implementer aborts, propagate the failure and stop — do not proceed to Step 5.

### Step 5 — Implement command serializers

Invoke `rest-api-spec:command-serializers-implementer` with prompt `<locations_report_text> <rest_api_spec_file>`. Wait for completion.

This emits one Python module per command endpoint under `api/serializers/<surface>/<operation>.py` and (re)writes the per-surface `__init__.py` plus the root `serializers/__init__.py`.

**Do not run Steps 4 and 5 in parallel.** Both agents (re)write the same per-surface and root aggregator `__init__.py` files based on a disk scan; running them concurrently risks a write race where one agent's aggregator clobbers the other's freshly-written modules. Sequencing query → command guarantees the final aggregators reflect both sets.

If the implementer aborts, propagate the failure and stop — do not proceed to Step 6.

### Step 6 — Implement endpoints

Invoke `rest-api-spec:endpoints-implementer` with prompt `<locations_report_text> <rest_api_spec_file>`. Wait for completion.

This emits one router module per surface at `api/endpoints/<surface>/<plural>.py` containing the surface's `<plural>_router` plus one endpoint function per Table 2 / Table 3 row. The endpoints reference the serializer classes emitted in Steps 4–5 via the per-surface aggregator imports.

If the implementer aborts, propagate the failure and stop — do not proceed to Step 7.

### Step 7 — Integrate into the FastAPI app

Invoke `rest-api-spec:app-integrator` with prompt `<locations_report_text> <rest_api_spec_file>`. Wait for completion.

This regenerates the per-surface `endpoints/<surface>/__init__.py` aggregators and the top-level `endpoints/__init__.py` from a disk scan, patch-merges the API routing constants into `<pkg>/constants.py`, creates `<pkg>/entrypoint.py` (or additively patches `create_fastapi`'s `include_router` lines if the file already exists), and — when an `internal` surface is present — additively patches `<pkg>/api/auth.py` to skip auth on internal paths.

If the integrator aborts, propagate the failure and stop.

### Step 8 — Report

Emit a single completion line:

```
REST API code generation complete for <rest_api_spec_file>.
```

Substitute `<rest_api_spec_file>` with the value bound in Step 1.
