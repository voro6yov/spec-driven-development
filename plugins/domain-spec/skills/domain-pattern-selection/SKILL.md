---
name: domain-pattern-selection
description: Pattern selection guide for DDD domain models. Use when analyzing a Mermaid class diagram to determine which patterns to apply to each class, or when the user asks which patterns a class needs.
user-invocable: false
disable-model-invocation: false
---

# Domain Pattern Selection Guide

Select which patterns to apply to each class in a domain model Mermaid diagram.

**Workflow:** Select (this guide) -> Implement (pattern skills) -> Verify (pattern checklists)

**Key principle:** Assign patterns to what the class IS, not what it USES. Order uses OrderItems, but Order doesn't need the Collection pattern -- OrderItems does.

---

## Selection Process

For each class in the diagram:

1. **Check stereotype** -> Gets primary pattern
2. **Check attributes & types** -> Adds supporting patterns
3. **Check methods** -> Confirms/refines pattern choice
4. **Check relationships** -> Adds dependency patterns

---

## 1. Primary Pattern (By Stereotype)

| Stereotype | Primary Pattern | Skill |
|---|---|---|
| `<<Aggregate Root>>` | Aggregate Root | `domain-spec:aggregate-root` |
| `<<Entity>>` | Entity | `domain-spec:entity` |
| `<<Value Object>>` | Value Object | `domain-spec:value-object` |
| `<<Event>>` | Domain Event | `domain-spec:domain-events` |
| `<<Command>>` | Commands | `domain-spec:commands` |
| `<<Repository>>` | Repository | `domain-spec:repositories` |
| `<<Service>>` | Domain Service | `domain-spec:domain-services` |
| `<<TypedDict>>` | Domain TypedDict | `domain-spec:domain-typed-dicts` |
| `<<Query DTO>>` | Query DTO | `domain-spec:query-dtos` |

**Entity vs Value Object:**
- **Entity:** Has identity (id field), mutable, part of aggregate. Example: File with id, owned by Profile
- **Value Object:** No identity, immutable, descriptive. Example: FileStatus describing File's state

---

## 2. Supporting Patterns (By Attributes)

> **Critical:** When selecting `domain-spec:guards-and-checks`, **always also select** `domain-spec:constructor-guard-type-mapping`. These two are inseparable.

### For THIS class -- add supporting patterns:

| Attribute Pattern | Add Pattern | Skill |
|---|---|---|
| Is Aggregate Root, Entity, or Value Object | Guards & Checks (always) | `domain-spec:guards-and-checks` + `domain-spec:constructor-guard-type-mapping` |
| Has optional attributes (`name: str \| None`) | Optional Values | `domain-spec:optional-values` |
| Has multiple optional complex attributes | Optional Values (essential) | `domain-spec:optional-values` |
| Has union type attributes (`entity: Individual \| LegalEntity`) | Optional Values (XOR logic) | `domain-spec:optional-values` |
| Has complex value objects with multiple fields | Flat Constructor Arguments | `domain-spec:flat-constructor-arguments` |
| Has `events: list[Event]` | Domain Events | `domain-spec:domain-events` |
| Has `commands: list[Command]` | Commands | `domain-spec:commands` |
| Has `created_at` + `updated_at` | Confirms Aggregate Root | `domain-spec:aggregate-root` |

### For REFERENCED classes -- they need their own patterns:

| Your Attribute | Referenced Class Needs |
|---|---|
| `-details: ClientDetails` | ClientDetails -> `domain-spec:value-object` |
| `-items: OrderItems` | OrderItems -> `domain-spec:value-object` + `domain-spec:collection-value-objects` |
| `-status: OrderStatus` | OrderStatus -> `domain-spec:value-object` + `domain-spec:statuses` + `domain-spec:optional-values` |
| `-data: SomeTypedDict` | SomeTypedDict -> `domain-spec:domain-typed-dicts` |
| `-result: ProcessingResult \| None` | ProcessingResult -> `domain-spec:domain-typed-dicts` |

**TypedDict vs Value Object:**
- **TypedDict** for external data structures, API payloads, data crossing boundaries
- **Value Object** for domain concepts with business meaning and invariants

---

## 3. Pattern Refinement (By Methods)

### Factory Methods -> Confirms Aggregate/Entity/ValueObject

```
+new(...) Class$              -> Aggregate Root or Entity
+from_data(...) Class$        -> Aggregate Root, Entity, or Value Object (with DTO)
+from_status(...) Class$      -> Statuses pattern
```

### State Mutations -> Confirms Mutable Patterns

```
+update_status(...) None      -> Aggregate Root or Entity
+add_item(...) None           -> Aggregate Root with Collection
+remove_item(...) None        -> Aggregate Root with Collection
+mark_as_completed(...) None  -> Aggregate Root or Entity
```

### Immutable Mutations -> Confirms Value Object

```
+corrected(corrections) Self  -> Value Object (returns NEW instance)
+updated(data) Self           -> Value Object (returns NEW instance)
+with_value(value) Self       -> Value Object (returns NEW instance)
```

### Delegation -> Add `domain-spec:delegation-and-event-propagation`

```
+method(..., aggregate: Aggregate) None     -> Delegation pattern
+update(profile: Profile) Status            -> Delegation pattern (returns new status, emits events)
+add_corrections(corrections, document: Document) Subject -> Delegation pattern
```

### Repository Methods -> Confirms `domain-spec:repositories`

```
+save(aggregate: T) None               -> Command Repository
+{entity}_of_id(id, tenant_id) T       -> Command Repository
+find_one(id, tenant_id) DTO           -> Query Repository
+find_many(pagination) DTOList          -> Query Repository
```

---

## 4. Dependency Patterns (By Relationships)

**Key Principle:** Relationships tell you which OTHER classes need patterns, not the current class.

| Diagram Relationship | Pattern Assignment |
|---|---|
| `Aggregate *-- ValueObject` | **ValueObject** needs `domain-spec:value-object` |
| `Aggregate *-- Entity` | **Entity** needs `domain-spec:entity` (not Value Object!) |
| `Aggregate *-- Collection` | **Collection** needs `domain-spec:value-object` + `domain-spec:collection-value-objects` |
| `Aggregate --> Event : emits` | **Event** needs `domain-spec:domain-events` |
| `ValueObject --> Event : emits` | **ValueObject** needs `domain-spec:delegation-and-event-propagation`, **Event** needs `domain-spec:domain-events` |
| `Repository --() Aggregate` | **Repository** needs `domain-spec:repositories` |
| `Aggregate --> Service : uses` | **Service** needs `domain-spec:domain-services` |

**Important distinctions:**
- Entity vs Value Object: If the child has an `id` and identity, it's an Entity. If it's an immutable descriptor, it's a Value Object.
- `list[Entity]` vs Collection Value Object: Owning `list[File]` where File is Entity != Collection Value Object. Collection Value Object is for value objects like OrderItems.
- If Order owns OrderItems: Order doesn't get Collection pattern -- OrderItems does!
- If Profile owns File entities: Profile doesn't get Entity pattern -- File does!

---

## Decision Checklist

For each class in the diagram:

### 1. What's the stereotype?
-> Gets primary pattern from the table above.

### 2. What attributes does it have?

**For THIS class (supporting patterns):**
- [ ] Is Aggregate Root, Entity, or Value Object? -> `domain-spec:guards-and-checks` + `domain-spec:constructor-guard-type-mapping` (always)
- [ ] Has optional attributes (`name: str | None`)? -> `domain-spec:optional-values`
- [ ] Has multiple optional complex attributes? -> `domain-spec:optional-values` (essential)
- [ ] Has union type attributes (`entity: Individual | LegalEntity`)? -> `domain-spec:optional-values` (XOR logic)
- [ ] Has complex value objects (multiple fields)? -> `domain-spec:flat-constructor-arguments`
- [ ] Has `events` or `commands` list? -> `domain-spec:domain-events` or `domain-spec:commands`
- [ ] Has `created_at` + `updated_at`? -> Confirms `domain-spec:aggregate-root`

**For referenced classes (they need their own patterns):**
- [ ] Has value object attribute? -> Referenced class needs `domain-spec:value-object`
- [ ] Has collection attribute (`items: OrderItems`)? -> Referenced class needs `domain-spec:value-object` + `domain-spec:collection-value-objects`
- [ ] Has simple list of value objects (`boi: list[BeneficialOwner]`)? -> Referenced class needs `domain-spec:value-object` (NOT Collection pattern)
- [ ] Has status attribute? -> Status class needs `domain-spec:value-object` + `domain-spec:statuses` + `domain-spec:optional-values`
- [ ] Has TypedDict attribute? -> Referenced class needs `domain-spec:domain-typed-dicts`

### 3. What methods does it have?
- [ ] Factory method (`new()`, `from_data()`)? -> Confirms Aggregate/Entity/Value Object
- [ ] Mutation methods returning None? -> Confirms mutable pattern (Aggregate/Entity)
- [ ] Mutation methods returning Self (`corrected()`, `updated()`)? -> Confirms Value Object (immutable)
- [ ] Accepts `aggregate` parameter? -> `domain-spec:delegation-and-event-propagation`
- [ ] Repository methods? -> Confirms `domain-spec:repositories`

### 4. What relationships does it have?
- [ ] Owns other objects (`*--`)? -> Those objects need their own patterns
- [ ] Emits events (`-->`)? -> Event classes need `domain-spec:domain-events`
- [ ] Used by repository? -> Repository class needs `domain-spec:repositories`

### 5. If Guards & Checks was selected:
**MANDATORY**: Always add `domain-spec:constructor-guard-type-mapping`. These two patterns are inseparable.

---

## Quick Reference: Common Combinations

> **"Guards & Checks" always implies** `domain-spec:constructor-guard-type-mapping` -- they are inseparable.

This table shows patterns for a SINGLE class. Referenced classes need their own separate pattern lists.

| Class Type | Pattern Combination |
|---|---|
| Simple Aggregate | Aggregate Root + Guards & Checks |
| Aggregate with Value Objects | Aggregate Root + Flat Constructor Arguments + Guards & Checks |
| Aggregate with Optional Attributes | Aggregate Root + Optional Values + Guards & Checks |
| Aggregate with Child Entities | Aggregate Root + Flat Constructor Arguments + Guards & Checks |
| Aggregate with Collection | Aggregate Root + Guards & Checks |
| Aggregate with Events | Aggregate Root + Guards & Checks |
| Full Aggregate (Status + Optionals + Events) | Aggregate Root + Flat Constructor Arguments + Optional Values + Guards & Checks |
| Simple Entity | Entity + Guards & Checks |
| Entity with Status | Entity + Flat Constructor Arguments + Optional Values + Guards & Checks |
| Simple Value Object | Value Objects + Guards & Checks |
| Value Object with Union Types | Value Objects + Optional Values + Guards & Checks |
| Nested Value Object (with optionals) | Value Objects + Optional Values + Guards & Checks |
| Value Object with Event Delegation | Value Objects + Delegation & Events + Optional Values + Guards & Checks |
| Status Value Object | Value Objects + Statuses + Optional Values + Guards & Checks |
| Status Value Object with Event Delegation | Value Objects + Statuses + Delegation & Events + Guards & Checks |
| Collection Value Object | Value Objects + Collection Value Objects + Delegation & Events + Guards & Checks |
| Event | Domain Events |
| Command | Commands |
| Command Repository | Repositories (Command) |
| Query Repository | Repositories (Query) |
| Domain Service | Domain Services |
| TypedDict | Domain TypedDicts |

**Key clarifications:**
- **Aggregates with Child Entities:** Each child entity separately gets Entity + its own supporting patterns.
- **Aggregates with Collections:** The collection class separately gets Value Objects + Collection Value Objects + Delegation + Guards.
- **Status with Event Delegation:** Status VOs that emit events need Delegation & Events in addition to Statuses.
- **list[ValueObject] without Collection Pattern:** Only use Collection when the list has lifecycle management methods (add/remove). Simple `list[BeneficialOwner]` doesn't need it.
- **Guards & Checks scope:** Fundamental for Aggregates, Entities, and Value Objects. Not used for Events, Commands, Repositories, Services, or TypedDicts.

---

## Examples

For complete worked examples covering 9 scenarios (simple aggregate, aggregate with VO, collection+events, status, complex optionals, repository, TypedDict, child entities, nested VOs with union types), see [examples.md](examples.md).
