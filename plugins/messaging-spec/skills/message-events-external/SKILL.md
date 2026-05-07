---
name: message-events-external
description: Message Events (External) pattern for modeling events consumed from other services. Use when defining typed contracts for incoming messages from external bounded contexts that need to be processed by the application.
user-invocable: false
disable-model-invocation: false
---

# Message Events (External)

Category: Event Pattern

## Purpose

- Represent events received from other services that need to be processed by the application.
- Provide a structured way to model incoming messages with typed attributes.
- Define the contract for events consumed from external bounded contexts.

## Distinction from Internal Domain Events

This pattern is for **external** events — messages consumed FROM other services. For events **produced** by your service, see the [Internal Domain Events](internal-domain-events.md) pattern.

| Aspect | External Message Events | Internal Domain Events |
| --- | --- | --- |
| **Direction** | Consumed FROM other services | Produced BY this service |
| **Base Class** | `DomainEvent` from `deps_pubsub.events.common` | Local `Event` from `domain.shared` |
| **Location** | `messaging/*/events.py` | `domain/` layer |
| **Ownership** | External service defines the contract | This service defines the contract |

## Structure

- Implemented as `@dataclass` classes extending `DomainEvent` from `deps_pubsub.events.common`.
- Named after the past-tense action (e.g., `FileClassificationSucceeded`, `ProfileCreated`).
- Declared in `events.py` within the messaging submodule.
- Include all fields needed to process the event.

## Template Parameters

When using the template, replace these placeholders with your project-specific values:

- `{{ event_name }}` - Name of the event class (e.g., `FileClassificationSucceeded`)
- `{{ event_fields }}` - Dataclass field definitions (e.g., `id: str
    
    tenant_id: str
    
    path: str`)
    

## Example

```python
from dataclasses import dataclass

from deps_pubsub.events.common import DomainEvent

__all__ = ["FileClassificationSucceeded"]

@dataclass
class FileClassificationSucceeded(DomainEvent):
    id: str
    tenant_id: str
    path: str
    document_types: list[DocumentType]
    classified: bool
```

## Usage Patterns

- Each event represents a distinct message type from an external service.
- Events are immutable data carriers with no behavior.
- Events are imported in dispatcher factories and used as type parameters in handlers.

## Testing Guidance

- Assert full event payloads to ensure all fields are correctly populated.
- Test event construction with various combinations of required and optional fields.
- Verify events can be deserialized from the message broker format.

---

## Template

```python
from dataclasses import dataclass

from deps_pubsub.events.common import DomainEvent

__all__ = ["{{ event_name }}"]

@dataclass
class {{ event_name }}(DomainEvent):
    {{ event_fields }}
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ event_name }}` | Name of the event class | `FileClassificationSucceeded`, `ProfileCreated` |
| `{{ event_fields }}` | Dataclass field definitions | `id: str |

tenant_id: str

path: str` |
