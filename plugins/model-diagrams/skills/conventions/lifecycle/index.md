---
name: lifecycle
description: Diagram conventions for aggregate lifecycle, soft-delete and concurrency — enabled/active flags, Status VO, ready/evo gates, remove(), epoch_token (authoring + review).
user-invocable: false
---

# Lifecycle, soft-delete & concurrency

**Applies to:** domain diagrams

> This theme governs how an aggregate models its lifecycle: soft-delete (the `enabled` / `active` flag), multi-state and async-progress lifecycles (the `Status` Value Object), fallible service outcomes (Either VOs), hard-delete (`remove()` + repository `delete()`), readiness/version **gates**, and optimistic-concurrency (`epoch_token`). Pick the mechanism that matches the aggregate's nature — catalog/reference aggregates soft-delete; event-rich pipeline aggregates hard-delete and gate — and pin the read semantics in prose.

## Conventions

### Soft-delete via `enabled: bool` with paired `enable()` / `disable()`
- **Rule:** Model ordinary soft-delete as a private `-enabled: bool` on the aggregate root, mutated by paired parameterless `enable() None` / `disable() None`. Records are never physically removed — the command repository exposes only `save()`, never `delete()`. Surface `enabled` as a field on `<X>Info` and `Brief<X>Info`, and as an all-optional filter `enabled: bool | None` on `<X>Filtering`. Do not also carry a `remove()` / `delete()` path on an `enabled`-flag aggregate.
- **Notation:**
  ```
  class CacheType {
    <<Aggregate Root>>
    -enabled: bool
    +enable() None
    +disable() None
  }
  class CacheTypeFiltering {
    <<TypedDict>>
    +enabled: bool | None
  }
  class CommandCacheTypeRepository {
    <<Repository>>
    +save(cache_type: CacheType) None
  }
  ```
- **Example:** `CacheType.-enabled: bool` with `+enable() None` / `+disable() None`, `CacheTypeFiltering.+enabled: bool | None`, and a `CommandCacheTypeRepository` exposing only `save(...)` (no `delete`) — from `cache-type.md`.
- **You may:** make `enable()`/`disable()` **idempotent and event-emitting** — a no-op when already in the target state, emitting `<Aggregate>Enabled` / `<Aggregate>Disabled` (with the narrower `{id, code}` envelope) only on a real transition, drawn `<Root> --> <Aggregate>Enabled : emits (enable)`; you may add the cross-cutting guard *"All public operations other than `enable` and `disable` raise `<Aggregate>IsDisabled` when `enabled` is `False`"*; or you may use the plain non-event skeleton (lookup → call → save → publish) with no lifecycle events at all.
- **Review:** treat the `enabled` + `enable()`/`disable()` + save-only-repository shape as canonical — do not flag the absence of a `delete()` as a missing capability, and do not flag idempotent no-op `enable()`/`disable()` or the `<Aggregate>IsDisabled` cross-cutting guard as non-standard.

### `active: bool` (`activate()` / `deactivate()`) — narrow gate on one operation
- **Rule:** When a soft-delete-style flag must gate one *specific* operation rather than hide the record from reads, name it `-active: bool` and toggle it with `activate() None` / `deactivate() None` (each sets the flag and bumps `updated_at`). State in prose exactly which operation the flag gates — `active` does **not** hide the record from list/get reads.
- **Notation:**
  ```
  class ConversionReqs {
    <<Aggregate Root>>
    -active: bool
    +activate() None
    +deactivate() None
    +retry() None
  }
  ```
- **Example:** `ConversionReqs.-active: bool` with `activate()`/`deactivate()`; `active == False` makes `retry()` raise `InactiveConversionReqsError` and do no work, while event-driven `add_domain_model` / `add_error` run regardless — from `conversion.md`'s sibling `conversion-reqs` aggregate (notes corpus).
- **You may:** run `active` **alongside** a per-entity `Status` VO (dual-axis: `active` is the soft-delete-ish axis, `Status` the progress axis).
- **Review:** treat `active`/`activate()`/`deactivate()` as a sanctioned narrower-than-soft-delete idiom — do not propose renaming it to `enabled`/`enable`/`disable`, and do not assume it hides the record. Flag only if the gated operation is left undocumented in prose.

### `Status` `<<Value Object>>` for multi-state and async-inference lifecycles
- **Rule:** Model a genuine multi-state lifecycle as a `Status` `<<Value Object>>` holding a `Literal`-typed private `status` plus `is_*` bare-bool derived properties (no parentheses). Transition by **replacing the whole VO** through factories — never mutate in place. Compose any error payload as `Status *-- "0..n" <X>Error`. Flatten the VO into read models as a scalar `status` key plus split-out flag/error fields.
- **Notation:**
  ```
  class Status {
    <<Value Object>>
    -status: Literal["pending", "completed", "failed"]
    -fields_derived: bool
    -fields_resolved: bool
    -errors: list[InferenceError] | None
    +is_pending: bool
    +is_completed: bool
    +is_failed: bool
    +pending() Status$
    +cleared() Status
    +with_derived_fields() Status
    +with_resolved_fields() Status
    +failed(errors: list[InferenceError]) Status
  }
  Status *-- "0..n" InferenceError
  ```
- **Example:** `mapping.md`'s multi-axis `Status` (a `Literal["pending","completed","failed"]` plus two orthogonal progress booleans `fields_derived`/`fields_resolved` plus `errors: list[InferenceError] | None`), advanced by accumulating builder factories `pending()`, `cleared()`, `with_derived_fields()`, `with_resolved_fields()`, `failed(errors)`. The single-axis form is `ruleset.md`'s `Status` (`status: Literal["pending","completed","failed"]` with one factory effect per transition).
- **You may:** use **one named factory per terminal state** (`created()` / `completed()` / `failed(error)`) for an ordered state machine, **or** accumulating `with_<field>()` builders plus `pending()`/`cleared()`/`failed(errors)` for an orthogonal-progress async pipeline; expose extra list-typed projection properties on a derived-and-materialized `Status` (e.g. `inferred_stages`, `error_stages`, `stages_to_re_infer`, plus private `mapping_rules_inferred` / `mappings_inferred` flags as in `ruleset.md`); and use an `<X>Error` `<<TypedDict>>` payload that breaks the `Data`/`Info`/`Brief` suffix family and carries a `retryable: bool` + a `stage: Literal[...]` discriminator (`InferenceError { code, message, retryable: bool, stage: Literal["derivation","resolution"] }` in `mapping.md`; lighter `ParsingError { code, message }` in conversion-reqs).
- **Review:** treat a `Status` VO transitioned by wholesale factory replacement as canonical — do not flag mutating-method-free Status, do not flag accumulating `with_*` builders as "not one-factory-per-state", and do not flag the `<X>Error` payload for breaking the Data/Info/Brief role-suffix family. The `is_*` bare-bool **properties** (no `()`) are canonical; reserve `()` for repository/collection-VO predicate methods.

### Result-or-error (Either) `<<Value Object>>` for service outcomes
- **Rule:** Model a fallible service outcome as a result-or-error `<<Value Object>>` with two mutually-exclusive `Optional` fields (a result and an error) and a boolean gate the application service forks on to take exactly one of two paths. Do not conflate this with a plain pair/decision VO — a service-outcome VO is not automatically an Either.
- **Notation:**
  ```
  class ParsingResult {
    <<Value Object>>
    -result: DomainModelData | None
    -error: ParsingError | None
    +has_error: bool
    +as_result(domain_model: DomainModelData) ParsingResult$
    +as_error(error: ParsingError) ParsingResult$
  }
  ```
- **Example:** `conversion-reqs`'s `ParsingResult` (`-result: DomainModelData | None` + `-error: ParsingError | None`, gate `has_error`, factories `as_result(...)` / `as_error(...)`); `ruleset.md`'s `InferencedMappingRules` / `InferencedMappings` use list-typed `result`/`errors` arms with factories `as_result(...)$` / `with_errors(...)$` and a **plural** `has_errors` gate.
- **You may:** spell the factory/gate either `as_result`/`as_error` + `has_error` (singular, single-result outcome) or `as_result`/`with_errors` + `has_errors` (plural, batched list outcomes) — pick one consistently per VO; carry list-typed arms (`result: list[...] | None` + `errors: list[InferenceError] | None`).
- **Review:** treat a two-optional-fields-plus-boolean-gate VO as the canonical Either idiom — do not flag it as "inconsistent optionality". A plain two-field decision VO (e.g. `RulesetCreationDecision { is_ready: bool, description: str }` from `conversion.md`) is **not** an Either and must not be flagged for lacking the two-optional-arms/`has_error`/`as_result` shape.

### Hard-delete via `remove()` + repository `delete()` (event-rich pipeline aggregates)
- **Rule:** For event-bearing pipeline aggregates that are physically retired (not soft-hidden), expose a behavioral `remove() None` that emits a `<Aggregate>Removed` domain event, backed by a command-repository `delete(<aggregate>)`. Draw the event with `<Root> --> <Aggregate>Removed : emits (remove)`. Pair it with a *gate* governing when the aggregate becomes actionable (ready-gate / evo-version gate / epoch-token, below). Do **not** also carry an `enabled` flag on a hard-delete aggregate.
- **Notation:**
  ```
  class CommandConversionRepository {
    <<Repository>>
    +save(conversion: Conversion) None
    +delete(conversion: Conversion) None
  }
  class Conversion {
    <<Aggregate Root>>
    +remove() None
  }
  Conversion --> ConversionRemoved : emits (remove)
  ```
- **Example:** `conversion.md` — `Conversion.+remove() None`, `Conversion --> ConversionRemoved : emits (remove)`, and `CommandConversionRepository` exposing both `save(...)` and `delete(conversion)`. `ruleset.md` is the same shape (`Ruleset.+remove() None`, `CommandRulesetRepository.+delete(ruleset)`).
- **You may:** combine `remove()`+`delete()` with a `Status` VO and an `epoch_token` gate on the same aggregate (as `ruleset.md` does — three lifecycle mechanisms at once); use raw boolean flags (`ruleset_created`) toggled by a `mark_*_as_created()` mutator emitting a completion event instead of a Status VO (as `project` does).
- **Review:** treat `remove()` + repository `delete()` (with no `enabled` flag) as the canonical lifecycle for retired-not-hidden event-rich aggregates — do not flag the presence of `delete()`, and do not propose adding a soft-delete `enabled` flag to a hard-delete aggregate.

### Readiness / version **gates** governing when work fires
- **Rule:** Where an aggregate must accumulate state before it may act, model the gate as a **derived `bool` property** over monotonic fields, not a stored status. A two-flag ready-gate is `ready = <derived bool over a nullable field> AND <one-time monotonic latch>`. The gate controls **event emission** (and downstream triggering), not the state mutation — mutations always run; only the events are suppressed until the gate opens. The latch only ever transitions `False → True` and never reverts.
- **Notation:**
  ```
  class Conversion {
    <<Aggregate Root>>
    -evo_version: str | None
    -can_be_converted: bool
    +has_evo_version: bool
    +ready: bool
    +update_evo_version(evo_version: str) None
    +record_convertibility(is_ready: bool, description: str) None
    +force_convertibility(email: str, description: str) None
  }
  ```
- **Example:** `conversion.md` — `ready = has_evo_version AND can_be_converted`, where `+has_evo_version: bool` is derived over `-evo_version: str | None` and `-can_be_converted: bool` is a one-time `False→True` latch; the five `Process`-level events stay suppressed until `ready` is `True`, and "whichever completes the pair second fires the burst". `project`'s `-evo_version: str | None` write-once-then-update gate plus a `rulesets_created` bool is the same family.
- **You may:** drive a single latch from two setters with asymmetric no-op semantics — an AI path (`record_convertibility`, which refreshes its provenance VO even when already latched) and a human-override path (`force_convertibility`, a strict complete no-op once latched, preserving the original decider's provenance); set the version field write-once-then-update with an idempotency guard, never clearing it back to `None`.
- **Review:** treat a derived-boolean gate that suppresses event emission while letting state mutations run as canonical — do not flag "events not emitted on every mutation" when an aggregate-level ready-gate invariant is declared, and do not flag the dual-setter (AI + human-override) latch or its asymmetric no-op semantics as inconsistent.

### `epoch_token: int` optimistic-concurrency gate
- **Rule:** For an aggregate whose writes arrive out-of-band from asynchronous workers (event-driven inference write-backs), carry a root-held monotonic `-epoch_token: int`. Every (re)trigger increments it; every write-back takes an `epoch_token` argument, accepts only when it equals the aggregate's current token, and rejects a superseded epoch by raising `<Aggregate>EpochSuperseded`. A complete no-op must **not** increment the token (same-stage idempotency). Draw the rejection on the root as `<Root> --() <Aggregate>EpochSuperseded : raises`.
- **Notation:**
  ```
  class Ruleset {
    <<Aggregate Root>>
    -epoch_token: int
    +add_mapping_rules(mapping_rules: list[MappingRuleData], epoch_token: int) None
    +add_errors(errors: list[InferenceError], epoch_token: int) None
    +retry() None
  }
  Ruleset --() RulesetEpochSuperseded : raises
  ```
- **Example:** `ruleset.md` — `-epoch_token: int` incremented by every (re)trigger (`add_files` / `add_file` / `remove_file` / `change_file_stage` / `retry`) and checked by every write-back (`add_mapping_rules` / `add_mappings` / `add_errors` / `update_mapping_rule` / `update_mapping`, each carrying an `epoch_token: int` parameter), with `Ruleset --() RulesetEpochSuperseded : raises`.
- **You may:** layer `epoch_token` on top of a `Status` VO and `remove()` hard-delete on the same aggregate; have collection-VO mutators return a `bool` changed-signal (`Files.add_files(...) bool`, `add_file(...) bool`, `remove_file(...) bool`, `change_file_stage(...) bool`) so the root branches on "did it actually change" before advancing `epoch_token` / emitting — distinct from the corpus-wide `None`-returning collection mutators.
- **Review:** treat `epoch_token` + per-write-back `epoch_token` arguments + `<Aggregate>EpochSuperseded` as the canonical concurrency-safety model — do not flag the `bool`-returning collection mutators as deviating from `None`-return, and do not flag "token not incremented" on a documented complete no-op.

### Forward-only async-progress lifecycle (no soft-delete, no delete)
- **Rule:** An aggregate may legitimately model only **forward progress** — neither a soft-delete flag, nor an evo/ready gate, nor `epoch_token`, nor `remove()`. Its sole lifecycle surface is a `Status` VO advancing through an async pipeline. Such an aggregate may be structural-only: the diagram carries the contract (Literal types, cardinalities, `| None` on `Status.errors`) with no `## Invariants`, empty `.commands`/`.queries` stubs, and no `<<Repository>>`.
- **Notation:**
  ```
  class Mapping {
    <<Aggregate Root>>
    -status: Status
    +new(...) Mapping
  }
  Mapping *-- "1" Status
  ```
- **Example:** `mapping.md` — the root carries only `-status: Status` (plus details VOs) and a single `new(...)` factory, with no `enabled`/`active`, no evo/ready gate, no `epoch_token`, and no `remove()`; lifecycle is exclusively the multi-axis `Status` VO. `evo_version` is held as data inside `MappingDetails` but is **not** a gate (no `has_evo_version` derived boolean).
- **You may:** leave the aggregate pre-pipeline (hand-authored, structural-only) with no repository/query/ops artifacts yet; hold `evo_version` as plain data without making it a lifecycle gate.
- **Review:** treat a forward-only aggregate whose only lifecycle surface is a `Status` VO as canonical — do not flag the absence of a soft-delete flag, `remove()`, repository, query side, or `## Invariants` as missing; a structural-only domain file is a legitimate pre-`/generate-*` state.

### Soft-delete read semantics: list-hides / get-shows
- **Rule:** For **every** `enabled`-flag aggregate, pin the read contract in prose. **List path hides:** the query-side plural `find_<x>s` excludes `enabled=False` by default (filter unset / `None` ⇒ enabled-only), overridable via `<X>Filtering.enabled`, and `total` reflects the *filtered* set. **Get path shows:** single-id lookups never hide soft-deleted rows — both the command-side `<x>_of_id(...)` and the query-side singular `find_<x>(...)` return the record **regardless** of `enabled`, so a disabled record stays loadable and re-activatable. **Uniqueness checks include disabled:** `has_*_with*(...)` / `*_id_with_*(...)` count `enabled=False` records so codes/names stay reserved after soft-delete.
- **Notation:**
  ```
  class CommandDomainTypeRepository {
    <<Repository>>
    +domain_type_of_id(id: str) DomainType | None
    +has_domain_type_with_code(code: str) bool
    +domain_type_id_with_name(name: str) str | None
  }
  class QueryDomainTypeRepository {
    <<Repository>>
    +find_domain_type(domain_type_id: str) DomainTypeInfo | None
    +find_domain_types(filtering: DomainTypeFiltering | None, pagination: Pagination | None) DomainTypeListResult
  }
  class DomainTypeFiltering {
    <<TypedDict>>
    +enabled: bool | None
  }
  ```
  Prose invariant (under `## Invariants`):
  ```markdown
  ### QueryDomainTypeRepository.find_domain_types
  - Excludes `enabled=False` records by default; opt in via `DomainTypeFiltering.enabled=False`.
  - `total` reflects the filtered set.

  ### CommandDomainTypeRepository
  - `domain_type_of_id(id)` returns the aggregate regardless of `enabled` (so `enable()` can re-activate).
  - `has_domain_type_with_code` / `domain_type_id_with_name` include `enabled=False` records.
  ```
- **Example:** `domain-type` pins the full split (notes corpus); `mapping-rule` pins it as *"single-id lookups never hide soft-deleted rows"* (both `mapping_rule_of_id` and `find_mapping_rule` return regardless of state). `cache-type.md` carries it structurally: `CacheTypeFiltering.+enabled: bool | None` plus a `cache_type_of_id(...)` that loads regardless of state.
- **You may:** pin it in full prose (the reference exemplars), or carry it structurally via the `enabled` filter field plus a regardless-of-state command-side `*_of_id` lookup. Not applicable to hard-delete (conversion / project / ruleset) or forward-only (mapping) aggregates — they have no soft-delete read split.
- **Review:** treat the list-hides / get-shows split as a required, load-bearing prose invariant for every `enabled`-flag aggregate (the query-side code generator consumes it) — do not flag a singular `find_<x>` / `*_of_id` that returns a disabled record as a bug, and do not flag uniqueness checks that count disabled records.

## Pitfalls
- **Mixing soft- and hard-delete.** Do not put both an `enabled` flag and a `remove()`/`delete()` path on one aggregate — soft-delete (catalog/reference aggregates) and hard-delete (event-rich pipeline aggregates) are mutually exclusive choices. The soft-vs-hard split tracks the soft-CRUD-vs-event-pipeline split exactly.
- **Modeling lifecycle as an `Enum` or magic string.** Multi-state lifecycles are always a `Status` `<<Value Object>>` (a private `Literal`-typed `status` + `is_*` properties), never a bare `Enum` field or string constant.
- **Mutating a `Status`/Either VO in place.** State changes go through wholesale factory replacement (`pending()`, `with_*()`, `failed(errors)`, `as_result()`/`as_error()`), never an in-place field write on the VO.
- **`is_*` as a method.** Derived state checks on `Status`/result VOs are bare-`bool` **properties** with no parentheses; `()` is reserved for repository / collection-VO predicate methods.
- **Confusing `active` with full soft-delete.** `active: bool` gates one named operation and does **not** hide the record from reads; never assume `active == False` suppresses list/get visibility, and always document which operation it gates.
- **Calling a service-outcome VO an Either.** A two-field decision VO (`is_ready: bool` + `description`) is not an Either — only a VO with two mutually-exclusive optional arms and a boolean gate is.
- **Stored status instead of a derived gate.** A readiness/version gate is a derived `bool` property over monotonic fields, not a stored status field; the gate suppresses *events*, never the state mutation itself.
- **Incrementing `epoch_token` on a no-op.** A complete no-op (idempotent file mutation, redelivered write-back, empty retry) must not advance `epoch_token`; only a genuine (re)trigger increments it.
- **Inconsistent `$` static-marking within one VO.** Mark every static factory on a `Status`/Either VO with the trailing `$` consistently — do not leave `pending() Status$` marked while `with_*`/`cleared`/`failed` are unmarked.
- **Dangling references into a soft-deleted / commented-out lifecycle type.** When a forward-only aggregate is structural-only, do not leave active edges pointing at types that are not modeled live.
