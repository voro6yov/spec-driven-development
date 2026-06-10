# Optional application-service return (`<X> | None`) → `204 No Content`

> **Status: IMPLEMENTED** (rest-api-spec 0.57.0, model-diagrams 0.5.0). All eight touchpoints
> below are done — the table grew one row (ops-serializers-implementer was a necessary 8th, since
> it dispatches `<resp_shape>` off the Table 4 sub-block and the prepended optional note would
> otherwise confuse it). The model-diagrams `diagram-conventions` suppression was also added.

## The idea

`stps-mappings`' `ruleset.commands.md` introduces a new return shape on an application
service method — **optional aggregate**:

```
%% internal
+add_mapping_rules(ruleset_id: str, mapping_rules: list[MappingRuleData], epoch_token: int) Ruleset | None
+add_mappings(ruleset_id: str, mappings: list[MappingData], epoch_token: int) Ruleset | None
+add_errors(ruleset_id: str, errors: list[InferenceError], epoch_token: int) Ruleset | None
```

Semantics (from the commands invariants): the method returns the aggregate on the happy
path and **`None`** when the operation is an *idempotent no-op* — the target ruleset was
concurrently deleted (e.g. by a `ProcessRemoved` while inference was in flight), so there is
nothing to persist. The write-back must **not** surface a `404` (which would make the
inference-side message handler retry forever); it must be a benign empty success.

**REST mapping:** when the service returns the aggregate → `200 OK` + serialized body; when
it returns `None` → **`204 No Content`** (empty body).

The user already hand-wrote a blockquote documenting this under Table 3 of the `internal`
surface in `ruleset.rest-api/spec.md`. Nothing in the plugin *produces* or *consumes* that
note — the generators are blind to the `| None` return. This note designs the support.

## Why this is genuinely new (not the existing 204 cases)

The plugin already emits `204` in two places, but both are **static** — the status is fixed
at generation time:

| Existing 204 case | Where | Why it's static |
|---|---|---|
| `DELETE /{id}` | `endpoints-implementer` §Status codes | DELETE always 204; no body ever |
| Ops method returning bare `None` | `response-fields-writer` Step 3o case 1 → `*No response body — returns 204 No Content.*` marker; `endpoints-implementer` reads it | the ops method *always* returns `None` |

The optional-aggregate case is a **runtime-conditional** status: the *same* endpoint returns
`200`+body or `204`+empty depending on the runtime value. The generated endpoint must branch
on the result. No existing template covers this.

It also produces a **404 vs 204 asymmetry that only the spec can disambiguate**: for the
*same* "id not found" input, an optional command (`add_mapping_rules`) returns `204`, while a
non-optional sibling (`update_mapping_rule`) raises `RulesetNotFound` → `404`. The generators
cannot tell these apart from path shape alone — they need the recorded return type.

## Key constraint: the signal must live in `spec.md`

Two independent reasons force the optional-return signal to be recorded in `spec.md` rather
than re-derived from the commands diagram by each code generator:

1. **`tests-implementer` is purely spec-driven.** It reads `spec.md` + the domain diagram +
   `conftest.py` — it never opens `<stem>.commands.md`. It cannot learn the 204-on-None
   behavior unless the spec records it. (By contrast `endpoints-implementer` *does* parse the
   commands diagram in its Step 3.6, but only as a non-gating cross-check.)
2. **Repo principle.** `spec.md` is the authoritative, human-reviewable contract; diagrams are
   secondary cross-checks (`endpoints-implementer` Step 3.6 is explicit: the commands-diagram
   parse "does not gate emission"). A load-bearing status-code decision must be visible in the
   spec, not hidden in a diagram a reviewer of `spec.md` never sees.

This rules out a diagram-only design (read `| None` straight from `<stem>.commands.md` in each
implementer). The projection diagram→spec must happen **once**, in a spec writer; every
implementer then reads the spec.

## Where in the spec: a Table 4 marker

`Table 4: Response Fields` is the response-shape table. Today it carries a sub-block per
**query** endpoint (Table 2) and per **ops** endpoint (Table 3o); **command** endpoints
(Table 3) have *no* Table 4 sub-block (their response is implicitly the `<Operation>Response`
serializer, id-only by convention). The ops-`None`→204 marker already lives here.

**Decision:** extend Table 4 to carry a sub-block for any command (Table 3) **or** ops
(Table 3o) endpoint whose application-service method returns `<X> | None`. The presence of the
marker *is* the machine signal; a non-optional command stays exactly as today (no sub-block).

Canonical marker (stable phrasing — downstream matches on the `*Optional response —` prefix +
the literal `204`, the same way `tests-implementer` matches the ops `*No response body —`
placeholder):

```
**Endpoint:** `POST /{id}/mapping-rules`

*Optional response — `204 No Content` when `RulesetCommands.add_mapping_rules` returns `None`; otherwise `200 OK` with the serialized `Ruleset` (per the Table 3 response serializer).*
```

- For a **command** endpoint: just the marker — no field table (commands never tabulate
  response fields; the 200 body is whatever `<Operation>Response` already produces).
- For an **ops** endpoint returning `<DTO> | None`: the normal resolved field table for the
  `<DTO>` 200 branch, **plus** a leading 204-on-None note (closes a latent gap — today
  `response-fields-writer` Step 3o would mis-dispatch a `Ruleset | None` ops return, matching
  neither the bare-`None` case nor the exact-aggregate case).
- `<SuccessStatus>` in the marker is the row's normal success status (`200 OK` for the
  add/update case; `201 Created` if the optional method is a factory `POST /`).

Why a marker and not a Table 3 column: Table 3 is parsed positionally by five agents
(`endpoints-implementer`, `command-serializers-implementer`, `tests-implementer`,
`endpoint-tables-writer`, the updates writer). A new column shifts every index — high blast
radius. A Table-4 sub-block is purely additive and matches the existing ops precedent.

## The generated endpoint (the crux)

```python
from fastapi import APIRouter, Depends, Response, status   # Response added to the group
...

@rulesets_router.post(
    "/{id}/mapping-rules",
    status_code=status.HTTP_200_OK,                         # declared default = the value branch
    openapi_extra={"visibility": Visibility.INTERNAL},
    response_model=AddMappingRulesResponse,                 # validates/documents the 200 body
    responses={status.HTTP_204_NO_CONTENT: {"description": "Ruleset no longer exists; idempotent no-op."}},
)
@inject
def add_mapping_rules(
    id: str,
    request: AddMappingRulesRequest,
    ruleset_commands: RulesetCommands = Depends(Provide[Containers.ruleset_commands]),
):
    result = ruleset_commands.add_mapping_rules(
        id,
        mapping_rules=[item.to_domain() for item in request.mapping_rules],
        epoch_token=request.epoch_token,
    )
    if result is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return AddMappingRulesResponse.from_domain(result)
```

Mechanics that matter:

- **`status_code=HTTP_200_OK` stays** as the decorator default (the value branch + OpenAPI
  primary status). `responses={204: …}` documents the alternate status in the OpenAPI schema.
- **`response_model` stays** non-optional. Returning a bare `fastapi.Response` instance
  **bypasses `response_model`** entirely (FastAPI sends it as-is), so the 204 branch is safe;
  the 200 branch returns the `from_domain(...)` object, which *is* validated.
- **Use `return Response(status_code=204)`, not** the inject-`response: Response` + mutate
  `.status_code` + `return None` form: returning `None` against a non-Optional `response_model`
  raises `ResponseValidationError`. The explicit-Response form is the correct one.
- Bind the call to a local `result`, branch, then wrap only the non-None branch with the
  existing `<Operation>Response.from_domain(...)`.
- Add `Response` to the `fastapi` import group.

This is the one shape no current skill template covers; everything else (path params, body,
`to_domain()` on nested fields, DI) is unchanged.

## Files to change (rest-api-spec)

| # | File | Change |
|---|---|---|
| 1 | `skills/endpoint-io-template/SKILL.md` | Document the new `*Optional response — … 204 …*` Table 4 marker beside the ops `*No response body*` placeholder. Update the "Table 4 filled per query + ops" framing to "… and per command/ops endpoint with an optional (`\| None`) return"; add to italic-placeholder rules + validation checklist. |
| 2 | `agents/response-fields-writer.md` | **New input:** read `<dir>/<stem>.commands.md`, partition command methods by surface (same machinery it already uses for queries/ops). **New Step 3-cmd:** for each Table 3 row whose return type — after stripping `list[...]`/wrappers — is `<AggregateRoot> \| None`, emit the marker sub-block; non-optional commands emit nothing. **Step 3o:** add the `<DTO> \| None` union case (field table + 204 note). Update the both-placeholder rule and the "Table 4 carries a sub-block per …" framing. |
| 3 | `agents/endpoints-implementer.md` | §Status codes: new row — "Table 3 / Table 3o row whose Table 4 sub-block carries the optional-204 marker → **dual-status**". New rendering rule "Optional-return (dual-status) endpoint": `result = <call>; if result is None: return Response(204); return <Op>Response.from_domain(result)`; keep `response_model`; add `responses={204: …}`; add `Response` to fastapi imports. Step 3.3: associate Table 4 sub-blocks with Table 3 rows too (today only Table 2 + 3o) and detect the marker. Fold ops `<X> \| None` into the same dual-status path. |
| 4 | `agents/tests-implementer.md` | Step 5 parse: bind `<resp_optional>` per command/ops row from its Table 4 sub-block. Scenario dispatch: every optional command/ops endpoint gets a **`__no_content`** scenario (asserts `HTTPStatus.NO_CONTENT`). For an **id-bearing / composite-key** endpoint it **replaces** the `__not_found` (404) scenario — GIVEN no aggregate in DB, call with a non-existent id/key + a valid body, assert 204 (deterministic per the contract). For a **factory `POST /`** it is **added** but emitted `@pytest.mark.skip(...)` (see Q2 decision). Keep `__success` and `__missing_required_field` in all cases. |
| 5 | `agents/command-serializers-implementer.md` | **No functional change** — the 200 branch still serializes the aggregate; the endpoint guards `None` before calling `from_domain`. Add a one-line note that optionality is handled at the endpoint layer so the serializer/response_model stay non-optional. |
| 6 | `agents/rest-api-updates-writer.md` | (Minor) classify a Table 4 delta where the optional-204 marker appears/disappears as an "Optional return added/removed" change touching the endpoint module + its test. The *dispatch* already routes correctly: a return-type edit is a commands-axis `methods` change → `response_fields_dirty` → `response-fields-writer` re-runs → marker refreshes. Only the human-facing classification needs the new delta type; can ship later. |
| 7 | `.claude-plugin/plugin.json` | Bump `version` (user-visible behavior change). |

## Cross-plugin notes (out of the user's immediate ask, but adjacent)

- **`model-diagrams:diagram-conventions`** — document that an application-service command/ops
  method may legitimately return `<Aggregate> | None` to mean "idempotent no-op → `204`", so
  `@diagram-reviewer` doesn't flag it as a finding. (Memory: the conventions skill is the
  single source of truth for what counts as canonical; the reviewer must defer to it.)
- **`application-spec`** — the method genuinely returns `Optional`; `commands-methods-writer`
  already records the verbatim return type, so the application layer is fine. Worth having
  `commands-tests-implementer` assert the missing-aggregate path returns `None` (the no-op),
  symmetric to the REST `__no_content` test. Secondary to the REST work.
- The user's **hand-written Table 3 blockquote** becomes redundant once the Table 4 marker is
  generated (the marker is the load-bearing signal). It can stay as human prose but isn't
  parsed.

## Rejected alternative

**Diagram-driven (no spec change):** read `| None` straight from `<stem>.commands.md` in
`endpoints-implementer` (which already parses it) and `tests-implementer`. Rejected because
`tests-implementer` doesn't read the commands diagram, and because a load-bearing status
decision invisible in `spec.md` violates the "spec is authoritative" principle. The projection
must be recorded once, in `spec.md`.

## Resolved decisions

**Q1 — 204 test name → `__no_content`.** The 204 idempotent-no-op scenario is
`test_<operation>__no_content`, asserting `HTTPStatus.NO_CONTENT`. Names the HTTP outcome;
distinct token in the scenario dispatch vocabulary (does not overload `__not_found`'s 404
meaning).

**Q2 — support boundary → full support, including factory `POST /`.** *Every* command/ops
endpoint whose method returns `<X> | None` is rendered dual-status, and *every* one gets a
`__no_content` test. The endpoint render is uniform — the 204 branch (`if result is None:
return Response(204)`) is added regardless of path shape, and the declared `status_code` stays
the row's normal success status (`200 OK`, or `201 Created` for a factory), so a factory simply
becomes **201-or-204**.

The test side forks on whether the endpoint has a *deterministic* None precondition:

- **id-bearing / composite-key endpoint** (`POST|PUT /{id}/…`, composite-key command, ops
  `POST /{id}/…`): the `__no_content` test is real and passing — a non-existent id/key + a
  valid body deterministically drives the service to return `None` (per the missing-target
  no-op contract). This **replaces** the `__not_found` (404) scenario.
- **factory `POST /`** (no id, no not-found precondition): the trigger under which a factory
  returns `None` is domain-specific and **cannot be derived mechanically** — a `__success`-shaped
  call would actually create the aggregate and return `201`, so a naive 204 assertion would fail
  out of the box. "Full support" therefore means the `__no_content` scaffold is still emitted,
  but marked `@pytest.mark.skip(reason="arrange the precondition under which <operation> returns
  None — cannot be derived from the spec")` with a `# TODO`, so it exists for the author to
  complete without reddening CI. (This is the one place "full support" degrades to a skipped
  scaffold; everywhere else the test passes as generated.) `__already_exists` is unaffected —
  it still seeds `<aggregate>_1` and asserts `409`, orthogonal to the optional branch.

`tests-implementer` distinguishes the two by the same predicate it already uses elsewhere:
`{id}` in path or a non-empty `<cmd_query_params>` ⇒ deterministic; factory `POST /` ⇒ skip-scaffold.

**Q3 — Table 3 prose → marker-only.** The Table 4 marker is the single generated signal (it is
both machine- and human-readable). `endpoint-tables-writer` does **not** emit a Table 3
blockquote. The hand-written blockquote currently in `ruleset.rest-api/spec.md` can be deleted;
nothing regenerates it, and keeping it risks drift with the marker. (Bonus: avoids the fragility
of a `>`-prose line living between Table 3 and Table 3o in endpoint-tables-writer's territory.)
