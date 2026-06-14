---
name: typed-dicts
description: Authoring and review conventions for the TypedDict / DTO family in domain diagrams — Data/Info/Brief/Full*Info/Filtering/ListResult role suffixes, VO flattening, shared dicts, *Error payloads.
user-invocable: false
---

# TypedDicts / DTOs

**Applies to:** domain (Data shapes), queries (read-model family)

> This theme governs every `<<TypedDict>>` class in a domain diagram and its query side: how you name the read-model/DTO family off the aggregate stem, how you flatten domain value objects into DTO keys, when you share one dict across the command and query sides, and how you model error payloads. All TypedDict members are public (`+`).

## Conventions

### Role-suffixed TypedDict family
- **Rule:** Name every read-model/DTO `<<TypedDict>>` off the aggregate stem by its role: `<X>Data` (flat write-side input or event-payload snapshot), `<X>Info` (full read model, with nested `<Child>Info` mirroring composition), `Brief<X>Info` (trimmed list-row read model that drops nested collections / bulk fields), `<X>Filtering` (all-optional filter inputs), `<X>ListResult` (the collection-read wrapper). The full `Info`/`Brief`/`Filtering`/`ListResult` query family is present iff the aggregate has a query side.
- **Notation:**
  ```
  class CacheTypeInfo {
    <<TypedDict>>
    +id: str
    +code: str
    +name: str
    +lookups: list[LookupInfo]
    +enabled: bool
    +created_at: datetime
    +updated_at: datetime
  }
  ```
- **Example:** `CacheTypeInfo` / `BriefCacheTypeInfo` / `CacheTypeFiltering` / `CacheTypeListResult` — from `cache-type.md`.
- **You may:** use `Full<X>Info` as an Info sub-suffix for a rich inference/expansion projection that composes the leaf `*Info` children, distinct from the plain catalog `<X>Info` — e.g. `FullMappingTypeInfo` / `FullCacheTypeInfo` in `ruleset.md`. A `<<Domain Event>>` payload may also reference a `Data` dict directly.
- **Review:** when reviewing a diagram, treat the suffix family as canonical — do not flag it as non-standard. Do not flag the absence of `Brief`/`Filtering`/`ListResult` on an aggregate that has no query side, and do not flag `Full<X>Info` as a misspelled `<X>Info`. The carry-through of `id` / `created_at` / `updated_at` into `Info` and `Brief` rows is canonical.

### `ListResult` = domain-named plural list + `total: int`
- **Rule:** Give `<X>ListResult` exactly two fields: a list named after the plural aggregate noun (not `items` / `results`) typed `list[Brief<X>Info]`, plus `total: int`. Draw the composition to the brief row.
- **Notation:**
  ```
  class CacheTypeListResult {
    <<TypedDict>>
    +cache_types: list[BriefCacheTypeInfo]
    +total: int
  }

  CacheTypeListResult *-- "0..n" BriefCacheTypeInfo
  ```
- **Example:** `CacheTypeListResult { +cache_types: list[BriefCacheTypeInfo]; +total: int }` with `CacheTypeListResult *-- "0..n" BriefCacheTypeInfo` — from `cache-type.md`.
- **You may:** suffix the list field `_list` (e.g. `conversion_reqs_list`) when the bare plural noun would collide with itself; it still pairs with `+total: int`. Flatten paging metadata to a bare `total: int` — you need not model richer paging building blocks in the diagram.
- **Review:** treat the bare `total: int` and the domain-named list field as canonical — do not propose `items` / `results` field names, and do not flag the missing paging-metadata sub-DTO. Do not flag a `<noun>_list` field name on an already-plural aggregate noun.

### All-optional `Filtering`
- **Rule:** Make every field of `<X>Filtering` optional (`<type> | None`) to signal an independently-omittable, unset filter. Mirror a subset of the aggregate's filterable attributes plus the lifecycle key.
- **Notation:**
  ```
  class CacheTypeFiltering {
    <<TypedDict>>
    +name: str | None
    +enabled: bool | None
  }
  ```
- **Example:** `RulesetFiltering` carries `+process_id: str | None` … `+status: Literal["pending", "completed", "failed"] | None` (every field optional) — from `ruleset.md`.
- **You may:** track the aggregate's lifecycle style with the lifecycle filter key rather than hard-coding `enabled` — use `status | None` (Status-VO aggregates), `can_be_converted | None` (gate aggregates), or `enabled | None` (soft-delete aggregates). The optional value may be a `Literal[...] | None`.
- **Review:** an all-optional `Filtering` is canonical — do not flag a `Filtering` field for "missing required marker" or propose making any field non-optional. Do not flag a `status`/`can_be_converted` lifecycle key as a wrong substitute for `enabled`.

### VO flattening into read models
- **Rule:** In `Info` / `Brief` read models, flatten domain value objects into top-level scalar keys rather than nesting the VO — a Details VO's fields appear directly on the `Info` dict, and a Status VO collapses to its `status` literal. Mirror nested *child collections* as nested `<Child>Info` (never the domain entity), drawn with composition.
- **Notation:**
  ```
  class CacheTypeInfo {
    <<TypedDict>>
    +id: str
    +code: str
    +name: str
    +lookups: list[LookupInfo]
    ...
  }

  CacheTypeInfo *-- "1..n" LookupInfo
  ```
- **Example:** `CacheTypeInfo *-- "1..n" LookupInfo` nests the child `LookupInfo` read model while hoisting the `code` / `name` scalars onto the parent — from `cache-type.md`.
- **You may:** flatten a Status VO to its `status` literal **plus** any orthogonal progress/error fields and `is_*` derived booleans, not just a single `status: str` — e.g. `BriefRulesetInfo` surfaces `status` together with `mapping_rules_inferred` / `mappings_inferred` / `is_pending` / `is_completed` / `is_failed` (`ruleset.md`). A child read model need not mirror its domain entity field-for-field (it may drop a domain-only flag).
- **Review:** flattening a Details VO to scalar keys, and expanding a Status VO into `status` + progress/error/`is_*` fields, is canonical — do not flag "VO not represented" or propose nesting the VO as its own dict. Do not flag a multi-field Status projection as redundant, nor a child `Info` that omits a domain-only attribute.

### Shared TypedDict across command and query sides
- **Rule:** When a write-side (or event-payload) shape and a read-side shape are structurally identical, model **one** shared `<<TypedDict>>` reused on both sides rather than defining parallel `Data` and `Info` leaves. Only do this when the shapes are genuinely identical.
- **Notation:**
  ```
  class CategoryData {
    <<TypedDict>>
    ...
  }

  Ruleset *-- "1" CategoryData
  RulesetInfo --() CategoryData
  ```
- **Example:** `CategoryData` is composed by the command-side `Ruleset *-- "1" CategoryData` and referenced by the read-side `RulesetInfo --() CategoryData`, with no separate `CategoryInfo` twin — from `ruleset.md`. `FileData` is likewise reused across the `Files` collection VO and `RulesetInfo.files`.
- **You may:** keep parallel, non-reused `Data` and `Info` shapes when they are not genuinely identical — sharing is the deliberate exception, not the default.
- **Review:** a single dict appearing on both the write and read sides is canonical — do not flag it as a missing `Info`/`Data` split or as a layering leak. Do not propose forking a shared dict into parallel command/query twins.

### `*Error` payload dicts
- **Rule:** Model an error/failure payload as a flat `<X>Error` `<<TypedDict>>` — it is deliberately outside the `Data`/`Info`/`Brief`/`Filtering`/`ListResult` suffix family. For async/staged inference pipelines, give it a `retryable: bool` flag and a `stage: Literal[...]` discriminator so consumers can route retries by stage.
- **Notation:**
  ```
  class InferenceError {
    <<TypedDict>>
    +code: str
    +message: str
    +retryable: bool
    +stage: Literal["mapping-rules", "mappings"]
  }
  ```
- **Example:** `InferenceError { +code; +message; +retryable: bool; +stage: Literal["mapping-rules", "mappings"] }` — from `ruleset.md` (the `stage` vocabulary is per-pipeline; `mapping.md`'s `InferenceError` uses `stage: Literal["derivation", "resolution"]`).
- **You may:** use a plain `<X>Error { code, message }` (no `retryable` / `stage`) for a non-staged error payload — e.g. a `ParsingError` carried by an Either VO. The `stage` literal vocabulary is per-aggregate, tracking that pipeline's own stages.
- **Review:** an `*Error` dict that carries no role suffix is canonical — do not flag it as a misnamed `Data`/`Info` member or demand a suffix. Treat the `retryable: bool` + `stage: Literal[...]` discriminator as the canonical async-inference error shape; do not flag it, and do not require it on a non-staged `{code, message}` error.

### `as_data()` flat-snapshot accessor
- **Rule:** When an aggregate or VO needs a flat snapshot (event payload or write-side / AI-input projection), expose it as `as_data()` returning the matching `<X>Data` TypedDict; draw `<Class> --> <X>Data : returns`. The field set normally mirrors the stored fields one-to-one.
- **Notation:**
  ```
  +as_data() DomainTypeData

  DomainType --> DomainTypeData : returns
  ```
- **Example:** `DomainType.as_data() DomainTypeData` with `DomainType --> DomainTypeData : returns`; `conversion.md` exposes the accessor on several classes (`Conversion.as_data`, `Processes.as_data`, `Process.as_data`, …).
- **You may:** model an `<X>Data` write / event-payload family with **no** round-tripping `as_data()` accessor (only model `as_data()` where a flat snapshot is genuinely needed). You may also make `as_data()` a **deliberately lossy** projection that drops fields — e.g. `Conversion.as_data()` omits `ready` / `can_be_converted` / the `Convertibility` VO so an AI consumer never sees its own prior verdict.
- **Review:** an `as_data()` returning `<X>Data` with a `--> ... : returns` edge is canonical — do not flag it. Do not flag a lossy `as_data()` projection as "incomplete" against the stored field set, and do not require an `as_data()` accessor wherever an `<X>Data` family exists.

## Pitfalls
- Do not invent off-family suffixes (`<X>DTO`, `<X>Response`, `<X>Record`) — the only sanctioned suffixes are `Data` / `Info` / `Brief<X>Info` / `Full<X>Info` / `Filtering` / `ListResult`, plus the deliberately-unsuffixed `<X>Error`.
- Do not name the `ListResult` list field `items` / `results` / `data` — it is the plural aggregate noun (with `_list` only on a self-colliding plural), always paired with `total: int`.
- Do not leave any `Filtering` field non-optional — every field is `| None`; one required field defeats the partial-filter contract.
- Do not nest a domain value object inside an `Info` dict — flatten its scalars onto the parent; reserve nested dicts for child *collections*, which become `<Child>Info` (never the raw domain entity).
- Do not collapse a multi-axis Status VO to a single `status: str` in the read model when it carries orthogonal progress/error flags — surface those alongside the literal.
- Do not fork a genuinely-identical write+read shape into parallel `Data` and `Info` twins — share one dict; conversely, do not share a dict when the two shapes only happen to overlap today.
- Do not attach `retryable` / `stage` to a non-staged error payload, and do not omit them from an async-inference error that consumers must route by stage.
- Do not reference an `<X>Info` / `*FieldInfo` that lives only inside a `%%`-commented block — a live `from_info(...)` factory or lollipop pointing into a commented-out read-model tree is a dangling reference to resolve before the diagram is consistent.
