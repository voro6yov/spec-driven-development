---
name: domain-event-dispatchers
description: Domain Event Dispatchers pattern for messaging. Use when configuring routing of domain events from pubsub queues to handlers.
user-invocable: false
disable-model-invocation: false
---

# Domain Event Dispatchers

Category: Dispatcher Pattern

# Domain Event Dispatchers

## Purpose

- Configure routing of domain events from pubsub queues to handlers.
- Set up `DomainEventDispatcher` with event-to-handler mappings.
- Initialize message consumption for domain events.

## Variants

- **Single-aggregate dispatcher** (this pattern) - Events from one aggregate type
- **Multi-aggregate dispatcher** - Events from multiple aggregate types; see [Multi-Aggregate Domain Event Dispatchers](multi-aggregate-domain-event-dispatchers.md)

## Architecture Overview

### Multiple Dispatchers

A service can define **multiple dispatchers**, each handling a distinct set of events for different purposes:

```
Service
├── document_ops/dispatcher.py      → OPS_EVENTS_QUEUE
├── profile_ops/dispatcher.py       → PROFILE_OPS_EVENTS_QUEUE
└── subject_extraction/dispatcher.py → EXTRACTION_EVENTS_QUEUE
```

### Unique Queues Per Dispatcher

Each dispatcher **must have its own unique queue**. This ensures:

- Independent scaling of event processing
- Isolation of failure domains
- Clear separation of concerns

### Destination Constants

Aggregates are identified by **Destination constants** that define the source of events:

```python
# constants.py
FILES_DESTINATION = "files"
DOCUMENTS_DESTINATION = "documents"
PROFILES_DESTINATION = "profiles"
```

The dispatcher subscribes to events from specific destinations and routes them to handlers.

## Structure

- Implemented as factory functions returning configured `IMessageConsumer`.
- Use `DomainEventHandlersBuilder` to build handler mappings.
- Register handlers for specific aggregate types using Destination constants.
- Configure unique queue name and initialize the dispatcher.

## Template Parameters

When using the template, replace these placeholders with your project-specific values:

- `{{ constants_module }}` - Module path for constants (e.g., `my_project.constants`)
- `{{ aggregate_destination }}` - Destination constant for aggregate type (e.g., `FILES_DESTINATION`)
- `{{ queue_name }}` - Unique queue constant for this dispatcher (e.g., `OPS_EVENTS_QUEUE`)
- `{{ dispatcher_name }}` - Name identifier for this dispatcher (used in function name, e.g., `document_ops`)
- `{{ domain_module }}` - Module path for domain events (e.g., `my_project.domain`) — optional, use when handling internal domain events
- `{{ domain_event_imports }}` - Comma-separated list of domain event class names — optional
- `{{ external_event_imports }}` - Comma-separated list of event class names from `.events` module — optional
- `{{ handler_imports }}` - Comma-separated list of handler function names to import
- `{{ event_handlers }}` - List of event handler mappings with `event_name` and `handler_name`

**Note:** Use `domain_event_imports` for events from this service's domain layer, and `external_event_imports` for events from other services (defined in local `events.py`). A dispatcher can use either or both.

## Usage Patterns

- Factory function accepts `IMessageConsumer` and `IMessageProducer` as parameters.
- Build handler mappings using fluent builder API.
- Register handlers grouped by aggregate Destination.
- Initialize dispatcher and return consumer for startup.

## Example: Multiple Dispatchers in a Service

```python
# constants.py
FILES_DESTINATION = "files"
DOCUMENTS_DESTINATION = "documents"

OPS_EVENTS_QUEUE = "iv-documents-ops-events"
EXTRACTION_EVENTS_QUEUE = "iv-documents-extraction-events"
```

```python
# document_ops/dispatcher.py
def make_document_ops_dispatcher(subscriber, producer):
    events_handlers = (
        DomainEventHandlersBuilder.for_aggregate_type(FILES_DESTINATION)
        .on_event(FileClassificationSucceeded, file_classification_succeeded_handler)
        .for_queue(OPS_EVENTS_QUEUE)  # Unique queue
        .build()
    )
    ...
```

```python
# subject_extraction/dispatcher.py
def make_subject_extraction_dispatcher(subscriber, producer):
    events_handlers = (
        DomainEventHandlersBuilder.for_aggregate_type(DOCUMENTS_DESTINATION)
        .on_event(DocumentCreated, document_created_handler)
        .for_queue(EXTRACTION_EVENTS_QUEUE)  # Different unique queue
        .build()
    )
    ...
```

## Testing Guidance

- Test that all expected handlers are registered.
- Verify each dispatcher has a unique queue configuration.
- Test dispatcher initialization and consumer setup.
- Verify correct Destination constant is used for aggregate type.

---

## Template

```python
import logging

from deps_pubsub.events.subscriber import (
    DomainEventDispatcher,
    DomainEventHandlersBuilder,
)
from deps_pubsub.messaging.consumer import IMessageConsumer
from deps_pubsub.messaging.producer import IMessageProducer

from {{ constants_module }} import {{ aggregate_destination }}, {{ queue_name }}

__all__ = ["make_{{ dispatcher_name }}_dispatcher"]

_logger = logging.getLogger(__name__)

def make_{{ dispatcher_name }}_dispatcher(subscriber: IMessageConsumer, producer: IMessageProducer) -> IMessageConsumer:
    {% if domain_event_imports %}
    from {{ domain_module }} import {{ domain_event_imports }}
    {% endif %}
    {% if external_event_imports %}
    from .events import {{ external_event_imports }}
    {% endif %}
    from .handlers import (
        {{ handler_imports }}
    )

    events_handlers = (
        DomainEventHandlersBuilder.for_aggregate_type({{ aggregate_destination }})
        {% for event_handler in event_handlers %}
        .on_event({{ event_handler.event_name }}, {{ event_handler.handler_name }})
        {% endfor %}
        .for_queue({{ queue_name }})
        .build()
    )

    ded = DomainEventDispatcher(events_handlers, subscriber)
    ded.initialize()

    _logger.info("Start consuming....")

    return subscriber
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ constants_module }}` | Module path for constants | `my_project.constants` |
| `{{ aggregate_destination }}` | Destination constant for aggregate type | `FILES_DESTINATION` |
| `{{ queue_name }}` | Unique queue constant for this dispatcher | `OPS_EVENTS_QUEUE` |
| `{{ dispatcher_name }}` | Name identifier for this dispatcher | `document_ops` |
| `{{ domain_module }}` | Module path for domain events (optional) | `my_project.domain` - use for internal domain events |
| `{{ domain_event_imports }}` | Comma-separated list of domain event class names (optional) | `DocumentCreated, DocumentProcessingSucceeded` |
| `{{ external_event_imports }}` | Comma-separated list of event class names from `.events` module (optional) | `FileClassificationSucceeded` |
| `{{ handler_imports }}` | Comma-separated list of handler function names to import | `file_classification_succeeded_handler` |
| `{{ event_handlers }}` | List of event handler mappings with `event_name` and `handler_name` | `[{"event_name": "FileClassificationSucceeded", "handler_name": "file_classification_succeeded_handler"}]` |
