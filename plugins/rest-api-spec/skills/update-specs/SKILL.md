---
name: update-specs
description: "Surgically updates the REST API resource spec after a domain, commands-diagram, or queries-diagram change. Invoke with: /rest-api-spec:update-specs <domain_diagram>"
argument-hint: <domain_diagram>
allowed-tools: Read, Bash, Agent
---

You are a REST API spec **update** orchestrator. Given a domain diagram and its sibling commands/queries application-service diagrams, refresh the existing `<dir>/<stem>.rest-api/spec.md` in place — invoke the two app-service-axis update detectors, dispatch on the union of the three delta reports, re-run only the table writer(s) whose owned table is dirty (`resource-spec-initializer` → Table 1, `endpoint-tables-writer` → Tables 2/3, `response-fields-writer` → Table 4, `request-fields-writer` → Table 5, `parameter-mapping-writer` → Table 6), leave every other table byte-stable, and emit `<dir>/<stem>.rest-api/updates.md`. Do not rerun the full `@rest-api-spec:specs-generator` pipeline, do not touch the diagram files, and do not ask for confirmation before writing.

This skill is the REST-API-side counterpart to `/update-specs` (domain), `/persistence-spec:update-specs`, and `/application-spec:update-specs`. Design rationale lives in `notes/spec-updater-approach.md`, `notes/update-types.md`, `notes/updates-report.md`, and `notes/commands-queries-integration-approach.md`; the load-bearing ideas are **(a)** every section of `spec.md` is a pure snapshot (no append-only-log analog), **(b)** `spec.md` is one file owned table-by-table by five writers, and **(c)** the four trigger axes (domain, commands-diagram, queries-diagram, ops-diagram) reach different tables — domain reaches only Tables 4/5/6, while the app-service axes (commands/queries/ops) can reach Tables 1, 2/3/3o, 4, 5, 6 — so the surgical unit is "the dirty table writer(s)" of the unioned axis triggers.

The orchestrator consumes four update reports — one per axis — and unions their dispatch signals:

- **Domain axis** — `<dir>/<stem>.domain/updates.md`, produced by `domain-spec:updates-detector` (expected on disk; not invoked here).
- **Commands-diagram axis** — `<dir>/<stem>.application/commands-updates.md`, produced by `application-spec:commands-updates-detector` (invoked at Step 0 below).
- **Queries-diagram axis** — `<dir>/<stem>.application/queries-updates.md`, produced by `application-spec:queries-updates-detector` (invoked at Step 0 below).
- **Ops-diagram axis** — `<dir>/<stem>.application/ops-updates.md`, produced by `application-spec:ops-updates-detector` (invoked at Step 0 below). Every public ops method is a REST action endpoint (Table 3o), so an ops method add/remove/signature change or an ops surface-marker change reaches Tables 3o + 4/5/6 exactly as a commands/queries `methods` / `surface-markers` change reaches Tables 2/3 + 4/5/6. The ops report is one aggregate-wide file; schema owned by `spec-core:update-reports` (ops schema).

The orchestrator never re-diffs any diagram itself.

## Output path convention

Per `spec-core:naming-conventions`, given `<domain_diagram>` at `<dir>/<stem>.md`:

- `<dir>` = directory containing the diagrams.
- `<stem>` = the canonical aggregate stem (domain filename with `.md` stripped); must satisfy `^[a-z][a-z0-9-]*$`.
- `<plugin_dir>` = `<dir>/<stem>.rest-api` — the per-plugin folder for rest-api-spec.

The two app-service-axis detector reports live under `<dir>/<stem>.application/` (the application-spec plugin's per-aggregate folder). This cross-plugin path is intentional — the reports are owned by application-spec and shared across the application-spec, rest-api-spec, and messaging-spec consumers. See `spec-core:naming-conventions` and `notes/commands-queries-integration-approach.md` for the convention.

| File | Role | Touched by |
|---|---|---|
| `<dir>/<stem>.domain/updates.md` | input — domain delta report (must already exist) | not modified |
| `<dir>/<stem>.commands.md` | input — hand-authored commands application-service diagram (must already exist) | not modified |
| `<dir>/<stem>.queries.md` | input — hand-authored queries application-service diagram (must already exist) | not modified |
| `<dir>/<stem>.application/commands-updates.md` | input — commands-diagram delta report | produced by `application-spec:commands-updates-detector` at Step 0 |
| `<dir>/<stem>.application/queries-updates.md` | input — queries-diagram delta report | produced by `application-spec:queries-updates-detector` at Step 0 |
| `<dir>/<stem>.application/ops-updates.md` | input — ops-diagram delta report (one aggregate-wide report) | produced by `application-spec:ops-updates-detector` at Step 0 |
| `<plugin_dir>/spec.md` | the resource spec being updated (must already exist) | `resource-spec-initializer` (Table 1) / `endpoint-tables-writer` (Tables 2/3/3o) / `response-fields-writer` (Table 4) / `request-fields-writer` (Table 5) / `parameter-mapping-writer` (Table 6) — only the dirty one(s) |
| `<plugin_dir>/updates.md` | output — REST API delta report | `rest-api-updates-writer` |

`<domain_diagram>`, `<commands_diagram>`, and `<queries_diagram>` are read by the invoked agents; this orchestrator never modifies them. Every agent derives `<dir>` / `<stem>` from `$ARGUMENTS[0]` per `spec-core:naming-conventions` — pass `$ARGUMENTS[0]` verbatim as the prompt to each.

This skill keeps no runtime state between agents. The updates writer recovers the pre-update spec via `git show HEAD:<spec_file>`, so there is nothing for the orchestrator to capture or hand along.

## Workflow

### Step 0 — Verify inputs and produce the app-service-axis reports

Derive `<dir>` and `<stem>` from `$ARGUMENTS[0]` per `spec-core:naming-conventions`. `<stem>` must satisfy `^[a-z][a-z0-9-]*$`. Using `Bash` (`test -f`), verify the input files in this order:

- **0a.** If `<dir>/<stem>.domain/updates.md` is missing → hard-fail:

  ```
  ERROR: <dir>/<stem>.domain/updates.md not found. The REST API updater consumes the domain
  updates report; it is not the first-run pipeline. Run `/update-specs <domain_diagram>` (or
  `@updates-detector <domain_diagram>`) first, or run `@rest-api-spec:specs-generator <domain_diagram>`
  to regenerate the REST API spec from scratch.
  ```

- **0b.** If `<dir>/<stem>.rest-api/spec.md` is missing → hard-fail:

  ```
  ERROR: <dir>/<stem>.rest-api/spec.md not found. The REST API updater is not the first-run pipeline.
  Run `@rest-api-spec:specs-generator <domain_diagram>` to create the spec. (If the aggregate root was
  renamed, the spec now lives under a different stem — rename the diagrams and the `<stem>.rest-api/`
  folder, then run `@rest-api-spec:specs-generator`.)
  ```

- **0c.** If `<dir>/<stem>.commands.md` is missing → hard-fail:

  ```
  ERROR: <dir>/<stem>.commands.md not found. The commands application-service diagram is a required
  hand-authored input. Restore the file or run `@rest-api-spec:specs-generator <domain_diagram>`
  after authoring it.
  ```

- **0d.** If `<dir>/<stem>.queries.md` is missing → hard-fail:

  ```
  ERROR: <dir>/<stem>.queries.md not found. The queries application-service diagram is a required
  hand-authored input. Restore the file or run `@rest-api-spec:specs-generator <domain_diagram>`
  after authoring it.
  ```

Do not synthesize any of these files.

#### 0g. Invoke the two app-service-axis detectors in parallel (skipped when `--detectors-fresh` is set)

**Cascade-mode shortcut.** If `$ARGUMENTS` contains the literal token `--detectors-fresh` (the `/spec-core:update-specs` orchestrator passes it as the second positional arg when it runs the rest-api/messaging wave after the application wave, whose Step 0g already produced both commands/queries reports), the application-spec detector reports are already on disk and byte-stable. In that case:

1. Verify presence with `Bash`:
   ```
   test -f "<dir>/<stem>.application/commands-updates.md" && test -f "<dir>/<stem>.application/queries-updates.md"
   ```
   If either file is missing, hard-fail:
   ```
   ERROR: --detectors-fresh was passed but <missing-report-path> does not exist. The caller is
   contractually required to produce both <stem>.application/commands-updates.md and
   <stem>.application/queries-updates.md before invoking /rest-api-spec:update-specs in cascade
   mode. Drop the --detectors-fresh flag to let this skill produce the reports itself, or run
   `/spec-core:update-specs <domain_diagram>` (which runs the application wave first, then this
   skill with the flag) — or `/application-spec:update-specs <domain_diagram>` to produce them.
   ```
2. Skip the detector invocation below and proceed directly to Step 1.

Standalone invocations (without `--detectors-fresh`) take the default path below.

**Default path.** After 0a–0d pass, fan out the two detectors in a single message so they run concurrently. Pass `$ARGUMENTS[0]` (the domain diagram path) as the prompt to each — the detectors derive their own sibling diagrams via `spec-core:naming-conventions`.

- `application-spec:commands-updates-detector` with prompt `$ARGUMENTS[0]`.
- `application-spec:queries-updates-detector` with prompt `$ARGUMENTS[0]`.

Each detector writes its own report (`<dir>/<stem>.application/commands-updates.md`, `<dir>/<stem>.application/queries-updates.md`) or hard-fails with an `ERROR:` line. The detectors share `<dir>/<stem>.application/` only — both use `mkdir -p` idempotently, so the parallel pattern is safe.

If either detector hard-fails, abort the orchestrator with that detector's `ERROR:` line repeated verbatim. The other detector's output (if it completed) is left on disk for the next run; no rollback is performed. The same `@rest-api-spec:specs-generator <domain_diagram>` recovery path the detectors themselves direct to applies here.

Wait for both detectors to return successfully before proceeding to the ops detector below.

#### 0g-ops. Invoke the ops-diagram detector (always — even under `--detectors-fresh`)

Invoke `application-spec:ops-updates-detector` with prompt `$ARGUMENTS[0]`. **This runs on both the default and the cascade (`--detectors-fresh`) paths**: `--detectors-fresh` is the application-spec orchestrator's promise that it produced the *commands/queries* axis reports — it does **not** produce the ops report, so this skill produces it here regardless. The detector fast-paths on a combined-digest match when no ops diagram changed and is a true no-op (writes `_None_`) when the aggregate has zero ops diagrams. It writes `<dir>/<stem>.application/ops-updates.md` or hard-fails with an `ERROR:` line; on hard-fail, abort with that line verbatim. Wait for it to return before proceeding to Step 1.

### Step 1 — Preflight (per-axis-scoped)

`Read` all three reports — `<dir>/<stem>.domain/updates.md`, `<dir>/<stem>.application/commands-updates.md`, `<dir>/<stem>.application/queries-updates.md`. They are the orchestrator's single source of truth for dispatch — do not re-derive any structural signal from any diagram. Use `Bash` (`grep`) and `Read` to extract, per axis:

**Domain axis** (from `<stem>.domain/updates.md`):

- **`domain.degraded_baseline`** — whether the `## Summary` block contains a line beginning `_warning: HEAD `.
- **`domain.stereotype_changed`** — class names listed under `## Class Lifecycle → Stereotype Changed` (one bullet per class; the exact bullet format is owned by `spec-core:update-reports` (domain schema)). Empty when the heading is absent or its body is `_None._`-style.
- **`domain.removed_classes`** — bullets under `## Class Lifecycle → Removed`, each `` - `ClassName` `<<Stereotype>>` ``. Capture `(class_name, stereotype)` per bullet.
- **`domain.added_classes`** — bullets under `## Class Lifecycle → Added`, each `` - `ClassName` `<<Stereotype>>` `` (the `— <N> attributes, <N> methods` suffix is informational; ignore it). Capture `(class_name, stereotype)` per bullet.
- **`domain.affected_categories`** — bullets under `## Affected Categories`, in the order they appear. The literal body `_None._` means empty.
- **`domain.touched_data_types`** — the set of `<<TypedDict>>` / `<<Value Object>>` / `<<Command>>` class names that appear either as a `### <ClassName>` block under `## Per-Class Changes` (with at least one `**Members:**` bullet) or under `## Class Lifecycle → Added` / `→ Removed`. (Use the bullet's stereotype, where present, to filter; for a per-class block with no stereotype tag, fall back to whatever stereotype the same name carries elsewhere in the report, else include it conservatively.)
- **`domain.removed_or_renamed_data_types`** — the subset of `domain.touched_data_types` that appear under `## Class Lifecycle → Removed` (a rename is reported by `domain-spec:updates-detector` as `removed (old) + added (new)`, so the old name lands here).
- **`domain.orphan_prose`** — whether `## Orphan Prose Changes` is present with a non-empty body (the synthetic `### Preamble` block counts). Used only to colour the no-op message — orphan prose, including a bounded-context `title:` rename, is byte-neutral for `spec.md`.

**Commands-diagram axis** (from `<dir>/<stem>.application/commands-updates.md`):

- **`commands.degraded_baseline`** — whether the `## Summary` block contains a line beginning `_warning: HEAD `.
- **`commands.affected_categories`** — bullets under `## Affected Categories`, in the order they appear. The vocabulary is owned by `spec-core:update-reports` (application-axis schema). The literal body `_None._` means empty.

**Queries-diagram axis** (from `<dir>/<stem>.application/queries-updates.md`):

- **`queries.degraded_baseline`** — whether the `## Summary` block contains a line beginning `_warning: HEAD `.
- **`queries.affected_categories`** — bullets under `## Affected Categories`. The literal body `_None._` means empty.

**Ops-diagram axis** (from `<dir>/<stem>.application/ops-updates.md`; schema owned by `spec-core:update-reports` (ops schema)). The ops report aggregates per-service `## Service:` blocks, but for REST dispatch only the **aggregate-wide** `## Affected Categories` footer and the degraded warning matter:

- **`ops.degraded_baseline`** — whether the `## Summary` block contains a line beginning `_warning: HEAD ` (a degraded ops diagram baseline).
- **`ops.affected_categories`** — bullets under `## Affected Categories`. The literal body `_None._` means empty (zero ops diagrams, or no ops diagram changed). The only categories that drive the REST spec are `methods` (an ops method added / removed / signature-changed → Table 3o rows + Tables 4/5/6) and `surface-markers` (ops method moved between surfaces → per-surface section set). The others (`dependencies`, `raised-exceptions`, `external-interfaces`, `messaging-markers`) are ignored.

Then scan the two application-service diagrams **and every ops diagram** for the *referenced-type set* (used by domain-axis gate 1.dom.d). `Read` `<dir>/<stem>.commands.md`, `<dir>/<stem>.queries.md`, and every `<dir>/<stem>.ops.*.md`; walk each `<Resource>Commands` / `<Resource>Queries` / ops class body (tolerating `%% <name>` surface markers) and extract every PascalCase type token, after stripping `| None`, `list[...]`, `dict[..., ...]`, and `Literal[...]` wrappers:

- **`commands_referenced_types`** — every PascalCase token appearing as a *parameter* type on a public `<Resource>Commands` method.
- **`queries_referenced_types`** — every PascalCase token appearing as a *return* type or a *parameter* type on a public `<Resource>Queries` method.
- **`ops_referenced_types`** — every PascalCase token appearing as a *return* type or a *parameter* type on a public ops method (ops endpoints serialize free return types and accept body params, so both sides are REST-referenced).

These are the *direct* references. Transitive references (a referenced type whose field is itself a custom type that changed) are not computed here — `response-fields-writer` / `request-fields-writer` / `parameter-mapping-writer` resolve them recursively, and the conservative dispatch in Step 2 re-runs the relevant writer whenever *any* `data-structures` / `value-objects` change is present, so a missed transitive reference still gets picked up. (A *transitively*-referenced renamed/removed type that the Step-1 scan misses can still surface as a runtime writer abort in Step 3 — see *Abort-and-reconcile (runtime)* there.)

The structural hard-fails the app-service-axis detectors themselves enforce (anchor missing/renamed, multi-anchor, stereotype change inside the app-service diagram) never reach the orchestrator — the detector aborts at Step 0 and the orchestrator surfaces its `ERROR:` verbatim. The orchestrator only sees a `_warning:_` on an app-service axis when HEAD was degraded.

Apply the gates below per axis. Each gate sets a per-axis disable flag (`domain_axis_disabled`, `commands_axis_disabled`, `queries_axis_disabled`, `ops_axis_disabled`) and emits a `WARNING:` line describing what was skipped; the run continues if any other axis is still enabled. Only the aggregated 1.all gate aborts the orchestrator.

#### 1.dom — Domain-axis gates

Each gate **disables only the domain axis** and emits a `WARNING:` (not `ERROR:`). Evaluate in order; only the first matching gate fires per run.

| Gate | Trigger | Action |
|---|---|---|
| 1.dom.a | `domain.degraded_baseline` true | Set `domain_axis_disabled = true`; emit `WARNING: domain axis disabled — HEAD baseline is degraded (multiple or missing Mermaid blocks at HEAD per <stem>.domain/updates.md). The surgical REST API updater cannot operate against a degraded baseline. Run @rest-api-spec:specs-generator <domain_diagram> to regenerate the domain-driven half from scratch.` |
| 1.dom.b | `domain.stereotype_changed` non-empty | Set `domain_axis_disabled = true`; emit `WARNING: domain axis disabled — class(es) <names> have stereotype changes in <stem>.domain/updates.md. A stereotype change moves a class to a different pattern catalog (e.g. a value object becoming a child entity), so a referenced type is no longer the kind of thing the REST spec assumed; this subsumes the aggregate-root case. Run @rest-api-spec:specs-generator <domain_diagram> to regenerate from scratch.` (surface every offending name) |
| 1.dom.c | Any bullet in `domain.removed_classes` has stereotype `<<Aggregate Root>>` | Set `domain_axis_disabled = true`; emit `WARNING: domain axis disabled — aggregate root <ClassName> is listed under Class Lifecycle → Removed in <stem>.domain/updates.md. The resource loses its anchor (Table 1's Resource name / Plural / Router prefix and every Domain Ref in Tables 2/3). An aggregate-root rename — reported as removed (old) + added (new) — also moves all three diagram filenames (<stem>.md, <stem>.commands.md, <stem>.queries.md) and the <stem>.rest-api/ folder: a coordinated multi-file rename the updater cannot perform. Rename the diagrams and the <stem>.rest-api/ folder, then run @rest-api-spec:specs-generator <domain_diagram>.` |
| 1.dom.d | `domain.removed_or_renamed_data_types ∩ (commands_referenced_types ∪ queries_referenced_types ∪ ops_referenced_types)` non-empty | Set `domain_axis_disabled = true`; emit `WARNING: domain axis disabled — data type(s) <names> were removed or renamed in <stem>.domain/updates.md but are still referenced by a method return/parameter type in <stem>.commands.md / <stem>.queries.md / a <stem>.ops.*.md. response-fields-writer / request-fields-writer / parameter-mapping-writer would abort (a query DTO) or degrade to a TODO (an ops return). Reconcile the offending diagram — point the method's type token at the new name, or drop the reference — then re-run /rest-api-spec:update-specs <domain_diagram>. (The rest of the spec is fine; this is not a from-scratch rebuild.)` (surface every offending name) |

Only one of 1.dom.a–1.dom.d fires per run (whichever is first); evaluate in order and stop at the first match. Unlike the previous design where 1.dom.d aborted the orchestrator wholesale, it now only disables the domain axis — the commands/queries-axis dispatch can still proceed if those axes have triggers.

#### 1.cmd — Commands-axis gates

Each gate **disables only the commands axis** and emits a `WARNING:`.

| Gate | Trigger | Action |
|---|---|---|
| 1.cmd.a | `commands.degraded_baseline` true | Set `commands_axis_disabled = true`; emit `WARNING: commands-diagram axis disabled — HEAD baseline is degraded (multiple or missing Mermaid blocks at HEAD per <stem>.application/commands-updates.md). Commands-diagram-driven dispatch is skipped for this run.` |

(The commands detector itself hard-fails on stereotype change, anchor rename, multi-anchor — those never reach the orchestrator. The orchestrator only sees a `_warning:_` if HEAD was degraded.)

#### 1.qry — Queries-axis gates

Each gate **disables only the queries axis** and emits a `WARNING:`.

| Gate | Trigger | Action |
|---|---|---|
| 1.qry.a | `queries.degraded_baseline` true | Set `queries_axis_disabled = true`; emit `WARNING: queries-diagram axis disabled — HEAD baseline is degraded (multiple or missing Mermaid blocks at HEAD per <stem>.application/queries-updates.md). Queries-diagram-driven dispatch is skipped for this run.` |

#### 1.ops — Ops-axis gates

Each gate **disables only the ops axis** and emits a `WARNING:`.

| Gate | Trigger | Action |
|---|---|---|
| 1.ops.a | `ops.degraded_baseline` true | Set `ops_axis_disabled = true`; emit `WARNING: ops-diagram axis disabled — an ops diagram's HEAD baseline is degraded (multiple or missing Mermaid blocks at HEAD per <stem>.application/ops-updates.md). Ops-diagram-driven dispatch is skipped for this run.` |

(The ops detector itself hard-fails on an ops service-class rename or multi-anchor — those never reach the orchestrator. When the aggregate has zero ops diagrams the ops report is a `_None._` no-op and this gate never fires.)

#### 1.all — Total-abort gate

If `domain_axis_disabled` AND `commands_axis_disabled` AND `queries_axis_disabled` AND `ops_axis_disabled` are all true, abort the orchestrator with:

```
ERROR: all four input axes are disabled by preflight gates (see WARNING lines above). The orchestrator
cannot regenerate any table. Resolve the underlying conditions or run @rest-api-spec:specs-generator
<domain_diagram> to rebuild the REST API spec from scratch.
```

No writes; no downstream agents are invoked.

### Step 2 — Dispatch tier (four-way union)

Compute the per-writer dirty flags from the values captured in Step 1, treating disabled axes as contributing the empty set.

#### Domain-axis contribution (existing rules, axis-gated)

```
data_or_vo_changed = (set(domain.affected_categories) & {"data-structures", "value-objects"}) ≠ ∅

domain_response_fields_dirty   = false if domain_axis_disabled else data_or_vo_changed
domain_parameter_mapping_dirty = false if domain_axis_disabled else data_or_vo_changed
domain_request_fields_dirty    = false if domain_axis_disabled else (
    data_or_vo_changed
    or ("commands" in domain.affected_categories
        and ∃ name ∈ (domain.touched_data_types ∩ commands_referenced_types) with stereotype <<Command>>)
)
```

Rationale (the **conservative v1 rule** on the domain axis, retained verbatim from the prior design):

- A `data-structures` (`<<TypedDict>>`) or `value-objects` (`<<Value Object>>`) change anywhere re-runs all three of the Tables 4/5/6 writers. It over-regenerates — re-runs a writer even when the changed type is purely internal to the aggregate and never surfaces in the REST spec, producing a byte-stable table modulo LLM drift — but it is correct without computing the domain diagram's type-reference graph, and the diff is small.
- A `commands` (the domain `<<Command>>` dataclass category — *not* the `<Resource>Commands` application service) change re-runs only `request-fields-writer`, and only when a changed `<<Command>>` dataclass is *directly* a command-method parameter type. This keeps the common `commands`-fires case — an inferred-command rename with no Table 5 reference — a no-op.
- `domain-events`, `aggregates`, and `repositories-services` never reach the REST spec as a regen signal on the domain axis: domain events / domain services / repository finders are invisible to it; the only way `aggregates` matters is the root-identity hard-fail, already caught by 1.dom.b / 1.dom.c. Domain prose (P1–P4) is byte-neutral here — no rest-api-spec writer consumes domain prose.

#### App-service-axis contributions (new)

```
commands_axis_triggers = ∅ if commands_axis_disabled else
    set(commands.affected_categories) & {"methods", "surface-markers"}

queries_axis_triggers  = ∅ if queries_axis_disabled else
    set(queries.affected_categories)  & {"methods", "surface-markers"}

ops_axis_triggers      = ∅ if ops_axis_disabled else
    set(ops.affected_categories)      & {"methods", "surface-markers"}

app_service_triggers = commands_axis_triggers ∪ queries_axis_triggers ∪ ops_axis_triggers
```

The ops axis contributes the same two trigger categories as commands/queries: an ops `methods` change adds/removes/re-signatures a Table 3o row (and its Tables 4/5/6 entries); an ops `surface-markers` change relocates an ops endpoint between surfaces (and may add/drop an ops-only surface, which changes Table 1's `Surfaces` row). Because `endpoint-tables-writer` owns Tables 2 **and** 3o, and the Tables 4/5/6 writers process ops endpoints, folding `ops_axis_triggers` into `app_service_triggers` re-runs exactly the right writers with no new dirty flag.

The other app-service-axis categories (`dependencies`, `raised-exceptions`, `external-interfaces`, `external-domain-events`, `messaging-markers`) never reach the REST spec — they drive `/application-spec:update-specs` and `/messaging-spec:update-specs` instead, and this orchestrator silently ignores them (no contribution to any dirty flag, no log line).

#### Per-writer dirty flags

```
table_1_dirty            = ("surface-markers" in app_service_triggers)
                           # Table 1's `Surfaces` row reflects the union of marker sets across both diagrams

tables_2_3_dirty         = ("methods" in app_service_triggers)
                        or ("surface-markers" in app_service_triggers)
                           # endpoint inventory (Tables 2, 3, AND 3o) + per-surface section set
                           # endpoint-tables-writer owns Table 3o, so this flag also re-runs ops endpoints

response_fields_dirty    = domain_response_fields_dirty
                        or ("methods" in app_service_triggers)
                        or ("surface-markers" in app_service_triggers)

request_fields_dirty     = domain_request_fields_dirty
                        or ("methods" in app_service_triggers)
                        or ("surface-markers" in app_service_triggers)

parameter_mapping_dirty  = domain_parameter_mapping_dirty
                        or ("methods" in app_service_triggers)
                        or ("surface-markers" in app_service_triggers)
```

Per-category mapping to REST writers (cross-reference `notes/commands-queries-integration-approach.md` § "Step 2 — Dispatch tier" for the full table):

| Category | Source axis | Drives |
|---|---|---|
| `methods` | commands | `endpoint-tables-writer` (Table 3 add/remove rows); Tables 4/5/6 writers (refresh affected endpoint) |
| `methods` | queries | `endpoint-tables-writer` (Table 2 add/remove rows); Tables 4/5/6 writers (refresh affected endpoint) |
| `methods` | ops | `endpoint-tables-writer` (Table 3o add/remove rows); Tables 4/5/6 writers (refresh affected ops endpoint) |
| `surface-markers` | any | `resource-spec-initializer` (Table 1 `Surfaces` row); `endpoint-tables-writer` (materialize / drop `## Surface:` sections; relocate endpoints between surfaces); Tables 4/5/6 writers (per-surface scoping) |

**Why `surface-markers` fans out to nearly every writer.** A surface added (S1) materializes a brand-new `## Surface: <name>` section in `spec.md` — every table in that section (Tables 2/3 + per-endpoint Tables 4/5/6) must be filled. A surface removed (S2) symmetrically drops the section. A method moved between surfaces (S3) relocates its row in Tables 2/3 *and* its per-endpoint Tables 4/5/6 entries. This is by design: writer ownership of `## Surface: <name>` sections is monolithic — when a surface appears or disappears, all surface-scoped writers run.

#### Tier 3 — No-op

If none of `table_1_dirty` / `tables_2_3_dirty` / `response_fields_dirty` / `request_fields_dirty` / `parameter_mapping_dirty` is set:

1. Skip Step 3.
2. Still run Step 4 (emit `updates.md`) — so a `<stem>.rest-api/updates.md` exists after every successful run (the `/update-code` consumer's contract is "a report always exists"); the writer sees the working-tree spec unchanged versus HEAD and emits an all-`_no changes_` report.
3. Still run Step 5 (operator one-liner).

Tier 3 fires for any of: every axis empty enough to leave all five dirty flags false; a pure prose change (P1–P4) on the domain axis; a bounded-context `title:` rename in `## Orphan Prose Changes → Preamble` and nothing else; a domain-only `tenant_id` flip on the aggregate root (REST-spec multi-tenancy is an application-diagram property); app-service-axis reports whose `affected_categories` contain only `dependencies` / `raised-exceptions` / `external-interfaces` / `external-domain-events` / `messaging-markers`.

If at least one flag is true, proceed to Step 3.

### Step 3 — Per-writer regen (sequential, expanded repertoire)

For each dirty writer, **in this order**, invoke it via the `Agent` tool with prompt `$ARGUMENTS[0]` (the domain diagram path) and wait for completion before invoking the next:

| Order | Writer | When | Owns |
|---|---|---|---|
| 1 | `rest-api-spec:resource-spec-initializer` | `table_1_dirty` | Table 1 `Surfaces` row; per-surface `## Surface:` H2 headings (materialization / removal) |
| 2 | `rest-api-spec:endpoint-tables-writer` | `tables_2_3_dirty` | Tables 2 (Query Endpoints) + 3 (Command Endpoints) + 3o (Ops Endpoints) per surface |
| 3 | `rest-api-spec:response-fields-writer` | `response_fields_dirty` | Table 4 (Response Fields) per surface per endpoint |
| 4 | `rest-api-spec:request-fields-writer` | `request_fields_dirty` | Table 5 (Request Fields) per surface per endpoint |
| 5 | `rest-api-spec:parameter-mapping-writer` | `parameter_mapping_dirty` | Table 6 (Parameter Mapping) per surface per endpoint |

Each writer parses `<stem>.commands.md` / `<stem>.queries.md` / `<stem>.md` fresh, locates its owned table inside `spec.md`, and rewrites it in place (`Edit`, anchored on the table's heading + body, per-Surface section). The writers do not read any `updates.md`; they have no per-axis dispatch — re-running on identical diagrams produces byte-identical output modulo LLM nondeterminism. `resource-spec-initializer` and `endpoint-tables-writer` are explicitly idempotent on stable inputs (existing Table 1 is preserved; existing per-surface Tables 2/3 are replaced in place).

**Why sequential, not parallel.** All five writers edit the single `spec.md` in place — running them concurrently risks one writer's `Edit` landing on a stale view of the file. (`/application-spec:update-specs` can fan its two sides out in parallel because `commands.specs.md` and `queries.specs.md` are separate files; here they aren't.) Additionally, `endpoint-tables-writer` must run before the Tables 4/5/6 writers because the latter scope per-endpoint and need the freshly written Tables 2/3 to know which endpoints exist; `resource-spec-initializer` must run before `endpoint-tables-writer` because the per-surface `## Surface:` sections it materializes are where `endpoint-tables-writer` writes Tables 2/3. Sequence them initializer → endpoint-tables → response → request → parameter-mapping, the same order `@rest-api-spec:specs-generator` uses.

The cost accepted: when a dirty writer runs, it rewrites its *whole* table — every endpoint's sub-block in Table 4, not just the one whose nested type changed — so endpoints whose referenced types are unchanged get re-emitted (byte-stable modulo LLM drift). This is the same "LLM drift is `git diff` noise, not a correctness failure" contract the persistence-spec and application-spec writers already operate under. The tables the dirty writers *don't* own are not touched at all.

#### Abort-and-reconcile (runtime)

A table writer can abort at runtime even though gate 1.dom.d passed — specifically when a renamed/removed type is referenced *transitively* (a referenced type's field, or that field's field, …) rather than directly, so the Step-1 scan didn't catch it. The Tables 4/5/6 writers surface `Cannot resolve response DTO <Name>` / `Cannot resolve nested type <Name>` / `Cannot resolve query-param composite <Type>` and produce no edit.

The new writers can also abort at runtime — `resource-spec-initializer` may abort on a surface marker name that's not a valid kebab-case identifier or on a malformed Table 1 `Resource name` derivation; `endpoint-tables-writer` may abort on a method signature its parser can't tokenize. The orchestrator surfaces those aborts verbatim per the same pattern.

If any writer reports a failure, abort the workflow and emit a single `ERROR:` line repeating its message verbatim, appending: ` Reconcile the offending diagram so the writer can resolve every reference, then re-run /rest-api-spec:update-specs.` Do not run downstream agents. Earlier-sequenced writers may have already edited `spec.md`; those edits are left in place (the orchestrator does not roll back) and a subsequent successful run re-runs *all* dirty writers from the top (idempotent), overwriting whatever partial edits are on disk.

### Step 4 — Emit the REST API updates report

Invoke `rest-api-spec:rest-api-updates-writer` via the `Agent` tool with prompt `$ARGUMENTS[0]`. It diffs the working-tree `spec.md` against `git HEAD`, classifies the Table 1 / per-surface Table 2–6 deltas, derives the `## Affected Artifacts` table mechanically, reads the sibling `<stem>.domain/updates.md` only as a `Source delta` enrichment source (missing is non-fatal), and writes `<dir>/<stem>.rest-api/updates.md` (always — even on the Tier-3 no-op, where every section after `## Summary` renders `_no changes_` and the Affected Artifacts table has no data rows). The writer recovers everything it needs from disk + git + the sibling domain report; the orchestrator passes nothing else.

> *Follow-up:* the updates writer currently reads only `<stem>.domain/updates.md` for `Source delta` attribution. Extending it to also read `<stem>.application/{commands,queries}-updates.md` for app-service-axis attribution is a v2 enhancement — not blocking for this integration. See `notes/commands-queries-integration-approach.md` § "Open questions".

This step runs **on every successful run**, including the Tier-3 no-op early-exit. If the writer reports a failure, abort and emit a single `ERROR:` line repeating its message. `spec.md` is already in its final post-update state by this point — re-running the orchestrator (or just the writer agent standalone) idempotently produces the report.

### Step 5 — Report

Print one summary line. The shape depends on the dispatch outcome.

Build `<axis_summary>` first — a comma-separated list (in canonical order: `domain`, `commands-diagram`, `queries-diagram`, `ops-diagram`) of axes that contributed at least one trigger to any dirty flag. An axis whose contribution was the empty set (either disabled, or its triggers all resolved to empty) does not appear in `<axis_summary>`. Use ` + ` (space-plus-space) as the separator (e.g. `domain + ops-diagram`).

- **Tier 3 no-op**:
  - If `domain.orphan_prose` is true: `No REST API spec updates required. Orphan prose changes detected — review <stem>.domain/updates.md (a bounded-context title rename, if any, is byte-neutral for the REST spec). Emitted <stem>.rest-api/updates.md.`
  - Otherwise: `No REST API spec updates required (no REST-relevant changes on any axis). Emitted <stem>.rest-api/updates.md.`

- **At least one writer ran**:
  ```
  Updated <stem>.rest-api/spec.md (<regen_clause>; triggers: <axis_summary>) and emitted <stem>.rest-api/updates.md.
  ```
  Where `<regen_clause>` names exactly the tables whose writer ran, in writer-order. Examples:
  - `regenerated Tables 4, 5 & 6` (domain-only data-structures/value-objects change — pre-integration behaviour)
  - `regenerated Table 5` (domain-only commands change with a `<<Command>>` command-method parameter type)
  - `regenerated Tables 2/3 + Tables 4, 5 & 6` (commands- or queries-axis `methods` change)
  - `regenerated Table 1 + Tables 2/3 + Tables 4, 5 & 6` (commands- or queries-axis `surface-markers` change)

If any preflight axis was disabled (Step 1.dom / 1.cmd / 1.qry fired), the `WARNING:` line(s) for those gates are emitted before the summary so the operator sees what got skipped. The summary itself still runs.

Do not emit additional commentary — each invoked agent already printed its own per-step report.

## Failure semantics

- **Step 0 detector hard-fail** (0g): orchestrator aborts with the detector's `ERROR:` line repeated verbatim. The other detector's report (if it completed) is left on disk. Re-running after fixing the trigger re-runs both detectors. No rollback.
- **Total preflight abort (1.all)**: no writes; the WARNING lines for each disabled axis are emitted before the aggregated ERROR. Operator runs `@rest-api-spec:specs-generator`.
- **Partial preflight disable (1.dom xor 1.cmd xor 1.qry)**: the enabled axis (or axes) regenerate as normal; the disabled axis's WARNING is surfaced before the Step 5 summary. (Gate 1.dom.d directs the operator to reconcile the commands/queries diagram and re-run *this* skill — not `specs-generator` — since only a subset of types are unreferenced.)
- **Step 3+ agent failure**: every step that aborts emits exactly one `ERROR:` line and exits the workflow. Do not chain further agents on top of a failed step. The orchestrator does not roll back partial writes.
- **Re-running `/rest-api-spec:update-specs` after fixing the trigger is the supported recovery path** — every step is idempotent on stable inputs:
  - **Step 0 detectors** regenerate their reports wholesale on every call (output stable modulo LLM nondeterminism in prose-summary blocks).
  - **Step 3** writers regenerate their owned table wholesale from current diagrams on every call (output stable modulo LLM nondeterminism). `resource-spec-initializer` and `endpoint-tables-writer` are explicitly idempotent on stable inputs.
  - **Step 4** (`rest-api-updates-writer`) is a pure HEAD-vs-working-tree diff and overwrites `updates.md` from scratch.
- The only failures `/rest-api-spec:update-specs` cannot retry through are the Step 0 missing-input cases (0a–0d) and the total-abort gate (1.all). Each error message directs the operator to the correct fix — `/update-specs` / `@updates-detector` for the missing domain report, diagram-restore-or-rename for the missing input diagrams, `@rest-api-spec:specs-generator` for everything else.

## Idempotency

Re-running `/rest-api-spec:update-specs` against unchanged inputs (working-tree spec unchanged versus HEAD, same domain `updates.md`, same `<stem>.commands.md` / `<stem>.queries.md`) produces:

- Fresh, byte-stable (modulo LLM drift) commands-updates.md / queries-updates.md from Step 0.
- A no-op early-exit through Step 2 when every axis's contribution is empty.
- Otherwise, byte-identical tables and updates report — modulo LLM prose drift in the re-run table writers (`git diff` noise, not a correctness failure). The tables the dirty writers don't own are not touched and stay byte-identical.

There are no sentinel comments. Unlike persistence-spec's `<!-- appended-from updates-hash:<hash> -->` (which guards the append-only migrations log), every table here is a snapshot — re-running over an unchanged input set simply reproduces the same content.

## What this skill deliberately does not do

- It does not regenerate `<stem>.rest-api/spec.md` end-to-end — that is `@rest-api-spec:specs-generator`. It runs only the table writer(s) whose dirty flag fired; the tables those writers don't own are not touched.
- It does not re-diff `<domain_diagram>` and does not invoke `domain-spec:updates-detector` — the domain `updates.md` is expected on disk before this skill runs. (It *does* invoke the two app-service-axis detectors at Step 0g.)
- It does not touch the diagram files (`<stem>.md`, `<stem>.commands.md`, `<stem>.queries.md`) or any Artifacts index — those siblings are linked from the original `@rest-api-spec:specs-generator` run.
- It does not act on the `dependencies` / `raised-exceptions` / `external-interfaces` / `external-domain-events` / `messaging-markers` categories that may appear on the app-service-axis updates reports — those drive `/application-spec:update-specs` and `/messaging-spec:update-specs`. This orchestrator silently ignores them.
- It does not handle aggregate-root removal/rename (which also cascades to the diagram filenames and the `<stem>.rest-api/` folder), domain stereotype changes, or a degraded domain baseline as a wholesale fatal — those disable only the domain axis via 1.dom.a–1.dom.c; the app-service axes may still proceed. A total-abort (1.all) routes to `@rest-api-spec:specs-generator`.
- It does not act on a domain-only multi-tenancy flip — REST-spec `tenant_id` handling (dropped from the body in Table 5, excluded from the query-parameter list in Table 4, sourced as `Auth context` in Table 6) is keyed off the *app-service method signatures* (`tenant_id: str` parameters), not the domain root. A domain-only `tenant_id` flip is byte-neutral here; it takes effect only once the commands/queries diagrams' method signatures are updated (a commands/queries-diagram-axis change). Deliberate divergence from persistence-spec; matches application-spec.
- It does not act on a bounded-context `title:` rename — the `<Resource>Commands` / `<Resource>Queries` class names come from the application-service diagrams' class nodes, and Table 1's Resource name comes from the `<<Aggregate Root>>` *class name*. A domain-`title:` change is byte-neutral. Tier 3 no-op.
- It does not pre-check the *transitive* analog of gate 1.dom.d (a renamed/removed type referenced only via another referenced type's field). The Step-1 scan catches the direct case; a transitive one surfaces as a runtime writer abort in Step 3 and is routed the same way ("reconcile the commands/queries diagram, then re-run").
- It does not track the Shared domain types registry (`Pagination`, `PaginatedResultMetadataInfo`, `ResultSetInfo`) — those are hard-coded in the table writers. Changes to them are plugin-source changes, not diagram changes; they never appear in any `updates.md` and are picked up only by re-running `@rest-api-spec:specs-generator` after a plugin upgrade.
- It does not preserve hand-edits inside a regenerated table — the writer contract is that the spec is regenerated from the diagrams, not curated. The blast radius is bounded by which tables fire (a writer rewriting Table 4 leaves Tables 1, 2/3, 5, 6 byte-stable), but inside a regenerated table manual enrichments are wholesale replaced.
- It does not auto-update generated REST API code (the per-surface serializer modules `api/serializers/<surface>/`, endpoint modules `api/endpoints/<surface>/`, the FastAPI app wiring `entrypoint.py` / `constants.py` / the aggregator `__init__.py` files / `api/auth.py`, the test fixtures `tests/conftest.py`, the integration tests) — that is the per-layer `/…-spec:update-code` flow (sequenced cross-layer by `/spec-core:update-code`), which consumes the `<stem>.rest-api/updates.md` this skill emits.
- It is independently invocable, **and** is run as part of the rest-api/messaging wave by `/spec-core:update-specs` (after that orchestrator's application wave). In that cascade mode `/spec-core:update-specs` passes `--detectors-fresh` as the second positional arg (it does so only when the application wave left both app-service-axis detector reports on disk), signalling that the reports are current; Step 0g of this skill takes the cascade-mode shortcut and skips its own commands/queries detector invocation. That orchestrator runs this skill in parallel with `/messaging-spec:update-specs`; a `spec.md`-missing hard-fail (Step 0b) does not abort that sibling — each runs to completion and prints its own report. Standalone invocation (without `--detectors-fresh`) follows the default Step-0g detector-invocation path.
