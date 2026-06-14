---
name: application-services
description: Authoring + review conventions for the <<Application>> Commands/Queries sibling diagrams — class shape, injected collaborators, --() role labels, messaging coupling.
user-invocable: false
---

# Application services — Commands & Queries

**Applies to:** commands and queries diagrams

> This theme governs the `<stem>.commands.md` and `<stem>.queries.md` sibling diagrams: the `<<Application>>` `<Aggregate>Commands` / `<Aggregate>Queries` classes, the collaborators they inject, the `--()` lollipop role-label vocabulary that wires every dependency, and the inbound-messaging `handles` edges that bind upstream events to `on_<event>` command handlers. Author each sibling against these rules top-to-bottom.

## Conventions

### Application-service class shape
- **Rule:** Put the command/query services only on the `<stem>.commands.md` and `<stem>.queries.md` siblings (never the domain diagram). Name them `<Aggregate>Commands` and `<Aggregate>Queries`, give each the `<<Application>>` stereotype on the first body line, and inject collaborators as private (`-`) snake_case fields. Make every member public (`+`). Command methods take the aggregate `id` first (except `create`) and return the live aggregate; query methods return `Info` / `ListResult` read models.
- **Notation:**
  ```mermaid
  classDiagram
    class CacheTypeCommands {
      <<Application>>
      -command_cache_type_repository: CommandCacheTypeRepository
      -event_publisher: DomainEventPublisher
      +create(code: str, name: str, lookups: list[LookupData]) CacheType
      +update_details(id: str, name: str) CacheType
      +enable(id: str) CacheType
    }
  ```
- **Example:** `CacheTypeCommands` carries `+update_details(id: str, name: str) CacheType` (id-first, returns the aggregate) and `+create(code: str, name: str, lookups: list[LookupData]) CacheType` — from `cache-type.commands.md`.
- **You may:** name the creation method `create` (not `new`) and have it take **no** `id`; name event-driven handlers `on_<event>` instead of imperative verbs; key methods by a composite business key instead of `id` (`ProjectCommands.update_evo_version(project_type, company_id, cmf, evo_version)`); return `list[<Aggregate>]` from a fan-out handler (`ConversionCommands.on_project_removed(project_id: str) list[Conversion]`); leave a sibling as an empty stub (`classDiagram` keyword, no class) when the aggregate is domain-only.
- **Review:** when reviewing a diagram, treat this as canonical — do not flag it as non-standard. The `<<Application>>` stereotype on a non-domain sibling, `create` taking no id, `on_<event>` handler names, composite-business-key parameter lists, and `list[<Aggregate>]` fan-out returns are all sanctioned shapes, not modeling errors.

### Injected collaborators — repository + publisher (commands) / repository only (queries)
- **Rule:** Inject the command repository **and** a `DomainEventPublisher` into `<Aggregate>Commands`; inject only the query repository into `<Aggregate>Queries`. Name the repo field `-command_<stem>_repository: Command<X>Repository` (or `-query_<stem>_repository: Query<X>Repository`) and the publisher `-event_publisher: DomainEventPublisher`. Wire each injected field with a `--() <Collaborator> : uses` edge.
- **Notation:**
  ```mermaid
    -command_ruleset_repository: CommandRulesetRepository
    -event_publisher: DomainEventPublisher
  ...
    RulesetCommands --() CommandRulesetRepository : uses
    RulesetCommands --() DomainEventPublisher : uses
  ```
- **Example:** `RulesetCommands --() DomainEventPublisher : uses` paired with `-event_publisher: DomainEventPublisher` — from `ruleset.commands.md`.
- **You may:** name the publisher field `-domain_event_publisher` instead of `-event_publisher`; inject domain `<<Service>>` / `<<Interface>>` ports beyond the repo+publisher pair when the aggregate needs them (`ConversionCommands` injects `-template_retriever: ICanRetrieveTemplate` and `-decision_maker: ICanStartRulesetCreation`); inject the publisher and end Flows with "Publish … domain events" even when no `<<Domain Event>>` class is modeled (events may be behavioral-only).
- **Review:** when reviewing a diagram, treat this as canonical — do not flag it as non-standard. A `<<Query>>` sibling carrying no publisher is correct (queries emit no events); extra `<<Service>>`/`<<Interface>>` injections are not "too many dependencies"; an injected `DomainEventPublisher` with zero modeled events is the known events-referenced-but-unmodeled shape, not a missing-class defect.

### Cross-aggregate command-repo injection
- **Rule:** When a command must validate a reference against a sibling aggregate, inject that sibling's **command** repository (`Command<Foreign>Repository`) purely for existence / resolvability pre-flight checks. Use it only for `has_*` / `*_of_<key>` lookups — never reach into the foreign aggregate's state or mutate it.
- **Notation:**
  ```mermaid
    -command_cache_type_repository: CommandCacheTypeRepository
  ...
    MappingTypeCommands --() CommandCacheTypeRepository : uses
  ```
- **Example:** `MappingTypeCommands` injects `CommandCacheTypeRepository` so `add_resolved_field` / `update_resolved_field` can check resolvability via `CacheType.ensure_can_resolve` (referenced in `mapping-type.commands.md`); `TemplateCommands` injects three foreign command repos (`CommandDomainTypeRepository`, `CommandMappingTypeRepository`, `CommandCacheTypeRepository`).
- **You may:** inject more than one foreign repo (template injects three) and omit a foreign check where none is needed (template has no FileType repo, so `add_file_type` has no cross-aggregate check); name the foreign existence-check method by its repo's own vocabulary (prefer `has_<foreign>_with_<key>`, but `<foreign>_of_<key>` finders are also used).
- **Review:** when reviewing a diagram, treat this as canonical — do not flag it as non-standard. A `<<Application>>` command service that depends on a *foreign* command repository for a pre-flight check is intended cross-aggregate validation, not an aggregate-boundary violation; do not propose collapsing the two aggregates or routing the check through the foreign query side.

### `--()` lollipop role-label vocabulary
- **Rule:** Draw every dependency on the `<<Application>>` siblings as a lollipop `--()` edge labelled with one role from the fixed set — `uses`, `manipulates`, `raises`, `returns`, `takes as argument`. Use `uses` for every injected collaborator (repo / publisher / service / port); `manipulates` for the aggregate (commands only); `raises` once per exception, enumerated individually; `returns` for output DTOs (queries); `takes as argument` for input DTOs and `Pagination`. Command siblings carry `uses` / `manipulates` / `takes as argument` / `raises`; query siblings carry `uses` / `returns` / `takes as argument` / `raises`.
- **Notation:**
  ```mermaid
    CacheTypeCommands --() CommandCacheTypeRepository : uses
    CacheTypeCommands --() CacheType : manipulates
    CacheTypeCommands --() LookupData : takes as argument
    CacheTypeCommands --() CacheTypeNotFound : raises
    CacheTypeQueries --() CacheTypeInfo : returns
    CacheTypeQueries --() Pagination : takes as argument
  ```
- **Example:** `CacheTypeCommands --() CacheType : manipulates` and `CacheTypeQueries --() CacheTypeInfo : returns` — from `cache-type.commands.md` and `cache-type.queries.md`.
- **You may:** enumerate two distinct `NotFound` exceptions when an aggregate has dual-key lookups (`--() ConversionNotFound : raises` **and** `--() ConversionNotFoundBySource : raises`); declare `raises` edges on a query sibling even though its finders return non-optional `Info` (encoding service-layer optionality resolution on the query side).
- **Review:** when reviewing a diagram, treat this as canonical — do not flag it as non-standard. The lollipop arrow head here is not the domain-diagram pass-through/event idiom — on application siblings it is the universal dependency edge, disambiguated by its role label. Do not propose switching `--()` to `-->`, do not flag a separate `raises` edge per exception as redundant, and do not flag a query-side `raises` edge as contradicting a non-optional return.

### Query services resolve repository optionality
- **Rule:** Have the query repository's singular finder return `<X>Info | None`, but declare the corresponding `<Aggregate>Queries` finder **non-optional** `<X>Info` — the service raises `<Aggregate>NotFound` when the repo yields `None`. Resolve the `None` at the service boundary, not in the repo signature. Expose the public query pair as `find_<entity>(<entity>_id) <X>Info` (singular) and `find_<entities>(filtering: <X>Filtering | None, pagination: Pagination | None) <X>ListResult` (plural).
- **Notation:**
  ```mermaid
    class CacheTypeQueries {
      <<Application>>
      -query_cache_type_repository: QueryCacheTypeRepository
      +find_cache_type(cache_type_id: str) CacheTypeInfo
      +find_cache_types(filtering: CacheTypeFiltering | None, pagination: Pagination | None) CacheTypeListResult
      %% internal
      +find_cache_types_by_codes(cache_type_codes: list[str]) list[CacheTypeInfo]
    }
  ```
- **Example:** `+find_cache_type(cache_type_id: str) CacheTypeInfo` — non-optional on the service even though the repo returns `CacheTypeInfo | None` — from `cache-type.queries.md`.
- **You may:** drop the singular/plural `find_<x>` / `find_<x>s` split for an already-plural noun (`find_single_reqs` / `find_multiple_reqs`); resolve **two** optional finders to two distinct `NotFound`s on dual-key aggregates; place an internal service-to-service finder (a keyed bulk read returning bare `list[<X>Info]`, or a secondary `_by_<key>` lookup) under a `%% internal` surface marker.
- **Review:** when reviewing a diagram, treat this as canonical — do not flag it as non-standard. A `Queries` finder returning non-optional `<X>Info` over a repo's `<X>Info | None` is the intended optionality resolution, not a swallowed-null bug. The `%% internal` line is a surface-partition marker (parsed by `rest-api-spec:surface-markers`), not a commented-out method — do not treat a method following `%% internal` as disabled, and do not flag the bare `list[<X>Info]` bulk return for "not using `ListResult`".

### Application-service methods may return `<Aggregate> | None` (idempotent no-op)
- **Rule:** A method on an `<<Application>>` service — an `<Aggregate>Commands` method, or a free-form ops-class method on a `<stem>.ops.<op-name>.md` diagram — may declare a return type of `<AggregateRoot> | None`. The `None` arm signals an **idempotent no-op**: the target no longer exists (e.g. it was concurrently deleted by another handler while work was in flight), so there is nothing to persist and the call returns without error rather than raising not-found. The value arm returns the aggregate as usual. Use this whenever a missing target must be a benign success — typically a write-back consumed by a message handler that would otherwise retry forever on a `404`.
- **Notation:**
  ```mermaid
    +add_mapping_rules(ruleset_id: str, mapping_rules: list[MappingRuleData], epoch_token: int) Ruleset | None
  ```
- **Example:** `+add_mapping_rules(ruleset_id: str, mapping_rules: list[MappingRuleData], epoch_token: int) Ruleset | None` — from `ruleset.commands.md`; its Flow step 1 reads "if not found … **return without error (idempotent no-op)**" (symmetric to `on_process_removed`'s missing-ruleset no-op).
- **You may:** use the same `<X> | None` return on a free-form ops-class method (where `<X>` may be any return DTO / value object, not just the aggregate root); leave a sibling `Commands` method returning the bare aggregate (`Ruleset`) when its missing target *should* raise `NotFound` instead — the two shapes coexist in one class (`update_mapping_rule(...) Ruleset` raises `RulesetNotFound`; `add_mapping_rules(...) Ruleset | None` no-ops).
- **Review:** this is the **primary home** of the "Application-service methods may return `<Aggregate> | None`" convention. When reviewing, suppress the finding when **all** hold: (1) the diagram is a commands (`<stem>.commands.md`) or ops (`<stem>.ops.<op-name>.md`) diagram and the class carries `<<Application>>`; (2) a public method's return type is `<X> | None` where `<X>` is the aggregate root (or, on an ops class, any return DTO / value object); (3) the method's Flow describes the missing-target branch as a *return without error* / no-op, not a raise. When the cues hold, **do not flag** the optional return as "inconsistent optionality", "should raise `NotFound` instead", or "missing error handling", and **do not** propose changing the return type to the bare aggregate or adding a not-found raise — the optionality is the deliberate idempotent-no-op contract (it maps at the REST layer to a runtime-conditional `200`/`201`-or-`204 No Content`). A reviewer may still raise a substantive concern only if the Flow's no-op rationale is genuinely absent. Note the scope: a `Queries` / `<<Query>>` method returning `<DTO> | None` is an ordinary nullable lookup, **not** this convention — do not apply the suppression there.

### Inbound messaging coupling — `%% Messaging` marker + `handles` edges
- **Rule:** When a command service consumes upstream events, group the bindings under a `%% Messaging - <channel>` marker comment and draw one `handles (<SourceContext>, on_<handler>)` edge per consumed event, binding the inbound `<<Domain Event>>` to its `<Aggregate>Commands.on_<event>` handler. Declare each inbound event inline as a `<<Domain Event>>` class in the same `.commands.md` file.
- **Notation:**
  ```mermaid
    %% Messaging - ruleset-ops
    RulesetCommands --> RulesetCreationTriggered : handles (Conversions, on_ruleset_creation_triggered)
    RulesetCommands --> ProcessRemoved : handles (Conversions, on_process_removed)

    class RulesetCreationTriggered {
      <<Domain Event>>
      +process_id: str
      +conversion_id: str
    }
  ```
- **Example:** `ConversionCommands --> SourceDMSFileAdded : handles (Projects, on_source_dms_file_added)` under `%% Messaging - conversion-ops` — from `conversion.commands.md` (seven such edges over inline `SourceDMSFileAdded` … `ProjectRemoved` events).
- **You may:** use either arrow style for the `handles` edge — association `-->` is the `.commands.md` majority and the recommended canonical form, but a lollipop `--()` carrying the same `handles (...)` label is also accepted (conversion-reqs and the ops diagrams use it); model a self-loop where the service handles its own aggregate's event (`ConversionReqsCommands --() DomainTypeAdded : handles (ConversionReqs, on_domain_type_added)`); make a handler a create-on-demand upsert that never raises `NotFound` (`project.on_file_validated`) instead of lookup-or-raise.
- **Review:** when reviewing a diagram, treat this as canonical — do not flag it as non-standard. A `%% Messaging - <channel>` line is a section marker, not a commented-out class; the two-part `handles (<Context>, on_<handler>)` label naming both source context and handler is the intended label shape; an `on_<event>` upsert handler that creates on demand and never raises `NotFound` is sanctioned. Do not flag either `-->` or `--()` for the `handles` edge as wrong — only a mismatched label is a defect.

## Pitfalls
- **Putting the services on the domain diagram.** `<Aggregate>Commands` / `<Aggregate>Queries` live only on the `.commands.md` / `.queries.md` siblings — never the `<stem>.md` domain file.
- **Naming the creation method `new` or giving it an `id`.** The creation carve-out is `create(...)` and takes **no** `id`; every other command method is id-first (or composite-business-key-first).
- **Injecting a `DomainEventPublisher` into a `Queries` class.** Queries emit no events — inject the query repository only.
- **Using `-->` for an injected-collaborator or DTO edge on a sibling.** Every dependency edge on an `<<Application>>` sibling is a lollipop `--()`; `-->` is reserved for the inbound `handles` association (which may also be `--()`).
- **Collapsing multiple `raises` edges into one or omitting them.** Enumerate each exception individually as its own `--() <Exception> : raises` edge — including the second `NotFound` for a dual-key aggregate, and `raises` edges on query siblings whose finders return non-optional `Info`.
- **Declaring the query finder as `<X>Info | None`.** The repo returns `| None`; the `Queries` service returns non-optional `<X>Info` and raises `<Aggregate>NotFound`. Pushing the optionality up to the service signature defeats the convention.
- **Treating `<X> | None` as a bug or `%% internal` as a comment-out.** An `<X> | None` return on a commands/ops method is the idempotent-no-op contract; `%% internal` is a surface-partition marker — the method after it is live.
- **Forgetting to declare an inbound event class.** Every event named in a `handles (...)` edge must have its inline `<<Domain Event>>` class in the same `.commands.md` file.
