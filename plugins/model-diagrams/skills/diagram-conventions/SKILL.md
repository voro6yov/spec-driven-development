---
name: diagram-conventions
description: Conventions used by hand-authored Mermaid class diagrams in this project (domain, commands, queries kinds). Auto-load when reviewing or critiquing a diagram to recognize convention-driven choices as valid and avoid false-positive findings.
when_to_use: Use when reviewing, critiquing, or otherwise judging the soundness of a Mermaid class diagram in this project. Consult before flagging any pattern as non-standard — if the pattern is documented here, it is canonical and must not be a finding.
user-invocable: false
---

# Diagram Conventions

## Purpose

This skill exists to **suppress false positives** during diagram review. The reviewer evaluates architectural soundness, not formatting; but a generic reviewer would mistakenly flag many of this project's deliberate conventions as "non-standard". Everything documented here is a deliberate convention. Reviewers must treat documented patterns as **correct by definition** and skip them.

This skill is the single source of truth for what a valid hand-authored diagram in this project looks like — across all three diagram kinds.

## How the reviewer should use this skill

For a given diagram:

1. Detect the diagram kind from the filename (`<stem>.md` → domain, `<stem>.commands.md` → commands, `<stem>.queries.md` → queries).
2. Read the conventions for that kind (sections below).
3. When assessing a passage, check it against the conventions first. If the pattern is documented as canonical here, **do not flag it**.

If a pattern in the diagram is not documented here but is also not an architectural concern, prefer omission over flagging. False positives erode trust faster than missing one minor concern.

---

## Domain diagrams (`<stem>.md`)

### Pass-through argument arrow

**Convention.** When a class accepts a parameter via a method but only forwards it to a delegate that does the actual work, the relationship is drawn as a lollipop arrow (`--()`) instead of a plain association arrow (`-->`). The class that actually inspects the parameter's fields uses `-->`. The arrow heads encode the consumer-vs-forwarder distinction.

**Notation.**

```
<Forwarder> --()  <Target> : takes as argument
<Consumer>  -->   <Target> : takes as argument
```

Worked example (from `mapping-type.md`):

- `MappingType --()  CacheTypeData : takes as argument` — `MappingType.add_resolved_field` receives `cache_type_data` and forwards it to `ResolvedFields.add(...)`; the aggregate root never reads its fields.
- `ResolvedFields --> CacheTypeData : takes as argument` — `ResolvedFields.add` inspects `.enabled`, `.code`, `.lookups`, etc., so it is the real consumer.

**Recognition rule (reviewer).** When you see `--() <Target> : takes as argument`:

1. Look for a paired `--> <Target> : takes as argument` elsewhere in the same diagram.
2. If the paired `-->` exists, this is a pass-through forwarder — **do not flag**. Treat it as canonical, regardless of source-class stereotype, target-class stereotype, or multiplicity annotations.
3. If no paired `-->` exists, the arrow is not covered by this convention — fall back to normal arrow-vocabulary review.

**Scope and constraints.**

- Applies to domain diagrams (`<stem>.md`) only. Not used on commands or queries diagrams.
- Applies to method **arguments** only. Return-type relationships are out of scope.
- The label must be exactly `takes as argument` on both arrows in the pair.
- One or more `--()` forwarders may appear (the same target may be forwarded through a chain of intermediaries); exactly one terminal `-->` consumer carries the matching label.
- Source and target class stereotypes are unconstrained — any class type may sit on either end.

**Disambiguation from `--()` for domain events.** Both conventions use the lollipop arrow head; the **label** disambiguates:

- Domain-event emission: arrow label is the event name (or empty / event-method prose).
- Pass-through argument: arrow label is the exact string `takes as argument`.

A `--()` with the label `takes as argument` is always pass-through, never event emission. A `--()` with any other label is not pass-through and is reviewed under the event-emission convention.

### Direct-raises-only exceptions

**Convention.** A method spec's `**Exceptions:**` section lists **only** the exceptions raised directly by the method's own code. Exceptions raised by delegated calls (factories, child VOs, collaborators invoked from the Flow) are **not** re-listed at the caller — they remain documented at the method that actually raises them.

The Flow may describe a delegated call in domain terms ("Calls `DerivedFields.has_fields(...)` to verify…") but must be silent on what the delegate raises. No `— propagates any exception raised by that factory` qualifier; no `— may raise X` qualifier; no `**May propagate:**` bullet under Exceptions.

**Rationale (drift hazard).** The list of exceptions a method raises is its own contract. When a caller duplicates that list, the duplicate is a copy with no enforcement: a future change to the delegate's exceptions silently desyncs every caller that mirrored them. Keeping the list at exactly one site — the method that raises it — is the only way to keep the spec coherent over edits.

**Notation.** Positive form (canonical):

```markdown
### Parent.method
**Flow:**
1. Calls `Child.foo(...)` to verify some condition
2. …

**Exceptions:**
- `DirectlyRaisedError` — raised when …
```

Negative form (non-conforming — must be removed):

```markdown
### Parent.method
**Flow:**
1. Calls `Child.foo(...)` — propagates any exception raised by that factory   ← strip the qualifier
2. …

**Exceptions:**
- `DirectlyRaisedError` — raised when …
- **May propagate:** `ChildErrorA`, `ChildErrorB` from `Child.foo`            ← delete this bullet
```

Worked example (from `mapping-type.md`):

- `MappingType.add_resolved_field` is **conforming**: it lists only `EmptyDerivedFieldIds` and `DerivedFieldNotFound` (its own direct raises), even though step 4 delegates to `ResolvedFields.add` which raises four more (`CacheTypeDisabled`, `ResolvedFieldAlreadyExists`, `CacheTypeLookupNotFound`, `LookupArityMismatch`). Those four belong to `ResolvedFields.add`'s spec and stay there.
- `MappingType.new` is **non-conforming**: its Exceptions section says `May propagate EmptySourceFields, DuplicateSourceFieldName, …`, and step 2 of its Flow says `— propagates any exception raised by that factory`. Both should be removed; the Exceptions section becomes empty (or is omitted entirely), and the Flow step describes only the call.

**Recognition rule (reviewer).**

1. When the Exceptions section omits exceptions raised by methods the Flow delegates to: **do not flag**. This is the canonical shape — the missing exceptions live at the delegate.
2. When the Exceptions section includes a `May propagate` bullet, or any enumeration of exceptions sourced from a delegated call, **flag as a violation of `Direct-raises-only exceptions`** and recommend deletion. This holds for pre-existing specs as well as new ones — the convention is forward-looking but legacy specs are expected to be migrated.
3. When a Flow step carries `— propagates …`, `— may raise …`, or any similar exception-behavior qualifier about a delegate, **flag** and recommend stripping the qualifier while keeping the rest of the step.

**Scope and constraints.**

- Applies to domain diagrams (`<stem>.md`) only.
- Applies to every method spec under `## Invariants` (factories, mutating methods, queries) — no exemption for any method kind.
- The rule governs the `**Exceptions:**` section and exception-related qualifiers in `**Flow:**`. It does not constrain `**Preconditions:**` prose, which may describe what causes a direct raise even when that direct raise originates inside a tightly-coupled internal check.

### Collection Value Objects compose Entities with mutating methods

**Convention.** A `<<Value Object>>` whose role is to manage an aggregate-owned collection of `<<Entity>>` (or another `<<Value Object>>`) is a **Collection Value Object**. It holds the collection in an internal `dict` / `list` keyed by natural identity, exposes mutating methods (`add_*`, `remove_*`, `increment`, `confirm_*`, `defer_*`, `associate`, etc.) that batch changes and forward domain events through the owning aggregate, and is the canonical way the project keeps aggregate roots thin. The pattern is implemented under `domain-spec:collection-value-objects` and is the project's deliberate alternative to either fattening the aggregate root with collection bookkeeping or modelling each child collection as its own aggregate.

The VO stereotype is preserved by `ImmutableCheck()` Guard descriptors on the attribute slots: the **container references** (`items`, `overages`, etc.) cannot be reassigned, while their **contents** are mutated through the VO's dedicated methods. Generic DDD intuition flags this as "VOs must be immutable, so a VO with mutating methods or entity children contradicts the stereotype" — in this project that intuition is wrong, and the reviewer must suppress it.

**Recognition cues.** A class is a Collection Value Object when **all** of the following hold:

1. Stereotype is `<<Value Object>>`.
2. It composes (`*--` or `o--`) one or more `<<Entity>>` or `<<Value Object>>` children, typically at `1 --> "0..*"` multiplicity.
3. It is itself composed by an `<<Aggregate Root>>` (single-aggregate ownership).
4. It exposes one or more mutating methods (return type `None`, names like `add_*`, `remove_*`, `increment`, `confirm_*`, `associate`, etc.) that operate on the collection.

When these cues line up, the VO is canonical and **must not be flagged** for any of:

- "Value Object declared as `<<Value Object>>` but contains mutable Entities" — composing Entities is the pattern.
- "Value Object exposes mutating methods, contradicting the stereotype" — mutation through dedicated methods is the pattern (the Guard's `ImmutableCheck()` enforces container-reference immutability, not deep immutability).
- "Equality / hashing will break because the VO holds identity-bearing entities" — Collection VOs are not used as dict keys; they are aggregate-internal orchestrators.
- "Child Entities should live directly on the aggregate root" — pulling them out of the Collection VO defeats the pattern's purpose.

The same suppression applies recursively: a child Entity inside a Collection VO may itself expose mutating methods that own its own grandchildren (e.g. `SourceDMS.add_file(...)` where `SourceDMS` is the entity owned by the `SourceDMSes` Collection VO). The mutation-through-dedicated-method shape is canonical at every level of the aggregate-owned hierarchy, not just at the top.

**Recognition rule (reviewer).**

1. Before flagging a `<<Value Object>>` for "containing mutable Entities", "exposing mutating methods", or "breaking VO immutability/equality semantics", check whether the four recognition cues above hold. If they do, **do not flag** — this is the Collection Value Objects pattern.
2. Do not propose "convert to `<<Entity>>`", "promote to `<<Aggregate Root>>`", or "hoist children onto the aggregate root" as remediation for a class that matches the pattern. Those changes would break the project's chosen aggregate decomposition.
3. The reviewer is free to raise substantive concerns about a Collection VO that are **independent** of the stereotype-vs-mutation question (e.g., a missing invariant, an inconsistent batch policy, an event emitted without the aggregate parameter). This suppression covers the stereotype objection only.

**Scope and constraints.**

- Applies to domain diagrams (`<stem>.md`) only.
- Applies regardless of the child stereotype: `<<Entity>>`, `<<Value Object>>`, or `<<Domain TypedDict>>` may all sit inside a Collection VO.
- Does not apply to a `<<Value Object>>` that holds only primitive / immutable VO attributes (e.g. `Money { amount, currency }`). Those remain plain Value Objects and are reviewed under generic VO rules.

### Aggregate-level cross-cutting invariants

**Convention.** An aggregate root may declare invariants that apply uniformly across all of its state-mutating methods — `updated_at` is bumped on every mutation, domain events are accumulated by the root, a version counter is incremented, an audit field is touched, and so on. These cross-cutting rules are stated **once**, as free-form prose bullets under the aggregate root's class-level `### <Aggregate>` block in the `## Invariants` section. They are **not** re-stated in each method's `**Flow:**`, `**Postconditions:**`, or `**Exceptions:**`, and they are **not** cross-referenced from child Value Object / Entity methods that participate in the mutation path.

The single-declaration site is the contract. Per-method Flow and Postcondition entries describe only the method's own work; the aggregate-level rule is layered on top by the reader.

**Rationale (drift hazard).** Same hazard as `Direct-raises-only exceptions`: if every state-mutating method re-states the cross-cutting rule, those copies have no enforcement, and a future change to the rule silently desyncs every method that mirrored it. Keeping the rule at exactly one site — the aggregate's own `### <Aggregate>` invariants block — is the only way to keep the spec coherent across edits.

The same logic applies at the VO / Entity boundary: a child method does not know its caller is an aggregate mutation path. Forcing it to cross-reference "the aggregate root will bump `updated_at`" couples the child to one specific caller and rots the moment another path emerges.

**Notation.** Canonical form — declared once on the aggregate root:

```markdown
### <Aggregate>
- `updated_at` is bumped on every state-mutating method.
- Domain events emitted by collaborators are accumulated on `self.events`.
- …

### <Aggregate>.some_mutating_method
**Flow:**
1. Validates …
2. Delegates to `<Collection>.add(...)`

**Postconditions:**
- The new item is present in the collection.
```

Note: the method spec is silent about `updated_at`, about event accumulation, and about any other rule already declared at the class level. That silence is the convention.

**Worked examples (from `mapping-type.md`):**

- `### MappingType` declares the cross-cutting rule: *"`updated_at` is bumped on every state-mutating method."*
- `MappingType.add_resolved_field`'s `**Flow:**` does **not** include a "Bumps `updated_at`" step. **This is canonical — do not flag.** The aggregate-level declaration covers it. (The author may also choose to mention `updated_at` in `**Postconditions:**`; both presence and absence are conforming.)
- `ResolvedFields.add` is a Value Object method invoked from `MappingType.add_resolved_field`. Its `**Postconditions:**` are silent about aggregate-level `updated_at` bookkeeping — no "the calling aggregate is responsible for bumping `updated_at`" cross-reference. **This is canonical — do not flag.** Child VO / Entity methods carry no responsibility to point upward at the aggregate's contract.

**Recognition rule (reviewer).**

1. Before flagging any per-method spec for an "omitted bookkeeping step" (timestamp bump, event accumulation, version increment, audit-field update, etc.), scan the aggregate root's `### <Aggregate>` invariants block. If the rule is declared there as a class-level invariant, **do not flag** the per-method omission — the single declaration covers every state-mutating method by construction.
2. Before flagging a VO or child-Entity method for "silently relying on the caller to do bookkeeping" or for failing to cross-reference an aggregate-level rule, check the same `### <Aggregate>` block. If the rule is declared there, **do not flag** — silent VO-to-aggregate boundaries are canonical.
3. Per-method restatement of an aggregate-level rule (e.g., a method that does mention `updated_at` in its `**Postconditions:**`) is permitted but not required. **Do not flag** restatement either; it is a style choice, not a violation.
4. A state-mutating method whose Flow does not realize the cross-cutting rule (e.g., a method that does not in fact bump `updated_at`) is not required to call out the deviation in prose. **Do not flag** silent deviations under this convention. (A reviewer may still raise a separate, substantive logic concern; this rule only governs the documentation-style axis.)

**Scope and constraints.**

- Applies to domain diagrams (`<stem>.md`) only.
- Applies only to invariants the aggregate root declares as **universal** across its state-mutating methods. A localized rule that holds for one specific method (e.g., "only `update_details` clears the cache") is not covered by this suppression — it is a normal per-method invariant and must be documented at the method.
- The single declaration site is the aggregate root's class-level `### <Aggregate>` block under `## Invariants`. A cross-cutting rule stated in scattered prose elsewhere (e.g., in the Description preamble, or only inside one method) does **not** receive this suppression — the reviewer is free to evaluate per-method completeness as usual.
- The cross-cutting invariant is free-form prose. Universal-quantifier language ("every", "all", "on each") is the clearest signal, but any bullet under the aggregate's invariants block that reads as a global rule qualifies.

---

## Maintenance notes

- This skill is the single suppression source for the diagram reviewer. When the user identifies a new false positive, update this skill — not the agent.
- Keep examples concrete. Where a convention has a non-obvious shape, include a minimal Mermaid snippet.
- When a convention is project-specific (not in general DDD literature), say so — the reviewer's prior is general DDD, so highlighting the deviation is what stops the false positive.
