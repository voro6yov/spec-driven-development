---
name: commands-specification-template
description: Commands Specification Template pattern for application service command specs. Use when documenting a Commands application service that orchestrates aggregate operations, repositories, and external interfaces.
user-invocable: false
disable-model-invocation: false
---

# Commands Specification Template

This template provides a standardized structure for documenting Commands Application Service specifications. Generate specifications section-by-section by applying the referenced pattern skills.

---

## Section 1: Service Architecture

**Pattern Reference**: `application-spec:commands`

### Diagram

```mermaid
---
title: {ServiceName} Domain Model (Application)
config:
    class:
        hideEmptyMembersBox: true
---

classDiagram
	class {ServiceName}Commands {
			<<Application>>
			-command_repository: Command{Aggregate}Repository
			+method_name(params) ReturnType
	}
	
	{ServiceName}Commands --() Command{Aggregate}Repository : uses
	{ServiceName}Commands --() {Aggregate} : manipulates
```

## {ServiceName}Commands Application Service Specification

The `{ServiceName}Commands` application service orchestrates {domain} operations by coordinating between the `{Aggregate}` aggregate, the `Command{Aggregate}Repository`, and external processing interfaces. It unwraps `ProcessingResult` from interfaces and handles errors before calling aggregate methods.

**Validation Responsibility**: State-based validations (status checks, entity existence, state transitions) are handled by the `{Aggregate}` aggregate. This service only validates infrastructure concerns and propagates domain exceptions from the aggregate.

---

## Section 2: External Interfaces

**Pattern Reference**: `application-spec:interfaces`

**When to include**: External system interaction required (conveyor, ERP, etc.)

**Skip if**: Command only uses UoW repositories internally.

### Interface: `ICanPerform{Action}`

**Purpose**: [Protocol interface for external system interaction]

**Methods**:

```python
class ICanPerform{Action}(Protocol):
    def method_name(self, param1: type, param2: type) -> ResultType:
        """[Method description]"""
        ...
```

**Implementation Location**: `application/{context}/i_can_perform_{action}.py`

**Notes**:

- [When this interface is needed]
- [Expected implementations]
- [Error handling strategy]

---

## Section 3: Method Specifications

**Pattern Reference**: `application-spec:commands`

### Method: `method_name(param1: type, param2: type) -> ReturnType`

**Purpose**: [One-liner describing what this method does]

**Preconditions**:

- `param1` must be a valid UUID string (non-empty)
- `param2` must be [validation requirement]
- [Additional precondition]

**Dependencies**:

- `command_repository: Command{Aggregate}Repository`
- `event_publisher: EventPublisher`
- [Additional dependency: Interface or service]

**Method Flow**:

1. Call `command_repository.[method](params)` to retrieve/create entity
2. Call `aggregate.[domain_method](params)` on the aggregate
3. Call `command_repository.save(aggregate)` to persist changes
4. Extract events from aggregate and publish via `event_publisher`
5. Return the [created/updated] {Aggregate}

**Postconditions**:

- [State change description]
- [Event published description]
- [Downstream effect description]

**Error Handling**:

- If {entity} not found: raise `{Entity}NotFoundError`
- If aggregate rejects operation (invalid state): propagate aggregate's domain exception
- If repository operations fail: raise `PersistenceError`

**Implementation Notes**:

- Triggered by [event/API endpoint/handler]
- Handler should be idempotent: [describe idempotency behavior]
- Consider wrapping in database transaction

---

### Method: `on_event_name(param1: str, tenant_id: str) -> ReturnType`

**Purpose**: Event handler that [describes reaction to domain event]

**Preconditions**:

- `param1` must be a valid UUID string (non-empty)
- `tenant_id` must be a valid UUID string (non-empty)

**Dependencies**:

- `command_repository: Command{Aggregate}Repository`
- `event_publisher: EventPublisher`

**Method Flow**:

1. Call `command_repository.[lookup_method](param1, tenant_id)` to retrieve entity
2. Call `aggregate.[state_change_method](params)` on the aggregate
3. Call `command_repository.save(aggregate)` to persist changes
4. Extract events from aggregate and publish via `event_publisher`
5. Return the updated {Aggregate}

**Postconditions**:

- [State transition description]
- [Event published for downstream consumers]

**Outcome Table** (if multiple paths exist):

| Outcome | Status | Action |
| --- | --- | --- |
| Success with data | `[status_a]` | [Description] |
| Success without data | `[status_b]` | [Description] |
| Processing Error | `failed` | [Description] |

**Error Handling**:

- If {entity} not found: raise `{Entity}NotFoundError`
- If invalid state transition: propagate domain exception
- Infrastructure errors propagated to caller

**Implementation Notes**:

- Triggered by `{EventName}` event from {Domain} domain (async message handler)
- Handler should be idempotent: if already in target state, aggregate will reject
- [Additional consideration]

---

## Section 4: Dependency Injection

**Pattern Reference**: `application-spec:dependency-injection-patterns` → Container Provider Template

**Dependencies to wire**:

- `unit_of_work: UnitOfWork`
- `event_publisher: EventPublisher`
- `command_producer: CommandProducer` (if saga patterns used)
- [External interfaces from Section 2]

---

## General Implementation Guidelines

### Validation Responsibilities

| Layer | Validates | Examples |
| --- | --- | --- |
| {ServiceName}Commands (Application Service) | Infrastructure concerns | Entity existence, external service availability, input format |
| {Aggregate} (Aggregate) | Domain invariants | Status transitions, entity existence, business rules |

### Transaction Management

- Each handler should wrap repository operations in database transaction
- Event publishing should occur after successful transaction commit
- Consider outbox pattern for reliable event publishing

### Idempotency

- All event handlers must be idempotent
- If aggregate rejects operation due to state, propagate exception (let caller handle retry logic)
- Use correlation IDs for tracing duplicate messages

### Error Categories

| Error Type | Retryable | Example |
| --- | --- | --- |
| Transient Infrastructure | Yes | AWS service timeout, network error |
| Rate Limiting | Yes | Service throttling |
| Invalid Content | No | Unrecognized format, validation failure |
| Domain Rule Violation | No | Invalid state transition (propagated from aggregate) |

### Observability

- Log entry and exit of each handler with correlation ID
- Track processing duration metrics per operation type
- Alert on high error rates or unusual processing times
- Capture detailed error information for debugging

### Testing Considerations

- Unit tests for each method with mocked dependencies
- Integration tests for event flow between handlers
- Test error scenarios and retry behavior
- Test idempotency with duplicate message delivery
- Test that aggregate exceptions propagate correctly

---

> **Note**: [Add any domain-specific notes or cross-references to related bounded contexts here]
>
