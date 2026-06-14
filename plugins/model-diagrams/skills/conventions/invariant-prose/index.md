---
name: invariant-prose
description: How to author and review the trailing ## Invariants prose on domain/commands/ops diagrams — keyed sections, validation formulas, direct-raises-only, cross-cutting rules.
user-invocable: false
---

# Invariant prose

**Applies to:** domain, commands, ops diagrams (trailing ## Invariants)

The contract a diagram cannot express in Mermaid lives in a trailing `## Invariants` prose section: per-class and per-method preconditions, flow, postconditions, constraints, and exceptions. This theme governs the shape of that section — its headings, its fixed validation/flow formulas, and the single-declaration rules that keep it from drifting. The queries diagram carries no such prose (bare mermaid fence only); domain, commands, and ops diagrams carry it.

## Conventions

### Keyed `## Invariants` section with fixed bold sub-headings
- **Rule:** Follow the mermaid block with exactly one `## Invariants` section. Key class-level invariants under `### <Class>` and per-method invariants under `### <Class>.<method>`. Inside each method block use these bold sub-headings, in this order, including only the ones that apply: **Preconditions:**, **Flow:** (numbered), **Postconditions:**, **Invariants / Constraints:**, **Exceptions:**. You may share one block across methods with a slash-grouped heading (`### DomainType.enable / DomainType.disable`).
- **Notation:**
  ```markdown
  ## Invariants

  ### MappingType
  **Invariants / Constraints:**
  - `id` is assigned at construction and is immutable for the lifetime of the aggregate
  - `updated_at` ... must be bumped (advanced to "now") on every state-mutating method

  ### MappingType.new
  **Preconditions:**
  - ...
  **Flow:**
  1. Validate `name` ...
  2. ...
  **Postconditions:**
  - ...
  **Exceptions:**
  - `InvalidMappingTypeName` — raised when `name` is empty after trimming ...
  ```
- **Example:** `### MappingType` (class-level block) followed by `### MappingType.new`, `### MappingType.rename` — from `mapping-type.md`.
- **You may:** nest `#### <method>` (or `#### <Class>.<method>`) under a `### <Class>` parent instead of flat `### <Class>.<method>` headings; group shared methods under one slash-joined heading; embed a `**Event matrix (per scenario):**` table sub-heading or a `#### Design Note:` essay alongside the standard sub-headings for event-heavy or inference-pipeline aggregates; omit any sub-heading that does not apply (e.g. a method with no preconditions carries no **Preconditions:**).
- **Review:** treat the keyed section with fixed bold sub-headings as canonical — do not flag `####`-nesting, slash-grouped headings, Event-matrix tables, or Design-Note essays as non-standard structure. A purely structural-only domain diagram that ends at the closing mermaid fence with **no** `## Invariants` section is an allowed variation when the diagram alone (Literal types, cardinalities, `| None` optionals) carries the contract — do not flag the missing prose.

### Uniform string-validation formula tied to a per-field `Invalid<Type><Field>` exception
- **Rule:** State string-attribute validation with the uniform formula and tie each rule to a named `Invalid<Type><Field>` exception raised at construction, citing the factory site in parentheses. Use exactly these two formulas: for **codes/ids** — "non-empty, not all whitespace, no leading/trailing whitespace"; for **names/descriptions** — "non-empty, not all whitespace" (no trim constraint). Where name comparison is involved, document normalization as trim + case-fold, the stored value left unmodified, and the DB index as a functional index over the same expression.
- **Notation:**
  ```markdown
  ### Lookup
  **Invariants / Constraints:**
  - `code` must be a non-empty string, must not consist entirely of whitespace, and must have no leading or trailing whitespace. Violations raise `InvalidLookupCode` at construction time (`Lookup.new`).
  - `name` must be a non-empty string and must not consist entirely of whitespace. Violations raise `InvalidLookupName` at construction time (`Lookup.new`) and whenever a new name is supplied via `Lookup.update(...)`.
  ```
- **Example:** `Lookup.code` → `InvalidLookupCode` (`Lookup.new`) and `Lookup.name` → `InvalidLookupName` — from `cache-type.md`.
- **You may:** apply the name's trim+case-fold normalization to only the name key while treating the code key as exact-match; omit the description-field validation for leaf reference VOs that take only `(id, code, name)`; add a max-length clause per field (e.g. "at most 240 characters") raising the same `Invalid<Type><Field>`.
- **Review:** treat the formula and the `Invalid<Type><Field>` exception naming as canonical — the downstream guard/exception generators parse this prose to derive `Check` classes and exception codes. Do not flag a code field for the stricter trim rule or a name field for the looser one; the asymmetry is intentional.

### Uniqueness enforced at the persistence layer; in-aggregate checks are pre-flight only
- **Rule:** Document uniqueness as enforced at the persistence layer (a DB unique/functional index). Flag the in-aggregate `has_*` / `_id_with_` checks and the application-service existence checks explicitly as **non-race-safe pre-flight** checks: state that read-then-write across these checks and `save()` is racy without the unique index, and that the aggregate relies on — but does not itself perform — cross-aggregate uniqueness/resolvability checks.
- **Notation:**
  ```markdown
  ### MappingType.new
  **Preconditions:**
  - No other `MappingType` may share the same `name` or `code` — this uniqueness constraint is enforced by the application service layer via a repository existence check before invoking `MappingType.new`; the aggregate relies on this guarantee but does not perform the check itself
  ```
- **Example:** `MappingType.new`'s uniqueness precondition deferred to the service-layer existence check — from `mapping-type.md`.
- **You may:** push a cross-aggregate resolvability check entirely to the application layer (a command service calling a foreign aggregate's `ensure_*` assertion); pair a narrow existence check (`has_<x>_with(name, code)`, OR-semantics) with a broad one (`has_<x>_with_name(name)`) used on different paths.
- **Review:** treat the persistence-layer-uniqueness framing as canonical — do not flag the in-aggregate `has_*` check as "racy / insufficient" or demand the aggregate enforce uniqueness itself; the prose already names it as pre-flight backed by a DB index.

### Cross-cutting rules declared once at the class level
- **Rule:** State universal cross-cutting rules — `updated_at` bumped on every successful state-mutating method, `created_at` set once and immutable, domain events accumulated on the root, child-to-aggregate delegation/forwarding protocols, lifecycle/concurrency gates — exactly **once** under the aggregate's class-level `### <Aggregate>` block. Do not restate them in each method's **Flow:**, **Postconditions:**, or **Exceptions:**, and do not have a child VO/Entity method cross-reference the aggregate-level rule. A delegating method may say "See `### <other>`" rather than duplicating the other method's flow.
- **Notation:**
  ```markdown
  ### MappingType
  **Invariants / Constraints:**
  - `updated_at` ... must be bumped (advanced to "now") on every state-mutating method

  ### MappingType.add_resolved_field
  **Flow:**
  1. Validates ...
  2. Delegates to `ResolvedFields.add(...)`
  **Postconditions:**
  - The new resolved field is present in the collection
  ```
  (the method block is silent about `updated_at` — that silence is the convention.)
- **Example:** `### MappingType` declares *"`updated_at` ... must be bumped ... on every state-mutating method"*; `MappingType.add_resolved_field` does not re-state it — from `mapping-type.md`.
- **You may:** restate an aggregate-level rule per method as a style choice (e.g. mapping-type also writes "Bumps `updated_at` to now" in each Flow) — restatement is permitted but not required; declare lifecycle/concurrency rules (`epoch_token` gate, Ready-gate, Status-derived resets) once under the relevant `### <Aggregate>` / `### Status` / `### <Collection>` block with per-method back-references.
- **Review:** **Aggregate-level cross-cutting invariants — suppress.** Before flagging any per-method spec for an "omitted bookkeeping step" (timestamp bump, event accumulation, version/`epoch_token` increment, audit-field touch), scan the aggregate root's `### <Aggregate>` block; if the rule is declared there as a class-level (universal) invariant, **do not flag** the per-method omission — the single declaration covers every state-mutating method by construction. Likewise, before flagging a child VO/Entity method for "silently relying on the caller to bump `updated_at`" or for not cross-referencing an aggregate-level rule, check the same block; silent VO-to-aggregate boundaries are canonical — **do not flag**. Per-method *restatement* of an aggregate-level rule is permitted, not a violation — do not flag it either. A method whose Flow does not in fact realize the cross-cutting rule need not call out the deviation in prose — do not flag silent deviations under this convention. Drift-hazard rationale: re-stating a universal rule at every method creates unenforced copies that silently desync when the rule changes; the single `### <Aggregate>` declaration is the contract. Scope: this suppression covers only invariants declared **universal** across the root's state-mutating methods, declared in the aggregate root's class-level `### <Aggregate>` block. A *localized* rule that holds for one specific method ("only `update_details` clears the cache") is a normal per-method invariant and must be documented at the method — it is **not** covered. A cross-cutting rule scattered in the Description preamble or buried inside one method does **not** receive this suppression. Do **not** propose remediation that pushes a universal rule down into each method.

### A method's **Exceptions:** lists only its own direct raises
- **Rule:** In each method's **Exceptions:** section list only the exceptions that method raises **directly**. Do not re-list exceptions raised by delegated calls (factories, child VOs, collaborators), do not add a "May propagate" bullet under **Exceptions:**, and do not add "— propagates …" / "— may raise …" qualifiers to **Flow:** steps. Those exceptions are documented only at the delegate that raises them. The **Flow:** may name a delegated call in domain terms ("Delegates to `ResolvedFields.add(...)`") but must be silent on what that delegate raises.
- **Notation:**
  ```markdown
  ### MappingType.add_resolved_field
  **Flow:**
  1. Checks that `derived_fields_ids` is non-empty; if empty, raises `EmptyDerivedFieldIds`
  2. ...
  4. Delegates to `ResolvedFields.add(...)`            ← silent on ResolvedFields.add's raises
  **Exceptions:**
  - `EmptyDerivedFieldIds` — raised when ...
  - `DerivedFieldNotFound` — raised when ...
  ```
  Negative form (non-conforming — strip the qualifier / delete the bullet):
  ```markdown
  **Flow:**
  1. Calls `Child.foo(...)` — propagates any exception raised by that factory   ← strip
  **Exceptions:**
  - **May propagate:** `ChildErrorA`, `ChildErrorB` from `Child.foo`            ← delete
  ```
- **Example:** `MappingType.add_resolved_field` lists only `EmptyDerivedFieldIds` and `DerivedFieldNotFound` (its own direct raises) even though it delegates to `ResolvedFields.add` which raises four more — from `mapping-type.md`.
- **You may:** fold exceptions into Flow/Invariants prose or `--() <Error> : raises` edges and carry **no** **Exceptions:** sub-heading at all (most aggregates do this) — the direct-raises-only rule then applies trivially; describe in **Preconditions:** what causes a direct raise even when the direct raise originates inside a tightly-coupled internal check.
- **Review:** **Direct-raises-only exceptions — suppress.** When an **Exceptions:** section omits exceptions raised by methods the **Flow:** delegates to, **do not flag** — that is the canonical shape; the missing exceptions live at the delegate. When an **Exceptions:** section includes a "May propagate" bullet, or any enumeration of exceptions sourced from a delegated call, **flag it as a violation of Direct-raises-only exceptions** and recommend deletion (this holds for legacy specs too — they are expected to be migrated). When a **Flow:** step carries "— propagates …", "— may raise …", or any similar exception-behavior qualifier about a delegate, **flag** and recommend stripping the qualifier while keeping the rest of the step. Drift-hazard rationale: the list of exceptions a method raises is its own contract; a caller that duplicates that list holds an unenforced copy that silently desyncs when the delegate's exceptions change — keeping the list at exactly one site (the raiser) is the only way the spec stays coherent. Scope: applies to every method kind under `## Invariants` (factories, mutators, queries) with no exemption; governs the **Exceptions:** section and exception qualifiers in **Flow:** only — it does not constrain **Preconditions:** prose.

### Standard application command flow: lookup-or-raise → call → persist → publish
- **Rule:** Specify each application command method's **Flow** with the fixed skeleton: (1) look up the aggregate by id and raise `<Aggregate>NotFound` if missing, (2) call the aggregate's domain method, (3) persist via the command repository's `save()`, (4) publish accumulated domain events via the injected `DomainEventPublisher`. The creation method (named `create`, taking no id) omits step 1. Cross-aggregate commands extend the skeleton with extra existence/resolvability lookups (up to ~6 steps).
- **Notation:**
  ```markdown
  ## Invariants

  ### RulesetCommands

  #### RulesetCommands.on_file_removed_from_process
  **Flow:**
  1. Obtain the ruleset by process_id from the repository; if not found, raise `RulesetNotFoundbyProcess`.
  2. Remove the file (file_id) from the ruleset.
  3. Save the ruleset via the repository.
  4. Publish the accumulated domain events via the event publisher.
  ```
- **Example:** `RulesetCommands.on_file_removed_from_process` (the 4-step skeleton) — from `ruleset.commands.md`.
- **You may:** extend to a 6-step cross-aggregate variant with extra existence / resolvability lookups; write an inbound-event handler keyed by a composite business key instead of an id; write a create-on-demand **upsert** handler that creates the aggregate when the lookup returns `None` and therefore never raises NotFound (e.g. `on_ruleset_creation_triggered` / `on_file_added_to_process`); write a missing-target branch that returns without error as an idempotent no-op (`Ruleset | None` return) instead of raising — used by write-backs a message handler would otherwise retry forever.
- **Review:** treat the four-step skeleton — and its create-omits-lookup, composite-key, upsert-no-NotFound, and idempotent-no-op variants — as canonical. Do not flag a `create` method for "missing the NotFound lookup", an upsert handler for "not raising NotFound on a missing target", or an `<Aggregate> | None` command return as "inconsistent optionality / should raise NotFound" when the Flow describes the `None` arm as a deliberate no-op. Commands-file prose lives on the `<stem>.commands.md` sibling (and ops Flow prose on each `<stem>.ops.<service>.md`); the `<stem>.queries.md` sibling carries no `## Invariants` prose — do not flag its absence.

### Optionality resolved at the service layer (repo returns `T | None`; service returns non-optional `T`)
- **Rule:** Have repository finders return `<Aggregate> | None` / `<X>Info | None`, but declare the corresponding application-service finder as **non-optional** `<Aggregate>` / `<X>Info`, raising `<Aggregate>NotFound` when the repo returns `None`. The `None`-handling lives at the service boundary — not in the repository signature and not at every caller. Carry this onto the **query side** too: the queries diagram draws `--() <Aggregate>NotFound : raises` even though its methods return non-optional `Info`.
- **Notation:**
  ```
  RulesetQueries --() RulesetNotFound : raises
  RulesetQueries --() RulesetNotFoundbyProcess : raises
  ```
- **Example:** `RulesetQueries --() RulesetNotFound : raises` on the queries diagram (methods return non-optional `Info`) — from `ruleset.queries.md`.
- **You may:** declare two distinct NotFound exceptions for two lookup keys — an id lookup raising `<Aggregate>NotFound` and a composite-key/secondary-id lookup raising `<Aggregate>NotFoundBy<Key>` — and enumerate **both** on the commands and queries diagrams (e.g. `RulesetNotFound` / `RulesetNotFoundbyProcess`).
- **Review:** treat the repo-`| None` / service-non-optional asymmetry as canonical — do not flag the service finder for "dropping the `| None`" nor the query-side `--() <Aggregate>NotFound : raises` edge as spurious (the methods return non-optional `Info`; the edge documents the not-found raise at the service boundary). Do not flag a second `<Aggregate>NotFoundBy<Key>` exception as a duplicate.

## Pitfalls
- Do not duplicate a universal cross-cutting rule (timestamp bump, event accumulation, `epoch_token` increment) into every method's Flow as a substitute for declaring it once under `### <Aggregate>` — the single class-level declaration is the contract.
- Do not list a delegate's exceptions at the caller, add a "May propagate" bullet, or qualify a Flow step with "— propagates …" — those exceptions belong only at the method that raises them directly.
- Do not put `## Invariants` prose on the `<stem>.queries.md` sibling — the query side is a bare mermaid block; service-layer not-found behavior is expressed only via its `--() <Aggregate>NotFound : raises` edge.
- Do not mix the two string-validation formulas — code/id fields get the trim constraint, name/description fields do not — and always tie each to a named `Invalid<Type><Field>` exception citing the construction site; an un-named or formula-free validation rule starves the guard/exception generators.
- Do not have the aggregate enforce cross-aggregate or persistence-layer uniqueness itself — document it as a service-layer pre-flight existence check backed by a DB unique/functional index, and label the in-aggregate `has_*` check as non-race-safe.
- Do not give the `create` command a NotFound lookup step, and do not force an inbound-event upsert handler to raise NotFound on a missing target — both are sanctioned carve-outs from the lookup-or-raise skeleton.
