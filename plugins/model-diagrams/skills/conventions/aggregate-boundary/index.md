---
name: aggregate-boundary
description: Aggregate-boundary diagram conventions — root as sole mutation entry point and single event source, forwarding chains, and sanctioned collection-mutator return shapes (authoring + review).
user-invocable: false
---

# Aggregate boundary

**Applies to:** domain diagrams

> This theme governs how a domain diagram encodes the aggregate boundary: the root is the only object callers mutate through and the only place domain events accumulate, interior children are reached only by id through forwarding methods, and a small set of non-`None` collection-mutator return types is sanctioned. Use it when drawing the root's method surface, its `emits` edges, and the composition chain down to grandchildren.

## Ground knowledge

*Why these conventions are what they are — the canonical patterns they instantiate, and where the project deliberately bends them. Names and sources let a reviewer cite the principle behind a suppression rather than assert it.*

- **Aggregate = consistency boundary** (Evans, *DDD*; Vernon, *IDDD*; Richardson, *Microservices Patterns*). The root is the only object outside callers may reference, all invariants hold on every commit, and you modify **one aggregate per transaction** — the four conventions below are this discipline made concrete, not project idiosyncrasy.
- **Root-only forwarding CRUD = Law of Demeter + Tell-Don't-Ask** (Vernon, *IDDD* ch.10). Forwarding a `*_id` down the ownership chain while keeping every mutator behind the root *is* Vernon's two named aggregate-implementation techniques — the forwarding is the boundary, not boilerplate. Reaching an interior child by a domain `code` is fine because interior entities have only *local identity* (distinct from cross-aggregate reference-by-*global*-id).
- **Root is the single event source** (Evans/Vernon; Richardson). An aggregate must not call the messaging API itself; events accumulate on the root and the application service drains them — which is *why* children get no `DomainEventPublisher` and no back-reference.
- **Silent-create asymmetry** (Evans/Vernon): an event is modeled only for "an occurrence domain experts care about" — not every command yields one, so a purely structural on-demand container legitimately emits nothing on create.
- **Deliberate divergence — thread-the-aggregate emission.** Canon has a child *return* events upward or accumulate them on an `AbstractAggregateRoot` the service drains (Richardson prefers the return form, calling the superclass route "awkward for non-root members"). The project instead threads the root object *into* the child's mutator signature so the child appends to the root's list — a transient inward reference that preserves the canonical invariant (root stays the sole accumulation point) while avoiding per-child event lists. The non-`None` collection-mutator returns likewise bend Command-Query Separation (Meyer) deliberately: the value is load-bearing for the root's boundary bookkeeping.

## Conventions

### Root is the sole mutation entry point; CRUD forwards down the ownership chain
- **Rule:** Make the aggregate root the only object callers mutate through. Give the root a per-interior-child CRUD method that accepts the relevant child **id** (and any leaf `*_id`) plus the new data, and forwards the call down the full ownership chain (root → collection VO → entity → child collection → grandchild), up to four levels deep. Never expose a method that hands a caller a direct reference to an interior child; interior objects are reached only by id — or by a domain key like `code` — through the root's methods. The composition chain is drawn with `*--` edges and quoted cardinality.
- **Notation:**
  ```
  class Template {
    <<Aggregate Root>>
    +add_file_type(category_id: str, file_type_id: str, code: str, name: str, description: str) None
    +remove_file_type(category_id: str, file_type_id: str) None
  }
  Template *-- "1" Categories
  Categories *-- "0..n" Category
  Category *-- "1" FileTypes
  FileTypes *-- "0..n" FileType
  ```
- **Example:** `Template.add_file_type(category_id, file_type_id, code, name, description) None` forwards `Template` → `Categories` → `Category` → `FileTypes` — from `template.md`. The deepest corpus case is `Project.register_file(file_id, source_id, file_type, stage) None`, a 4-level VO/Entity/VO/Entity alternation `Project → SourceDMSes → SourceDMS → Files` — from `project.md`.
- **You may:** forward through an `<<Entity>>` composed directly under the root with no intervening collection VO (e.g. a root composing a `Lookup` entity at `*-- "0..n"` and forwarding `update_lookup(id, …)` to it by id); reach an interior child by a domain key (`code`, `file_type`) instead of an id; or, for a wholesale collection swap, model a `replace_<children>(...)` method that builds a fresh collection VO via its `new(...)` factory and swaps the whole VO instead of forwarding into the existing one. Flat aggregates with no interior depth correctly carry no forwarding methods at all.
- **Review:** treat root-only forwarding CRUD as canonical — do not flag a root method that takes a `category_id`/`*_id` and "merely passes it down" as boilerplate or as a leaky abstraction; the forwarding is deliberate aggregate-boundary enforcement (it is how the root stays the sole entry point for grandchild mutations). Do not propose hoisting interior children onto the root, exposing a direct `Category`/`SourceDMS` accessor, or collapsing the chain. The Collection Value Objects suppression in `model-diagrams:conventions` → `value-objects/` applies recursively at every level of this chain.

### Root is the single event source; children propagate events up
- **Rule:** Accumulate every domain event on the aggregate root — it is the single event-accumulation point the application layer publishes. Pick one of two shapes. (a) **Root-emits-directly:** draw all `--> <Event> : emits (<method>, …)` edges from the root, and give child entities/collection VOs no `emits` edge. (b) **Thread-the-aggregate:** let a child's mutating method emit, but thread the owning aggregate into that method's signature (e.g. `add_file(…, project)`, `remove(source_id, project)`, `add(child, conversion_reqs)`) so the event lands on the root's list; children hold no event list and no back-reference to the root.
- **Notation:**
  ```
  %% (a) root-emits-directly
  Ruleset --> RulesetFilesAdded : emits (add_files, add_file)
  Ruleset --> RulesInferenceCompleted : emits (add_mapping_rules, add_mappings)

  %% (b) thread-the-aggregate — child emits, aggregate threaded into the method
  SourceDMS --> SourceDMSFileAdded : emits (add_file)
  class SourceDMS {
    <<Entity>>
    +add_file(file_id: str, file_type: str, stage: str, project: Project) None
  }
  ```
- **Example:** root-emits-directly — `Ruleset --> RulesetFilesAdded : emits (add_files, add_file)` with the `Files`/`MappingRules`/`Mappings` VOs carrying no `emits` edge — from `ruleset.md`. Thread-the-aggregate — `SourceDMS.add_file(file_id, file_type, stage, project: Project) None` emitting `SourceDMSFileAdded`, the `project` parameter being the sole mechanism for forwarding the event up — from `project.md`.
- **You may:** put a single method on multiple `emits` edges or list multiple methods on one edge (`emits (add_files, add_file)`); thread the aggregate under any parameter name matching its type (`project`, `conversion`, `conversion_reqs`); accumulate a root-level summary event last, after the per-child events; and omit `<<Domain Event>>` classes and `emits` edges entirely for an aggregate that models no events.
- **Review:** treat both variants as canonical — do not flag a child mutating method that takes the aggregate as a parameter as an odd dependency or a back-reference smell; threading the aggregate is how events reach the root's single accumulation list. Do not flag a child `<<Entity>>`/collection VO for lacking its own `emits` edge or event list, and do not propose giving children a `DomainEventPublisher` or a root back-reference. Only the root publishes.

### Sanctioned collection-mutator return types beyond `None`
- **Rule:** Collection-VO and entity mutators are imperative verbs that return `None` by default. Two non-`None` return shapes are sanctioned where the root needs the result to drive boundary bookkeeping: a **creating mutator** returns the freshly-created (or fetched) child so the root can act on it next, and a **changed-signal mutator** returns `bool` (did-state-change) so the root can branch on whether to advance lifecycle (e.g. bump a concurrency token) or emit.
- **Notation:**
  ```
  class SourceDMSes {
    <<Value Object>>
    +add(source_id: str) SourceDMS
    +mark_ruleset_as_created(source_id: str) None
  }
  class Files {
    <<Value Object>>
    +add_file(file_id: str, file_type: str, stage: str) bool
    +remove_file(file_id: str) bool
  }
  ```
- **Example:** creating mutator — `SourceDMSes.add(source_id: str) SourceDMS`, consumed by the root as `target = source_dms_of_id(source_id) or add(source_id)` — from `project.md`. Changed-signal mutator — `Files.add_file(file_id, file_type, stage) bool` (and `add_files`/`remove_file`/`change_file_stage`), where the root branches on the returned `bool` to decide whether to advance `epoch_token` and emit — from `ruleset.md`.
- **You may:** mix these with `None`-returning mutators on the same VO (a creating `add` alongside a `None`-returning `mark_ruleset_as_created`; a `bool`-returning `Files.*` alongside `None`-returning `Mappings.add`). The creating-mutator and changed-signal variants need not co-occur in one aggregate.
- **Review:** treat a collection-VO mutator returning the created child or a `bool` as canonical — do not flag it as "mutators should return `None`", as an inconsistent return type, or as a command-query-separation violation. The return value is load-bearing for the root's forwarding, event accumulation, or idempotent at-least-once handling.

### Silent-create / observable-remove asymmetry on structural collection children
- **Rule:** When a collection child is created on demand purely as a structural container (not a user-visible state change), emit **no** event on its creation but **do** emit an event on its removal. State the asymmetry explicitly in the `## Invariants` prose so the absent create event reads as intentional, not as a missing step. An empty collection is then a valid aggregate state.
- **Notation:**
  ```
  %% creation via add(...) draws NO emits edge; only removal does
  SourceDMS --> SourceDMSRemoved : emits (remove)
  ```
  ```markdown
  ### <Aggregate>.<method>
  **Invariants / Constraints:**
  - **SourceDMS creation is silent; removal is observable.** Implicit creation via
    `SourceDMSes.add(source_id)` emits no event; removal of an emptied `SourceDMS`
    after a move emits `SourceDMSRemoved`. The asymmetry is intentional.
  ```
- **Example:** `SourceDMSes.add(source_id)` creates a `SourceDMS` with no event while `SourceDMS --> SourceDMSRemoved : emits (remove)` fires on cleanup, and "Empty `SourceDMSes` is a valid `Project` state" — from `project.md`.
- **You may:** instead choose the symmetric default — emit on both create and remove of the same child (e.g. a `LookupAdded` paired with a `LookupDeleted`). Both are sanctioned; the asymmetry is a per-aggregate choice for structural containers, not a corpus-wide rule.
- **Review:** when the create event is absent but the matching remove event is present and the prose pins the asymmetry, treat it as canonical — do not flag the missing create event as an omitted step or an inconsistent event model. Equally, do not flag a symmetric add/remove event pair as redundant.

## Pitfalls
- Exposing a method that returns or accepts a direct interior-child reference (a `Category`, a `SourceDMS`) instead of forwarding by id — this punches a hole in the boundary and lets callers bypass the root's invariant enforcement.
- Stopping a forwarding chain short: assuming a single root→grandchild hop when the real ownership chain is deeper (project forwards four levels). Walk the full `*--` composition path.
- Giving a child entity or collection VO its own event list, `emits` edge, `DomainEventPublisher`, or a back-reference to the root. Children either emit through a threaded aggregate parameter or not at all; the root is the sole event source.
- In the thread-the-aggregate shape, forgetting to thread the aggregate into the child's mutating signature — without that parameter the child has nowhere to accumulate the event.
- Forcing every collection mutator to return `None` when the root genuinely needs the created child or a changed-signal `bool`; conversely, returning a value the root never consumes (return `None` unless the root branches on or uses the result).
- Emitting a create event for a purely structural on-demand container, or omitting the create event without pinning the silent-create/observable-remove asymmetry in prose — either way the event model reads as inconsistent.
