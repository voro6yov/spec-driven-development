---
name: mixed-dispatcher-events-and-commands
description: Mixed Dispatcher (Events and Commands) pattern for messaging dispatchers. Use when a single service needs to consume both domain events and commands through one dispatcher factory and unified consumer lifecycle.
user-invocable: false
disable-model-invocation: false
---

# Mixed Dispatcher (Events and Commands)

Category: Dispatcher Pattern

## Purpose

- Configure a single dispatcher factory that handles both domain events AND commands.
- Combine `DomainEventDispatcher` and `CommandDispatcher` in one initialization.
- Provide a unified entry point for services that consume both message types.

## When to Use

Use a mixed dispatcher when:

- A service needs to react to events AND respond to commands
- You want a single consumer process for both message types
- The event and command processing share the same lifecycle

Use separate dispatchers when:

- Events and commands need independent scaling
- Different failure isolation is required
- Teams own different message types

## Structure

A mixed dispatcher factory:

1. Configures event handlers with `DomainEventHandlersBuilder`
2. Configures command handlers with `CommandHandlersBuilder`
3. Initializes both `DomainEventDispatcher` and `CommandDispatcher`
4. Returns the consumer for lifecycle management

## Template Parameters

When using the template, replace these placeholders with your project-specific values:

- `{{ constants_module }}` - Module path for constants
- `{{ aggregate_destination }}` - Destination constant for events
- `{{ events_queue }}` - Queue constant for events
- `{{ channel_name }}` - Channel constant for commands
- `{{ commands_queue }}` - Queue constant for commands
- `{{ dispatcher_name }}` - Name identifier for this dispatcher
- `{{ event_imports }}` - Event class names to import
- `{{ event_handler_imports }}` - Event handler function names
- `{{ event_handlers }}` - Event-to-handler mappings
- `{{ command_imports }}` - Command class names to import
- `{{ command_handler_imports }}` - Command handler function names
- `{{ command_handlers }}` - Command-to-handler mappings

## Example

```python
import logging

from deps_pubsub.commands.consumer import CommandDispatcher, CommandHandlersBuilder
from deps_pubsub.events.subscriber import (
    DomainEventDispatcher,
    DomainEventHandlersBuilder,
)
from deps_pubsub.messaging.consumer import IMessageConsumer
from deps_pubsub.messaging.producer import IMessageProducer

from my_project.constants import (
    COMMANDS_CHANNEL,
    COMMANDS_QUEUE,
    DOCUMENTS_DESTINATION,
    EVENTS_QUEUE,
)

__all__ = ["make_message_dispatcher"]

_logger = logging.getLogger(__name__)

def make_message_dispatcher(
    subscriber: IMessageConsumer,
    producer: IMessageProducer,
) -> IMessageConsumer:
    from .commands import StartLabelProcessing
    from .events import DocumentCreated
    from .handlers import (
        document_created_handler,
        start_label_processing_handler,
    )

    # Configure event handlers
    events_handlers = (
        DomainEventHandlersBuilder.for_aggregate_type(DOCUMENTS_DESTINATION)
        .on_event(DocumentCreated, document_created_handler)
        .for_queue(EVENTS_QUEUE)
        .build()
    )

    # Configure command handlers
    commands_handlers = (
        CommandHandlersBuilder.from_channel(COMMANDS_CHANNEL)
        .on_message(StartLabelProcessing, start_label_processing_handler)
        .for_queue(COMMANDS_QUEUE)
        .build()
    )

    # Initialize both dispatchers
    ded = DomainEventDispatcher(events_handlers, subscriber)
    ded.initialize()

    cd = CommandDispatcher(commands_handlers, subscriber, producer)
    cd.initialize()

    _logger.info("Start consuming events and commands....")

    return subscriber
```

## Queue Isolation

Even in a mixed dispatcher, events and commands use **separate queues**:

```python
# constants.py
EVENTS_QUEUE = "my-service-events"
COMMANDS_QUEUE = "my-service-commands"
```

This ensures:

- Independent message ordering per type
- Separate retry/dead-letter handling
- Clear operational visibility

## Testing Guidance

- Test that both event and command handlers are registered.
- Verify each message type routes to the correct handler.
- Test that both dispatcher types initialize correctly.
- Verify unique queue configurations for events and commands.

---

## Template

```python
import logging

from deps_pubsub.commands.consumer import CommandDispatcher, CommandHandlersBuilder
from deps_pubsub.events.subscriber import (
    DomainEventDispatcher,
    DomainEventHandlersBuilder,
)
from deps_pubsub.messaging.consumer import IMessageConsumer
from deps_pubsub.messaging.producer import IMessageProducer

from {{ constants_module }} import (
    {{ aggregate_destination }},
    {{ channel_name }},
    {{ commands_queue }},
    {{ events_queue }},
)

__all__ = ["make_{{ dispatcher_name }}_dispatcher"]

_logger = logging.getLogger(__name__)

def make_{{ dispatcher_name }}_dispatcher(
    subscriber: IMessageConsumer,
    producer: IMessageProducer,
) -> IMessageConsumer:
    from .commands import {{ command_imports }}
    from .events import {{ event_imports }}
    from .handlers import (
        {{ event_handler_imports }},
        {{ command_handler_imports }},
    )

    events_handlers = (
        DomainEventHandlersBuilder.for_aggregate_type({{ aggregate_destination }})
        {% for event_handler in event_handlers %}
        .on_event({{ event_handler.event_name }}, {{ event_handler.handler_name }})
        {% endfor %}
        .for_queue({{ events_queue }})
        .build()
    )

    commands_handlers = (
        CommandHandlersBuilder.from_channel({{ channel_name }})
        {% for command_handler in command_handlers %}
        .on_message({{ command_handler.command_name }}, {{ command_handler.handler_name }})
        {% endfor %}
        .for_queue({{ commands_queue }})
        .build()
    )

    ded = DomainEventDispatcher(events_handlers, subscriber)
    ded.initialize()

    cd = CommandDispatcher(commands_handlers, subscriber, producer)
    cd.initialize()

    _logger.info("Start consuming events and commands....")

    return subscriber
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ constants_module }}` | Module path for constants | `my_project.constants` |
| `{{ aggregate_destination }}` | Destination constant for events | `DOCUMENTS_DESTINATION` |
| `{{ events_queue }}` | Queue constant for events | `EVENTS_QUEUE` |
| `{{ channel_name }}` | Channel constant for commands | `COMMANDS_CHANNEL` |
| `{{ commands_queue }}` | Queue constant for commands | `COMMANDS_QUEUE` |
| `{{ dispatcher_name }}` | Name identifier for this dispatcher | `message` |
| `{{ event_imports }}` | Event class names | `DocumentCreated, DocumentUpdated` |
| `{{ event_handler_imports }}` | Event handler function names | `document_created_handler,\n        document_updated_handler` |
| `{{ event_handlers }}` | Event-to-handler mappings | `[{"event_name": "DocumentCreated", "handler_name": "document_created_handler"}]` |
| `{{ command_imports }}` | Command class names | `StartLabelProcessing` |
| `{{ command_handler_imports }}` | Command handler function names | `start_label_processing_handler` |
| `{{ command_handlers }}` | Command-to-handler mappings | `[{"command_name": "StartLabelProcessing", "handler_name": "start_label_processing_handler"}]` |
