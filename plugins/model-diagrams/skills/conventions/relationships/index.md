---
name: relationships
description: Diagram conventions for relationship edges — composition cardinality, the --> verb vocabulary, the --() lollipop's three meanings, the handles edge, and %% markers (authoring + review).
user-invocable: false
---

# Relationships

**Applies to:** all diagram kinds

> This theme governs every edge you draw between classes: composition (`*--`), association (`-->`), and lollipop (`--()`), the controlled label vocabulary each carries, the inbound messaging `handles` edge, and the `%%` markers that partition a diagram. Pick the arrow by what the edge *means*, and label it from the closed vocabulary below.

## Conventions

### Ownership uses composition `*--` with quoted cardinality

- **Rule:** Draw an owned part with composition (`*--`) and an explicit **quoted** cardinality label. Use `"1"` for a single held VO/child, `"0..1"` for an optional single part, `"1..n"` for a required collection, `"0..n"` for an optional collection. Apply the same on the `Info` read-model graph (`<X>Info *-- "0..n" <Child>Info`; `<X>ListResult *-- "0..n" Brief<X>Info`). Always quote the cardinality — never write a bare `*--` with no label.
- **Notation:**
  ```
  MappingType *-- "1" SourceFields
  SourceFields *-- "1..n" SourceField
  ResolvedFields *-- "0..n" ResolvedField
  MappingTypeListResult *-- "0..n" BriefMappingTypeInfo
  ```
- **Example:** `CacheType *-- "1..n" Lookup` and `CacheTypeListResult *-- "0..n" BriefCacheTypeInfo` — from `cache-type.md`.
- **You may:** carry the same `*--` link into the read-model graph with a different lower bound than the write side when the read model is genuinely more constrained (e.g. a write-side `"0..n"` collection surfaced as a required `"1..n"` on its `Info`); compose a single VO at `"1"` for a flat, mostly-`"1"` root (e.g. `Mapping *-- "1" MappingDetails`).
- **Review:** when reviewing a diagram, treat quoted-cardinality `*--` as canonical — do not flag it as non-standard. Flag only a `*--` whose cardinality label is **missing** (a bare `Processes *-- Process`); that is the one authoring error under this convention.

### Behavioral/boundary associations use `-->` with a controlled verb vocabulary

- **Rule:** Use association (`-->`) for behavioral and boundary edges, labelled from the closed verb set: command-repo → aggregate is `: retrieves/stores`; query-repo → output DTO is `: returns`; query-repo → filter input is `: takes as argument`; a method-return / `as_data` / `<<Service>>`-return edge is `: returns`; an event-emission edge is `: emits (<method>)`, naming the emitting method(s) in parentheses. The parenthesized list **may name multiple** methods that all emit the same event.
- **Notation:**
  ```
  CommandCacheTypeRepository --> CacheType : retrieves/stores
  QueryCacheTypeRepository --> CacheTypeInfo : returns
  QueryCacheTypeRepository --> CacheTypeFiltering : takes as argument
  CacheType --> CacheTypeCreated : emits (new)
  Ruleset --> RulesInferenceCompleted : emits (add_mapping_rules, add_mappings)
  ```
- **Example:** `CacheType --> LookupAdded : emits (add_lookup)` — from `cache-type.md`; the multi-method form `Ruleset --> RulesetFilesAdded : emits (add_files, add_file)` — from `ruleset.md`.
- **You may:** name multiple emitting methods in one `emits (m1, m2)` label; originate every `emits` edge on the aggregate root even when a child does the emitting (events accumulate on the root regardless).
- **Review:** treat `{retrieves/stores, returns, takes as argument, emits (<method>)}` as the closed `-->` vocabulary and `emits (m1, m2)` as a sanctioned form — do not flag them. Treat the full string `: takes as argument` as canonical for the filter-input edge; **do not propose `: takes`** as a fix (the bare `takes` is the drift). Likewise canonicalize on `: returns` (with the `s`) for a return edge — `: return` is the drift, not the standard.

### The lollipop `--()` has three meanings, disambiguated by label

- **Rule:** Use `--()` for exactly three things, told apart by the **label**:
  1. **Pass-through argument** — `: takes as argument` on a forwarder whose real consumer carries a matching `-->`/`*--` (see *Pass-through argument arrow* below).
  2. **Application/domain role label** — `uses` / `manipulates` / `raises` / `returns` / `takes as argument` on `<<Application>>` and port edges (and, on the domain root, `: raises` for exceptions a method raises directly).
  3. **Nested-dict / optional ownership** — an **unlabeled** `--()` carrying only a quoted cardinality, holding a nested TypedDict.
  Prefer `*--` over `--()` for owned nested dicts: reach for meaning 3 only where the dict is genuinely an optional/nested payload, not a composed part.
- **Notation:**
  ```
  Conversion --() TemplateInfo : takes as argument     %% (1) pass-through
  MappingRulesInference --() ICanManageRuleset : uses  %% (2) role label
  Ruleset --() RulesetEpochSuperseded : raises          %% (2) raises on the domain root
  RulesInferenceFailed --() "0..n" InferenceError       %% (3) nested-dict ownership
  ```
- **Example:** `LookupInfo --() "0..n" LookupArgumentData` and `LookupInfo --() "1..n" EntryItemData` (meaning 3, nested-dict ownership) — from `cache-type.md`; `Ruleset --() FileData : takes as argument` (meaning 1) and `Ruleset --() MappingRuleNotFound : raises` (meaning 2, on the domain root) — from `ruleset.md`.
- **You may:** carry all three meanings on one diagram (`ruleset.md` does); place `: raises` lollipops directly in the domain file on the aggregate root, not only on application siblings; use the unlabeled cardinality-only form for a nested TypedDict.
- **Review:** a `--()` labelled `takes as argument` is **always** pass-through, never event emission — do not flag it as an event edge. Treat all three labelled meanings as canonical. The unlabeled nested-dict-ownership form (meaning 3) is tolerated; do not flag it as non-standard, but a cardinality-only `--()` whose **target class does not exist** (e.g. it lives only inside a `%%`-commented block) is a dangling edge — flag that.

### Pass-through argument arrow

- **Rule:** When a class accepts a parameter via a method but only **forwards** it to a delegate that does the real work, draw that edge as a lollipop `--()` with the exact label `takes as argument`. The class that actually inspects the parameter's fields draws `-->` (or `*--`) with the matching `takes as argument` label. The arrowheads encode forwarder-vs-consumer. One or more `--()` forwarders may chain to the same target; exactly one terminal `-->`/`*--` consumer carries the matching label.
- **Notation:**
  ```
  <Forwarder> --() <Target> : takes as argument
  <Consumer>  --> <Target> : takes as argument
  ```
- **Example:** from `cache-type.md` — `CacheType --() LookupArgumentData : takes as argument` (the root forwards `arguments` into `Lookup`) paired with `Lookup --() EntryItemData : takes as argument` down the chain; the terminal consumer is the class whose method reads the fields. (On `mapping-type.md` the canonical pair is `MappingType --() CacheTypeData : takes as argument` forwarder vs `ResolvedFields --> CacheTypeData : takes as argument` consumer — the root forwards, `ResolvedFields.add` inspects the fields.)
- **You may:** chain several `--()` forwarders through intermediaries to a single target, as long as exactly one terminal `-->`/`*--` carries the matching `takes as argument` label.
- **Review:** when you see `--() <Target> : takes as argument`, look for a paired `--> <Target> : takes as argument` (or `*--`) elsewhere in the same diagram. **If the paired consumer arrow exists, do not flag** — this is a pass-through forwarder, canonical regardless of source/target stereotype or multiplicity. If no paired consumer arrow exists, fall back to normal arrow-vocabulary review. The label disambiguates from event emission: `--()` labelled exactly `takes as argument` is pass-through; a `--()` with any other label is reviewed under the role-label or event conventions. Do **not** propose "convert the forwarder to `-->`" as remediation — the lollipop-vs-solid split is the convention.

### The inbound messaging `handles` edge under a `%% Messaging - <channel>` marker

- **Rule:** Model an inbound external event bound to an `on_<event>` handler as a `handles` edge on the application/ops diagram, placed under a `%% Messaging - <channel>` marker comment. Label it `: handles (<SourceContext>, on_<method>)` — a two-part payload naming both the upstream bounded context (or aggregate) and the bound handler method. Declare each consumed event inline on that diagram as a `<<Domain Event>>` class. Use the **solid arrow** `-->` for the handles edge on `<X>Commands` diagrams; use the **lollipop** `--()` on `.ops.<service>.md` diagrams.
- **Notation:**
  ```
  %% Messaging - <channel>
  <Resource>Commands --> <Event> : handles (<SourceContext>, on_<method>)
  ```
- **Example:** from `ruleset.ops.mapping-rules-inference.md` —
  ```
  %% Messaging - mapping-rules-inference
  MappingRulesInference --() RulesetFilesAdded : handles (Ruleset, on_ruleset_files_added)
  MappingRulesInference --() RulesInferenceRetried : handles (Ruleset, on_rules_inference_retried)
  ```
- **You may:** name the source as either a bounded context or an aggregate in the `(<SourceContext>, …)` slot; consume an event the same aggregate also emits (a closed emit-and-handle loop); place the marker under a per-ops-segment channel name (`%% Messaging - mappings-inference`).
- **Review:** the two-part `(<SourceContext>, on_<method>)` label is canonical — do not flag it. Both arrow styles are sanctioned for the `handles` edge: solid `-->` is the commands-diagram form, lollipop `--()` is the ops-diagram form. **Do not flag either style, and do not propose normalizing one to the other** — the style follows the diagram family (commands → solid, ops → lollipop). The marker line `%% Messaging - <channel>` is a section marker, not a commented-out class; do not flag it as dead code.

### Application/ops dependency edges use `--()` role labels; `%% internal` partitions the surface

- **Rule:** On `<<Application>>` Commands / Queries / Ops diagrams, draw every dependency as a `--()` lollipop with a role label from the fixed set: `uses` (injected collaborators), `manipulates` (the aggregate — commands only), `raises` (one edge per exception, enumerated individually), `returns` (output DTOs), `takes as argument` (input DTOs). Group methods that are internal / service-to-service (not public surface) under a `%% internal` surface-partition marker comment.
- **Notation:**
  ```
  MappingRulesInference --() MappingRuleInferrer : uses
  MappingRulesInference --() RulesetNotFound : raises
  CacheTypeQueries --() CacheTypeFiltering : takes as argument
  %% internal
  CacheTypeQueries --() ...   %% the bulk find_*_by_codes finder sits here
  ```
- **Example:** from `ruleset.ops.mapping-rules-inference.md` — `MappingRulesInference --() ICanManageRuleset : uses` and the per-exception `MappingRulesInference --() RulesetEpochSuperseded : raises`. The `%% internal` marker consistently fronts a bulk keyed finder (`CacheTypeQueries.find_cache_types_by_codes`) returning a bare `list[<X>Info]`.
- **You may:** enumerate several distinct `raises` edges (one per exception type); place `%% internal` on both a commands diagram (the write-back `add_*`/`update_*` methods) and a queries diagram (a `find_*` finder).
- **Review:** treat per-exception `raises` enumeration and the `%% internal` surface marker as canonical — do not flag them. `%% internal` is a surface-partition marker, **not** a commented-out class; do not conflate it with `%%`-fencing of whole class declarations, and do not flag it as dead code.

### Ops orchestration diagrams wire consumers via `on_<event>` handlers and `ICan*` ports

- **Rule:** When an aggregate needs free-form orchestration/inference beyond Commands/Queries, model it as one or more `<<Application>>` classes in `<stem>.ops.<service>.md` sibling diagrams (N per aggregate). Each ops class injects `<<Service>>` inferrer ports and `<<Interface>>` `ICan<Verb>` capability/client ports as private fields, draws each injection as `--() <Port> : uses`, consumes the aggregate's domain events via `on_<event>` handler methods (returning `None`), and binds those handlers with `handles (<SourceAggregate>, on_<event>)` edges under a `%% Messaging - <channel>` marker. The class calls back into the aggregate through an `ICanManage<Aggregate>` write-back port.
- **Notation:**
  ```
  class <Service>Inference {
    <<Application>>
    -inferrer: <X>Inferrer
    -ruleset_client: ICanManage<Aggregate>
    +on_<event>(...) None
  }
  <Service>Inference --() <X>Inferrer : uses
  <Service>Inference --() ICanManage<Aggregate> : uses
  ```
- **Example:** from `ruleset.ops.mapping-rules-inference.md` — `MappingRulesInference` injects six collaborators (`MappingRuleInferrer` `<<Service>>` + four `ICanRetrieve*Info` `<<Interface>>` ports + the `ICanManageRuleset` write-back port), each wired `--() <Port> : uses`, with `+on_ruleset_files_added(...) None` and the demand-driven `+infer_rule(...) None`.
- **You may:** inject a heavier dependency surface than `<X>Commands`/`<X>Queries` (several `uses` edges); mix `<<Service>>` inferrer ports and `<<Interface>>` capability ports in one ops class; point an `ICanManage<Aggregate>` write-back port *inward* (the ops class calls back into the aggregate through it).
- **Review:** the `<stem>.ops.<service>.md` filename, the `<<Application>>` ops-class shape, `on_<event>` handlers, and `ICan*`/`<X>Inferrer` `uses` edges are all canonical — do not flag them. The lollipop `handles` style on ops diagrams is canonical here (see the messaging convention) — do not propose converting it to the commands-diagram solid form.

## Pitfalls

- **Bare composition.** Writing `*--` with no quoted cardinality (e.g. `Processes *-- Process`). Always quote the multiplicity (`"1"`, `"0..1"`, `"1..n"`, `"0..n"`).
- **Verb-label drift.** Writing `: takes` instead of `: takes as argument` for a filter-input edge, or `: return` instead of `: returns` for a return edge. Use the long, plural canonical forms.
- **Overloading `--()` for owned nesting.** Reaching for an unlabeled cardinality-only `--()` where the part is genuinely composed — prefer `*--` for owned nested dicts and reserve the lollipop for pass-through, role labels, and truly optional nested payloads.
- **Dangling lollipop targets.** A cardinality-only `--()` (or a pass-through `--()`) whose target class exists only inside a `%%`-commented block — the edge points at nothing. Either enable the target or drop the edge.
- **Pass-through without a consumer.** A `--() <Target> : takes as argument` forwarder with no paired `--> <Target> : takes as argument` (or `*--`) consumer anywhere in the diagram — the forwarder is meaningless without the class that actually reads the fields.
- **One-armed `handles` label.** Writing `handles` with only the method or only the source — the label must be the two-part `(<SourceContext>, on_<method>)`. And it must sit under a `%% Messaging - <channel>` marker.
- **Collapsing `raises`.** Bundling multiple exceptions onto one edge — enumerate one `--() <Exception> : raises` edge per exception type.
- **Confusing `%%` kinds.** Treating a `%% internal` or `%% Messaging - <channel>` **surface/section marker** as a commented-out class (or vice-versa). Surface markers partition live content; `%%`-fenced class declarations disable a subgraph.
