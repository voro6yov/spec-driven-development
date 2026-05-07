---
name: domain-event-handlers
description: Domain Event Handlers pattern for processing domain events from pubsub queues. Use when translating domain events into application layer commands with dependency injection, error logging, and re-raising for retry.
user-invocable: false
disable-model-invocation: false
---

# Domain Event Handlers

Category: Handler Pattern

## Purpose

- Process domain events received from pubsub queues.
- Translate domain events into application layer commands.
- Handle errors and logging for event processing.

## Structure

- Implemented as functions decorated with `@inject` for dependency injection.
- Accept `DomainEventEnvelope[EventType]` as the first parameter.
- Use dependency injection to access application layer command objects.
- Include try-except blocks with error logging and re-raising.

## Template Parameters

When using the template, replace these placeholders with your project-specific values:

- `{{ application_module }}` - Module path for application layer (e.g., `my_project.application`)
- `{{ command_class_name }}` - Name of the command class to inject
- `{{ containers_module }}` - Module path for dependency injection containers (e.g., `my_project.containers`)
- `{{ containers_class_name }}` - Name of the containers class (e.g., `Containers`)
- `{{ container_property_name }}` - Property name on containers for the command instance
- `{{ event_class_name }}` - Name of the event class to handle
- `{{ event_import_module }}` - Module path for event import (e.g., `my_project.domain`) — optional, defaults to `.events` if not provided
- `{{ handler_function_name }}` - Name of the handler function
- `{{ command_param_name }}` - Parameter name for the injected command
- `{{ command_method_name }}` - Method name on command to call
- `{{ command_method_params }}` - Parameters to pass to command method

**Event Import:** Use `event_import_module` for internal domain events (from `my_project.domain`). Omit it for external events (imports from local `.events` module).

## Usage Patterns

- Each handler function is dedicated to a single event type.
- Handlers extract the event from the envelope and call appropriate command methods.
- Error handling logs the error with context and re-raises to allow retry mechanisms.
- Handlers are registered in dispatchers using `DomainEventHandlersBuilder`.

## Example

```python
import logging

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
            classified=event.classified,
        )

    except Exception as e:
        logger.error(f"Error processing FileClassificationSucceeded event: {e}.", exc_info=True)
        raise
```

## Testing Guidance

- Test handlers with valid event envelopes and verify command calls.
- Test error handling paths to ensure exceptions are logged and re-raised.
- Verify that correct command methods are called with correct parameters.

---

## Template

```python
import logging

from dependency_injector.wiring import Provide, inject
from deps_pubsub.events.subscriber.domain_event_envelope import DomainEventEnvelope

from {{ application_module }} import {{ command_class_name }}
from {{ containers_module }} import {{ containers_class_name }}
{% if event_import_module %}
from {{ event_import_module }} import {{ event_class_name }}
{% else %}
from .events import {{ event_class_name }}
{% endif %}

logger = logging.getLogger(__name__)

@inject
def {{ handler_function_name }}(
    envelope: DomainEventEnvelope[{{ event_class_name }}],
    {{ command_param_name }}: {{ command_class_name }} = Provide[{{ containers_class_name }}.{{ container_property_name }}],
) -> None:
    event = envelope.event

    try:
        {{ command_param_name }}.{{ command_method_name }}(
            {{ command_method_params }}
        )

    except Exception as e:
        logger.error(f"Error processing {{ event_class_name }} event: {e}.", exc_info=True)
        raise
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ application_module }}` | Module path for application layer | `my_project.application` |
| `{{ command_class_name }}` | Name of the command class to inject | `DocumentCommands` |
| `{{ containers_module }}` | Module path for dependency injection containers | `my_project.containers` |
| `{{ containers_class_name }}` | Name of the containers class | `Containers` |
| `{{ container_property_name }}` | Property name on containers for the command instance | `document_commands` |
| `{{ event_class_name }}` | Name of the event class to handle | `FileClassificationSucceeded` |
| `{{ event_import_module }}` | Module path for event import (optional) | `my_project.domain` - omit for external events |
| `{{ handler_function_name }}` | Name of the handler function | `file_classification_succeeded_handler` |
| `{{ command_param_name }}` | Parameter name for the injected command | `document_commands` |
| `{{ command_method_name }}` | Method name on command to call | `on_file_classification_succeeded` |
| `{{ command_method_params }}` | Parameters to pass to command method | `file_id=event.id, |

tenant_id=event.tenant_id` |
