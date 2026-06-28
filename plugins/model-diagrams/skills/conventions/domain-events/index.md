---
name: domain-events
description: How to model domain events on a Mermaid domain diagram — PascalCase past-tense classes, identity envelope, snapshot payloads, emits/handles edges, and the closed self-loop.
user-invocable: false
---

# Domain events

**Applies to:** domain diagrams (emit), commands/ops (handle)

This theme governs how an aggregate's published state transitions appear on the diagram: the `<<Domain Event>>` classes, their identity-first field envelopes and optional snapshot payloads, the `emits` edges that anchor them to the methods that fire them, and the `handles` edges that bind a consumed event back to an `on_<event>` handler. Model events on the domain `<stem>.md`; model the inbound handle on the `.commands.md` / `.ops.<service>.md` sibling.

## Ground knowledge

*Why these conventions are what they are — the canonical patterns they instantiate, the payload trade-off they span, and one safety obligation the self-loop implies. Names and sources let a reviewer cite the principle behind a suppression rather than assert it.*

- **Domain event = a past-tense record of something experts care about** (Evans/Vernon/Khononov; Lawrence). The past-tense name captures a *fact that happened* — "the moment your events read like commands (`ChargeCard`) you've smuggled coupling back in." Not every command yields one; model only what the business cares about (grounds "you may omit events").
- **Identity-first envelope** (Vernon's "enrich, but not over-enrich" / ~80%-of-subscribers rule): the minimal contract is the aggregate identity, which also supports message de-duplication; the deliberate narrow/wide variation per event is the bounded-enrichment discipline, not "inconsistent identity."
- **A denormalized snapshot payload IS Event-Carried State Transfer** (Khononov; Richardson; Lawrence) — the *most coupling-prone* event type, "decoupling in availability at the cost of coupling in schema." The three sanctioned forms map onto a spectrum: full snapshot = ECST, lossy snapshot = plain domain event, id-delta-only = an event notification (thin event). Choose deliberately rather than defaulting to a fat payload.
- **The root is the event source** (Aggregate; domain-event): events append to the root's list and the application service drains them — confirming both the root-emits and thread-the-aggregate realizations.
- **The closed self-loop carries an unstated obligation:** emit-and-handle is message-driven self-triggering across a transaction boundary (eventual consistency), so under at-least-once delivery the `on_<event>` handler **must be idempotent**, and the emit should ride the *same transaction* as the state change (outbox pattern). The loop is legal *and* safe only on those terms.

## Conventions

### Model each published transition as a `<<Domain Event>>` class, PascalCase past-tense
- **Rule:** Give every state transition the aggregate publishes its own class stereotyped `<<Domain Event>>` (the authored string — write it exactly as `<<Domain Event>>`, not `<<Event>>`). Name it PascalCase past-tense as `<Thing><Verb-ed>` (`CacheTypeCreated`, `LookupAdded`, `RulesetFilesAdded`, `SourceDMSFileAdded`, `EvoVersionUpdated`). Mark every field public (`+`).
- **Notation:**
  ```
  class CacheTypeCreated {
    <<Domain Event>>
    +id: str
    +code: str
    +name: str
    +lookups: list[LookupData]
  }
  ```
- **Example:** `CacheTypeCreated { <<Domain Event>> ... }` — from `cache-type.md`.
- **You may:** omit events entirely on a purely structural, never-pipeline-run domain-only aggregate (see "Domain-only aggregates may model no events"); within that exception there is no `<<Domain Event>>` class at all.
- **Review:** treat `<<Domain Event>>` (not `<<Event>>`) and PascalCase past-tense names as canonical — do not flag them. Do not flag a baked-in typo carried consistently across files (e.g. `FileAddedToProccess`, double-c, in `conversion.md` and re-declared in `ruleset`'s consumed-event set) as a one-site fix: the name propagates verbatim into payload fields and handler bindings, so a rename is a deliberate cross-file pass, not a review nit on a single edge.

### Lead every event with an identity envelope; let its width vary per event scope
- **Rule:** Put the aggregate's identity first in each event's fields so consumers route and correlate without a body lookup — the root `id` plus the aggregate's external-id context where one exists. Deliberately **narrow** the envelope for light lifecycle events and **widen** it for child-scoped events; do not force one uniform envelope across an aggregate's events.
- **Notation:**
  ```
  class LookupAdded {
    <<Domain Event>>
    +id: str
    +code: str
    +name: str
    +lookup_id: str
    +lookup_data: LookupData
  }

  class CacheTypeDisabled {
    <<Domain Event>>
    +id: str
    +code: str
  }
  ```
- **Example:** `LookupAdded` widens to `{id, code, name, lookup_id, lookup_data}` while the lifecycle event `CacheTypeDisabled` narrows to `{id, code}` — both from `cache-type.md`.
- **You may:** lead with a wide identity tuple where the aggregate has composite external identity (`project`'s events all lead `project_id, project_type, company_id, cmf`; `ruleset`'s lead `id` plus the `process_id, conversion_id, project_id, source_id, evo_version` quintet); add an `+epoch_token: int` to file-change/retry events and omit it from completion events within the same aggregate.
- **Review:** treat per-event envelope width as canonical — do not flag a narrower lifecycle envelope or a wider child-scoped one as "inconsistent identity". A single uniform envelope is not required; only the identity-first ordering is.

### Carry a denormalized snapshot in the payload when a consumer needs post-state
- **Rule:** When a downstream consumer needs the post-transition state (event-sourced projection, inference input), embed a denormalized `Data`/`Info`-typed snapshot in the event body rather than a bare id-delta, and own the nested payload off the event class with a lollipop edge (cardinality optional). Where the snapshot is only valid past a gate, justify that in the method's `## Invariants` prose.
- **Notation:**
  ```
  class RulesetCreationTriggered {
    <<Domain Event>>
    +process_id: str
    +conversion_id: str
    +project_id: str
    +source_id: str
    +evo_version: str
    +globals: Globals
    +category: CategoryData
    +files: list[FileData]
  }

  RulesetCreationTriggered --() Globals
  RulesetCreationTriggered --() CategoryData
  RulesetCreationTriggered --() "0..n" FileData
  ```
- **Example:** `RulesetCreationTriggered` carries the denormalized `evo_version + globals + category + files` snapshot — fired only once `conversion.ready` guarantees `evo_version` is non-`None` — from `conversion.md`. `CacheTypeCreated --() "1..n" LookupData` is the cardinality-bearing form in `cache-type.md`.
- **You may:** project a **lossy** snapshot on purpose (e.g. an `as_data()` source that excludes a field a consumer must not see fed back as its own input); attach no snapshot at all when consumers only need the id-delta (`project`'s events carry only scalar fields). Note the owned-payload edge here is the lollipop `--()` (sometimes unlabeled, carrying only cardinality) — a tolerated nested-payload-ownership form; a plain `*--` composition for the same owned dict is equally acceptable.
- **Review:** treat an embedded `*Data`/`*Info` snapshot payload as canonical — do not flag it as "denormalization smell" or demand a bare id-delta. Do not flag the cardinality-only / unlabeled `--()` owning a nested payload dict on an event class as a malformed edge.

### Draw `emits` from the emitting class; label the method(s), one event per class
- **Rule:** Draw event emission as `<Source> --> <Event> : emits (<method>)`, anchoring the arrow on the class that emits and naming the emitting method in parentheses. When one event fires from several methods, list them comma-separated inside the parens — never duplicate the event class per method.
- **Notation:**
  ```
  CacheType --> CacheTypeCreated : emits (new)
  Ruleset  --> RulesetFilesAdded : emits (add_files, add_file)
  ```
- **Example:** `Ruleset --> RulesetFilesAdded : emits (add_files, add_file)` and `Ruleset --> RulesInferenceCompleted : emits (add_mapping_rules, add_mappings)` — multi-method labels from `ruleset.md`.
- **You may:** use the multi-method form `emits (<method>[, <method>…])` whenever one event is fired from more than one site (commonly a bulk/singular mutator pair sharing a verb stem, `add_files`/`add_file`).
- **Review:** treat both the single-method `emits (<method>)` and the comma-listed multi-method `emits (m1, m2)` forms as canonical — do not flag a multi-emit label, and do not propose splitting one event into per-method duplicate classes.

### Children emit; the root accumulates — thread the owning aggregate into the mutator
- **Rule:** Let child entities and collection VOs anchor their own `emits` edges, but thread the owning aggregate into the mutating method's signature (`add_file(..., project: Project)`) so emitted events accumulate on the **root's** event list. Children hold no event list and no back-reference; the aggregate is the single accumulation point the application layer reads and publishes.
- **Notation:**
  ```
  class SourceDMS {
    <<Entity>>
    +add_file(file_id: str, file_type: str, stage: str, project: Project) None
  }

  SourceDMS --> SourceDMSFileAdded : emits (add_file)
  ```
- **Example:** `SourceDMS --> SourceDMSFileAdded : emits (add_file)` where `add_file` takes a trailing `project: Project` argument — from `project.md`. (Root-only emitters are equally valid: in `cache-type.md` all six `emits` edges originate on `CacheType` and `Lookup` has none.)
- **You may:** emit only from the root (no child `emits` edges at all — `cache-type`, `ruleset`); thread the owning aggregate under whatever parameter name fits (`project`, `conversion`, `conversion_reqs`); constrain ordering in prose (e.g. the root-summary event appended last, after all child events).
- **Review:** treat both realizations — child-emit-then-propagate and root-only emit — as canonical. Do not flag a child `<<Entity>>` / collection `<<Value Object>>` that carries an `emits` edge, and do not flag the trailing owning-aggregate argument on a child mutator as an extraneous parameter; it is the propagation thread that lands the event on the root.

### Closed self-loop: emit an event, then route it back to your own `on_<event>` handler
- **Rule:** When an aggregate both produces and consumes the same event, declare the event once as `<<Domain Event>>` (on the domain `.md`) and bind it inbound on the sibling under a `%% Messaging - <channel>` marker via a `handles (<context>, on_<event>)` edge to the matching `on_<event>` handler. Name both the source context and the bound handler in the label.
- **Notation:**
  ```
  %% Messaging - conversion-ops
  ConversionCommands --> SourceDMSFileAdded : handles (Projects, on_source_dms_file_added)
  ```
- **Example:** `ConversionCommands --> SourceDMSFileAdded : handles (Projects, on_source_dms_file_added)` under a `%% Messaging - conversion-ops` marker — from `conversion.commands.md`. On ops diagrams the same conceptual edge uses the lollipop form: `MappingRulesInference --() RulesetFilesAdded : handles (Ruleset, on_ruleset_files_added)` under `%% Messaging - mapping-rules-inference` — from `ruleset.ops.mapping-rules-inference.md`.
- **You may:** author the `handles` edge as either association `-->` (commands diagrams) or lollipop `--()` (ops diagrams, and conversion-reqs's commands) — both are the same conceptual inbound-handle edge; the `(context, on_<event>)` label disambiguates it. The `<channel>` token names the messaging channel for that consumer.
- **Review:** treat emit-and-consume of one event by the same aggregate as a deliberate closed loop, not a modeling cycle error — do not flag it. Recognize the `handles` edge by its `(context, on_<event>)` label regardless of arrow head (`-->` or `--()`); do not flag the arrow-style difference between commands and ops diagrams as inconsistent, and do not propose collapsing the loop.

### Domain-only aggregates may model no events at all
- **Rule:** A purely structural, never-pipeline-run domain-only aggregate may model **no** events — no `<<Domain Event>>` class, no `emits` edge, and (because its application siblings are empty stubs) no `DomainEventPublisher` reference. This is wholesale absence, distinct from the referenced-but-unmodeled gap below.
- **Notation:**
  ```
  %% (no <<Domain Event>> class, no `: emits` edge, no DomainEventPublisher edge)
  ```
- **Example:** `mapping.md` (stps-mappings) is structural-only — no `## Invariants`/`## Implementation`/`## Artifacts`, empty `.commands`/`.queries` stubs, no repository, and no events — the corpus's sole domain-only aggregate.
- **You may:** ship an event-shaped `Status` (e.g. a multi-stage `pending`/`completed`/`failed` inference lifecycle) without modeling any event, as long as the aggregate is genuinely structural-only and has no command flow or publisher to dangle.
- **Review:** treat the total absence of events on a structural-only domain-only diagram as canonical — do not flag "missing domain events" when there is also no command service, no publisher, and no repository. (This is the one case where eventlessness is acceptable; contrast the publisher-referenced gap in Pitfalls, which is an authoring defect.)

## Pitfalls
- **Events referenced but never modeled.** Do not inject `-event_publisher: DomainEventPublisher` with a `--() DomainEventPublisher : uses` edge and end every command Flow with a "Publish the accumulated domain events" step while declaring zero `<<Domain Event>>` classes. If the flows publish events, model the event classes (`<X>Created`/`<X>Enabled`/`<X>Disabled`, plus per-mutation events on nested children) with their `emits` edges and payloads. An aggregate with a publisher dependency and a publish-step is an incomplete event model, not an event-free one.
- **Wrong stereotype string.** Author `<<Domain Event>>`, not `<<Event>>`.
- **Duplicating an event per method.** When one event fires from several methods, comma-list them in a single `emits (m1, m2)` label; do not declare the event class once per method.
- **Re-listing the same event class for emit and consume.** In a closed self-loop the event is declared once (on the domain `.md`); the inbound side adds only the `handles` edge on the sibling — do not redeclare the class.
- **Dangling references into commented-out event/payload blocks.** If a payload type is `%%`-commented, do not leave an active `emits`/`--()` edge pointing into it; resolve the reference before relying on it.
- **Silent typo divergence.** When renaming a baked-in event typo (e.g. `FileAddedToProccess`), change every site — payload fields, `emits` labels, and handler bindings across files — in one deliberate pass; a one-site "fix" desyncs the binding.
