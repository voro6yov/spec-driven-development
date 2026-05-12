---
name: update-specs
description: Surgically updates the REST API resource spec (`spec.md`) after a domain diagram change — re-runs only the table writers whose owned table a domain delta touches (Tables 4/5/6), leaves Tables 1/2/3 byte-stable, and emits the REST API updates report. Consumes the domain `updates.md`; never re-diffs the diagram. Most domain changes are a no-op here. Invoke with: /rest-api-spec:update-specs <domain_diagram>
argument-hint: <domain_diagram>
allowed-tools: Read, Bash, Agent
---

You are a REST API spec **update** orchestrator. Given a domain diagram whose `<dir>/<stem>.domain/updates.md` report describes a change, refresh the existing `<dir>/<stem>.rest-api/spec.md` in place — re-run only the table writer(s) whose owned table the domain delta touches (`response-fields-writer` → Table 4, `request-fields-writer` → Table 5, `parameter-mapping-writer` → Table 6), leave every other table byte-stable, and emit `<dir>/<stem>.rest-api/updates.md`. Do not rerun the full `/rest-api-spec:generate-specs` pipeline, do not touch the diagram files, and do not ask for confirmation before writing.

This skill is the REST-API-side counterpart to `/update-specs` (domain), `/persistence-spec:update-specs`, and `/application-spec:update-specs`. Design rationale lives in `notes/spec-updater-approach.md`, `notes/update-types.md`, and `notes/updates-report.md`; the load-bearing ideas are **(a)** every section of `spec.md` is a pure snapshot (no append-only-log analog), **(b)** `spec.md` is one file owned table-by-table by five writers, and **(c)** a domain delta reaches *only* Tables 4/5/6, and only through nested-type / composite-query-param resolution against the domain diagram — so the surgical unit is "the dirty table writer(s)", and the median domain change leaves `spec.md` byte-identical and this skill early-exits.

This skill **does not** detect domain-level deltas — it consumes the `<dir>/<stem>.domain/updates.md` report that `domain-spec:updates-detector` (Step 0 of domain `/update-specs`, or an explicit prior invocation) already wrote. It never re-diffs the diagram and never invokes `domain-spec:updates-detector`.

This skill covers only the **domain-driven axis**. Changes that originate in `<stem>.commands.md` / `<stem>.queries.md` (the application-service diagrams) — an endpoint added/removed, a method signature changed, a surface added/removed/renamed, the resource's plural changed — are out of scope here and are *not* captured by `<stem>.domain/updates.md`; see *What this skill deliberately does not do* below.

## Output path convention

Per `rest-api-spec:naming-conventions`, given `<domain_diagram>` at `<dir>/<stem>.md`:

- `<dir>` = directory containing the diagrams.
- `<stem>` = the canonical aggregate stem (domain filename with `.md` stripped); must satisfy `^[a-z][a-z0-9-]*$`.
- `<plugin_dir>` = `<dir>/<stem>.rest-api` — the per-plugin folder for rest-api-spec.

| File | Role | Touched by |
|---|---|---|
| `<dir>/<stem>.domain/updates.md` | input — domain delta report (must already exist) | not modified |
| `<dir>/<stem>.commands.md` | input — hand-authored commands application-service diagram (must already exist) | not modified |
| `<dir>/<stem>.queries.md` | input — hand-authored queries application-service diagram (must already exist) | not modified |
| `<plugin_dir>/spec.md` | the resource spec being updated (must already exist) | `response-fields-writer` (Table 4) / `request-fields-writer` (Table 5) / `parameter-mapping-writer` (Table 6) — only the dirty one(s) |
| `<plugin_dir>/updates.md` | output — REST API delta report | `rest-api-updates-writer` |

`<domain_diagram>`, `<commands_diagram>`, and `<queries_diagram>` are read by the invoked agents; this orchestrator never modifies them. Every agent derives `<dir>` / `<stem>` from `$ARGUMENTS[0]` per `rest-api-spec:naming-conventions` — pass `$ARGUMENTS[0]` verbatim as the prompt to each.

This skill keeps no runtime state between agents. The updates writer recovers the pre-update spec via `git show HEAD:<spec_file>`, so there is nothing for the orchestrator to capture or hand along.

## Workflow

### Step 0 — Verify inputs

Derive `<dir>` and `<stem>` from `$ARGUMENTS[0]` per `rest-api-spec:naming-conventions`. `<stem>` must satisfy `^[a-z][a-z0-9-]*$`. Using `Bash` (`test -f`), each missing input is its own hard-fail with a one-line operator instruction:

- **0a.** If `<dir>/<stem>.domain/updates.md` is missing → hard-fail:

  ```
  ERROR: <dir>/<stem>.domain/updates.md not found. The REST API updater consumes the domain
  updates report; it is not the first-run pipeline. Run `/update-specs <domain_diagram>` (or
  `@updates-detector <domain_diagram>`) first, or run `/rest-api-spec:generate-specs <domain_diagram>`
  to regenerate the REST API spec from scratch.
  ```

- **0b.** If `<dir>/<stem>.rest-api/spec.md` is missing → hard-fail:

  ```
  ERROR: <dir>/<stem>.rest-api/spec.md not found. The REST API updater is not the first-run pipeline.
  Run `/rest-api-spec:generate-specs <domain_diagram>` to create the spec. (If the aggregate root was
  renamed, the spec now lives under a different stem — rename the diagrams and the `<stem>.rest-api/`
  folder, then run `/rest-api-spec:generate-specs`.)
  ```

- **0c.** If `<dir>/<stem>.commands.md` is missing → hard-fail:

  ```
  ERROR: <dir>/<stem>.commands.md not found. The commands application-service diagram is a required
  hand-authored input. Restore the file or run `/rest-api-spec:generate-specs <domain_diagram>`
  after authoring it.
  ```

- **0d.** If `<dir>/<stem>.queries.md` is missing → hard-fail:

  ```
  ERROR: <dir>/<stem>.queries.md not found. The queries application-service diagram is a required
  hand-authored input. Restore the file or run `/rest-api-spec:generate-specs <domain_diagram>`
  after authoring it.
  ```

Do not synthesize any of these files. Do not invoke any agent.

### Step 1 — Preflight

`Read` `<dir>/<stem>.domain/updates.md`. It is the orchestrator's single source of truth for the delta — do not re-derive anything from the diagram. Use `Bash` (`grep`) and `Read` to extract:

- **`degraded_baseline`** — whether the `## Summary` block contains a line beginning `_warning: HEAD `.
- **`stereotype_changed`** — class names listed under `## Class Lifecycle → Stereotype Changed` (one bullet per class; the exact bullet format is owned by `domain-spec:updates-report-template`). Empty when the heading is absent or its body is `_None._`-style.
- **`removed_classes`** — bullets under `## Class Lifecycle → Removed`, each `` - `ClassName` `<<Stereotype>>` ``. Capture `(class_name, stereotype)` per bullet.
- **`added_classes`** — bullets under `## Class Lifecycle → Added`, each `` - `ClassName` `<<Stereotype>>` `` (the `— <N> attributes, <N> methods` suffix is informational; ignore it). Capture `(class_name, stereotype)` per bullet.
- **`affected_categories`** — bullets under `## Affected Categories`, in the order they appear. The literal body `_None._` means empty.
- **`touched_data_types`** — the set of `<<TypedDict>>` / `<<Value Object>>` / `<<Command>>` class names that appear either as a `### <ClassName>` block under `## Per-Class Changes` (with at least one `**Members:**` bullet) or under `## Class Lifecycle → Added` / `→ Removed`. (Use the bullet's stereotype, where present, to filter; for a per-class block with no stereotype tag, fall back to whatever stereotype the same name carries elsewhere in the report, else include it conservatively.)
- **`removed_or_renamed_data_types`** — the subset of `touched_data_types` that appear under `## Class Lifecycle → Removed` (a rename is reported by `domain-spec:updates-detector` as `removed (old) + added (new)`, so the old name lands here).
- **`orphan_prose`** — whether `## Orphan Prose Changes` is present with a non-empty body (the synthetic `### Preamble` block counts). Used only to colour the no-op message — orphan prose, including a bounded-context `title:` rename, is byte-neutral for `spec.md` (the `<Resource>Commands` / `<Resource>Queries` class names come from the application-service diagrams, not the domain `title:`).

Then scan the two application-service diagrams for the *referenced-type set*. `Read` `<dir>/<stem>.commands.md` and `<dir>/<stem>.queries.md`; walk each `<Resource>Commands` / `<Resource>Queries` class body (tolerating `%% <name>` surface markers per `rest-api-spec:surface-markers` — they do not affect which method lines exist) and extract every PascalCase type token, after stripping `| None`, `list[...]`, `dict[..., ...]`, and `Literal[...]` wrappers:

- **`commands_referenced_types`** — every PascalCase token appearing as a *parameter* type on a public `<Resource>Commands` method.
- **`queries_referenced_types`** — every PascalCase token appearing as a *return* type or a *parameter* type on a public `<Resource>Queries` method.

These are the *direct* references. Transitive references (a referenced type whose field is itself a custom type that changed) are not computed here — `response-fields-writer` / `request-fields-writer` / `parameter-mapping-writer` resolve them recursively, and the conservative dispatch in Step 2 re-runs the relevant writer whenever *any* `data-structures` / `value-objects` change is present, so a missed transitive reference still gets picked up. (A *transitively*-referenced renamed/removed type that the Step-1 scan misses can still surface as a runtime writer abort in Step 3 — see *Runtime abort* there.)

Apply the gates below **in order** — they are the **hard-fail tier (Tier 1)** of the dispatch. The first one that fires terminates the workflow — later gates are not evaluated, and no agent runs.

#### 1a. Hard-fail: degraded baseline

If `degraded_baseline` is true:

```
ERROR: HEAD baseline is degraded (multiple or missing Mermaid blocks at HEAD per <stem>.domain/updates.md).
The surgical REST API updater cannot operate against a degraded baseline. Run
`/rest-api-spec:generate-specs <domain_diagram>` to regenerate the REST API spec from scratch.
```

#### 1b. Hard-fail: stereotype change

If `stereotype_changed` is non-empty:

```
ERROR: Class(es) <names> have stereotype changes in <stem>.domain/updates.md. A stereotype change moves a
class to a different pattern catalog (e.g. a value object becoming a child entity), so a referenced type is
no longer the kind of thing the REST spec assumed; this subsumes the aggregate-root case. Run
`/rest-api-spec:generate-specs <domain_diagram>` to regenerate from scratch.
```

Surface every offending name, not just the first.

#### 1c. Hard-fail: aggregate-root removal

If any bullet in `removed_classes` has stereotype `<<Aggregate Root>>`:

```
ERROR: Aggregate root `<ClassName>` is listed under `## Class Lifecycle → Removed` in
<stem>.domain/updates.md. The resource loses its anchor (Table 1's Resource name / Plural / Router prefix
and every Domain Ref in Tables 2/3). An aggregate-root rename — reported as `removed (old)` + `added (new)`
— also moves all three diagram filenames (`<stem>.md`, `<stem>.commands.md`, `<stem>.queries.md`) and the
`<stem>.rest-api/` folder: a coordinated multi-file rename the updater cannot perform. Rename the diagrams
and the `<stem>.rest-api/` folder, then run `/rest-api-spec:generate-specs <domain_diagram>`.
```

#### 1d. Abort-and-reconcile: a referenced data type was renamed or removed

If `removed_or_renamed_data_types ∩ (commands_referenced_types ∪ queries_referenced_types)` is non-empty:

```
ERROR: Data type(s) <names> were removed or renamed in <stem>.domain/updates.md but are still referenced
by a method return/parameter type in <stem>.commands.md / <stem>.queries.md. `response-fields-writer` /
`request-fields-writer` / `parameter-mapping-writer` would abort with `Cannot resolve …`. Reconcile the
commands/queries diagram — point the method's type token at the new name, or drop the reference — then
re-run `/rest-api-spec:update-specs <domain_diagram>`. (The rest of the spec is fine; this is not a
from-scratch rebuild.)
```

Surface every offending name. This is an **abort-and-reconcile**, not a full hard-fail — no writes, no `spec.md` change; the operator fixes the application-service diagram and re-runs *this* skill (not `generate-specs`).

### Step 2 — Dispatch tier

The Step-1 gates already covered the **hard-fail tier (Tier 1)**. This step picks between the **regen tier (Tier 2)** — re-run the dirty table writer(s) in Step 3 — and the **no-op tier (Tier 3)** — skip straight to the report. Compute three booleans from the values captured in Step 1:

```
data_or_vo_changed   = (set(affected_categories) & {"data-structures", "value-objects"}) != set()

response_fields_dirty   = data_or_vo_changed

parameter_mapping_dirty = data_or_vo_changed

request_fields_dirty    = data_or_vo_changed
                       or ("commands" in affected_categories
                           and ∃ name ∈ (touched_data_types ∩ commands_referenced_types)
                               with stereotype <<Command>>)
```

Rationale (the **conservative v1 rule**):

- A `data-structures` (`<<TypedDict>>`) or `value-objects` (`<<Value Object>>`) change anywhere re-runs all three table writers. It over-regenerates — re-runs a writer even when the changed type is purely internal to the aggregate and never surfaces in the REST spec, producing a byte-stable Table 4/5/6 modulo LLM drift — but it is correct without computing the domain diagram's type-reference graph, and the diff is small.
- A `commands` (the domain `<<Command>>` dataclass category — *not* the `<Resource>Commands` application service) change re-runs only `request-fields-writer`, and only when a changed `<<Command>>` dataclass is *directly* a command-method parameter type (`request-fields-writer` Step 4d accepts a `<<Command>>` as a nested request type). This keeps the common `commands`-fires case — an inferred-command rename with no Table 5 reference — a no-op.
- `domain-events`, `aggregates`, and `repositories-services` never reach the REST spec as a regen signal: domain events / domain services / repository finders are invisible to it; the only way `aggregates` matters is the root-identity hard-fail, already caught by 1b/1c. Domain prose (P1–P4) is byte-neutral here — no rest-api-spec writer consumes domain prose.

> **v2 optimization (not in this cut).** Narrow the dirty flags by intersecting `touched_data_types` (plus its transitive closure over the domain diagram's `<<Value Object>>` / `<<TypedDict>>` field types) against `queries_referenced_types` (for `response_fields_dirty` and the composite-query-param part of `parameter_mapping_dirty`) and `commands_referenced_types` (for `request_fields_dirty`). Skips a writer entirely when none of its referenced types changed, at the cost of a domain-diagram type-graph walk in the orchestrator. Defer until the no-drift diff matters more than the implementation cost.

#### Tier 3 — No-op

If none of `response_fields_dirty` / `request_fields_dirty` / `parameter_mapping_dirty` is set:

1. Skip Step 3.
2. Still run Step 4 (emit `updates.md`) — so a `<stem>.rest-api/updates.md` exists after every successful run (the future `/rest-api-spec:update-code` consumer's contract is "a report always exists"); the writer sees the working-tree spec unchanged versus HEAD and emits an all-`_no changes_` report.
3. Still run Step 5 (operator one-liner).

Tier 3 fires for any of: `affected_categories` empty; `affected_categories ⊆ {domain-events, commands (with no changed `<<Command>>` directly a command-method param type), aggregates, repositories-services}`; a pure prose change (P1–P4); a bounded-context `title:` rename in `## Orphan Prose Changes → Preamble` and nothing else; a domain-only `tenant_id` flip on the aggregate root (REST-spec multi-tenancy is an application-diagram property). Tier 3 is hit far more often here than in any other downstream updater — the domain diagram's contribution to the REST spec is so narrow that the median domain change is a flat no-op.

If at least one flag is true, proceed to Step 3.

### Step 3 — Table-writer regen (sequential)

For each dirty writer, **in this order**, invoke it via the `Agent` tool with prompt `$ARGUMENTS[0]` (the domain diagram path) and wait for completion before invoking the next:

1. `rest-api-spec:response-fields-writer` — if `response_fields_dirty`.
2. `rest-api-spec:request-fields-writer` — if `request_fields_dirty`.
3. `rest-api-spec:parameter-mapping-writer` — if `parameter_mapping_dirty`.

Each writer parses `<stem>.commands.md` / `<stem>.queries.md` / `<stem>.md` fresh, locates its owned table inside `spec.md`, and rewrites it in place (`Edit`, anchored on the table's H3 heading + body, per-Surface section). The writers do not read `<stem>.domain/updates.md`; they have no idempotency contract beyond "output is a function of inputs" — re-running on identical diagrams produces byte-identical output modulo LLM nondeterminism.

**Why sequential, not parallel.** All three edit the single `spec.md` in place. Running them concurrently risks one writer's `Edit` landing on a stale view of the file. (`/application-spec:update-specs` can fan its two sides out in parallel because `commands.specs.md` and `queries.specs.md` are separate files; here they aren't.) Sequence them response → request → parameter-mapping — the same order `/rest-api-spec:generate-specs` uses.

The cost accepted: when a dirty writer runs, it rewrites its *whole* table — every endpoint's sub-block in Table 4, not just the one whose nested type changed — so endpoints whose referenced types are unchanged get re-emitted (byte-stable modulo LLM drift). This is the same "LLM drift is `git diff` noise, not a correctness failure" contract the persistence-spec and application-spec writers already operate under. The tables the dirty writers *don't* own — Table 1, Tables 2/3, and whichever of Tables 4/5/6 isn't dirty — are not touched at all.

#### Runtime abort

A table writer can abort at runtime even though gate 1d passed — specifically when a renamed/removed type is referenced *transitively* (a referenced type's field, or that field's field, …) rather than directly, so the Step-1 scan didn't catch it. The writer surfaces `Cannot resolve response DTO <Name>` / `Cannot resolve nested type <Name>` / `Cannot resolve query-param composite <Type>` and produces no edit. If any writer reports a failure, abort the workflow and emit a single `ERROR:` line repeating its message verbatim, appending: ` Reconcile the commands/queries diagram so the type resolves, then re-run /rest-api-spec:update-specs.` Do not run downstream agents. Earlier-sequenced writers may have already edited `spec.md`; those edits are left in place (the orchestrator does not roll back) and a subsequent successful run re-runs *all* dirty writers from the top (idempotent), overwriting whatever partial edits are on disk.

### Step 4 — Emit the REST API updates report

Invoke `rest-api-spec:rest-api-updates-writer` via the `Agent` tool with prompt `$ARGUMENTS[0]`. It diffs the working-tree `spec.md` against `git HEAD`, classifies the Table 1 / per-surface Table 2–6 deltas, derives the `## Affected Artifacts` table mechanically, reads the sibling `<stem>.domain/updates.md` only as a `Source delta` enrichment source (missing is non-fatal), and writes `<dir>/<stem>.rest-api/updates.md` (always — even on the Tier-3 no-op, where every section after `## Summary` renders `_no changes_` and the Affected Artifacts table has no data rows). The writer recovers everything it needs from disk + git + the sibling domain report; the orchestrator passes nothing else.

This step runs **on every successful run**, including the Tier-3 no-op early-exit. If the writer reports a failure, abort and emit a single `ERROR:` line repeating its message. `spec.md` is already in its final post-update state by this point — re-running the orchestrator (or just the writer agent standalone) idempotently produces the report.

### Step 5 — Report

Print one summary line. The shape depends on the dispatch outcome:

- **Tier 3 no-op**:
  - If `orphan_prose` is true: `No REST API spec updates required. Orphan prose changes detected — review <stem>.domain/updates.md (a bounded-context title rename, if any, is byte-neutral for the REST spec). Emitted <stem>.rest-api/updates.md.`
  - Otherwise: `No REST API spec updates required (no REST-relevant domain changes). Emitted <stem>.rest-api/updates.md.`

- **At least one writer ran**:
  ```
  Updated <stem>.rest-api/spec.md (<regen_clause>) and emitted <stem>.rest-api/updates.md.
  ```
  Where `<regen_clause>` names exactly the tables whose writer ran, in Table-number order. Under the v1 dispatch that is either `regenerated Tables 4, 5 & 6` (a `data-structures` / `value-objects` change — all three dirty) or `regenerated Table 5` (a `commands`-only change with a `<<Command>>` command-method parameter type). (A future v2 dispatch could narrow this to other combinations — e.g. `regenerated Table 4` or `regenerated Tables 4 & 6` — in which case the clause still names exactly the writers that ran.)

Do not emit additional commentary — each invoked agent already printed its own per-step report.

## Failure semantics

- Every step that aborts emits exactly one `ERROR:` line and exits the workflow. Do not chain further agents on top of a failed step.
- The orchestrator does not roll back partial writes. **Re-running `/rest-api-spec:update-specs` after fixing the trigger is the supported recovery path** — every step is idempotent on stable inputs:
  - **Step 3** writers regenerate their owned table wholesale from current diagrams on every call (output stable modulo LLM nondeterminism).
  - **Step 4** (`rest-api-updates-writer`) is a pure HEAD-vs-working-tree diff and overwrites `updates.md` from scratch.
- Recovery routes by failure kind:
  - **Step 0 missing-input cases (0a–0d)** — no writes; operator runs `/update-specs` / `@updates-detector` for the missing domain report, restores the missing input diagram, or runs `/rest-api-spec:generate-specs`.
  - **Step 1 hard-fail (1a–1c)** — no writes; operator runs `/rest-api-spec:generate-specs` (after renaming the diagrams + folder for the aggregate-root case).
  - **Step 1 abort-and-reconcile (1d)** — no writes; operator updates the offending type token in `<stem>.commands.md` / `<stem>.queries.md`, then re-runs `/rest-api-spec:update-specs`.
  - **Step 3 runtime abort** — earlier-sequenced writers may have already edited `spec.md`; the aborting writer made no edit. Operator reconciles the commands/queries diagram per the writer's error and re-runs; the next run re-runs *all* dirty writers from the top (idempotent), overwriting partial edits.
  - **Step 4 failure** — rare; `spec.md` is already correct. Operator re-runs; Step 3 re-runs harmlessly (byte-stable) and Step 4 retries.

## Idempotency

Re-running `/rest-api-spec:update-specs` against unchanged inputs (working-tree spec unchanged versus HEAD, same domain `updates.md`) produces:

- A no-op early-exit through Step 2 when `affected_categories` is empty enough to leave all three dirty flags false.
- Otherwise, byte-identical tables and updates report — modulo LLM prose drift in the re-run table writers (`git diff` noise, not a correctness failure). The tables the dirty writers don't own (Table 1, Tables 2/3, the non-dirty member of Tables 4/5/6) are not touched and stay byte-identical.

There are no sentinel comments. Unlike persistence-spec's `<!-- appended-from updates-hash:<hash> -->` (which guards the append-only migrations log), every table here is a snapshot — re-running over an unchanged domain `updates.md` simply reproduces the same content.

## What this skill deliberately does not do

- It does not regenerate `<stem>.rest-api/spec.md` end-to-end — that is `/rest-api-spec:generate-specs`. In particular it never re-invokes `resource-spec-initializer` (Table 1) or `endpoint-tables-writer` (Tables 1/2/3) — those are pure functions of the application-service diagrams + the `<<Aggregate Root>>` class name, and the only domain delta that touches the `<<Aggregate Root>>` name (a root rename / removal / stereotype-demotion) is a hard-fail (1b/1c), not a regen.
- It does not re-diff `<domain_diagram>` and does not invoke `domain-spec:updates-detector` — the domain `updates.md` is expected on disk before this skill runs.
- It does not touch the diagram files (`<stem>.md`, `<stem>.commands.md`, `<stem>.queries.md`) or any Artifacts index — those siblings are linked from the original `/rest-api-spec:generate-specs` run.
- It does not handle commands-/queries-diagram changes — an endpoint added/removed (Tables 2/3), a method signature changed (parameters, return type → Tables 4/5/6), a surface added/removed/renamed (Table 1's Surfaces row + the `## Surface:` section set + orphaned sections), the resource's plural changed (Table 1). Those originate in the *application-service* diagrams, are not captured by `<stem>.domain/updates.md`, and require either a future `application-spec:updates-detector` analog (a shared detector that diffs `<stem>.commands.md` / `<stem>.queries.md` and feeds both the application updater and this one) or a fresh `/rest-api-spec:generate-specs` run.
- It does not handle aggregate-root removal/rename (which also cascades to the diagram filenames and the `<stem>.rest-api/` folder), stereotype changes, or a degraded baseline — those route to `/rest-api-spec:generate-specs` via the Step 1 hard-fails (1a–1c).
- It does not act on a domain-only multi-tenancy flip — REST-spec `tenant_id` handling (dropped from the body in Table 5, excluded from the query-parameter list in Table 4, sourced as `Auth context` in Table 6) is keyed off the *app-service method signatures* (`tenant_id: str` parameters), not the domain root. A domain-only `tenant_id` flip is byte-neutral here; it takes effect only once the commands/queries diagrams' method signatures are updated (a commands/queries-diagram-axis change). Deliberate divergence from persistence-spec; matches application-spec.
- It does not act on a bounded-context `title:` rename — the `<Resource>Commands` / `<Resource>Queries` class names come from the application-service diagrams' class nodes, and Table 1's Resource name comes from the `<<Aggregate Root>>` *class name*. A domain-`title:` change is byte-neutral. Tier 3 no-op.
- It does not pre-check the *transitive* analog of gate 1d (a renamed/removed type referenced only via another referenced type's field). The Step-1 scan catches the direct case; a transitive one surfaces as a runtime writer abort in Step 3 and is routed the same way ("reconcile the commands/queries diagram, then re-run").
- It does not track the Shared domain types registry (`Pagination`, `PaginatedResultMetadataInfo`, `ResultSetInfo`) — those are hard-coded in `response-fields-writer` / `request-fields-writer` / `parameter-mapping-writer`. Changes to them are plugin-source changes, not domain-diagram changes; they never appear in `updates.md` and are picked up only by re-running `/rest-api-spec:generate-specs` after a plugin upgrade.
- It does not preserve hand-edits inside a regenerated table — the writer contract is that the spec is regenerated from the diagrams, not curated. The Tables 4–6 `**Nested:**` sub-tables and `**Query Parameters:**` Descriptions are emitted mechanically; a regen of the owning table discards any hand enrichment of *that* table (the other tables are byte-stable). The blast radius is small (a domain-only change re-runs at most three writers, each rewriting one table) but non-zero.
- It does not auto-update generated REST API code (the per-surface serializer modules `api/serializers/<surface>/`, endpoint modules `api/endpoints/<surface>/`, the FastAPI app wiring `entrypoint.py` / `constants.py` / the aggregator `__init__.py` files / `api/auth.py`, the test fixtures `tests/conftest.py`, the integration tests) — that is the future `/rest-api-spec:update-code` skill, which consumes the `<stem>.rest-api/updates.md` this skill emits.
- It does not chain into domain `/update-specs` — it is independently invocable; the opt-in chained-step integration (Step 11 of domain `/update-specs`, alongside the persistence Step 9 and application Step 10 chains, gated on `<stem>.rest-api/spec.md` presence) is a separate, later change.
