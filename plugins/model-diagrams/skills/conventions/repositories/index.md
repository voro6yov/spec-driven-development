---
name: repositories
description: Repository diagram conventions — CQRS Command/Query split, command lookup vocabulary, find_<x>/find_<x>s query surface, _by_codes bulk finders, keyed composite-key finders, ops ICanManage write-port.
user-invocable: false
---

# Repositories

**Applies to:** domain (repo classes), queries (finder surface)

This theme governs how an aggregate's persistence boundary is drawn: the CQRS split into a command repository and a query repository, the method vocabulary on each side, the keyed and bulk finder variants, and the ops-layer write-port that replaces the repository in event-driven orchestration. Repository classes are declared **in the domain diagram** (`<stem>.md`), not in the `.commands.md` / `.queries.md` siblings.

## Ground knowledge

*Why these conventions are what they are — the canonical patterns behind the CQRS split and the finder vocabulary, and one naming divergence. Names and sources let a reviewer cite the principle behind a suppression rather than assert it.*

- **The two-class split materializes CQRS** (Vernon; Khononov, *LDDD* ch.8; Lawrence, *MEDS* ch.5; DDIA). The command repo is the write model / system of record where invariants and concurrency live; the query repo serves *derived* read models (a materialized view kept in sync). Vernon's command repo "shrinks to add()/save() + a single fromId() finder" — exactly this doc's `*_of_id` + `save` core.
- **Repositories exist only for aggregate roots** (Evans, *DDD* — the narrowing rule): everything aggregate-internal is reached by traversal from the root, not by query — which grounds "omit both repos for a flat aggregate."
- **A command repo may return data** (Khononov): returning `<Aggregate> | None` plus `Data` shapes from the strongly-consistent command model is not a CQS violation, so the command-optional / service-raises asymmetry is sound.
- **`_by_codes` / `ICanRetrieve*` bare-list finders = use-case-optimal queries** (Vernon, *IDDD* ch.12): reads shaped to one use case, projected into a purpose-built DTO. The threshold to remember: *one is fine; a drawerful is the "Repository masks Aggregate mis-design" smell* (mis-drawn boundaries or the CQRS trigger) — which the `%% internal` marker quarantines.
- **Uniqueness can't be a one-aggregate invariant** (Aggregate boundary limit; Lawrence's invariant-vs-validation): set-wide uniqueness is structurally outside any single aggregate (one aggregate per transaction, others by id), so the `has_*` pre-flight is *necessarily* non-race-safe and the real guard is a DB unique/functional index — cross-links to `invariant-prose/`.
- **Deliberate divergence — "Repository" for the query side.** Canon (Lawrence) reserves *Repository* for the write side and calls query-side persistence **stores** / read models. The `Query<X>Repository` naming is an established project divergence — do not "correct" it toward canon.

## Conventions

### CQRS split into `Command<X>Repository` and `Query<X>Repository`
- **Rule:** When the aggregate has a persistence boundary, declare exactly two `<<Repository>>` classes in the domain diagram, named `Command<Aggregate>Repository` and `Query<Aggregate>Repository`. The command side returns the live aggregate (`<Aggregate> | None`) plus primitive/`Data` shapes and owns `save()` (plus `delete()` for hard-delete aggregates); the query side returns only read-model TypedDicts (`Info` / `ListResult` / `list[Info]`) and never the aggregate. Draw the command repo's aggregate edge `--> <Aggregate> : retrieves/stores`, and each query-repo return/argument edge `--> <DTO> : returns` / `--> <Filtering> : takes as argument`.
- **Notation:**
  ```
  class CommandCacheTypeRepository {
    <<Repository>>
    +cache_type_of_id(id: str) CacheType | None
    +save(cache_type: CacheType) None
  }
  CommandCacheTypeRepository --> CacheType : retrieves/stores

  class QueryCacheTypeRepository {
    <<Repository>>
    +find_cache_type(cache_type_id: str) CacheTypeInfo | None
    +find_cache_types(filtering: CacheTypeFiltering | None, pagination: Pagination | None) CacheTypeListResult
  }
  QueryCacheTypeRepository --> CacheTypeInfo : returns
  QueryCacheTypeRepository --> CacheTypeListResult : returns
  QueryCacheTypeRepository --> CacheTypeFiltering : takes as argument
  ```
- **Example:** `CommandCacheTypeRepository` and `QueryCacheTypeRepository` with `CommandCacheTypeRepository --> CacheType : retrieves/stores` — from `cache-type.md`.
- **You may:** omit both repository classes entirely for a flat aggregate that expresses no persistence boundary (no `<<Repository>>` class, no `save`/`find_*`/`*_of_id`, no `retrieves/stores` edge); add a `delete(<aggregate>)` to the command repo for hard-delete aggregates (see vocabulary below).
- **Review:** when reviewing a diagram, treat the two-class CQRS split as canonical — do not flag it as non-standard. Do not flag the command finders returning `<Aggregate> | None` while the matching `<<Application>>` service re-declares the same finder non-optional and raises `<Aggregate>NotFound`: the repo-optional/service-raises asymmetry is the intended division of labor (the repo reports presence, the service enforces it). Do not flag the absence of a repository on a flat no-persistence aggregate.

### Command repository method vocabulary
- **Rule:** On the command repository use `<entity>_of_id(id) <Aggregate> | None` for id lookup, `<entity>_of_<key>(...)` / `<entity>_with_<attr>(...) <Aggregate> | None` for alternate-key lookups, `has_<entity>_with[_<field>](...) bool` for existence pre-flight checks, and `save(<aggregate>) None`. Optionally add `<entity>_id_with_<attr>(...) str | None` for id-resolution and `all_<plural>() list[<X>Data]` for a bulk dump. Add `delete(<aggregate>) None` only for hard-delete aggregates (those with no `enabled` soft-delete flag).
- **Notation:**
  ```
  class CommandCacheTypeRepository {
    <<Repository>>
    +cache_type_of_id(id: str) CacheType | None
    +cache_type_of_code(code: str) CacheType | None
    +has_cache_type_with(name: str, code: str) bool
    +has_cache_type_with_name(name: str) bool
    +save(cache_type: CacheType) None
  }
  ```
- **Example:** `has_cache_type_with(name: str, code: str) bool` (OR-semantics, used by `create`) paired with `has_cache_type_with_name(name: str) bool` (used by `rename`) — from `cache-type.md`. Hard-delete: `+delete(ruleset: Ruleset)` alongside `+save(ruleset: Ruleset) None` — from `ruleset.md`.
- **You may:** add a keyed `*_of_<key>` lookup beside `*_of_id` (`cache_type_of_code(code) CacheType | None` in `cache-type.md`, `template_of_source_id(source_id) Template | None` in `template.md`, `ruleset_of_process(process_id) Ruleset | None` in `ruleset.md`); pair a narrow and a broad existence check (`has_<x>_with(name, code)` plus `has_<x>_with_name(name)`); add `all_<plural>() list[<X>Data]` for a full dump and `<entity>_id_with_<attr>(...) str | None` for id-resolution.
- **Review:** when reviewing a diagram, treat these method names as canonical — do not flag the `*_of_id`/`*_of_<key>`/`has_*`/`save`/`delete` vocabulary, the keyed or paired-existence variants, or the bulk `all_*` dump as non-standard. Do not flag the id parameter being named `id` here while the query side names the same concept `<x>_id` (e.g. `find_<x>(<x>_id)`) — the cross-repo param-name difference is established. Do not flag `has_*` existence checks as race-unsafe; they are deliberate pre-flight checks the service layer pairs with its own enforcement.

### Query repository `find_<x>` (singular) / `find_<x>s` (plural)
- **Rule:** On the query repository expose `find_<entity>(<entity>_id) <X>Info | None` for the single read and `find_<entities>(filtering: <X>Filtering | None, pagination: Pagination | None) <X>ListResult` for the collection read. The plural method always takes optional `<X>Filtering` plus optional `Pagination`; both arguments are nullable. The singular returns `<X>Info | None`; the plural returns `<X>ListResult` (never `| None`).
- **Notation:**
  ```
  class QueryTemplateRepository {
    <<Repository>>
    +find_template(template_id: str) TemplateInfo | None
    +find_template_by_source(source_id: str) TemplateInfo | None
    +find_templates(filtering: TemplateFiltering | None, pagination: Pagination | None) TemplateListResult
  }
  QueryTemplateRepository --> TemplateInfo : returns
  QueryTemplateRepository --> TemplateListResult : returns
  QueryTemplateRepository --> TemplateFiltering : takes as argument
  ```
- **Example:** `find_template(template_id: str) TemplateInfo | None` and `find_templates(filtering: TemplateFiltering | None, pagination: Pagination | None) TemplateListResult` — from `template.md`.
- **You may:** add keyed single-read finders alongside the standard pair (`find_template_by_source(source_id) TemplateInfo | None` in `template.md`, `find_ruleset_by_process(process_id) RulesetInfo | None` in `ruleset.md`); rename the pair when the aggregate noun is already plural (use `find_single_<noun>` / `find_multiple_<noun>` instead of singular/plural `find_<x>`/`find_<x>s`); reference `Pagination` by type without declaring it as a class in the diagram.
- **Review:** when reviewing a diagram, treat `find_<x>` / `find_<x>s` and the `find_single_*` / `find_multiple_*` rename as canonical — do not flag either, nor the `find_<x>_by_<key>` keyed extension. Do not flag `Pagination` being referenced as a parameter type but not declared as a class. Do not flag the singular finder returning `| None` while its `<<Application>>` query service re-declares it non-optional and raises `<Aggregate>NotFound` — the same repo-optional/service-raises asymmetry as the command side.

### Bulk keyed batch finder `find_<x>_by_codes(...) list[<X>Info]`
- **Rule:** When a service-to-service caller needs a non-paginated, unfiltered batch read keyed by a list of business codes, add a third query-repo method `find_<entities>_by_codes(<entity>_codes: list[str]) list[<X>Info]` returning a **bare `list[<X>Info]`** — the full `Info` (not `Brief`), and **not** wrapped in a `ListResult`. Mirror it on the `<<Application>>` `<X>Queries` service under a `%% internal` surface marker to segregate it from the public query surface.
- **Notation:**
  ```
  class QueryCacheTypeRepository {
    <<Repository>>
    +find_cache_type(cache_type_id: str) CacheTypeInfo | None
    +find_cache_types(filtering: CacheTypeFiltering | None, pagination: Pagination | None) CacheTypeListResult
    +find_cache_types_by_codes(cache_type_codes: list[str]) list[CacheTypeInfo]
  }
  ```
- **Example:** `find_cache_types_by_codes(cache_type_codes: list[str]) list[CacheTypeInfo]` — from `cache-type.md`.
- **You may:** key the batch read on more than a single code list (`find_reqs_domain_models(evo_version, domain_type_codes) list[DomainModelInfo]` keys on `evo_version` plus a code list and returns a nested model — same bare-list, escapes-the-pair shape with a different key/return); place a *single* keyed finder under `%% internal` too, not only a bulk one.
- **Review:** when reviewing a diagram, treat a bare `list[<X>Info]` batch finder — returning full `Info`, unpaginated, unwrapped — as canonical; do not flag it as "should return a `ListResult`" or "should be paginated/filtered". Do not flag a `%% internal` marker fronting such a finder (or any single keyed finder) on the `<X>Queries` sibling: `%% internal` is a surface-partition marker, not a commented-out method.

### Keyed single-item finders for composite-business-key aggregates
- **Rule:** When an aggregate is identified by a composite business key (not only its synthetic `id`), pair the id finders with a keyed finder on **both** repos: command `<entity>_with_<key>(...) <Aggregate> | None` and query `find_<entity>_by_<key>(...) <X>Info | None`. Surface a distinct `<Aggregate>NotFoundBy<Key>` exception so the service reports which lookup failed.
- **Notation:**
  ```
  class CommandRulesetRepository {
    <<Repository>>
    +ruleset_of_id(id: str) Ruleset | None
    +ruleset_of_process(process_id: str) Ruleset | None
    +save(ruleset: Ruleset) None
    +delete(ruleset: Ruleset)
  }

  class QueryRulesetRepository {
    <<Repository>>
    +find_ruleset(ruleset_id: str) RulesetInfo | None
    +find_ruleset_by_process(process_id: str) RulesetInfo | None
    +find_rulesets(filtering: RulesetFiltering | None, pagination: Pagination | None) RulesetListResult
  }
  ```
- **Example:** `ruleset_of_process(process_id: str) Ruleset | None` on the command repo paired with `find_ruleset_by_process(process_id: str) RulesetInfo | None` on the query repo (keyed by `process_id`) — from `ruleset.md`.
- **You may:** provide the keyed finder on the **query** side only when the command side already covers the key via a `*_of_<key>` finder (e.g. `template.md` has query-only `find_template_by_source` while the command side uses `template_of_source_id`); take the composite key as the *leading arguments* of the `<<Application>>` command methods when it is the primary load path rather than a secondary one.
- **Review:** when reviewing a diagram, treat keyed finders (`<entity>_with_<key>`, `find_<entity>_by_<key>`) and a second `<Aggregate>NotFoundBy<Key>` exception as canonical for composite-key aggregates — do not flag them as redundant with `*_of_id`/`find_<x>`. Do not require the keyed finder to appear on both repos in lockstep; query-only is a sanctioned shape.

### Ops-layer `ICanManage<Aggregate>` write-port replaces the repository
- **Rule:** In an ops/orchestration diagram (`<stem>.ops.<service>.md`), an `<<Application>>` inference service does **not** inject the `Command<Aggregate>Repository`. Instead inject an `<<Interface>>` capability port named `ICanManage<Aggregate>` exposing the aggregate's load + write-back surface (`find_<x>`, the mutating `add_*` / `update_*` methods), and read catalog inputs through sibling `ICanRetrieve<X>Info` `<<Interface>>` ports. The repository stays in the domain file for the `<X>Commands` / `<X>Queries` services; the ops service couples to the aggregate only through the capability port.
- **Notation:**
  ```
  class ICanManageRuleset {
    <<Interface>>
    +find_ruleset(ruleset_id: str) RulesetInfo | None
    +add_mapping_rules(ruleset_id: str, mapping_rules: list[MappingRuleData], epoch_token: int) None
    +update_mapping_rule(ruleset_id: str, mapping_rule_id: str, mapping_rule_data: MappingRuleData, epoch_token: int) None
    +add_mappings(ruleset_id: str, mappings: list[MappingData], epoch_token: int) None
    +update_mapping(ruleset_id: str, mapping_id: str, mapping_data: MappingData, epoch_token: int) None
    +add_errors(ruleset_id: str, errors: list[InferenceError], epoch_token: int) None
  }
  ICanManageRuleset --() RulesetInfo : returns
  ```
- **Example:** `ICanManageRuleset` (`<<Interface>>`) with `find_ruleset` plus the `add_mapping_rules` / `update_mapping_rule` / `add_mappings` / `update_mapping` / `add_errors` write-back surface — from `ruleset.md`; the ops services inject it as `-ruleset_client: ICanManageRuleset` alongside the four `ICanRetrieve*Info` ports.
- **You may:** inject several `ICanRetrieve<X>Info` retrieval ports next to the single `ICanManage<Aggregate>` write-back port (ruleset injects `ICanRetrieveFilesInfo`, `ICanRetrieveDomainModelsInfo`, `ICanRetrieveMappingTypesInfo`, `ICanRetrieveCacheTypesInfo`); stage a retrieval port as a `%%`-commented-out `<<Interface>>` block when it is intended-but-not-yet-enabled.
- **Review:** when reviewing an ops diagram, treat the `ICanManage<Aggregate>` write-port — rather than the `Command<Aggregate>Repository` — as canonical; do not flag the ops service for "not using the repository" or propose injecting the command repo. Do not flag the `ICanManage*` / `ICanRetrieve*Info` ports as a non-standard stereotype: `<<Interface>>` (`ICan<Verb><Noun>` naming) is the canonical capability-port role, distinct from `<<Service>>` inferrer ports. The repository correctly remains in the domain file for the `<X>Commands`/`<X>Queries` services — do not flag its coexistence with the port.

## Pitfalls
- Do not collapse the two repositories into one `<<Repository>>` mixing aggregate returns and read-model TypedDicts — the command/query split is the boundary. The command side never returns `Info`/`ListResult`; the query side never returns the aggregate.
- Do not declare the repositories on the `.commands.md` / `.queries.md` siblings — both `<<Repository>>` classes live in the domain diagram (`<stem>.md`).
- Do not wrap a `_by_codes` batch finder in a `ListResult` or pass it `Pagination`/`Filtering` — it returns a bare `list[<X>Info]` of full `Info`, by design.
- Do not return `Brief<X>Info` from `find_<x>_by_codes` — the bulk-by-code finder returns full `<X>Info`; `Brief` belongs inside `ListResult`.
- Do not make the plural `find_<x>s` return `<X>ListResult | None` — the plural read always returns a `ListResult` (an empty one when nothing matches); only the singular finder is `| None`.
- Do not add a `delete()` to the command repo of a soft-delete aggregate (one carrying an `enabled` flag) — `delete()` is reserved for hard-delete aggregates.
- Do not inject the `Command<Aggregate>Repository` into an ops/orchestration service — use the `ICanManage<Aggregate>` write-port.
- Do not leave a `%%`-commented-out `<<Interface>>` retrieval port half-wired: if the active diagram still references types inside a commented block, either enable the block or remove the dangling reference before treating the diagram as final.
