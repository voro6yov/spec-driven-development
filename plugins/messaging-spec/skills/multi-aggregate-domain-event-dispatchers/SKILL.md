---
name: multi-aggregate-domain-event-dispatchers
description: Multi-Aggregate Domain Event Dispatchers pattern for routing domain events from multiple aggregate types to handlers in a single dispatcher. Use when events from multiple Destinations need coordinated handling, related business logic spans multiple domain boundaries, or related events from different services should be processed together.
user-invocable: false
disable-model-invocation: false
---

# Multi-Aggregate Domain Event Dispatchers

Category: Dispatcher Pattern

# Multi-Aggregate Domain Event Dispatchers

## Purpose

- Configure routing of domain events from multiple aggregate types to handlers.
- Handle events from different services/aggregates in a single dispatcher.
- Consolidate related event processing that spans multiple domains.

## Architecture Overview

### Multiple Dispatchers Coexistence

A service can define **multiple dispatchers** (both single and multi-aggregate). Each dispatcher serves a distinct purpose and has its own queue:

```
Service
├── profile_ops/dispatcher.py       → PROFILE_OPS_EVENTS_QUEUE (multi-aggregate)
│   ├── PROFILES_DESTINATION events
│   └── DOCUMENTS_DESTINATION events
├── document_ops/dispatcher.py      → OPS_EVENTS_QUEUE (single-aggregate)
│   └── FILES_DESTINATION events
└── subject_extraction/dispatcher.py → EXTRACTION_EVENTS_QUEUE (single-aggregate)
    └── DOCUMENTS_DESTINATION events
```

### Unique Queue Per Dispatcher

Each dispatcher **must have its own unique queue**, even when handling multiple aggregates. This ensures:

- Independent scaling and processing
- Failure isolation between different event processing concerns
- Clear operational boundaries

### Destination Constants

Aggregates are identified by **Destination constants**. A multi-aggregate dispatcher chains multiple destinations:

```python
# constants.py
PROFILES_DESTINATION = "profiles"
DOCUMENTS_DESTINATION = "documents"
FILES_DESTINATION = "files"

PROFILE_OPS_EVENTS_QUEUE = "iv-documents-profile-ops-events"
```

## Structure

- Implemented as factory functions returning configured `IMessageConsumer`.
- Use `DomainEventHandlersBuilder` with `and_for_aggregate_type()` to chain multiple Destination constants.
- Register handlers for each aggregate type in sequence.
- Configure a single unique queue name for all aggregates in this dispatcher.

## Template Parameters

When using the template, replace these placeholders with your project-specific values:

- `{{ constants_module }}` - Module path for constants (e.g., `my_project.constants`)
- `{{ aggregate_destinations }}` - Comma-separated Destination constants (e.g., `PROFILES_DESTINATION, DOCUMENTS_DESTINATION`)
- `{{ queue_name }}` - Unique queue constant for this dispatcher
- `{{ dispatcher_name }}` - Name identifier for this dispatcher (used in function name)
- `{{ domain_module }}` - Module path for domain events (e.g., `my_project.domain`) — optional
- `{{ domain_event_imports }}` - Comma-separated list of domain event class names — optional
- `{{ external_event_imports }}` - Comma-separated list of external event class names from `.events` — optional
- `{{ handler_imports }}` - Comma-separated list of handler function names to import
- `{{ first_aggregate_destination }}` - Destination constant for the first aggregate type
- `{{ first_aggregate_handlers }}` - List of event handler mappings for first aggregate
- `{{ additional_aggregates }}` - List of additional aggregates, each with `destination` and `handlers`

**Note:** Use `domain_event_imports` for events from this service's domain layer, and `external_event_imports` for events from other services (defined in local `events.py`). A dispatcher can use either or both.

## When to Use

Use this pattern when:

- Events from multiple Destinations need coordinated handling in a single processing context
- Related business logic spans multiple domain boundaries
- You want to process related events from different services together

Use the single-aggregate dispatcher when:

- All events come from one Destination
- Simpler routing is sufficient
- Events should be processed independently from other aggregates

## Usage Patterns

- Factory function accepts `IMessageConsumer` and `IMessageProducer` as parameters.
- Chain Destination constants using `.and_for_aggregate_type()`.
- Each aggregate section registers its own event-to-handler mappings.
- All aggregates share the same unique queue configuration.

## Example Structure

```python
from my_project.constants import (
    PROFILES_DESTINATION,
    DOCUMENTS_DESTINATION,
    PROFILE_OPS_EVENTS_QUEUE,
)

def make_profile_ops_dispatcher(subscriber, producer):
    events_handlers = (
        DomainEventHandlersBuilder.for_aggregate_type(PROFILES_DESTINATION)
        .on_event(ProfileCreated, profile_created_handler)
        .on_event(FileUploaded, file_uploaded_handler)
        .and_for_aggregate_type(DOCUMENTS_DESTINATION)
        .on_event(DocumentCreated, document_created_handler)
        .on_event(DocumentProcessingSucceeded, document_processing_succeeded_handler)
        .on_event(DocumentProcessingFailed, document_processing_failed_handler)
        .for_queue(PROFILE_OPS_EVENTS_QUEUE)  # Unique queue for this dispatcher
        .build()
    )
    
    ded = DomainEventDispatcher(events_handlers, subscriber)
    ded.initialize()
    
    return subscriber
```

## Testing Guidance

- Test that all expected handlers are registered for each Destination.
- Verify the dispatcher has a unique queue configuration.
- Test dispatcher initialization and consumer setup.
- Ensure events from different Destinations route to correct handlers.
- Verify Destination constants are correctly used in builder chain.

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

from {{ constants_module }} import {{ aggregate_destinations }}, {{ queue_name }}

__all__ = ["make_{{ dispatcher_name }}_dispatcher"]

_logger = logging.getLogger(__name__)

def make_{{ dispatcher_name }}_dispatcher(subscriber: IMessageConsumer, producer: IMessageProducer) -> IMessageConsumer:
    {% if domain_event_imports %}
    from {{ domain_module }} import (
        {{ domain_event_imports }}
    )
    {% endif %}

    {% if external_event_imports %}
    from .events import {{ external_event_imports }}
    {% endif %}
    from .handlers import (
        {{ handler_imports }}
    )

    events_handlers = (
        DomainEventHandlersBuilder.for_aggregate_type({{ first_aggregate_destination }})
        {% for handler in first_aggregate_handlers %}
        .on_event({{ handler.event_name }}, {{ handler.handler_name }})
        {% endfor %}
        {% for aggregate in additional_aggregates %}
        .and_for_aggregate_type({{ aggregate.destination }})
        {% for handler in aggregate.handlers %}
        .on_event({{ handler.event_name }}, {{ handler.handler_name }})
        {% endfor %}
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
| `{{ aggregate_destinations }}` | Comma-separated Destination constants | `PROFILES_DESTINATION, DOCUMENTS_DESTINATION` |
| `{{ queue_name }}` | Unique queue constant for this dispatcher | `PROFILE_OPS_EVENTS_QUEUE` |
| `{{ dispatcher_name }}` | Name identifier for this dispatcher | `profile_ops` |
| `{{ domain_module }}` | Module path for domain events (optional) | `my_project.domain` - use for internal domain events |
| `{{ domain_event_imports }}` | Comma-separated list of domain event class names (optional) | `DocumentCreated, ProfileCreated` |
| `{{ external_event_imports }}` | Comma-separated list of external event class names from `.events` (optional) | `FileUploaded` |
| `{{ handler_imports }}` | Comma-separated list of handler function names to import | `profile_created_handler, document_created_handler` |
| `{{ first_aggregate_destination }}` | Destination constant for the first aggregate type | `PROFILES_DESTINATION` |
| `{{ first_aggregate_handlers }}` | List of event handler mappings for first aggregate | `[{"event_name": "ProfileCreated", "handler_name": "profile_created_handler"}]` |
| `{{ additional_aggregates }}` | List of additional aggregates, each with `destination` and `handlers` | `[{"destination": "DOCUMENTS_DESTINATION", "handlers": [{"event_name": "DocumentCreated", "handler_name": "document_created_handler"}]}]` |
