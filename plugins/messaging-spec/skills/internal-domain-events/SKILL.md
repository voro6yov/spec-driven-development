---
name: internal-domain-events
description: Internal Domain Events pattern for messaging. Use when defining events produced by this service's domain layer to signal state changes within the bounded context and enable other services to react via pubsub.
user-invocable: false
disable-model-invocation: false
---

# Internal Domain Events

Category: Event Pattern

## Purpose

- Represent events produced by this service's domain layer.
- Signal state changes within the bounded context.
- Enable other services to react to changes via pubsub.

## Distinction from External Events

| Aspect | Internal Domain Events | External Message Events |
| --- | --- | --- |
| **Direction** | Produced BY this service | Consumed FROM other services |
| **Base Class** | Local `Event` from `domain.shared` | `DomainEvent` from `deps_pubsub.events.common` |
| **Location** | `domain/` layer | `messaging/*/events.py` |
| **Ownership** | This service defines the contract | External service defines the contract |

## Structure

- Implemented as `@dataclass` classes extending the local `Event` base class.
- Named after the past-tense action or state change (e.g., `DocumentCreated`, `DocumentProcessingSucceeded`).
- Declared within the domain layer, typically one file per event.
- Include all fields needed by consumers to react to the event.

## Template Parameters

When using the template, replace these placeholders with your project-specific values:

- `{{ domain_shared_module }}` - Module path for shared domain base class (e.g., `..shared` or `my_project.domain.shared`)
- `{{ event_name }}` - Name of the event class in past tense (e.g., `DocumentCreated`)
- `{{ event_fields }}` - Dataclass field definitions (e.g., `id: str
    
    tenant_id: str`)
    

## Field Guidelines

Internal domain events typically include:

- `id: str` - Entity identifier
- `tenant_id: str` - Multi-tenant isolation key
- Additional context fields specific to the event

Avoid including:

- Complex nested objects (prefer IDs for references)
- Mutable data structures
- Implementation details

## Usage Patterns

- Events are raised by aggregates/entities when state changes.
- Events are published through infrastructure layer to message broker.
- Other services subscribe to these events via their messaging layer.
- Events should be self-contained with all data needed by consumers.

## Example

```python
from dataclasses import dataclass

from ..shared import Event

__all__ = ["DocumentProcessingSucceeded"]

@dataclass
class DocumentProcessingSucceeded(Event):
    id: str
    tenant_id: str
    file_id: str
    subject_extracted: bool
```

## Testing Guidance

- Assert that events are immutable dataclasses.
- Verify all required fields are present.
- Test event construction with valid and edge-case data.
- Ensure events can be serialized for messaging infrastructure.

---

## Template

```python
from dataclasses import dataclass

from {{ domain_shared_module }} import Event

__all__ = ["{{ event_name }}"]

@dataclass
class {{ event_name }}(Event):
    {{ event_fields }}
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ domain_shared_module }}` | Module path for shared domain base class | `..shared`, `my_project.domain.shared` |
| `{{ event_name }}` | Name of the event class in past tense | `DocumentCreated`, `DocumentProcessingSucceeded` |
| `{{ event_fields }}` | Dataclass field definitions | `id: str |

tenant_id: str` |
