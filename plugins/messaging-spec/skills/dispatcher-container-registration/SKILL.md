---
name: dispatcher-container-registration
description: Dispatcher Container Registration pattern for wiring messaging dispatchers as DI singletons. Use when registering dispatcher factory functions in the root Containers class so dispatchers receive shared consumer/producer dependencies.
user-invocable: false
disable-model-invocation: false
---

# Dispatcher Container Registration

Category: Bootstrap Pattern

# Dispatcher Container Registration

## Purpose

- Register dispatcher factory functions as singletons in the DI container.
- Wire dispatcher dependencies (consumer, producer) through dependency injection.
- Enable dispatcher access throughout the application via container.

## Structure

- Dispatcher registered as `providers.Singleton` in the root `Containers` class.
- Factory function (e.g., `make_document_ops_dispatcher`) passed as first argument.
- `messaging.consumer` and `messaging.producer` passed as dependencies.
- Type hint as `IMessageConsumer` (the return type of dispatcher factory).

## Template Parameters

When using the template, replace these placeholders with your project-specific values:

- `{{ dispatcher_name }}` - Name identifier for this dispatcher (e.g., `document_ops`)
- `{{ dispatcher_factory }}` - Factory function name (e.g., `make_document_ops_dispatcher`)

## Prerequisites

Before registering a dispatcher:

1. Create the dispatcher factory in `messaging/<name>/dispatcher.py`
2. Export it from `messaging/__init__.py`
3. Ensure `Messaging` container provides `consumer` and `producer`

## Example

```python
# containers.py
from deps_pubsub.messaging.consumer import IMessageConsumer

from my_project.messaging import (
    make_document_ops_dispatcher,
    make_profile_ops_dispatcher,
    make_subject_extraction_dispatcher,
)

class Containers(containers.DeclarativeContainer):
    # ... other providers ...

    messaging: providers.Container[Messaging] = providers.Container(
        Messaging,
        config=config,
        message_brokers=message_brokers,
    )

    # Dispatcher registrations
    document_ops_dispatcher: providers.Singleton[IMessageConsumer] = providers.Singleton(
        make_document_ops_dispatcher,
        messaging.consumer,
        messaging.producer,
    )

    subject_extraction_dispatcher: providers.Singleton[IMessageConsumer] = providers.Singleton(
        make_subject_extraction_dispatcher,
        messaging.consumer,
        messaging.producer,
    )

    profile_ops_dispatcher: providers.Singleton[IMessageConsumer] = providers.Singleton(
        make_profile_ops_dispatcher,
        messaging.consumer,
        messaging.producer,
    )
```

## Key Points

- Each dispatcher is a **Singleton** — only one instance per container lifecycle.
- Dispatchers receive the **same** consumer/producer instances from the `Messaging` container.
- The factory function is called lazily when the dispatcher is first accessed.
- Type hint `IMessageConsumer` reflects the return type of dispatcher factories.

## Testing Guidance

- Verify dispatcher can be resolved from container.
- Test that factory function receives correct consumer/producer.
- Ensure singleton behavior — multiple accesses return same instance.

---

## Template

```python
{{ dispatcher_name }}_dispatcher: providers.Singleton[IMessageConsumer] = providers.Singleton(
    {{ dispatcher_factory }},
    messaging.consumer,
    messaging.producer,
)
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ dispatcher_name }}` | Name identifier for this dispatcher | `document_ops`, `profile_ops` |
| `{{ dispatcher_factory }}` | Factory function name | `make_document_ops_dispatcher` |
