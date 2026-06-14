---
name: value-objects
description: Value Object diagram conventions — Details VOs, single/multi-axis Status, Either result VOs, collection VOs, wholesale replacement, and externally-supplied-id VO vs Entity (authoring + review).
user-invocable: false
---

# Value Objects

**Applies to:** domain diagrams

> This theme governs how to model value semantics on a domain class diagram: grouping cohesive scalars into Details VOs, lifecycle as a Status VO, service outcomes as Either VOs, aggregate-owned collections as Collection VOs, and the Entity-vs-VO decision for id-bearing children. Value Objects are immutable: state changes are modeled as factory replacement, never in-place mutation.

## Conventions

### Details Value Object (descriptive, identity-context, or multi-Details)
- **Rule:** When a root carries a cohesive cluster of scalars that together describe or classify it, wrap that cluster in a `<<Value Object>>` named `<Aggregate>Details` (or `Details`), composed at cardinality `"1"`, built through its own `new(...)$`. A Details VO comes in two stable sub-kinds — **descriptive** (a `name` + `description` pair) and **identity-context** (an external composite key such as `project_id`/`source_id`/`evo_version`, with no name/description). When a flat root has several independent scalar clusters, model each as its own co-equal `*Details` VO rather than one omnibus Details. Never scatter a cohesive cluster flat on the root, and never accept a pre-built Details from the caller — `new(...)$` always composes it internally from flat primitives.
- **Notation:**
  ```
  Mapping *-- "1" MappingDetails
  Mapping *-- "1" FileDetails
  Mapping *-- "1" TransformationDetails

  class MappingDetails {
    <<Value Object>>
    -evo_version: str
    -category_code: str
    -file_type: str
    -domain_type: str
    +new(evo_version: str, category_code: str, file_type: str, domain_type: str) MappingDetails$
  }
  ```
- **Example:** identity-context `RulesetDetails` = `process_id`/`conversion_id`/`project_id`/`source_id`/`evo_version` with `new(...) RulesetDetails$` — from `ruleset.md`; descriptive `CategoryDetails` = `name` + `description` with `new(name, description) CategoryDetails$`, composed under the child `Category` entity — from `template.md`; the multi-Details root (three co-equal `*Details` VOs on one flat root) — from `mapping.md`.
- **You may:** compose a descriptive Details under a **child entity** rather than the root (as `CategoryDetails` sits under `Category`); compose **multiple** co-equal `*Details` VOs on one flat root (`MappingDetails` + `FileDetails` + `TransformationDetails`); or omit Details entirely when the root has no 2-or-more-scalar cluster (a single descriptor scalar like a lone `evo_version` stays flat on the root, and `name`/`code` may stay bare on the root).
- **Review:** when reviewing a diagram, treat this as canonical — do not flag it as non-standard. An identity-context Details (a composite key VO with no name/description) is a first-class realization, not a deviation; do not propose flattening it onto the root or demand a name/description. Multiple `*Details` VOs on one root are canonical; do not propose merging them into one omnibus VO.

### Lifecycle Status Value Object (single-axis named-factory vs multi-axis builder-accumulation)
- **Rule:** Model a true multi-state lifecycle as a `Status` `<<Value Object>>` holding a `Literal`-typed private `status` plus bare `is_*: bool` **properties** (no parens). For a simple state machine, expose **one named factory per state** (`created()$`/`completed()$`/`failed(...)$`). When the lifecycle has orthogonal progress sub-axes, the Status additionally carries independent boolean progress flags and an optional `errors` list, and advances via **accumulating immutable `with_*` builders** that each return a fresh `Status` with one more flag set — plus a `cleared()` reset and a terminal `failed(errors)`. Never use a Python `Enum` or a bare magic string for lifecycle.
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
- **Example:** the multi-axis builder Status (`pending()$`/`cleared()`/`with_derived_fields()`/`with_resolved_fields()`/`failed(errors)` over `Literal["pending","completed","failed"]` + two progress booleans + `errors: list[InferenceError] | None`) — from `mapping.md`; the ruleset variant adds derived list-projection properties `inferred_stages`/`error_stages`/`stages_to_re_infer` — from `ruleset.md`.
- **You may:** use the simple **one-named-factory-per-state** shape for a plain state machine, OR the **multi-axis** shape (orthogonal progress booleans + optional `errors` + accumulating `with_*` builders) for a staged/async-inference lifecycle; carry extra derived list-typed projection properties (`inferred_stages`/`error_stages`/`stages_to_re_infer`) beyond the `is_*` set when the lifecycle drives re-inference. Mark the `$` static marker consistently on every factory/builder in a single Status (canonical even where some real diagrams left `cleared`/`with_*`/`failed` un-`$`-marked).
- **Review:** when reviewing a diagram, treat this as canonical — do not flag it as non-standard. A `Status` whose transitions are accumulating `with_*` builders (rather than one-factory-per-terminal-state) is the sanctioned multi-axis idiom — do not flag it as "missing one factory per state" or propose collapsing the progress flags into a single enum. The bare `is_*: bool` properties without parens are intentional; do not propose `()` methods. Do not flag derived list-projection properties on Status as out of place.

### Either / result-or-error Value Object
- **Rule:** Model a domain-service success/failure outcome as a result-or-error `<<Value Object>>` (Either idiom) with two mutually-exclusive `Optional` fields — a `result` slot and an `error(s)` slot — a bare boolean gate property, and intent-named static factories. Do not model the same outcome as an exception or as a plain pair VO. The factory/gate vocabulary follows the error cardinality: a **singular-error** VO uses `as_result(...)$` / `as_error(...)$` with a `has_error: bool` gate; a **list-error** VO uses `as_result(...)$` / `with_errors(...)$` with a `has_errors: bool` gate.
- **Notation:**
  ```
  class InferencedMappingRules {
    <<Value Object>>
    -result: list[MappingRuleData] | None
    -errors: list[InferenceError] | None
    +has_errors: bool
    +as_result(mapping_rules: list[MappingRuleData]) InferencedMappingRules$
    +with_errors(errors: list[InferenceError]) InferencedMappingRules$
  }

  MappingRuleInferrer --> InferencedMappingRules : returns
  ```
- **Example:** list-error `InferencedMappingRules` / `InferencedMappings` with `has_errors: bool` + `as_result(...)$` / `with_errors(...)$`, returned by the `<<Service>>` inferrer ports via `--> ... : returns` — from `ruleset.md`. (The singular-error counterpart, `ParsingResult` with `has_error` + `as_result`/`as_error`, lives on conversion-reqs.)
- **You may:** carry the `result` slot as a flat `<X>Data | None` dict rather than a fully-built VO (the VO conversion happens downstream); pick the `as_error`/`has_error` (singular) or the `with_errors`/`has_errors` (list) factory/gate vocabulary per the error cardinality. Draw the producing service edge as `<Service> --> <EitherVO> : returns`.
- **Review:** when reviewing a diagram, treat this as canonical — do not flag it as non-standard. Do not flag the two-optional-fields shape as "should be one field" or as "should raise an exception instead"; the Either VO is a deliberate functional-style wrapper that exception-using peers do not adopt. Accept `with_errors`/`has_errors` (plural) as the list-error vocabulary — do not normalize it to `as_error`/`has_error`. A plain two-field pair VO that is **not** result-or-error (no two-optional slots, no `has_error*` gate) is not an Either and is reviewed as an ordinary VO.

### Collection Value Objects compose Entities with mutating methods
- **Rule:** Model an aggregate-owned collection as a named plural `<<Value Object>>` (the **Collection VO**) wrapping a single private `list[<Child>]` / `dict` keyed by natural identity. The Collection VO owns the collection's mutation and lookup surface (`add_*`, `remove_*`, `update_*`, `has_*`, `*_with_id`) and the root delegates to it rather than holding a raw list. The VO stereotype is preserved because the **container reference** is immutable while its **contents** are mutated through the VO's dedicated methods. A Collection VO may compose `<<Entity>>` children and may itself carry rich behavior (target-excluding predicates, derived flags) and still be a VO.
- **Notation:**
  ```
  class MappingRules {
    <<Value Object>>
    -mapping_rules: list[MappingRule]
    +empty() MappingRules$
    +from_list(mapping_rules: list[MappingRule]) MappingRules$
    +add(mapping_rules: list[MappingRuleData]) None
    +update(mapping_rule_id: str, mapping_rule_data: MappingRuleData) None
    +clear() None
  }

  MappingRules *-- "0..n" MappingRule
  ```
- **Example:** `MappingRules` (a `<<Value Object>>`) composes the `MappingRule` `<<Entity>>` at `*-- "0..n"` and exposes `add`/`update`/`clear` mutators; `Files` exposes `add_files`/`add_file`/`remove_file`/`change_file_stage` — from `ruleset.md`. The `ResolvedFields` Collection VO exposes `add`/`update`/`remove` over `ResolvedField` — from `mapping-type.md`.
- **You may:** have a Collection-VO mutator return something other than `None` — a `bool` "did-it-change" signal the root branches on (ruleset `Files.add_files/add_file/remove_file/change_file_stage` return `bool`), or the freshly-created child entity (e.g. an `add(...)` returning the new entity) for idempotent/at-least-once handling; expose public derived projection properties on the Collection VO (`Files.pre_file_ids: list[str]`); use `empty()$` as the construction entry for a `0..n` collection and `new(...)$` for a `1..n` collection; rehydrate via `from_list(...)$` (non-validating, trusts persistence).
- **Review:** when reviewing a diagram, treat this as canonical — do not flag it as non-standard. A class is a Collection VO when **all** hold: (1) stereotype `<<Value Object>>`; (2) it composes (`*--` or `o--`) one or more `<<Entity>>` / `<<Value Object>>` children, typically at `"0..*"`/`"0..n"`; (3) it is itself composed by an `<<Aggregate Root>>` (single-aggregate ownership); (4) it exposes one or more mutating methods (`add_*`, `remove_*`, `update_*`, `increment`, `confirm_*`, `associate`, etc.) operating on the collection. When these cues line up, **do not flag** any of: "VO declared `<<Value Object>>` but contains mutable Entities" (composing Entities is the pattern); "VO exposes mutating methods, contradicting the stereotype" (mutation through dedicated methods is the pattern — an `ImmutableCheck()` Guard enforces container-reference immutability, not deep immutability); "equality/hashing will break because the VO holds identity-bearing entities" (Collection VOs are aggregate-internal orchestrators, never dict keys); "child Entities should live on the aggregate root" (hoisting them defeats the pattern). Do **not** propose "convert to `<<Entity>>`", "promote to `<<Aggregate Root>>`", or "hoist children onto the root" as remediation. The same suppression applies recursively: a child Entity inside a Collection VO may expose its own mutators over its own grandchildren — canonical at every level. The reviewer remains free to raise substantive concerns **independent** of the stereotype-vs-mutation question (a missing invariant, an inconsistent batch policy, an event emitted without the aggregate parameter); this suppression covers the stereotype objection only. It does **not** apply to a `<<Value Object>>` holding only primitive/immutable attributes (e.g. `Money { amount, currency }`) — those are plain VOs reviewed under generic rules.

### Value Objects are replaced wholesale, never mutated (`with_new_<field>` vs id-preserving `with_id`)
- **Rule:** Treat leaf VOs as immutable: to change a field, build a fresh instance and swap it in — never mutate in place. Use one of two attested replace-whole factory realizations: (a) `with_new_<field>(...)$`, which carries the unchanged fields plus the one changed field, minting fresh identity; or (b) an id-preserving `with_id(id, ...)$`, used to rebuild a collection entry while keeping its original `id` during an update. Status/Either/Details VOs are likewise rebuilt through their own factories, never field-mutated.
- **Notation:**
  ```
  class ResolvedField {
    <<Value Object>>
    -id: str
    -derived_fields_ids: list[str]
    -cache_type_code: str
    -lookup_code: str
    +new(derived_fields_ids: list[str], cache_type_code: str, lookup_code: str) ResolvedField$
    +with_id(id: str, derived_fields_ids: list[str], cache_type_code: str, lookup_code: str) ResolvedField$
  }
  ```
- **Example:** `ResolvedField.with_id(id, ...)$` rebuilds a collection entry preserving its `id` while swapping all other data (used by `ResolvedFields.update`) — from `mapping-type.md`; `File.with_new_stage(stage) File$` is the canonical `with_new_<field>` replace-whole — from `conversion.md`.
- **You may:** omit an explicit `with_new_*` / `with_id` factory entirely when Collection-VO `add`/`update`/`remove` flows or Status/Details factory-rebuilds already enforce immutability; realize replacement through accumulating Status `with_*` builders (see the Status convention) as a third form of wholesale replacement.
- **Review:** when reviewing a diagram, treat this as canonical — do not flag it as non-standard. Do not flag the absence of in-place setters on a VO, and do not propose adding mutating setters. `with_id` (preserves identity) and `with_new_<field>` (fresh identity) are both canonical; neither is required when collection CRUD or factory-rebuild already covers immutability.

### Externally-supplied-id Value Object vs locally-minted-id Entity
- **Rule:** Decide Entity-vs-VO for an id-bearing child by **identity provenance**, not by the mere presence of an `id` field. If the child's `new(...)` factory **self-generates** its id (locally minted) and the child needs mutable identity, model it `<<Entity>>`. If the id is **externally governed** — supplied by an upstream system or sibling subdomain and merely held as a reference, built via a factory that **accepts** the id (`new(id, ...)$` / `with_id(...)$` / `from_info(...)$`) — model it `<<Value Object>>` even though it carries an `id`.
- **Notation:**
  ```
  class MappingType {
    <<Value Object>>
    -id: str
    -code: str
    -name: str
    +new(id: str, code: str, name: str) MappingType$
  }

  class Category {
    <<Entity>>
    -id: str
    -code: str
    +new(code: str, name: str, description: str) Category$
  }
  ```
- **Example:** the leaf reference VOs `FileType`/`DomainType`/`MappingType`/`CacheType` whose `new(id, code, name, ...)$` **accept** an externally-supplied id are `<<Value Object>>`, while `Category.new(code, name, description)$` self-generates its id and is `<<Entity>>` — both from `template.md`; `MappingType` holding an externally-governed `-id: str` built via `from_info(mapping_type_info) MappingType$` — from `mapping.md`.
- **You may:** model an id-bearing child whose id is auto-generated yet whose semantics are pure value-equality as a `<<Value Object>>` anyway (e.g. `SourceField`/`DerivedField`, whose `SourceFields.new`/`DerivedFields.new` auto-generate the id but the leaf is still a VO) — here value-semantics override the provenance cue; rehydrate an `<<Entity>>` from upstream data via `from_data(...)$` (it remains an Entity).
- **Review:** when reviewing a diagram, treat this as canonical — do not flag it as non-standard. Do not flag an id-bearing `<<Value Object>>` as "should be an Entity because it has an id" — the deciding factor is identity provenance (external-reference → VO) or value-semantics, not id presence. Do not flag an auto-generated-id leaf modeled as a VO as a contradiction.

## Pitfalls
- Do not scatter a cohesive scalar cluster flat on the root, and do not ask the caller to pass a pre-built Details VO — `new(...)$` composes Details internally from flat primitives.
- Do not give a Details VO a return type for a **different** aggregate's Details (a copy-paste leak such as `MappingDetails.new(...) MappingRuleDetails$`); the `new(...)$` return type must be the owning VO.
- Do not model lifecycle as a Python `Enum` or a bare magic-string status field — use a `Status` `<<Value Object>>`.
- Do not model `is_*` / `has_error(s)` derived checks as `()` methods on Status/result VOs — they are bare `bool` **properties** with no parens. Reserve `()` for repository/Collection-VO predicate methods (`has_<entity>_with(...) bool`).
- Do not add in-place setters or mutating field-writes to a leaf VO; replace it wholesale via a factory (`with_new_<field>` / `with_id`) or rebuild through Status/Details/Either factories.
- Do not promote a Collection VO to an Entity or Aggregate Root, and do not hoist its children onto the root, just because it composes entities and exposes mutators — that is the Collection VO pattern.
- Do not classify an id-bearing child as an Entity solely because it has an `id`; check identity provenance (externally supplied → VO).
- Do not leave a Collection VO mutator's `None` return implicit when it is genuinely `None`; conversely, do annotate a `bool` changed-signal or entity return where one is intended.
- Do not let an active class reference a `%%`-commented-out VO/TypedDict (dangling `from_info`/lollipop targets); enable or remove the commented block before relying on it.
