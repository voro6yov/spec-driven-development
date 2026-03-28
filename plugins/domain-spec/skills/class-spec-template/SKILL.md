---
name: class-spec-template
description: Reference template for DDD domain model class specifications. Load when generating or reviewing class specs, or working with Aggregate Roots, Entities, Value Objects, Domain Events, TypedDicts, Commands, or Query DTOs.
user-invocable: false
---

# Class Spec Template

> **Formatting rules — apply to all class types:**
> - Attributes: bullet list `- \`name\`: type`, never a markdown table
> - Methods: `◦` for each method entry, `▪` for each detail line (`▪ Effect:`, `▪ Delegates:`, `▪ Emits:`, `▪ Raises:`, `▪ Allowed from:`); never use blockquotes (`>`) or markdown tables
> - Detailed method spec heading: h3 (`### Method:`), not h4 or h5
> - Domain Exceptions: bullet list `- \`ExceptionName\` — trigger condition`, never a table
> - `**Pattern**`: always left as `- **Pattern**: —`; the pattern values shown in the templates below are for human reference only — a spec generator must never fill this field in

---

## Aggregate Root

```
**`ClassName`** `<<Aggregate Root>>`

- **Pattern**: Pattern1; Pattern2; ...

Purpose statement.

- `id`: str
- `attribute_name`: type
- `attribute_name`: type | None
- **Methods**:

    ◦ `new(param: type, ...) -> ClassName`

    ▪ Effect: creates instance in initial state

    ◦ `method_name(params) -> ReturnType`

    ▪ Allowed from: `state1`, `state2`

    ▪ Effect: what changes occur

    ▪ Delegates: `TargetClass.method()`

    ▪ Emits: `EventName`

    ▪ Raises: `ExceptionName` — when condition
```

Detailed method specs are **required** for Aggregate Roots — add a sub-section after the class block for each non-trivial method (see Detailed Method Specification below).

---

## Entity

```
**`ClassName`** `<<Entity>>`

- **Pattern**: Pattern1; Pattern2; ...

Purpose statement.

- `id`: str
- `attribute_name`: type
- `attribute_name`: type | None
- **Methods**:

    ◦ `method_name(params) -> ReturnType`

    ▪ Allowed from: `state1`, `state2`

    ▪ Effect: what changes occur

    ▪ Delegates: `TargetClass.method()`

    ▪ Emits: `EventName`

    ▪ Raises: `ExceptionName` — when condition
```

---

## Value Object

Immutable — no mutation methods. Show `__init__` only when it has non-trivial validation logic.

```
**`ClassName`** `<<Value Object>>`

- **Pattern**: Pattern1; Pattern2; ...

Purpose statement.

- `attribute_name`: type
- `attribute_name`: type | None
- `computed_property`: type (computed property)
    - Computation logic description
- **Methods** (if applicable):

    ◦ `__init__(params) -> None`

    ▪ Effect: sets internal fields; describe any conditional validation
```

---

## Domain Event

Fields only. No methods.

```
**`EventName`** `<<Event>>`

- **Pattern**: Domain Events

Purpose statement describing what domain occurrence this event represents.

- `field_name`: type
- `field_name`: type
```

---

## TypedDict

Fields only. No methods. Use `<<TypedDict>>` for all data structures regardless of whether they are internal domain structures or query return types.

```
**`ClassName`** `<<TypedDict>>`

- **Pattern**: Domain TypedDicts

Purpose statement.

- `field_name`: type
- `field_name`: type | None
```

---

## Command

```
**`CommandName`** `<<Command>>`

- **Pattern**: Commands

Purpose statement describing what action this command triggers and which method emits it.

- `COMMAND_CHANNEL`: ClassVar[str] = "ChannelName"
- `REPLY_CHANNEL`: ClassVar[str] = "ReplyChannelName"
- `field_name`: type
- `field_name`: type

**Success Reply**: `CommandNameSuccess`

- `field_name`: type

**Failure Reply**: `CommandNameFailure`

- `field_name`: type
- `error_message`: str
```

---

## Repository / Service

Methods only. Same method fields as Aggregate Root minus `Emits`.

```
**`ClassName`** `<<Repository>>`   (or <<Service>>)

- **Pattern**: Pattern1; ...

Purpose statement.

- **Methods**:

    ◦ `method_name(params) -> ReturnType`

    ▪ Raises: `ExceptionName` — when condition
```

---

## Detailed Method Specification

**Required** for Aggregate Roots. Optional for Entities.

```
### Method: `method_name(params) -> ReturnType`

**Purpose**: What this method accomplishes

**Preconditions**:

- Current status must be...
- Input must satisfy...

**Method Flow**:

1. First step
2. Second step
3. Emit event

**Postconditions**:

- State transitions to...
- Event added to domain events

**Invariants**:

- Rule that must always hold

**Implementation Notes**:

- Technical guidance
- Edge case handling
```

---

## Package-Level Structure

```markdown
### Diagram
(Mermaid class diagram)

### Class Specification

#### Data Structures
(TypedDicts — all domain data structures and query return types)

#### Value Objects

#### Domain Events

#### Commands                      ← include if any commands exist in the diagram

#### Aggregate Root / Entities

#### Domain Exceptions             ← always required; infer from all Raises: clauses

#### Repositories / Services

### Dependencies                   ← always required; derive from all diagram relationships
1. **ClassA** depends on **ClassB** (relationship type)
```
