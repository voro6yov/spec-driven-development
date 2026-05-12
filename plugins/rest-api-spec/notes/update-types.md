# REST API Spec Update Types

Analysis of how every kind of domain-diagram delta — as emitted by `domain-spec:updates-detector` into `<dir>/<stem>.domain/updates.md` — ripples into the **REST API resource spec** sibling at `<dir>/<stem>.rest-api/spec.md`.

The goal is to enumerate every distinct kind of change a rest-api-spec updater would have to handle, so it can dispatch the right action per change rather than re-running `/rest-api-spec:generate-specs` from scratch.

This is the REST-API-side analog of `plugins/persistence-spec/notes/update-types.md` and `plugins/application-spec/notes/update-types.md`. It assumes the domain `updates.md` is already produced; the rest-api updater **consumes that report directly** (same as the persistence and application updaters) and never re-diffs the domain diagram. It does **not** consume the domain `specs.md` or the application `*.specs.md` — the rest-api-spec writers read the Mermaid *diagrams* (`<stem>.commands.md`, `<stem>.queries.md`, `<stem>.md`), not any other plugin's spec — so the rest-api updater can run before / independently of the domain and application specs being regenerated.

**The same structural fact that dominates `application-spec/notes/update-types.md` dominates this one:** the REST API spec is derived from *three* hand-authored diagrams, and the domain diagram is the *least* of them. See *The three-diagram trigger surface* below — the rest of this catalog covers only the domain-driven axis, which is the narrow minority.

---

## The three-diagram trigger surface

Per `rest-api-spec:naming-conventions`, three hand-authored Mermaid diagrams feed the resource spec for one aggregate:

| Diagram | Path | Diffed by | Diff artifact |
|---|---|---|---|
| Domain | `<dir>/<stem>.md` | `domain-spec:updates-detector` | `<dir>/<stem>.domain/updates.md` |
| Commands application service | `<dir>/<stem>.commands.md` | — *(nothing today)* | — |
| Queries application service | `<dir>/<stem>.queries.md` | — *(nothing today)* | — |

Which rest-api-spec table reads which diagram:

| Table (owner agent) | Domain diagram | Commands diagram | Queries diagram |
|---|:-:|:-:|:-:|
| **Table 1: Resource Basics** — Resource name / Plural / Router prefix (`resource-spec-initializer`) | ✅ *(the `<<Aggregate Root>>` class name)* | ✅ *(validation: `<X>Commands` ⇒ `<X>` must match)* | ✅ *(validation: `<X>Queries` ⇒ `<X>` must match)* |
| **Table 1: Resource Basics** — Surfaces row (`resource-spec-initializer` init → `endpoint-tables-writer` updates) | — | ✅ *(surface markers)* | ✅ *(surface markers)* |
| **Table 2: Query Endpoints** (`endpoint-tables-writer`) | — | — | ✅ *(method names + signatures + surface markers)* |
| **Table 3: Command Endpoints** (`endpoint-tables-writer`) | — | ✅ *(method names + signatures + surface markers; `on_*` filtered out)* | — |
| **Table 4: Response Fields** — response sub-tables + `**Nested:**` sub-tables + `**Query Parameters:**` block (`response-fields-writer`) | ✅ *(resolve the response DTO, its nested types recursively, and composite query-param types)* | — | ✅ *(method return types + parameter lists + surface markers)* |
| **Table 5: Request Fields** — body sub-tables + `**Nested:**` sub-tables (`request-fields-writer`) | ✅ *(resolve nested request types recursively)* | ✅ *(method parameter lists; the path/auth-bound partition; surface markers)* | — |
| **Table 6: Parameter Mapping** — per-endpoint parameter→source sub-blocks (`parameter-mapping-writer`) | ✅ *(resolve composite query-param types for the `Constructed from query params … → <Type>` source line)* | ✅ *(command-method parameter lists)* | ✅ *(query-method parameter lists)* |

The consequence: a domain-`updates.md`-only updater covers exactly **one of three trigger axes**, and it's the smallest. The entire **endpoint inventory** (Tables 2 and 3), **every method signature** that drives Tables 4/5/6, the **surface set** (Table 1's Surfaces row + the `## Surface:` H2 sections), and the **resource's plural / router prefix** are pure functions of the commands/queries diagrams (and, for the plural, Table 1 itself) — no domain delta can ever touch them. The domain diagram contributes only:

1. **Table 1's Resource name** — the `<<Aggregate Root>>` class name. The only way it changes is a rename, removal, or stereotype-demotion of the root, and all three are *hard-fails* (see *Hard-fail conditions*). So Table 1 is effectively domain-neutral except in the hard-fail cases.
2. **Nested-type resolution in Tables 4 and 5** — every PascalCase `<<Query DTO>>` / `<<Value Object>>` / `<<Domain TypedDict>>` / `<<Command>>` referenced by an app-service method's return type (queries → Table 4) or parameter type (commands → Table 5) is expanded into a `**Nested:**` sub-table by reading the type's declared fields off the domain diagram, recursively.
3. **Composite query-param decomposition in Tables 4 and 6** — a custom PascalCase query-method parameter type (e.g. `<Resource>Filtering`, `Pagination`) is decomposed into one Query-Parameter row per constituent field (Table 4) and rendered as `Constructed from query params <f1>, <f2>, … → <Type>` (Table 6), again by reading the type's declared fields off the domain diagram (falling back to the Shared domain types registry hard-coded in the writer agents).

So a complete rest-api-spec updater needs one of:

- **(A)** an updates-detector analog that diffs `<stem>.commands.md` / `<stem>.queries.md` — the *same two diagrams* an `application-spec:updates-detector` would diff (the two updaters could share one detector), invoked alongside the domain-`updates.md` consumption; **or**
- **(B)** accepting that commands/queries-diagram changes are handled by re-running `/rest-api-spec:generate-specs`, with the domain-driven updater handling only the ripple cataloged here.

This document catalogs the **domain-driven axis** — what an updater must do with `<stem>.domain/updates.md`. The app-diagram axis is a parallel, much larger concern; see *Out-of-scope but worth flagging*.

---

## Snapshot only — no append-only log

Unlike persistence-spec, where `§2.Migrations` is a cumulative changeset history that must never be rewritten, **every section of `spec.md` is a pure snapshot** — fully regeneratable from the three diagrams. There is no migration-log equivalent, no row-immutability contract, no delta-driven appender. So the rest-api-spec updater is structurally simpler than the persistence one (mirroring application-spec).

The only open design question is **granularity**:

- **Whole-pipeline regen** — re-run `/rest-api-spec:generate-specs` end-to-end (initializer → endpoint-tables → response-fields → request-fields → parameter-mapping). Correct, simplest, but produces a noisy `git diff` (regenerates all six tables across all surfaces) for a one-field change inside one nested type.
- **Per-writer regen** — re-run only the writer(s) whose table the domain delta touches. For any domain-only change that's at most `response-fields-writer` (Table 4) + `request-fields-writer` (Table 5) + `parameter-mapping-writer` (Table 6) — never `endpoint-tables-writer` (Tables 1/2/3 are pure functions of the app-service diagrams + the `<<Aggregate Root>>` name) and never `resource-spec-initializer` (a no-op once Table 1 exists). Tighter, zero new agent code.
- **Per-sub-block splice** — splice only the regenerated `**Nested:**` sub-tables and the touched composite-query-param rows into the existing `spec.md`, leaving every other table, surface section, and endpoint sub-block byte-identical. Tightest diff; most updater code (each of the three table writers regenerates its whole owned table in one pass — they have no "regenerate sub-block X only" mode — so a splicer would diff fresh writer output against the live file at `**Nested:**`/`**Endpoint:**` granularity).

As with persistence-spec and application-spec, hand-edits inside the spec are **not a preservation goal** — the operator's contract is "the spec is regenerated from the diagrams, not curated." But note the regen unit is *small* here (a domain-only change touches at most a handful of `**Nested:**` sub-tables and the `include` / `Constructed from …` rows), so per-writer regen already gives a much tighter diff than the persistence or application updaters — most of the file is byte-stable on any domain-only change.

---

## REST API spec sections and their domain-sensitivity

| Section | Kind | Owner agent | Domain-diagram-sensitive to |
|---|---|---|---|
| **Table 1: Resource Basics** (Resource name, Plural, Router prefix, Surfaces) | snapshot | `resource-spec-initializer` (init) → `endpoint-tables-writer` (Surfaces row updates) | **Resource name only** — the `<<Aggregate Root>>` class name. Plural and Router prefix derive from Resource name; Surfaces derives from the commands/queries diagrams' surface markers. The only domain delta that reaches Resource name is a root rename / removal / stereotype-demotion — all *hard-fails*. |
| **Table 2: Query Endpoints** / **Table 3: Command Endpoints** | snapshot | `endpoint-tables-writer` | **Nothing.** Pure function of the `<Resource>Queries` / `<Resource>Commands` class bodies (method names, signatures, surface markers; `on_*` filtered). The Domain Ref column traces to an *application-service* method, never to a domain class member. No domain delta reaches it. |
| **Table 4: Response Fields** (per query endpoint: response-DTO field rows + `**Nested:**` sub-tables + `**Query Parameters:**` block) | snapshot | `response-fields-writer` | The declared field list of the response DTO (`<<Query DTO>>` / `<<Value Object>>` / `<<Domain TypedDict>>`) returned by the matching queries method; the declared field lists of every nested type that DTO references, recursively; the declared field lists of composite query-param types (the `<Resource>Filtering`-style parameter, decomposed into the `**Query Parameters:**` rows). Field add/remove/retype on any of those → row/type-cell changes. A rename/removal of a referenced type → **ABORT** (the queries diagram still names the old token). |
| **Table 5: Request Fields** (per command endpoint: body-field rows + `**Nested:**` sub-tables) | snapshot | `request-fields-writer` | The declared field lists of every nested *request* type a command method's parameters reference (`<<Value Object>>` / `<<Domain TypedDict>>` / `<<Command>>` / `<<Query DTO>>` — any accepted), recursively. The body-field *set* itself comes from the command method's parameter list (commands diagram) minus the path/auth-bound parameters — that's app-diagram-driven, not domain. Field add/remove/retype on a referenced nested type → row/type-cell changes. Rename/removal still referenced → **ABORT**. |
| **Table 6: Parameter Mapping** (per endpoint: parameter→source sub-blocks) | snapshot | `parameter-mapping-writer` | The declared field list of composite query-param types only (drives the `Constructed from query params <f1>, <f2>, … → <Type>` source string). Everything else — `Path param {id}`, `Auth context`, `Request body \`<field>\``, `Query param \`<name>\`` — is classified from the method's parameter names/types (app-diagram-driven). A composite-type field add/remove → the source string's field list changes. A composite-type rename/removal still referenced → **ABORT**. |

The downstream artifacts — the per-surface serializer modules (`api/serializers/<surface>/<operation>.py`), endpoint modules (`api/endpoints/<surface>/<plural>.py`), the FastAPI app wiring (`entrypoint.py`, `constants.py`, the aggregator `__init__.py` files, `api/auth.py`), the test fixtures (`tests/conftest.py`), and the integration tests — are owned by `/rest-api-spec:generate-code`. They are **out of scope** for the spec updater (analogous to `notes/code-updater-approach-c.md` on the domain side).

---

## Domain shape constraints

Load-bearing facts about how the REST API spec relates to the domain diagram:

- **The domain diagram is one of three inputs, and the least of them.** The trigger for a domain-driven REST-spec update is `<stem>.domain/updates.md`. Commands/queries-diagram changes — which dominate in practice — are a separate axis (see above).
- **Exactly one `<<Aggregate Root>>` per domain diagram.** The same invariant the domain, persistence, and application updaters lean on. Removal, stereotype-demotion, or rename of the root is a **hard-fail** for the REST updater: the resource loses its anchor, and a rename also moves all three diagram filenames *and* the `<stem>.rest-api/` folder (the stem changed) — a coordinated multi-file rename the updater cannot perform.
- **Domain `<<Event>>` classes never appear in the REST spec.** Command endpoints don't emit or name domain events; query endpoints don't return them. A pure `<<Event>>` change in the domain footer leaves the REST spec byte-stable.
- **Domain `<<Command>>` dataclasses almost never appear in the REST spec.** They are cross-context message payloads, not HTTP request bodies. The one exception: `request-fields-writer` Step 4d accepts a `<<Command>>` as a nested request type, so a command method declared (in the *commands* diagram) to take a domain `<<Command>>` dataclass as a parameter would surface as a Table 5 `**Nested:**` sub-table — but command methods overwhelmingly take primitives or `<<Value Object>>` request types. Treat `<<Command>>` as byte-neutral unless a Table 5 nested sub-table actually references it.
- **The `Command<AggregateRoot>Repository` / `Query<AggregateRoot>Repository` ABCs are invisible to the REST spec.** Its Domain Ref columns point at `<Resource>Commands` / `<Resource>Queries` *application-service* methods, never at repository finders. Repository-finder churn ripples into the *application* spec (and from there an operator may add/drop app-service methods, which is a commands/queries-diagram change) but does not touch the REST spec directly. Byte-neutral.
- **Domain `<<Service>>` classes are invisible to the REST spec.** The REST layer calls application services, which call domain services — but the REST spec never references a domain service. Byte-neutral.
- **The `<Resource>Commands` / `<Resource>Queries` class names come from the commands/queries diagrams' class nodes**, not from any domain class and not from the domain diagram's `title:` directive. A bounded-context rename (domain `title:` change) is byte-neutral for the REST spec — Table 1's Resource name comes from the `<<Aggregate Root>>` *class name*, the Router prefix from the plural.
- **REST-spec multi-tenancy is an application-diagram property.** Whether `tenant_id` is dropped from a request body (Table 5), excluded from the query-parameter list (Table 4), and sourced as `Auth context` (Table 6) is keyed entirely off the *app-service method signatures* declaring a `tenant_id: str` parameter — which is the commands/queries diagrams' concern. A domain-only `tenant_id` flip on the aggregate root does **not** change the REST spec until the app-service method signatures are updated to add/drop the parameter — see *Out-of-band signals*. (Deliberate divergence from the persistence-spec model, where `tenant_id` on the root *is* the trigger.)
- **Surface markers live only in the commands/queries diagrams.** A `%% v1` / `%% internal` marker is a comment inside a `<Resource>Commands` / `<Resource>Queries` class body; the domain diagram has none. Adding/removing/renaming a surface is therefore a commands/queries-diagram change, never a domain change.
- **The Shared domain types registry is hard-coded in the writer agents.** `Pagination`, `PaginatedResultMetadataInfo`, `ResultSetInfo` are baked into `response-fields-writer` / `request-fields-writer` / `parameter-mapping-writer` and resolved without touching the domain diagram. Changes to those types are plugin-source changes, not domain-diagram changes; they never appear in `updates.md` and are out of the updater's scope.

---

## Mapping `affected_categories` → REST-spec impact

Per the canonical category order from `domain-spec:updates-report-template`:

### 1. `data-structures` (`<<TypedDict>>`)

The single highest-frequency domain-driven REST-spec ripple — but narrow, and routed entirely through nested-type resolution.

- **`<<Domain TypedDict>>` referenced by a queries-method return type** (the response DTO, or a nested type the response DTO references recursively) → field add/remove/retype on it → that type's `**Nested:**` sub-table in **Table 4** regenerates: a `<DTO>["<field>"]` row added/dropped, a type cell rewritten. A retype *to a custom PascalCase type* adds another `**Nested:**` sub-table (recursively); a retype *to `A | B`* adds two. If the changed TypedDict *is* the top-level response DTO, the endpoint's response-fields table regenerates wholesale. → **Table 4 sub-block regen.**
- **`<<Domain TypedDict>>` referenced by a commands-method parameter type** (a nested request type, or a type one references recursively) → same, in **Table 5**. → **Table 5 sub-block regen.**
- **`<<Domain TypedDict>>` used as a composite query-param type** (rare for a TypedDict — usually a `<<Value Object>>` — but `parameter-mapping-writer` resolves any custom PascalCase type) → field add/remove → the **Table 4 `**Query Parameters:**`** block re-decomposes (one row per constituent field) *and* the **Table 6 `Constructed from query params … → <Type>`** source line's field list changes. → **Table 4 + Table 6 regen.**
- **`<<Domain TypedDict>>` renamed or removed while still referenced** by an app-service method's return/parameter/composite-param type in the commands/queries diagram → the writer can no longer resolve the token (`Cannot resolve response DTO <Name>` / `Cannot resolve nested type <Name>` / `Cannot resolve query-param composite <Type>`) → **ABORT** — the operator must reconcile the commands/queries diagram (point the method's type token at the new name, or drop the reference) before re-running.
- **`<<Domain TypedDict>>` lifecycle/member change, not referenced by any app-service method signature** → **byte-neutral.**
- **Net:** `data-structures` → `**Nested:**` sub-table regen in Table 4 and/or Table 5 (and Table 4 `**Query Parameters:**` + Table 6 source line for the rare composite-TypedDict case), **or ABORT** on a still-referenced rename/removal. Never touches Tables 1/2/3.

> The "Includable / Wish List" wrinkle: a heavy field (`T | None` where `T` is a custom PascalCase type) added/removed on the response DTO also re-lists the `include` query-parameter row's "Optional list of heavy fields: `f1`, `f2`" enumeration in the **Table 4 `**Query Parameters:**`** block (`response-fields-writer` Step 3c–3d). So a response-DTO field change can nudge both the response-fields table and the `include` row.

### 2. `value-objects` (`<<Value Object>>`)

Same nested-type-resolution axis as `data-structures`, plus it carries the composite-query-param axis (the `<Resource>Filtering`-style parameters are usually `<<Value Object>>`s, and `<<Value Object>>`s frequently surface as both response sub-types and request body types).

- **`<<Value Object>>` referenced by a queries-method return type / a Table 4 nested type** → field add/remove/retype → that VO's `**Nested:**` sub-table in **Table 4** regenerates (recursively for any custom types it now references). → **Table 4 sub-block regen.**
- **`<<Value Object>>` referenced by a commands-method parameter type / a Table 5 nested type** → same, in **Table 5**. → **Table 5 sub-block regen.**
- **`<<Value Object>>` used as a composite query-param type** (the common case for the resource's filtering parameter) → field add/remove → **Table 4 `**Query Parameters:**`** re-decomposes + **Table 6 `Constructed from query params … → <Type>`** source line changes. → **Table 4 + Table 6 regen.**
- **`<<Value Object>>` becomes polymorphic** (a discriminated hierarchy appears) → only matters if the *diagram* declares the polymorphic union (`IndividualData | LegalEntityData`) or a base type as a method return/parameter type's field type — and then it's the field *retype* (an M2 on the referencing DTO) that surfaces, with `**Nested:**` sub-tables emitted for each member of the union and a `Literal[...]` discriminator field appearing in the type column. The REST spec doesn't model VO polymorphism per se; it just emits the declared field types. → **Table 4 / Table 5 sub-block regen** when a referenced DTO's field retypes to the union; **byte-neutral** otherwise.
- **`<<Value Object>>` renamed or removed while still referenced** by an app-service method's return/parameter/composite-param type → **ABORT** (as for `data-structures`).
- **`<<Value Object>>` lifecycle/member change, not referenced by any app-service method signature** → **byte-neutral.** (A VO that's purely internal to the aggregate — never returned, never accepted, never a filtering parameter — is invisible to the REST spec.)
- **Net:** `value-objects` → `**Nested:**` sub-table regen in Table 4 and/or Table 5, and/or Table 4 `**Query Parameters:**` + Table 6 source-line regen for the filtering-composite case; **ABORT** on a still-referenced rename/removal; never touches Tables 1/2/3.

### 3. `domain-events` (`<<Event>>`)

**No REST-spec impact.** No domain event appears in any table — command endpoints don't name emitted events, query endpoints don't return them. Skip this category at dispatch time.

### 4. `commands` (`<<Command>>` — the *domain message dataclass*, not the application `Commands` service)

**Near-byte-neutral.** Domain `<<Command>>` dataclasses are cross-context message payloads dispatched via `command_producer`; they are not HTTP request bodies. The one exception is the same as for `data-structures`: a `<<Command>>` declared (in the *commands* diagram) as the parameter type of a command method would surface as a Table 5 `**Nested:**` sub-table — field add/remove/retype on such a referenced `<<Command>>` → **Table 5 sub-block regen**; rename/removal still referenced → **ABORT**. In practice command methods take primitives or `<<Value Object>>` request types, so this fires almost never. Treat `commands` as **byte-neutral** unless a Table 5 nested sub-table actually references the changed `<<Command>>`.

> ⚠ **Naming-collision warning.** The `commands` *category* (domain `<<Command>>` dataclasses) is unrelated to the *command side* of the REST spec (Tables 3 / 5 / 6, driven by the `<Resource>Commands` application-service diagram). `affected_categories: [commands]` is at most a single Table 5 nested-sub-table regen, and usually a no-op.

### 5. `aggregates` (`<<Aggregate Root>>`, `<<Entity>>`)

Almost entirely **byte-neutral as an `aggregates`-only signal**, with a **hard-fail spike on root identity**.

- **Aggregate-root method renamed / removed / added** → the REST endpoint comes from the `<Resource>Commands` / `<Resource>Queries` *application-service* method (commands/queries diagram), not from the domain method. A domain-method rename doesn't touch any table; if the operator also renamed the corresponding app-service method, that's a commands/queries-diagram change. **Byte-neutral.**
- **Aggregate-root method signature change** (params added/removed) → the args in Table 6 come from the *app-service* method's parameter list, not the aggregate's; the Table 2/3 endpoint shape is derived from the app-service method's signature. A domain-method-signature change touches neither. **Byte-neutral.**
- **Aggregate-root / `<<Entity>>` attribute add / remove / type change** → the REST spec never references aggregate attributes; it references app-service method parameters (commands/queries diagrams) and DTO/VO fields (the Tables 4/5 nested types). **Byte-neutral** *as an `aggregates`-category signal* — if the attribute happens to be a field of a `<<Query DTO>>` or `<<Value Object>>` that surfaces as a nested or composite type, it's that type's category (`data-structures` / `value-objects`) that fires, not `aggregates`.
- **Entity added / removed** (children flip) → the REST spec doesn't model the aggregate's child-collection structure (that's the application spec's `Requires Aggregate State`). New child endpoints (`add_<child>`, `update_<child>`, …) appear only once the *commands* diagram declares those methods — a commands-diagram change. **Byte-neutral.**
- **Hard-fails:** aggregate root **removed** (`resource-spec-initializer` aborts on zero `<<Aggregate Root>>` matches if re-run; the resource has no anchor) — the established writers (`endpoint-tables-writer`, `response-fields-writer`, `request-fields-writer`, `parameter-mapping-writer`) all validate Table 1's Resource name against the aggregate root they derive, so a vanished root surfaces as an abort there too; root **stereotype-demoted** (same — no `<<Aggregate Root>>` on the diagram); root **renamed** (the commands/queries diagrams still say `OldNameCommands` / `OldNameQueries` *and* all three diagram filenames + the `<stem>.rest-api/` folder are at the old stem — a coordinated multi-file rename).
- **Aggregate root added** → impossible on an existing spec → treat as malformed.
- **Net:** `aggregates` → **byte-neutral** as an `aggregates`-only signal; **hard-fail** on root removal / stereotype-demotion / rename.

### 6. `repositories-services` (`<<Repository>>`, `<<Service>>`)

**Byte-neutral.** The REST spec's Domain Ref columns point at `<Resource>Commands` / `<Resource>Queries` *application-service* methods, never at repository finders, and the REST spec never references a domain `<<Service>>` at all. Repository-finder churn affects the *application* spec (which is derived from the commands/queries diagrams, not the other way around); domain-`<<Service>>` lifecycle affects the application spec and domain spec. Neither touches `spec.md`. Skip the category entirely.

---

## Out-of-band signals (not a direct `affected_categories` entry)

These are derived from member/relationship deltas in `## Per-Class Changes` (or are explicitly *not* derivable from the domain report at all):

- **Nested-type / composite-type churn** — the **only material domain-driven REST-spec axis**. Technically a `data-structures` / `value-objects` (rarely `commands`) member change — it surfaces under the changed type's `## Per-Class Changes → Members` block as `Attribute added/removed/changed` — but it is the single signal worth dispatching on directly: it drives the `**Nested:**` sub-tables in Tables 4 and 5, the `**Query Parameters:**` decomposition in Table 4, and the `Constructed from query params … → <Type>` source line in Table 6. Whether a given type change actually fires depends on whether *any* app-service method signature in the commands/queries diagrams references that type — the updater must cross-check the changed type names against the method return/parameter types declared in `<stem>.commands.md` / `<stem>.queries.md`.
- **Aggregate-root rename** — surfaces as `removed (old)` + `added (new)` under `## Class Lifecycle`. Cascades to *all three* diagram filenames (`old-name.md` → `new-name.md`, `.commands.md`, `.queries.md`), both application-service class names (`OldNameCommands` → `NewNameCommands`, `OldNameQueries` → `NewNameQueries`), every Domain Ref in Tables 2 and 3, Table 1's Resource name / Plural / Router prefix, *and* the `<stem>.rest-api/` folder name. A domain-`updates.md`-driven updater cannot perform that cascade. **Hard-fail.**
- **Multi-tenancy flip** — **NOT a domain-`updates.md`-driven signal for the REST spec.** REST-spec `tenant_id` handling (dropped from the body in Table 5, excluded from the query-param list in Table 4, sourced as `Auth context` in Table 6) is a property of the *app-service method signatures* (`tenant_id: str` parameters), which is the commands/queries diagrams' concern. A domain-only `tenant_id` add/remove on the aggregate root is byte-neutral for the REST spec; it takes effect only once the commands/queries diagrams' method signatures are updated (a commands/queries-diagram change). Deliberate divergence from the persistence-spec model; matches the application-spec model.
- **Bounded-context rename** — **not applicable.** The `<Resource>Commands` / `<Resource>Queries` class names come from the commands/queries diagrams' class nodes, not from the domain `title:`; Table 1's Resource name comes from the `<<Aggregate Root>>` *class name*. A domain-`title:` change is byte-neutral for the REST spec. (It surfaces in `## Orphan Prose Changes → Preamble` of the domain report; the REST updater ignores it.)
- **Surface-set change** — **NOT a domain-`updates.md`-driven signal.** Surface markers (`%% <name>`) live in the *commands/queries* diagram class bodies; adding/removing/renaming one restructures the entire per-surface layout — Table 1's Surfaces row, the `## Surface:` H2 section set, the per-surface copies of Tables 2–6, and orphaned sections (`endpoint-tables-writer` leaves a `## Surface:` section whose name is no longer in the surface set in place for manual review, since its Tables 4–6 may carry user customizations). The domain diagram has no surface markers. This is the commands/queries-diagram axis.

---

## Update types

Mirroring the domain-spec catalog (L / M / R / P / C codes), here is the REST-API-spec response to each domain-side delta:

### L. Lifecycle updates (whole-class, in the domain diagram)

- **L1. Class added** — dispatch by stereotype:
  - `<<Aggregate Root>>` → impossible on an existing spec; treat as malformed.
  - `<<Entity>>` → **byte-neutral** (the REST spec doesn't model child-collection structure; new child endpoints come only when the commands diagram declares the methods).
  - `<<Value Object>>` / `<<Domain TypedDict>>` / `<<Command>>` → **byte-neutral** unless an app-service method signature in the commands/queries diagram *already* references it by name (in which case the prior `generate-specs` run would have aborted on the unresolvable token; once the type is added, the `**Nested:**` / `**Query Parameters:**` resolution succeeds → **Table 4 / Table 5 / Table 6 sub-block regen**).
  - `<<TypedDict>>` (a `<<Query DTO>>` returned by a queries method) → same as above — byte-neutral unless a queries method's return type already names it; once present → **Table 4 regen** for that endpoint.
  - `<<Event>>` → **byte-neutral.**
  - `<<Service>>` / `<<Repository>>` → **byte-neutral.**
- **L2. Class removed** — symmetric to L1:
  - `<<Aggregate Root>>` → **hard-fail.**
  - `<<Entity>>` → **byte-neutral.**
  - `<<Value Object>>` / `<<Domain TypedDict>>` / `<<Command>>` / `<<Query DTO>>` → if still referenced by an app-service method's return / parameter / composite-param type in the commands/queries diagram → the writer can't resolve the token → **ABORT** — reconcile the commands/queries diagram first. If not referenced anywhere → **byte-neutral.**
  - `<<Event>>` / `<<Service>>` / `<<Repository>>` → **byte-neutral.**
- **L3. Stereotype changed** — **hard-fail** (route to `/rest-api-spec:generate-specs`), mirroring domain / persistence / application. Subsumes the aggregate-root case. (A `<<Value Object>>` → `<<Entity>>` re-classification, say, can break nested-type resolution if the renamed-category type is no longer the kind of thing the writer expects — and the cross-category move is rare enough that a from-scratch regen is the safe call.)

### M. Member updates (in-class, signature-affecting, in the domain diagram)

- **M1. Attribute added/removed** — on the aggregate root or an `<<Entity>>` → **byte-neutral** (the REST spec references app-service method parameters and DTO/VO fields, not aggregate attributes). On a `<<Query DTO>>` / `<<Value Object>>` / `<<Domain TypedDict>>` / `<<Command>>` that surfaces as a nested or composite type in some endpoint → that sub-table's rows change → **Table 4 / Table 5 sub-block regen** (and Table 4 `**Query Parameters:**` + Table 6 source line if the type is a composite query-param). Whether it fires hinges on the cross-check against the commands/queries diagrams' method signatures.
- **M2. Attribute type changed** — same dispatch as M1: byte-neutral on an aggregate; a retype inside a referenced DTO/VO/TypedDict changes that type's `**Nested:**` type cell, and a retype *to a custom PascalCase type* adds another `**Nested:**` sub-table (recursively), a retype *to `A | B`* adds two. → **Table 4 / Table 5 sub-block regen.**
- **M3. Attribute visibility changed** — **byte-neutral.** Visibility is a domain-encapsulation concern; nested-type field projection emits whatever fields are declared regardless of prefix (and `<<TypedDict>>` / `<<Value Object>>` members rarely carry one).
- **M4. Method added/removed** — on **any** domain class → **byte-neutral.** The REST spec references *application-service* methods (commands/queries diagrams), never domain-class methods.
- **M5. Method signature changed** — on **any** domain class (including a `<<Repository>>` finder) → **byte-neutral.** Tables 2/3 endpoint shapes and the Table 6 argument sources come from the app-service method signatures, not from domain-class members.

### R. Relationship updates (cross-class topology, in the domain diagram)

- **R1. Composition added/removed** (`*--`) — root → `<<Entity>>` = children flip → **byte-neutral** for the REST spec. Root or entity → `<<Value Object>>` = the VO is now (or no longer) part of the aggregate — but whether that VO appears in any table depends on whether an app-service method signature references it (a commands/queries-diagram property, independent of the domain composition edge). **Byte-neutral** as a composition-edge signal; if a Table 4/5 nested sub-table references the VO and its field set changed alongside, that's the M1/M2 axis.
- **R2. Dependency added/removed** (`-->`) — `: emits …` adds/removes a domain `<<Event>>` (byte-neutral); `-->` to a `<<Service>>` / external interface is domain-layer wiring (byte-neutral). **Byte-neutral.**
- **R3. Realization added/removed** (`--()`) — `: emits …` adds/removes a domain `<<Command>>` (byte-neutral; see category 4); `--()` to a `<<Repository>>` is the repo-realizes-aggregate edge (byte-neutral). **Byte-neutral.**
- **R4. Inheritance added/removed** (`<|--`) — makes a `<<Value Object>>` / `<<Entity>>` polymorphic; only matters if the diagram declares the resulting union (or a base type) as a referenced type's field/parameter type — and even then it's the field *retype* (M2 on the referencing DTO) that surfaces, not the inheritance edge. **Byte-neutral** as an inheritance-edge signal.
- **R5. Multiplicity changed** — "single inline → collection" on a child entity = children flip → **byte-neutral**. On a VO collection used as a field of a method return/parameter type → it's a field-retype (M2 on the referencing DTO) → **Table 4 / Table 5 sub-block regen**. **Byte-neutral** as a multiplicity signal per se.
- **R6. Label changed** (`: emits OrderPlaced` → `: emits OrderConfirmed`) — event-name rename; the REST spec doesn't name events. **Byte-neutral.**
- **R7. Orphan relationship change** — the unresolved source is typically an inferred `<<Event>>` or `<<Command>>` → **byte-neutral.**

### P. Prose updates (semantic, not structural)

**All byte-neutral for the REST spec.** No rest-api-spec writer consumes domain prose. The Description columns of Tables 2 and 3 are mechanical boilerplate produced by `endpoint-tables-writer`'s dispatch tables (`Create a new <resource>`, `Retrieve a single <resource> by id`, the plural-tail heuristic, …). The Description column of Table 4's `**Query Parameters:**` block is mechanical (`Required <field>` / `Optional <field>`). The Validation column of Table 5 is mechanical (`Required` / `Optional` + `, non-empty list` + `; valid UUID`). There is no advisory-prose channel like the one the application-spec methods writers consume.

- **P1. Class-keyed prose changed** (`### ClassName`) — **byte-neutral.**
- **P2. Method-keyed prose changed** (`### ClassName.method`) — **byte-neutral.**
- **P3. Orphan prose changed — `Preamble`** — the domain title/overview; the REST spec doesn't consume the domain title. **Byte-neutral.**
- **P4. Orphan prose changed — free-form** (`Notes`, `Glossary`, …) — **byte-neutral.**

### C. Composite / derived signals

- **C1. Pure prose change, zero structural** — **no-op.** Unlike application-spec (where a prose change can nudge an advisory-channel clause), this is a *guaranteed* no-op for the REST spec — the writers don't consume prose at all.
- **C2. Pure structural, zero prose** — standard regen path, but only on the nested-type / composite-type axis (categories 1, 2, and the rare category-4 case); the writers don't consume prose anyway, so the absence of prose summaries is irrelevant.
- **C3. `Affected Categories` empty** — **no-op.** By the report-template footer contract this implies no class lifecycle, no per-class changes, and no orphan-relationship changes — the only content is orphan prose, which is byte-neutral for the REST spec.
- **C4. `Affected Categories` spans multiple** — fan out, but in practice only `data-structures` ∪ `value-objects` (∪ the rare `commands` nested-type case) carry any REST-spec impact, and only via nested-/composite-type resolution; `domain-events` / `repositories-services` contribute nothing, and `aggregates` contributes nothing *except* the root-identity hard-fail spike. So a multi-category domain change reduces to "which referenced types changed their field lists, and was a referenced type renamed/removed (→ ABORT) or the root touched (→ hard-fail)."
- **C5. First-run / degraded baseline** (HEAD warning in the domain report Summary) — **hard-fail** (route to `/rest-api-spec:generate-specs`).

---

## Section-affected matrix

Quick lookup for "given a domain-side update, what happens in each REST-spec table". Tables 2 and 3 (the endpoint inventory) are always `—` for any domain-driven change — they're pure functions of the commands/queries diagrams. The "Table 4 query params" and "Table 6 mappings" columns only move for a *composite query-param type* whose field list changed (or, for Table 4 query params, an includable/heavy field added/removed on a response DTO).

| Domain update | Table 1 (Resource Basics) | Tables 2 & 3 (Endpoint Inventory) | Table 4 (Response Fields) | Table 4 (`**Query Parameters:**` block) | Table 5 (Request Fields) | Table 6 (Parameter Mapping) |
|---|:-:|:-:|---|---|---|---|
| Aggregate root removal / stereotype-demotion / rename | hard-fail |
| Stereotype changed (any class) | hard-fail |
| Degraded baseline (HEAD warning) | hard-fail |
| `<<Query DTO>>` / `<<Domain TypedDict>>` / `<<Value Object>>` renamed or removed, **still referenced** by an app-service method's return / parameter / composite-param type | ABORT — reconcile the commands/queries diagram first |
| Response-DTO (or a recursively-referenced nested type) field add/remove/retype | — | — | regen the type's `**Nested:**` sub-table (or the whole response table if it's the top-level DTO) | regen the `include` row's heavy-field list **iff** the changed field is includable (`CustomType \| None`) | — | — |
| Nested *request* type (a command method's parameter type, or one it references recursively) field add/remove/retype | — | — | — | — | regen the type's `**Nested:**` sub-table | — |
| Composite query-param type (the `<Resource>Filtering`-style parameter) field add/remove | — | — | — | regen the decomposed parameter rows for affected endpoints | — | regen the `Constructed from query params … → <Type>` source line for affected endpoints |
| `<<Command>>` dataclass field change, **referenced by a Table 5 nested type** | — | — | — | — | regen the type's `**Nested:**` sub-table | — |
| Referenced type added (an app-service method signature already named it) | — | — | resolve the new `**Nested:**` sub-table | resolve the new decomposed rows / `include` list, if applicable | resolve the new `**Nested:**` sub-table | resolve the new `Constructed from …` source line, if applicable |
| Aggregate-root / `<<Entity>>` method or attribute change (not surfacing via a referenced DTO/VO) | — | — | — | — | — | — |
| `<<Entity>>` added/removed (children flip) | — | — | — | — | — | — |
| `<<Repository>>` finder churn (add/remove/signature change) | — | — | — | — | — | — |
| `<<Service>>` lifecycle / member change | — | — | — | — | — | — |
| `<<Event>>` / `<<Command>>` lifecycle/member change (not referenced via a Table 5 nested type) | — | — | — | — | — | — |
| Bounded-context (domain `title:`) rename | — | — | — | — | — | — |
| Multi-tenancy flip on the domain root (not yet mirrored in the app-diagram method signatures) | — | — | — | — | — | — |
| Surface marker added/removed/renamed (this is a commands/queries-diagram change, not a domain change — listed for contrast) | *(Surfaces row regen via `endpoint-tables-writer`)* | *(per-surface tables regen)* | *(per-surface Table 4 regen)* | *(regen)* | *(per-surface Table 5 regen)* | *(per-surface Table 6 regen)* |
| Domain prose change (P1–P4) | — | — | — | — | — | — |

Legend:
- **regen** — the snapshot writer that owns the table re-runs and replaces the affected sub-block from the current diagrams; existing content (including hand-edited Descriptions / Validation prose inside that sub-block) is discarded.
- **resolve** — a previously-unresolvable reference now resolves; the sub-block is added.
- **ABORT** — the writer agent aborts; the operator must reconcile the commands/queries diagram before the updater can run.
- **— (byte-stable)** — the table is not touched.
- **hard-fail** — the updater bails out with a clear operator instruction (see *Hard-fail conditions*).

`response-fields-writer` owns Table 4 (including the `**Query Parameters:**` block); `request-fields-writer` owns Table 5; `parameter-mapping-writer` owns Table 6. The three tables regenerate independently — a domain change touching only nested *response* types re-runs only `response-fields-writer`; one touching only nested *request* types re-runs only `request-fields-writer`; a composite-query-param field change re-runs both `response-fields-writer` (the decomposed Query-Parameter rows) and `parameter-mapping-writer` (the `Constructed from …` source line). `endpoint-tables-writer` and `resource-spec-initializer` never re-run for a domain-only change.

---

## Hard-fail conditions

Mirror the domain / persistence / application `update-specs` failure semantics. Each prints exactly one `ERROR:` line and exits, directing the operator to `/rest-api-spec:generate-specs <domain_diagram>` (after reconciling the commands/queries diagrams where the message says so):

- **Aggregate root removal** in `## Class Lifecycle → Removed` — the resource loses its anchor; `resource-spec-initializer` (and every established writer's Table-1-Resource-name validation) would abort.
- **Aggregate root stereotype change** in `## Class Lifecycle → Stereotype Changed` (old or new bucket = `<<Aggregate Root>>`).
- **Aggregate root rename** (reported as `removed (old)` + `added (new)`) — cascades to all three diagram filenames, both application-service class names, every Domain Ref in Tables 2/3, Table 1's Resource name / Plural / Router prefix, *and* the `<stem>.rest-api/` folder name. A coordinated multi-file rename the domain-`updates.md`-driven updater cannot perform. Route to: rename the diagrams and the `<stem>.rest-api/` folder, then `/rest-api-spec:generate-specs`.
- **Any stereotype change** in the domain report — `## Class Lifecycle → Stereotype Changed` non-empty (subsumes the aggregate-root case above).
- **Degraded baseline** — `_warning: HEAD ..._` line in the domain report Summary.

Plus an **abort-and-reconcile** sub-case (not a full hard-fail — the rest of the spec is fine, but the affected writer cannot run): a `<<Query DTO>>` / `<<Value Object>>` / `<<Domain TypedDict>>` / `<<Command>>` **renamed or removed while still referenced** by an app-service method's return type, parameter type, or composite-query-param type in `<stem>.commands.md` / `<stem>.queries.md` → `response-fields-writer` / `request-fields-writer` / `parameter-mapping-writer` abort (`Cannot resolve response DTO <Name>` / `Cannot resolve nested type <Name>` / `Cannot resolve query-param composite <Type>`). The updater should detect the pending abort from `updates.md` (a `data-structures` / `value-objects` / `commands` removal-or-rename whose name appears in a method return/parameter type token in the commands/queries diagrams) and route to "reconcile the commands/queries diagram (point the method's type token at the new name, or drop the reference), then re-run" rather than running the writer blind.

---

## Out-of-scope but worth flagging to the operator

These belong in operator-facing warnings, not in the spec content itself:

- **The commands/queries diagrams are the second and third trigger surfaces — and the dominant ones.** Most REST-spec changes in practice — an endpoint added/removed, a method signature changed (parameters, return type), a surface added/removed/renamed, the resource's plural changed — originate in the *application-service* diagrams (`<stem>.commands.md`, `<stem>.queries.md`) or in Table 1 itself, and `<stem>.domain/updates.md` does not capture them. A complete rest-api-spec updater needs an updates-detector analog that diffs those two diagrams — the *same two diagrams* an `application-spec:updates-detector` would diff, so a single shared detector could feed both the application updater and the REST updater — **or** must accept that those changes are handled by re-running `/rest-api-spec:generate-specs`. This is *the* central design decision for the updater. The domain-driven axis cataloged here is the narrow minority.
- **Aggregate-root rename cascades to diagram filenames and the plugin folder.** Per `rest-api-spec:naming-conventions`, the aggregate stem drives `<stem>.md`, `<stem>.commands.md`, `<stem>.queries.md`, and `<stem>.rest-api/`. A domain-`updates.md`-driven updater cannot perform that cascade; the operator renames the diagrams and the folder, then re-runs `/rest-api-spec:generate-specs`. Surfaces as a hard-fail.
- **Multi-tenancy is an application-diagram property.** A domain-only `tenant_id` flip on the aggregate root does not change the REST spec; the app-service method signatures must add/drop the `tenant_id` parameter (in the commands/queries diagrams) before Table 5 (body fields), Table 4 (query-parameter list), and Table 6 (`Auth context` source) change. Deliberate divergence from persistence-spec; matches application-spec.
- **Surface markers live in the commands/queries diagrams.** Adding/removing/renaming a `%% <name>` marker restructures the whole per-surface section layout (Table 1's Surfaces row, the `## Surface:` H2 set, the per-surface copies of Tables 2–6, orphaned sections). `endpoint-tables-writer` is the only writer that materializes new surface sections and updates Table 1's Surfaces row; it leaves orphaned sections in place for manual review (their Tables 4–6 may carry user customizations). None of this is domain-`updates.md`-driven.
- **Hand-edits inside the spec are not preserved within a regenerated sub-block.** The spec is regenerated from the diagrams, not curated. The Tables 4–6 nested sub-tables are emitted mechanically; the user is expected to enrich the `**Query Parameters:**` Descriptions, Table 5 Validation prose, and any domain-rule annotations by hand after generation — and a regen of the affected sub-block discards those enrichments. The blast radius is *small* (a domain-only change touches at most a handful of `**Nested:**` sub-tables and the `include` / `Constructed from …` rows, not whole tables), but it's non-zero — worth flagging.
- **The Shared domain types registry is not a domain-diagram surface.** `Pagination`, `PaginatedResultMetadataInfo`, `ResultSetInfo` are hard-coded in `response-fields-writer` / `request-fields-writer` / `parameter-mapping-writer`. Changes to those types are plugin-source changes, not domain-diagram changes; they never appear in `updates.md` and are picked up only by re-running `/rest-api-spec:generate-specs` after a plugin upgrade.
- **Code regen.** This concern stops at the spec. The per-surface serializer modules, endpoint modules, the FastAPI app wiring (`entrypoint.py`, `constants.py`, the aggregator `__init__.py` files, `api/auth.py`), the test fixtures (`tests/conftest.py`), and the integration tests are owned by `/rest-api-spec:generate-code` — a separate updater concern. (Some of those agents — `app-integrator`, `tests-implementer`, `test-fixtures-preparer`, the serializer implementers — are already additively idempotent, which eases a future `/rest-api-spec:update-code`.)
- **Concurrent updaters.** Two operators on parallel branches both re-running the updater produce a normal Git merge conflict on `spec.md`, resolved by standard merge tooling. Not an updater bug.

---

## Dispatch tiers for a rest-api-spec updater

Three natural tiers fall out of the type list, mirroring the domain / persistence / application dispatch tiers:

1. **Hard-fail** — aggregate-root removal / stereotype-demotion / rename, any stereotype change, degraded baseline. Operator runs `/rest-api-spec:generate-specs`. *Sub-case — abort-and-reconcile:* a `<<Query DTO>>` / `<<Value Object>>` / `<<Domain TypedDict>>` / `<<Command>>` renamed-or-removed-while-still-referenced by an app-service method signature; operator reconciles the commands/queries diagram, then re-runs.
2. **Regen the affected Table 4/5/6 sub-blocks** — `data-structures` / `value-objects` / (rare `commands`) member changes on a type that *is* referenced by an app-service method's return / parameter / composite-query-param type (cross-checked against `<stem>.commands.md` / `<stem>.queries.md`): re-run `response-fields-writer` (Table 4 — response sub-tables, nested sub-tables, the `include` query-param row) and/or `request-fields-writer` (Table 5 — request sub-tables, nested sub-tables) and/or `parameter-mapping-writer` (Table 6 — the `Constructed from query params … → <Type>` source line for a composite param type whose field list changed). Never re-run `endpoint-tables-writer` or `resource-spec-initializer` for a domain-only change. If splicing rather than wholesale re-running: replace only the touched `**Nested:**` sub-tables, the touched `**Query Parameters:**` rows, and the touched Table 6 source lines; leave everything else byte-identical.
3. **No-op** — `affected_categories` empty; or `⊆ {domain-events, commands (with no Table 5 nested-type reference to the changed `<<Command>>`), aggregates (non-root-identity), repositories-services}`; or any pure prose change (always byte-neutral for the REST spec); or a bounded-context `title:` rename; or a domain-only `tenant_id` flip; or a `data-structures` / `value-objects` change to a type that no app-service method signature references.

The lighter "no-op" tier is the persistence equivalent of the `domain-spec` "C3 empty footer" early-exit, and is hit *more often* here than in any other downstream updater — the domain diagram's contribution to the REST spec is so narrow that the median domain change leaves `spec.md` byte-identical. The middle "regen the affected sub-blocks" tier is the only tier that touches the spec on a domain-only change, and its regen unit is the smallest of any downstream updater (per-`**Nested:**`-sub-table / per-composite-row, not per-side or per-section).

Per the chaining contract in `application-spec/notes/spec-updater-approach.md` ("The same chaining shape extends to `rest-api-spec` and `messaging-spec` updaters as Steps 11, 12"), this updater is anticipated as **Step 11 of domain `/update-specs`** — opt-in by file presence (`<stem>.rest-api/spec.md` exists), reading the same `<stem>.domain/updates.md`, and also independently invocable. The chained step covers only the domain-driven axis above; the commands/queries-diagram axis remains a separate trigger (the shared `application-spec:updates-detector` invocation discussed above, or a fresh `/rest-api-spec:generate-specs` run).
