---
name: stereotypes
description: Stereotype vocabulary for diagram classes — the fixed role tags, ICan*/Interface ports, plural collection VOs, and the %% comment-out vs surface-marker distinction.
user-invocable: false
---

# Stereotypes

**Applies to:** all diagram kinds (domain, commands, queries, ops)

This theme governs the **role tag** that opens every class body: which of the fixed stereotype tokens to write, how to name the classes each tag implies (capability ports, collection Value Objects, ops services), and how to disable a subgraph with `%%` without confusing it for a `%% internal` / `%% Messaging` surface marker.

## Ground knowledge

*Why these conventions are what they are — the canonical building blocks each tag commits to, and where the project's tagging is finer than canon. Names and sources let a reviewer cite the principle behind a suppression rather than assert it.*

- **The closed tag set = the DDD tactical building blocks** (Evans; Vernon; Khononov): `<<Aggregate Root>>`/`<<Entity>>`/`<<Value Object>>`/`<<Repository>>`/`<<Domain Event>>`/`<<Service>>` are the Aggregate / Entity / Value-Object / Repository / Domain-Event / Domain-Service patterns; `<<Application>>` is the application service; `<<Interface>>` is a hexagonal port. Pick the tag by what the class *is* in DDD terms — which backs the "this vocabulary is canonical, not non-standard UML" review lens.
- **`ICan*` `<<Interface>>` = a hexagonal port** (Cockburn via Vernon; Khononov): an interface the inner layer defines, with an infrastructure adapter wired by DI — `ICanRetrieve*` is a driven/secondary port, `ICanManage*` the write-back port the layer calls out through. This is *why* it is an interface, not a service.
- **`<<Service>>` = a domain service** (Evans/Vernon): a stateless, activity-named operation (the `…Inferrer` shape) capturing a calculation/analysis that fits no single aggregate.
- **The mutable Collection VO** rests on Evans's explicit "mutable value object, never shared" carve-out (aggregate-internal, single-owner) — that is the textbook rebuttal to "but a VO must be immutable / holds mutable entities."
- **Deliberate divergence — the `<<Service>>` vs `<<Interface>>` split is finer than canon.** In DDD/hexagonal a domain service is routinely *itself* a port, so canon has one notion (a port the layer depends on) where the project tags two: `<<Service>>` for the domain-service/inferrer port and `<<Interface>>` for the thin `ICan*` capability/retrieval ports. A project taxonomy refinement, not a canonical line — so authors shouldn't read it as a DDD distinction. (`<<TypedDict>>` likewise has no canonical building-block name — it encodes use-case-shaped read/flat DTOs.)

## Conventions

### Exactly one stereotype, on the first body line
- **Rule:** Give every class exactly one stereotype, written in title-case double angle brackets as the **first member line** of the class body. Pick the role from the fixed vocabulary: `<<Aggregate Root>>`, `<<Entity>>`, `<<Value Object>>`, `<<TypedDict>>`, `<<Repository>>`, `<<Domain Event>>`, `<<Service>>`, `<<Interface>>`, and — only on `.commands.md` / `.queries.md` / `.ops.<service>.md` siblings — `<<Application>>`. Omit any stereotype the aggregate does not need (a flat aggregate carries no `<<Repository>>`/`<<Domain Event>>`/`<<Service>>`/`<<Entity>>`).
- **Notation:**
  ```
  class CacheType {
    <<Aggregate Root>>
    -id: str
    -code: str
    +new(code: str, name: str, lookups: list[LookupData]) CacheType$
  }
  ```
- **Example:** `class LookupArgument { <<Value Object>> ... }` — from `cache-type.md`.
- **You may:** omit whole stereotypes when a role is unused.
- **Review:** treat this vocabulary as canonical and closed — do not flag a class for carrying `<<Interface>>` or `<<Application>>` as "non-standard UML"; both are project stereotypes. Do not propose adding a stereotype to a role the aggregate legitimately omits.

### `<<Interface>>` capability ports (`ICan<Verb><Noun>`)
- **Rule:** Model an externally-implemented capability port (a hexagonal port the inference/ops layer depends on — retrieval or write-back) as an `<<Interface>>` class named `ICan<Verb><Noun>`. Use it for retrieval ports (`ICanRetrieve<Noun>Info`, returning `list[<X>Info]`) and for a write-back client port (`ICanManage<Aggregate>`, whose methods point back into the aggregate). Mark its members public (`+`). `<<Interface>>` is distinct from `<<Service>>`: a port the layer *calls out through* is `<<Interface>>`; a domain/inferrer service is `<<Service>>`.
- **Notation:**
  ```
  class ICanRetrieveFilesInfo {
    <<Interface>>
    +retrieve_files(file_ids: list[str]) list[FileInfo]
  }

  ICanRetrieveFilesInfo --> FileInfo : returns
  ```
- **Example:** `ICanManageRuleset` with `+find_ruleset(ruleset_id: str) RulesetInfo | None` and `+add_mapping_rules(ruleset_id, mapping_rules, epoch_token) None` — a write-back port the ops services call back into the aggregate through — from `ruleset.md`.
- **You may:** place `<<Interface>>` ports **in the domain file** (`<stem>.md`) alongside `<<Service>>` and the Info tree, as `ruleset.md` does — they are not confined to siblings; and use a write-back (inward-pointing) port, not just outward retrieval.
- **Review:** treat `<<Interface>>` as part of the fixed vocabulary — do not flag an `ICan*` port as an unknown stereotype, and do not propose collapsing it into `<<Service>>`. Do not flag an `<<Interface>>` port appearing in the domain file as misplaced.

### `<<Service>>` domain / inferrer ports
- **Rule:** Model an infrastructure-backed domain service or inference port (a parser, decision-maker, retriever, inferrer the application layer injects) as a `<<Service>>` class. Pair it with its result type via a returns edge `<<Service>> --> <ReturnVO> : returns`. Reserve `<<Service>>` for the service/inferrer itself; use `<<Interface>>` for the retrieval/write-back capability ports it depends on.
- **Notation:**
  ```
  class MappingRuleInferrer {
    <<Service>>
    +infer_rules(category_code: str, files: list[FileInfo], ...) InferencedMappingRules
  }

  MappingRuleInferrer --> InferencedMappingRules : returns
  ```
- **Example:** `class MappingInferrer { <<Service>> ... } ` returning `InferencedMappings` — from `ruleset.md`.
- **You may:** use both `<<Service>>` (inferrer ports) and `<<Interface>>` (retrieval/write-back ports) in the same diagram — they are not interchangeable; and have a `<<Service>>` outcome be a plain pair VO rather than an Either VO.
- **Review:** do not flag the coexistence of `<<Service>>` and `<<Interface>>` in one diagram as redundant — the two roles are deliberately split. Do not flag a `<<Service>>` whose result is a plain two-field VO for "not using the Either idiom".

### Aggregate-owned collections are named plural Value Objects
- **Rule:** Model an aggregate-owned collection as a named **plural** `<<Value Object>>` wrapping a single private `list[<Child>]` (snake_case plural) that owns the collection's mutation/lookup surface (`add`/`add_*`/`remove*`/`update`, `has_*`, `*_with_id`). The aggregate root composes the collection VO (`*--`) and delegates to it rather than holding a raw list. Provide `empty()` / `from_list(...)` rehydration factories (both `$`-marked) where the collection round-trips.
- **Notation:**
  ```
  class Mappings {
    <<Value Object>>
    -mappings: list[Mapping]
    +empty() Mappings$
    +from_list(mappings: list[Mapping]) Mappings$
    +add(mappings: list[MappingData]) None
    +update(mapping_id: str, mapping_data: MappingData) None
  }

  Ruleset *-- "1" Mappings
  Mappings *-- "0..n" Mapping
  ```
- **Example:** `Files` wrapping `-files: list[FileData]` and composed by `Ruleset *-- "1" Files` — from `ruleset.md`.
- **You may:** give a collection VO rich behavior (derived projection properties like `+pre_file_ids: list[str]`, target-excluding predicates) and keep it a VO; return a `bool` changed-signal from a collection mutator (`Files.add_files(...) bool`) for idempotent/at-least-once handling; or return the freshly-created child entity from an `add` (`SourceDMSes.add(source_id) SourceDMS`) instead of `None`; compose an `<<Entity>>` directly under the root with **no** collection VO when the aggregate is small.
- **Review:** treat a plural-named `<<Value Object>>` that wraps a list and exposes mutating methods as the canonical Collection Value Object — do not flag it for "a VO must be immutable", "VO holds mutable entities", or "hoist children onto the root". Do not flag a collection mutator returning `bool` or the created entity instead of `None`.

### `%%`-commented-out classes preserve a disabled subgraph
- **Rule:** When a class or edge is intentionally **disabled rather than deleted**, fence each of its lines with a leading `%%`, preserving the would-be `<<stereotype>>` and members so the subgraph can be re-enabled later. Use this only for staging an intended-but-not-yet-enabled subgraph.
- **Notation:**
  ```
  %% class ICanRetrieveMappingTypeInfo {
  %%   <<Interface>>
  %%   +retrieve_mapping_type(mapping_type_code: str) MappingTypeInfo
  %% }

  %% ICanRetrieveMappingTypeInfo --> MappingTypeInfo : returns
  ```
- **Example:** the commented `%% class MappingTypeInfo { <<TypedDict>> ... }` Info tree and its `%% ... *-- ...FieldInfo` composition block — from `mapping.md`.
- **You may:** stage an entire subgraph (class declarations **and** their edges) behind `%%` for later enabling.
- **Review:** recognize a `%%`-fenced **class/edge declaration** as a deliberately-disabled subgraph — do not flag the disabled class itself as missing or malformed. **But** a `%%`-fenced block is not a true target: if an **active** (non-`%%`) line references a commented-out type (e.g. an active `MappingType.from_info(... : MappingTypeInfo)` or a `MappingType --() ...FieldInfo` lollipop whose target is commented out), flag the **dangling reference** as an authoring error to resolve before the subgraph is enabled. Do NOT conflate `%%`-fenced declarations with `%% internal` / `%% Messaging` markers (next convention) — those are surface markers, not comment-outs.

### `%% internal` and `%% Messaging` are surface markers, not comments
- **Rule:** Inside an `<<Application>>` `<X>Commands` / `<X>Queries` body, group a service-to-service / internal method under a bare `%% internal` line to segregate it from the public surface — typically fronting a keyed bulk finder (`find_<entities>_by_codes`) or internal write-back methods. On a diagram's edge section, mark the messaging-handled edge group with a `%% Messaging - <channel>` line. Both are **section markers**, not commented-out members: the lines they front are live.
- **Notation:**
  ```
  class RulesetCommands {
    <<Application>>
    +create(...) Ruleset
    %% internal
    +find_ruleset(ruleset_id: str) RulesetInfo | None
  }
  ```
  ```
  %% Messaging - mapping-rules-inference
  MappingRulesInference --() RulesetFilesAdded : handles (Ruleset, on_ruleset_files_added)
  ```
- **Example:** `%% internal` fronting `+find_ruleset(ruleset_id: str) RulesetInfo | None` on `ruleset.commands.md`; `%% Messaging - mapping-rules-inference` on `ruleset.ops.mapping-rules-inference.md`.
- **You may:** place `%% internal` on either a `Commands` or a `Queries` surface; use one `%% Messaging - <channel>` per messaging channel.
- **Review:** treat `%% internal` and `%% Messaging - <channel>` as live surface/section markers — do not read them as commented-out methods or edges, do not flag the members below them as disabled, and do not flag the marker itself as stray. The distinguishing cue: a surface marker is a single bare label line (`%% internal`, `%% Messaging - x`); a comment-out is a `%%`-fenced `class`/edge **declaration**.

### `<<Application>>` ops / orchestration services on `.ops.<service>.md`
- **Rule:** Model a free-form orchestration/inference service (one that is neither `<X>Commands` nor `<X>Queries`) as an `<<Application>>` class in its own `<stem>.ops.<service>.md` sibling, one per service (N per aggregate). It consumes domain events via `on_<event>` handler methods, injects `<<Service>>` inferrer ports and `<<Interface>>` capability/write-back ports (one `--() <Collaborator> : uses` edge per injected dependency), and may carry demand-driven action methods (`infer_rule` / `infer_mapping`).
- **Notation:**
  ```
  class MappingRulesInference {
    <<Application>>
    -mapping_rule_inferrer: MappingRuleInferrer
    -ruleset_client: ICanManageRuleset
    +on_ruleset_files_added(ruleset_id: str, epoch_token: int, ...) None
    +infer_rule(ruleset_id: str, mapping_rule_id: str, feedback: str) None
  }

  MappingRulesInference --() MappingRuleInferrer : uses
  MappingRulesInference --() ICanManageRuleset : uses
  ```
- **Example:** `MappingRulesInference` injecting six collaborators (one inferrer `<<Service>>` + four `ICanRetrieve*Info` ports + the `ICanManageRuleset` write-back port), each drawn `--() <Collaborator> : uses` — from `ruleset.ops.mapping-rules-inference.md`.
- **You may:** inject a heavier dependency surface than a `Commands`/`Queries` class; and draw the inbound `handles` edge on an ops diagram as a **lollipop** — `MappingRulesInference --() RulesetFilesAdded : handles (Ruleset, on_ruleset_files_added)` — even though the same conceptual edge on a `<X>.commands.md` diagram is drawn as an **association**, `RulesetCommands --> RulesetCreationTriggered : handles (Conversions, on_ruleset_creation_triggered)`.
- **Review:** treat the `<stem>.ops.<service>.md` diagram and its `<<Application>>` ops-service shape as canonical — do not flag the `on_<event>` handlers, the dense `--() ... : uses` injection fan-out, or the demand-driven `infer_*` methods as out of place. Accept **both** the lollipop `--()` `handles` form (ops diagrams) and the association `-->` `handles` form (commands diagrams) for the inbound-event edge; do not flag either arrow style as wrong. Do not require an ops diagram merely because an aggregate carries an inference-shaped `Status` — ops is not implied by it.

## Pitfalls
- **Two stereotypes, or none, on one class.** Exactly one stereotype, and it must be the first body line — not buried below attributes, not duplicated.
- **Lowercase or wrong-case stereotype tokens.** Always title-case inside double angle brackets (`<<Value Object>>`, `<<Aggregate Root>>`), never `<<valueobject>>` or `<<VO>>`.
- **Confusing `<<Interface>>` with `<<Service>>`.** A capability port the layer calls *out through* (`ICan*`) is `<<Interface>>`; an injected domain/inferrer service is `<<Service>>`. Do not tag an `ICan*` port `<<Service>>`.
- **Raw `list[<Child>]` on the root instead of a collection VO.** Wrap an owned collection in a plural-named `<<Value Object>>` and delegate; do not fatten the root with collection bookkeeping unless the aggregate is small enough to compose a child entity directly.
- **Singular-named collection VO.** Name the wrapper plural (`Files`, `Mappings`, `SourceFields`) — never `File`/`Mapping` for the collection.
- **Mistaking a `%% internal` / `%% Messaging` surface marker for a comment-out** (or vice versa). A bare label line is a live section marker; a `%%`-fenced `class`/edge declaration is disabled.
- **Active references into a `%%`-commented block.** Never leave a live class method or lollipop pointing at a commented-out type — either enable the target or comment out the reference too.
- **An `<<Application>>` stereotype on a domain-file class.** `<<Application>>` belongs only on `.commands.md` / `.queries.md` / `.ops.<service>.md` siblings, never in `<stem>.md`.
