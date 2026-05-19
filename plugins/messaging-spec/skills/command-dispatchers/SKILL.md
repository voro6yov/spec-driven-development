---
name: command-dispatchers
description: Command Dispatchers pattern for messaging. Use when configuring routing of commands from pubsub queues to handlers.
user-invocable: false
disable-model-invocation: false
---

# Command Dispatchers

Category: Dispatcher Pattern

## Purpose

- Configure routing of commands from pubsub queues to handlers.
- Set up `CommandDispatcher` with command-to-handler mappings.
- Initialize message consumption for commands.

## Distinction from Event Dispatchers

| Aspect | Command Dispatchers | Event Dispatchers |
| --- | --- | --- |
| -------- | -------------------- | -------------------- |
| **Builder** | `CommandHandlersBuilder` | `DomainEventHandlersBuilder` |
| **Dispatcher** | `CommandDispatcher` | `DomainEventDispatcher` |
| **Routing key** | Channel (`from_channel`) | Destination (`for_aggregate_type`) |
| **Producer** | Required (for replies) | Optional |

## Architecture Overview

### Channels vs Destinations

Commands use **channels** for routing, while events use **destinations**:

```python
# constants.py - Command routing
COMMANDS_CHANNEL = "LabelProcessing"
COMMANDS_QUEUE = "label-processing-commands"

# constants.py - Event routing (for comparison)
FILES_DESTINATION = "files"
EVENTS_QUEUE = "iv-documents-ops-events"
```

### Unique Queues Per Dispatcher

Each dispatcher **must have its own unique queue**:

```
Service
├── label_processing/dispatcher.py  → COMMANDS_QUEUE
└── document_ops/dispatcher.py      → OPS_EVENTS_QUEUE
```

## Structure

- Implemented as factory functions returning configured `IMessageConsumer`.
- Use `CommandHandlersBuilder` to build handler mappings.
- Register handlers for specific channels.
- Configure unique queue name and initialize the dispatcher.
- Requires `IMessageProducer` for sending replies.

## Template Parameters

When using the template, replace these placeholders with your project-specific values:

- `{{ constants_module }}` - Module path for constants (e.g., `my_project.constants`)
- `{{ channel_name }}` - Channel constant for command routing (e.g., `COMMANDS_CHANNEL`)
- `{{ queue_name }}` - Unique queue constant for this dispatcher (e.g., `COMMANDS_QUEUE`)
- `{{ dispatcher_name }}` - Name identifier for this dispatcher (e.g., `label_processing`)
- `{{ command_imports }}` - Comma-separated list of command class names
- `{{ handler_imports }}` - Comma-separated list of handler function names
- `{{ command_handlers }}` - List of command handler mappings with `command_name` and `handler_name`

## Example

```python
import logging

from deps_pubsub.commands.consumer import CommandDispatcher, CommandHandlersBuilder
from deps_pubsub.messaging.consumer import IMessageConsumer
from deps_pubsub.messaging.producer import IMessageProducer

from my_project.constants import COMMANDS_CHANNEL, COMMANDS_QUEUE

__all__ = ["make_label_processing_dispatcher"]

_logger = logging.getLogger(__name__)

def make_label_processing_dispatcher(
    subscriber: IMessageConsumer,
    producer: IMessageProducer,
) -> IMessageConsumer:
    from .commands import StartLabelProcessing
    from .handlers import start_label_processing_command_handler

    commands_handlers = (
        CommandHandlersBuilder.from_channel(COMMANDS_CHANNEL)
        .on_message(StartLabelProcessing, start_label_processing_command_handler)
        .for_queue(COMMANDS_QUEUE)
        .build()
    )

    cd = CommandDispatcher(commands_handlers, subscriber, producer)
    cd.initialize()

    _logger.info("Start consuming commands....")

    return subscriber
```

## Multiple Commands per Channel

A single dispatcher can handle multiple commands from the same channel:

```python
commands_handlers = (
    CommandHandlersBuilder.from_channel(COMMANDS_CHANNEL)
    .on_message(StartLabelProcessing, start_label_processing_handler)
    .on_message(CancelLabelProcessing, cancel_label_processing_handler)
    .on_message(RetryLabelProcessing, retry_label_processing_handler)
    .for_queue(COMMANDS_QUEUE)
    .build()
)
```

## Testing Guidance

- Test that all expected handlers are registered.
- Verify the dispatcher has a unique queue configuration.
- Test dispatcher initialization and consumer setup.
- Verify correct channel constant is used for routing.

---

## Template

```python
import logging

from deps_pubsub.commands.consumer import CommandDispatcher, CommandHandlersBuilder
from deps_pubsub.messaging.consumer import IMessageConsumer
from deps_pubsub.messaging.producer import IMessageProducer

from {{ constants_module }} import {{ channel_name }}, {{ queue_name }}

__all__ = ["make_{{ dispatcher_name }}_dispatcher"]

_logger = logging.getLogger(__name__)

def make_{{ dispatcher_name }}_dispatcher(
    subscriber: IMessageConsumer,
    producer: IMessageProducer,
) -> IMessageConsumer:
    from .commands import {{ command_imports }}
    from .handlers import (
        {{ handler_imports }}
    )

    commands_handlers = (
        CommandHandlersBuilder.from_channel({{ channel_name }})
        {% for command_handler in command_handlers %}
        .on_message({{ command_handler.command_name }}, {{ command_handler.handler_name }})
        {% endfor %}
        .for_queue({{ queue_name }})
        .build()
    )

    cd = CommandDispatcher(commands_handlers, subscriber, producer)
    cd.initialize()

    _logger.info("Start consuming commands....")

    return subscriber
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ constants_module }}` | Module path for constants | `my_project.constants` |
| `{{ channel_name }}` | Channel constant for command routing | `COMMANDS_CHANNEL` |
| `{{ queue_name }}` | Unique queue constant for this dispatcher | `COMMANDS_QUEUE` |
| `{{ dispatcher_name }}` | Name identifier for this dispatcher | `label_processing` |
| `{{ command_imports }}` | Comma-separated list of command class names | `StartLabelProcessing, CancelLabelProcessing` |
| `{{ handler_imports }}` | Comma-separated list of handler function names | `start_label_processing_handler,\n        cancel_label_processing_handler` |
| `{{ command_handlers }}` | List of command handler mappings | `[{"command_name": "StartLabelProcessing", "handler_name": "start_label_processing_handler"}]` |
