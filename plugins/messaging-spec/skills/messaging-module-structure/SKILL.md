---
name: messaging-module-structure
description: Messaging Module Structure pattern for organizing the messaging/ module. Use when laying out submodules, naming dispatchers/handlers, defining exports, or deciding where events live.
user-invocable: false
disable-model-invocation: false
---

# Messaging Module Structure

Category: Structural Guide

# Messaging Module Structure

## Purpose

- Define the standard organization of the `messaging/` module.
- Establish conventions for submodule layout and exports.
- Ensure consistent structure across services.

## Directory Structure

```
messaging/
├── __init__.py                    # Exports all dispatcher factories
├── document_ops/                  # Concern-based submodule
│   ├── __init__.py               # Exports dispatcher only
│   ├── dispatcher.py             # Dispatcher factory function
│   ├── events.py                 # External events for this concern
│   └── handlers.py               # Event handlers
├── profile_ops/                   # Another concern-based submodule
│   ├── __init__.py
│   ├── dispatcher.py
│   ├── events.py
│   └── handlers.py
└── subject_extraction/            # Submodule using only domain events
    ├── __init__.py
    ├── dispatcher.py
    └── handlers.py               # No events.py if using domain events
```

## Naming Conventions

### Submodule Names

Name submodules after the **processing concern**, not the event source:

| Good | Bad |
| --- | --- |
| `document_ops` | `files_events` |
| `profile_ops` | `profile_created_handler` |
| `subject_extraction` | `documents_consumer` |

### Dispatcher Function Names

Use `make_<submodule_name>_dispatcher`:

```python
# document_ops/dispatcher.py
def make_document_ops_dispatcher(subscriber, producer):
    ...
```

### Handler Function Names

Use `<event_name_snake_case>_handler`:

```python
def file_classification_succeeded_handler(envelope, ...):
    ...

def document_created_handler(envelope, ...):
    ...
```

## Module Exports

### Root `messaging/__init__.py`

Export all dispatcher factories using wildcard imports:

```python
from .document_ops import *
from .profile_ops import *
from .subject_extraction import *

__all__ = document_ops.__all__ + profile_ops.__all__ + subject_extraction.__all__
```

### Submodule `__init__.py`

Export **only the dispatcher factory**:

```python
from .dispatcher import *

__all__ = dispatcher.__all__
```

Handlers and events are implementation details, not public API.

## When to Create a New Submodule

Create a new submodule when:

- Processing a new set of related events
- Events require a different queue (scaling/isolation needs)
- Business logic warrants separation of concerns

Each submodule should have:

- Its own unique queue constant
- Focused responsibility (single concern)
- Clear naming reflecting its purpose

## Events Location

| Event Type | Location | Import Path |
| --- | --- | --- |
| External (from other services) | `messaging/*/events.py` | `from .events import ...` |
| Internal (from this service) | `domain/` layer | `from my_project.domain import ...` |

A submodule can handle both external and internal events. Import them appropriately in the dispatcher.

## Example: Complete Submodule

```python
# messaging/document_ops/__init__.py
from .dispatcher import *

__all__ = dispatcher.__all__
```

```python
# messaging/document_ops/events.py
from dataclasses import dataclass
from deps_pubsub.events.common import DomainEvent

__all__ = ["FileClassificationSucceeded", "DocumentTypesAssignedToFile"]

@dataclass
class FileClassificationSucceeded(DomainEvent):
    id: str
    tenant_id: str
    document_types: list[str]

@dataclass
class DocumentTypesAssignedToFile(DomainEvent):
    id: str
    tenant_id: str
    document_types: list[str]
```

```python
# messaging/document_ops/handlers.py
from dependency_injector.wiring import Provide, inject
from deps_pubsub.events.subscriber.domain_event_envelope import DomainEventEnvelope

from my_project.application import DocumentCommands
from my_project.containers import Containers
from .events import FileClassificationSucceeded

logger = logging.getLogger(__name__)

@inject
def file_classification_succeeded_handler(
    envelope: DomainEventEnvelope[FileClassificationSucceeded],
    document_commands: DocumentCommands = Provide[Containers.document_commands],
) -> None:
    event = envelope.event
    try:
        document_commands.on_file_classification_succeeded(
            file_id=event.id,
            tenant_id=event.tenant_id,
            document_types=event.document_types,
        )
    except Exception as e:
        logger.error(f"Error processing FileClassificationSucceeded event: {e}.", exc_info=True)
        raise
```

```python
# messaging/document_ops/dispatcher.py
from deps_pubsub.events.subscriber import DomainEventDispatcher, DomainEventHandlersBuilder
from deps_pubsub.messaging.consumer import IMessageConsumer
from deps_pubsub.messaging.producer import IMessageProducer

from my_project.constants import FILES_DESTINATION, OPS_EVENTS_QUEUE

__all__ = ["make_document_ops_dispatcher"]

def make_document_ops_dispatcher(subscriber: IMessageConsumer, producer: IMessageProducer) -> IMessageConsumer:
    from .events import FileClassificationSucceeded, DocumentTypesAssignedToFile
    from .handlers import (
        file_classification_succeeded_handler,
        document_types_assigned_to_file_handler,
    )

    events_handlers = (
        DomainEventHandlersBuilder.for_aggregate_type(FILES_DESTINATION)
        .on_event(FileClassificationSucceeded, file_classification_succeeded_handler)
        .on_event(DocumentTypesAssignedToFile, document_types_assigned_to_file_handler)
        .for_queue(OPS_EVENTS_QUEUE)
        .build()
    )

    ded = DomainEventDispatcher(events_handlers, subscriber)
    ded.initialize()

    return subscriber
```
