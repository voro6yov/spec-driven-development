---
name: naming
description: Naming conventions for STPS domain/commands/queries/ops diagrams — factories, mutators, ids, repo finders, predicates, app-service method names; authoring + review.
user-invocable: false
---

# Naming

**Applies to:** domain (factories/mutators/ids), commands/queries/ops (method naming)

This theme governs how members are *named* across a diagram set: the static `new(...)$` factory and its intent-named alternates, imperative `None`-returning mutators, the fixed predicate/lookup/guard prefixes, the repository finder vocabulary, identity (`id`) and timestamp placement, member visibility, and the application-layer `create`/`on_<event>` method names. Walk it as a checklist when authoring; consult it before flagging any name as non-standard during review.

## Ground knowledge

*Why these conventions are what they are — the canonical patterns behind the fixed names, and the project's one notable identity departure. Names and sources let a reviewer cite the principle behind a suppression rather than assert it.*

- **Member names are the Ubiquitous Language** (Evans; Vernon; Khononov): class and prominent-operation names *are* the model's vocabulary, so the fixed prefixes are model decisions ("no synonymous / no ambiguous terms"), not style to relitigate on review.
- **`new()$` + intent-named alternates = the Factory pattern** (Evans; Vernon, *IDDD* ch.11). A factory is *atomic* (only ever returns a fully-valid object) and *hides internal structure* (callers pass flat primitives, never pre-built VOs — the primitive-obsession cure). The non-validating `from_*` / `with_id` family is the **reconstitution** branch: it does not mint identity and trusts the persistence layer — which is *why* skipping validation is the contract, not a bug.
- **Imperative-`None` mutators + bare-`bool` `is_*`/`has_*` = Command-Query Separation** (Meyer; Evans ch.10): commands change state and return no domain data; queries are pure and drop the `get` prefix. `ensure_*` is the residual guard *command* (raises, returns `None`), not a mistyped predicate.
- **`create` (app) vs `new` (domain)** is the application-service-wraps-domain-factory layering; `on_<event>` upsert handlers that never raise NotFound are canonical idempotent upserts under at-least-once delivery.
- **Deliberate divergence — bare-`str` `id` instead of a typed Id Value Object.** Canon is emphatic that identity be wrapped in a typed, format-verified Id VO (Vernon; Lawrence) so `UserId` ≠ `OrderId` at compile time. The project trades that mixing-protection and per-id validation for diagram/code simplicity — a conscious simplification worth naming as such. (The caller-supplied-`id` carve-out is itself canonical: a client/outside-actor-supplied id enables idempotent command processing.)

## Conventions

### Primary factory is a static `new(...)$` returning the owning type
- **Rule:** Expose construction as a public static factory named `new(...)` that returns the owning type and is marked with a trailing `$` (the Mermaid static marker). `new(...)` validates its inputs; `id`, `created_at`, and `updated_at` are assigned internally and are **never** `new()` parameters (the `Mapping` exception below is the one carve-out for `id`).
- **Notation:**
  ```
  class DomainType {
    <<Aggregate Root>>
    +new(code: str, name: str, description: str) DomainType$
  }
  ```
- **Example:** `+new(code: str, name: str, lookups: list[LookupData]) CacheType$` — from `cache-type.md`. Child VOs follow suit: `+new(name: str, type: str) LookupArgument$`.
- **You may:** caller-supply `id` as the first `new()` parameter when identity is externally governed rather than minted — e.g. `+new(id: str, evo_version: str, …) Mapping` from `mapping.md`. When you do, `created_at`/`updated_at` still stay out of the parameter list.
- **Review:** treat `new(...)$` returning the owning type as canonical. Do not flag a factory named `new` (rather than the class name) or the trailing `$`. The `$` is the static marker — its absence is the only sanctioned thing to note, not its presence.

### Alternate constructors are intent-named and `$`-marked
- **Rule:** Name non-primary constructors by intent and mark them static (`$`): `empty()` for an empty collection, `from_list(<plural>)` to rehydrate a collection, `from_data(<x>_data)` / `from_info(<x>_info)` to build a VO/entity from a flat TypedDict, `with_id(id, …)` when an externally-supplied id is trusted. Rehydration factories are non-validating — they trust the persistence layer and skip the `new()` invariants. Use the plural name for the `from_list` parameter (`from_list(source_fields)`, not `from_list(source_field)`).
- **Notation:**
  ```
  class ResolvedFields {
    <<Value Object>>
    +empty() ResolvedFields$
    +from_list(resolved_fields: list[ResolvedField]) ResolvedFields$
  }
  ```
- **Example:** `+from_list(resolved_fields: list[ResolvedField]) ResolvedFields$` and `+empty() ResolvedFields$` — from `mapping-type.md`; `+with_id(id: str, derived_fields_ids: list[str], cache_type_code: str, lookup_code: str) ResolvedField$` (id-preserving swap, same file); `+from_info(mapping_type_info: MappingTypeInfo) MappingType$` — from `mapping.md`.
- **You may:** use `empty()` as the construction entry for a `0..n` collection VO while its `1..n` siblings use `new()$` (the bound drives the choice). Flat or directly-composed aggregates with no round-trip (e.g. `domain-type`, `cache-type`) carry only `new()` and need none of these.
- **Review:** treat the whole `empty`/`from_list`/`from_data`/`from_info`/`with_id` family as canonical, including the non-validating rehydration semantics. Do not flag a `from_*`/`with_id` factory for "skipping validation" — that is the rehydration contract. Do not propose collapsing `empty()` into `new()`.

### `new()` takes flat primitives; the aggregate builds VOs internally
- **Rule:** Have `new(...)` accept **flat primitive** arguments and build its value objects internally; never ask callers to pass a pre-constructed VO. Order arguments consistently: identity/context first, then the grouped descriptive scalars that become a Details VO, then collections, then remaining primitives, then timestamps (which are assigned internally, not passed).
- **Notation:**
  ```
  class Mapping {
    <<Aggregate Root>>
    +new(id: str, evo_version: str, category_code: str, file_type: str, domain_type: str, mapping_type_info: MappingTypeInfo, file_id: str, source_fields: list[str], target_domain_attributes: list[str], definition: str, transform: str, function: str) Mapping
  }
  ```
- **Example:** `Mapping.new(...)` (above, from `mapping.md`) takes flat primitives and builds `MappingDetails`/`FileDetails`/`TransformationDetails` internally and `MappingType` via `from_info`; `CacheType.new(code, name, lookups: list[LookupData])` builds `Lookup` entities internally — from `cache-type.md`.
- **You may:** pass a flat TypedDict (`list[LookupData]`, `mapping_type_info: MappingTypeInfo`) where a child is rehydrated from data rather than primitives — it is still flat input, not a pre-built domain VO.
- **Review:** do not flag `new()` for taking "too many primitives" or propose accepting a pre-built Details/VO instead — flat-in, build-internally is the convention.

### Flat read-snapshot via `as_data()` returning `<X>Data`
- **Rule:** When an aggregate or VO needs a flat snapshot (event payload, write-side projection, AI input), expose it as `as_data()` returning the matching `<X>Data` TypedDict, and draw `<Class> --> <X>Data : returns`.
- **Notation:**
  ```
  class DomainType {
    <<Aggregate Root>>
    +as_data() DomainTypeData
  }
  DomainType --> DomainTypeData : returns
  ```
- **Example:** `+as_data() DomainTypeData` with edge `DomainType --> DomainTypeData : returns` — from `domain-type.md`.
- **You may:** project a **lossy** subset deliberately — `as_data()` is not required to mirror the stored fields one-to-one (e.g. dropping a derived verdict so an AI consumer never sees its own prior output fed back). Omit `as_data()` entirely when no flat snapshot is needed; most aggregates have none.
- **Review:** treat `as_data() → <X>Data` as canonical and do not flag a deliberately lossy projection as a "missing field". Only the `--> … : returns` arrow vocabulary (covered in the Relationships theme) is in scope for arrow review.

### State mutators are imperative verbs returning `None`
- **Rule:** Name state-mutating domain methods as imperative verbs — `rename`/`enable`/`disable`/`add_*`/`remove_*`/`update_*`/`change_*`/`mark_*`/`replace_*` — that return `None` and mutate in place. Always annotate the `None` return explicitly. Pair bulk and singular variants on the same verb stem (`add_files` / `add_file`).
- **Notation:**
  ```
  class CacheType {
    <<Aggregate Root>>
    +update_details(name: str) None
    +add_lookup(code: str, name: str, arguments: list[LookupArgumentData] | None, response: list[EntryItemData]) None
    +delete_lookup(id: str) None
    +enable() None
    +disable() None
  }
  ```
- **Example:** `+rename(name: str) None`, `+replace_source_fields(source_fields: list[str]) None`, `+add_resolved_field(...) None`, `+enable() None` — from `mapping-type.md`.
- **You may:** return a `bool` "did-it-change" signal from a collection-VO mutator the root branches on (to advance a version token or decide whether to emit), or return the freshly-created/fetched child entity from an `add(...)` — both are sanctioned idempotency/at-least-once variants. A Status VO may advance via immutable `with_*` builders instead of in-place mutators (see *Status transitions* below); such an aggregate may model no in-place mutators at all.
- **Review:** do not flag an imperative mutator for returning `None`, nor a collection-VO mutator that returns `bool` or the created entity. Do not propose "return the updated aggregate" from a domain mutator — that shape belongs to the application layer, not the domain.

### Lookups, predicates, and guards have fixed prefixes
- **Rule:** Name boolean predicates `has_*` / `is_*` / `converts_*` / `*_matches` returning `bool`; identity lookups `<thing>_of_<key>` / `<thing>_with_<key>` returning `<Thing> | None`; and pure guard assertions `ensure_*` returning `None` (they raise on failure, mutate nothing, emit nothing).
- **Notation:**
  ```
  class CacheType {
    <<Aggregate Root>>
    +ensure_can_resolve(derived_fields_ids: list[str], lookup_code: str) None
  }
  class DerivedFields {
    <<Value Object>>
    +has_fields(fields_ids: list[str]) bool
  }
  ```
- **Example:** `+ensure_can_resolve(derived_fields_ids: list[str], lookup_code: str) None` and `+ensure_arity(n: int) None` — from `cache-type.md`; `+has_fields(fields_ids: list[str]) bool` — from `mapping-type.md`.
- **You may:** define an `ensure_*` guard with no application-layer caller — it can exist to be invoked by a sibling aggregate (e.g. `CacheType.ensure_can_resolve` is called from `mapping-type`).
- **Review:** treat `ensure_*` (returns `None`, raises) as a canonical guard, not a mis-typed predicate. Do not flag `has_*`/`is_*` properties for lacking `()` (see *Derived state as bare-`bool` properties*).

### Repository finder vocabulary, including the bulk `_by_codes` finder
- **Rule:** On the **command** repo use `<entity>_of_<key>(...) <Aggregate> | None` for id/key lookup, `has_<entity>_with[_<field>](...) bool` for existence pre-flight, and `save(<x>: <Aggregate>) None`. On the **query** repo use `find_<entity>(<entity>_id) <X>Info | None` (singular) and `find_<entities>(filtering, pagination) <X>ListResult` (plural). For an unpaginated batch read keyed by a list of business keys, use a `find_<entities>_by_codes(<codes>: list[str]) list[<X>Info]` finder that returns a **bare `list[<X>Info]`** (no `ListResult`), segregated under a `%% internal` surface marker.
- **Notation:**
  ```
  class QueryCacheTypeRepository {
    <<Repository>>
    +find_cache_type(cache_type_id: str) CacheTypeInfo | None
    +find_cache_types(filtering: CacheTypeFiltering | None, pagination: Pagination | None) CacheTypeListResult
    +find_cache_types_by_codes(cache_type_codes: list[str]) list[CacheTypeInfo]
  }
  class CommandCacheTypeRepository {
    <<Repository>>
    +cache_type_of_id(id: str) CacheType | None
    +cache_type_of_code(code: str) CacheType | None
    +has_cache_type_with(name: str, code: str) bool
    +save(cache_type: CacheType) None
  }
  ```
- **Example:** `+find_cache_types_by_codes(cache_type_codes: list[str]) list[CacheTypeInfo]` (bare list) alongside `+find_cache_type(...) CacheTypeInfo | None` and `+find_cache_types(...) CacheTypeListResult` — from `cache-type.md`; the keyed command lookup `+cache_type_of_code(code: str) CacheType | None` and OR-semantics pre-flight `+has_cache_type_with(name: str, code: str) bool` from the same file.
- **You may:** key the command lookup on a secondary id rather than `code` (`ruleset_of_process(process_id)`); pair a narrow and a broad existence check on different fields (`has_mapping_type_with(name, code)` used by `create` plus `has_mapping_type_with_name(name)` used by `rename`, from `mapping-type.md`); resolve a name to an id via `<entity>_id_with_name(name) str | None` (from `domain-type.md`) where a uniqueness comparison needs the resolved id; and add a keyed-by-secondary-id single-result finder (`find_<x>_by_<key>`) distinct from the bulk `_by_codes` list finder.
- **Review:** treat the bulk `find_<entities>_by_codes(...) list[<X>Info]` finder (bare list, unpaginated, under `%% internal`) as a canonical third query-repo idiom beyond the singular/plural pair — do not flag the bare-list return as "should be a ListResult". Treat `_of_<key>`, `has_*_with[_field]`, `_id_with_name`, and secondary-id finders as canonical.

### Derived state is exposed as bare-`bool` properties (no parentheses)
- **Rule:** On `Status` and result VOs, model derived state checks as bare public `bool` *properties* without parentheses — `+is_<state>: bool`, `+has_error[s]: bool` — not as `()` methods. Reserve `()` for repository/collection-VO predicate methods (`has_<entity>_with(...) bool`).
- **Notation:**
  ```
  class Status {
    <<Value Object>>
    +is_pending: bool
    +is_completed: bool
    +is_failed: bool
  }
  ```
- **Example:** `+is_pending: bool` / `+is_completed: bool` / `+is_failed: bool` on `Status` — from `mapping.md`.
- **You may:** expose list-typed control projections as bare properties too (e.g. `inferred_stages`, `stages_to_re_infer`) alongside the `is_*` set; name the Either-VO gate `has_errors` (plural) or `has_error` (singular) to match the VO's error arity.
- **Review:** treat parenthesis-free `is_*`/`has_*[s]` on Status/result VOs as canonical properties — do not flag them as "methods missing `()`". Conversely, do not flag a repository `has_*_with(...)` for *having* `()` — that is the method form.

### Identity is a bare `str` `id`; timestamps are root-only `created_at` / `updated_at`
- **Rule:** Use a private bare-`str` field named `id` for identity (no typed Id VO). Place `created_at` and `updated_at` (`datetime`) as the **last two** attributes, on the aggregate root only; child entities/VOs carry `id` but not timestamps. Carry the same `id` / `created_at` / `updated_at` through into the query-side `Info` and `Brief` read models.
- **Notation:**
  ```
  class DomainType {
    <<Aggregate Root>>
    -id: str
    -code: str
    -details: Details
    -enabled: bool
    -created_at: datetime
    -updated_at: datetime
  }
  ```
- **Example:** `-id: str` … `-created_at: datetime` / `-updated_at: datetime` as the last two root attributes — from `domain-type.md`; the same trio re-appears in `DomainTypeInfo` (read model) in the same file.
- **You may:** use a domain-specific identity key such as `-file_id: str` on a child entity where the domain names it that way (propagating into `FileInfo.file_id` and event payloads); carry an externally-supplied `-id: str` on a `<<Value Object>>` (id supplied, not minted — e.g. `MappingType` in `mapping.md`); and place a provenance `datetime` on a non-root VO when it is genuinely a VO-level timestamp (root timestamps still stay on the root). When `id` is a `new()` parameter (externally-governed identity), `created_at`/`updated_at` still stay out of the parameter list.
- **Review:** treat bare-`str` `id` (no Id VO), root-only `created_at`/`updated_at`, `file_id` keys, and id-on-a-VO as canonical. Do not propose introducing a typed Id value object or hoisting timestamps onto children.

### Attributes are private (`-`); DTO / event / repo / service members are public (`+`)
- **Rule:** Mark every aggregate/entity/VO stored attribute private with a leading `-`. Mark every TypedDict field, domain-event field, repository/service method, and `<<Application>>`/`<<Interface>>` member public with a leading `+`. Derived/computed properties are public too.
- **Notation:**
  ```
  class Lookup {
    <<Entity>>
    -id: str
    -code: str
    +new(code: str, name: str, arguments: list[LookupArgumentData] | None, response: list[EntryItemData]) Lookup$
  }
  class LookupInfo {
    <<TypedDict>>
    +id: str
    +code: str
  }
  ```
- **Example:** private `-id: str`/`-code: str` on the `Lookup` entity vs public `+id: str`/`+code: str` on the `LookupInfo` TypedDict and `+save(...)` on the repository — from `cache-type.md`.
- **You may:** mark a derived `bool`/projection property public on a collection VO or Status (e.g. a `*_rulesets_created: bool` flag or a list-typed `*_stages` projection) — derived/computed members are public even on otherwise private-attribute classes.
- **Review:** treat `-` on stored attributes and `+` on DTO/event/repo/service/interface members (and on derived properties) as canonical. Do not flag a public derived property on a VO as a visibility error.

### Application command methods take the aggregate id first — `create` excepted
- **Rule:** On an `<<Application>>` command service, every mutating method takes the aggregate id as its **first** parameter and returns the aggregate. The lone carve-out is the creation method, conventionally named **`create`** (not `new`), which takes no id and constructs a fresh aggregate. Name inbound-event-driven methods `on_<event_snake>` (see below).
- **Notation:**
  ```
  class CacheTypeCommands {
    <<Application>>
    +create(code: str, name: str, lookups: list[LookupData]) CacheType
    +update_details(id: str, name: str) CacheType
    +add_lookup(id: str, ...) CacheType
  }
  ```
- **Example:** `create(code, name, lookups)` (no id) then id-first `update_details(id, ...)` / `add_lookup(id, ...)` — the cache-type command surface paired with `cache-type.md`.
- **You may:** key inbound-event upsert handlers on a composite business key instead of an id (`update_evo_version(project_type, company_id, cmf, evo_version)`, `on_source_dms_file_added(project_id, source_id, ...)`), and let such a handler create-on-demand when the lookup misses rather than raising NotFound — these are sanctioned carve-outs from id-first CRUD.
- **Review:** treat id-first (with `create` and inbound-event composite-key/upsert handlers as the carve-outs) as canonical. Do not flag `create` for omitting the id, nor an `on_*` upsert handler for not raising NotFound on a missing target.

### Status transitions are intent-named or accumulating-builder factories — `create` → `on_<event>` at the app layer
- **Rule:** Realize lifecycle/VO state changes through factory **replacement**, not in-place field writes. A `Status` VO transitions via either one named factory per state (`created()` / `completed()` / `failed(error)`) **or** an accumulating `with_<field>()` builder chain that returns a fresh `Status`; leaf VOs are replaced wholesale via `with_new_<field>(...)` / `with_id(...)`. At the application layer, the domain factory `Aggregate.new(...)` is wrapped by a service method named `create(...)`; event-driven service methods (commands and ops) are named `on_<event_snake>`; ops demand-path methods are imperative `infer_*`-style verbs.
- **Notation:**
  ```
  class Status {
    <<Value Object>>
    +pending() Status$
    +cleared() Status
    +with_derived_fields() Status
    +with_resolved_fields() Status
    +failed(errors: list[InferenceError]) Status
  }
  ```
- **Example:** `+pending() Status$`, `+with_derived_fields() Status`, `+with_resolved_fields() Status`, `+failed(errors: list[InferenceError]) Status` — accumulating-builder Status from `mapping.md`. (`+with_id(...) ResolvedField$` in `mapping-type.md` is the id-preserving wholesale leaf swap.)
- **You may:** use either the named-factory-per-state form or the accumulating `with_*` builder form — both are canonical Status idioms; mixing terminal-state factories (`pending()`, `failed(errors)`) with progress builders (`with_derived_fields()`, `cleared()`) in one VO is allowed. Mark all factory transitions in a single VO `$` consistently.
- **Review:** treat both Status-transition forms, the `create`-at-app-layer / `on_<event>`-handler naming, and imperative `infer_*` ops demand methods as canonical. Do not flag an accumulating `with_*` builder for "not being one-factory-per-terminal-state", and do not flag the app-layer `create` for diverging from the domain `new`.

### Capability ports are `ICan<Verb><Noun>` with the `<<Interface>>` stereotype
- **Rule:** Name an externally-implemented capability/port interface `ICan<Verb><Noun>` and stereotype it `<<Interface>>` — retrieval ports `ICanRetrieve<X>Info`, a write-back client port `ICanManage<Aggregate>`. Reserve `<<Service>>` for the concrete inference/domain-service ports (`<X>Inferrer`); the two stereotypes are not interchangeable.
- **Notation:**
  ```
  class ICanRetrieveMappingTypeInfo {
    <<Interface>>
    +retrieve_mapping_type(mapping_type_code: str) MappingTypeInfo
  }
  ```
- **Example:** `ICanRetrieveMappingTypeInfo` with member `+retrieve_mapping_type(mapping_type_code: str) MappingTypeInfo` — authored (here in a `%%`-fenced block) in `mapping.md`; live ports `ICanRetrieveFilesInfo`, `ICanManageRuleset` follow the same naming on the ruleset diagram.
- **You may:** place `<<Interface>>` capability ports directly in the domain file alongside `<<Service>>` ports rather than confining them to siblings; model a write-back port (`ICanManage<Aggregate>`) that the ops layer calls back through (a port pointing inward), not only outbound retrieval ports.
- **Review:** treat `ICan<Verb><Noun>` + `<<Interface>>` as a canonical capability-port name and stereotype — do not flag `<<Interface>>` as outside the vocabulary, and do not propose merging it into `<<Service>>`. (When ports live in a `%%`-fenced block, resolve any dangling active references into that block before enabling it — see Pitfalls.)

## Pitfalls
- **Dropping the `$` on a factory that returns the owning type.** `Mapping.new(...) Mapping` (no `$`) and `MappingRule.new(...) MappingRule` (bare type name, no `$`) are non-conformances to fix — `new()` must both return the owning type **and** carry `$`. A `new()` that returns `None` (instead of the owning type) is also wrong.
- **Return-type leak between sibling aggregates.** `MappingDetails.new(...) MappingRuleDetails$` in `mapping.md` declares the *sibling* aggregate's `MappingRuleDetails` as its return type — a copy-paste bug. A factory's return type must be its own owning type.
- **Inconsistent `$`-marking within one VO.** Marking only `pending() Status$` while leaving `cleared` / `with_*` / `failed` un-`$`-marked in the same Status VO is an authoring inconsistency — mark every factory transition in a VO the same way.
- **Singular `from_list` parameter.** `from_list(mapping_type: ...)` drifts from the convention; use the plural (`from_list(mapping_types)`).
- **Omitting the `None` annotation on an in-place mutator.** A mutator written `add_domain_type(domain_type: DomainTypeData)` with no return annotation is under-specified — always annotate the `None` return.
- **Naming the creation command `new` at the application layer.** The app-service creation method is `create`, not `new`; `new` is the domain factory it wraps.
- **Confusing `<<Service>>` and `<<Interface>>`.** Use `<<Interface>>` for `ICan<Verb>` capability/write-back ports and `<<Service>>` for concrete `<X>Inferrer` domain-service ports — do not collapse them.
- **Dangling references into a `%%`-fenced block.** An active member or edge (`MappingType.from_info(mapping_type_info: MappingTypeInfo)`, `MappingType --() SourceFieldInfo`) that points at a commented-out type is a half-disabled subgraph — resolve the references (or un-comment the block) before treating it as live.
