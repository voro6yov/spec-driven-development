---
name: domain-event-handlers
description: Domain Event Handlers pattern for processing domain events from pubsub queues. Use when translating domain events into application layer commands with dependency injection, logging-and-acking domain exceptions (non-retryable), and re-raising other errors for retry.
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
- Include try-except blocks that log-and-ack domain exceptions (non-retryable) and re-raise other errors for retry.

## Template Parameters

When using the template, replace these placeholders with your project-specific values:

- `{{ application_module }}` - Module path for application layer (e.g., `my_project.application`)
- `{{ command_class_name }}` - Name of the command class to inject
- `{{ containers_module }}` - Module path for dependency injection containers (e.g., `my_project.containers`)
- `{{ domain_exceptions_module }}` - Module path for the shared domain exception base (e.g., `my_project.domain.shared.exceptions`)
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
- Error handling distinguishes two cases: a `DomainException` is deterministic (a replay against the same state fails identically), so it is logged at INFO and **swallowed** — the message is acked, never retried; any other exception is transient (DB/network/lock), so it is logged at ERROR with `exc_info` and **re-raised** to let the pubsub layer redeliver. The `DomainException` clause MUST precede the `Exception` clause, since the former is a subclass of the latter.
- Handlers are registered in dispatchers using `DomainEventHandlersBuilder`.

## Example

```python
import logging

from dependency_injector.wiring import Provide, inject
from deps_pubsub.events.subscriber.domain_event_envelope import DomainEventEnvelope

from my_project.application import DocumentCommands
from my_project.containers import Containers
from my_project.domain.shared.exceptions import DomainException

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

    except DomainException as e:
        logger.info(f"Skipping FileClassificationSucceeded event: {e}.")

    except Exception as e:
        logger.error(f"Error processing FileClassificationSucceeded event: {e}.", exc_info=True)
        raise
```

## Testing Guidance

- Test handlers with valid event envelopes and verify command calls.
- Test the domain-exception path: a handler whose service raises a `DomainException` logs at INFO and returns `None` (no re-raise — the message is acked). Test the transient path: any other exception is logged at ERROR and re-raised.
- Verify that correct command methods are called with correct parameters.

---

## Template

```python
import logging

from dependency_injector.wiring import Provide, inject
from deps_pubsub.events.subscriber.domain_event_envelope import DomainEventEnvelope

from {{ application_module }} import {{ command_class_name }}
from {{ containers_module }} import {{ containers_class_name }}
from {{ domain_exceptions_module }} import DomainException
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

    except DomainException as e:
        logger.info(f"Skipping {{ event_class_name }} event: {e}.")

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
| `{{ domain_exceptions_module }}` | Module path for the shared domain exception base | `my_project.domain.shared.exceptions` |
| `{{ container_property_name }}` | Property name on containers for the command instance | `document_commands` |
| `{{ event_class_name }}` | Name of the event class to handle | `FileClassificationSucceeded` |
| `{{ event_import_module }}` | Module path for event import (optional) | `my_project.domain` - omit for external events |
| `{{ handler_function_name }}` | Name of the handler function | `file_classification_succeeded_handler` |
| `{{ command_param_name }}` | Parameter name for the injected command | `document_commands` |
| `{{ command_method_name }}` | Method name on command to call | `on_file_classification_succeeded` |
| `{{ command_method_params }}` | Parameters to pass to command method | `file_id=event.id, |

tenant_id=event.tenant_id` |
