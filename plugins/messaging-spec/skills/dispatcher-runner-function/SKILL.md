---
name: dispatcher-runner-function
description: Dispatcher Runner Function pattern for messaging bootstrap. Use when defining an entry point that initializes the DI container, performs base service init, and starts a dispatcher's message consumption loop.
user-invocable: false
disable-model-invocation: false
---

# Dispatcher Runner Function

Category: Bootstrap Pattern

# Dispatcher Runner Function

## Purpose

- Provide an entry point function to start a dispatcher process.
- Initialize the DI container with settings.
- Perform base service initialization (instrumentation, etc.).
- Start the dispatcher's message consumption loop.

## Structure

- Function named `run_<dispatcher_name>_dispatcher()`.
- Loads settings from environment/configuration.
- Calls `init_containers(settings)` to initialize DI container.
- Calls `_base_service_init(containers)` for common initialization.
- Retrieves dispatcher from container and starts consuming.

## Template Parameters

When using the template, replace these placeholders with your project-specific values:

- `{{ dispatcher_name }}` - Name identifier for this dispatcher (e.g., `document_ops`)
- `{{ settings_class }}` - Settings class name (e.g., `Settings`)
- `{{ containers_class }}` - Containers class name (e.g., `Containers`)
- `{{ init_containers_func }}` - Container initialization function (e.g., `init_containers`)
- `{{ base_init_func }}` - Base initialization function (e.g., `_base_service_init`)

## Prerequisites

Before creating a runner:

1. Register dispatcher in `containers.py`
2. Implement `init_containers()` function
3. Implement `_base_service_init()` function (optional but recommended)

## Example

```python
# entrypoint.py
from my_project.containers import Containers
from my_project.settings import Settings

def run_document_ops_dispatcher() -> None:
    settings = Settings()
    containers: Containers = init_containers(settings)
    _base_service_init(containers)

    dispatcher = containers.document_ops_dispatcher()
    dispatcher.start_consuming()

def run_subject_extraction_dispatcher() -> None:
    settings = Settings()
    containers: Containers = init_containers(settings)
    _base_service_init(containers)

    dispatcher = containers.subject_extraction_dispatcher()
    dispatcher.start_consuming()

def run_profile_ops_dispatcher() -> None:
    settings = Settings()
    containers: Containers = init_containers(settings)
    _base_service_init(containers)

    dispatcher = containers.profile_ops_dispatcher()
    dispatcher.start_consuming()
```

## Base Service Initialization

The `_base_service_init()` function handles common setup:

```python
def _base_service_init(containers: Containers) -> None:
    if containers.config.instrumentation_enabled():
        logger.info("Instrumentation enabled.")
        from deps_observability_instrumentation import (
            instrument_messaging,
            setup_instrumentation,
        )

        setup_instrumentation()
        instrument_messaging(containers.messaging.producer(), containers.messaging.consumer())
```

## Key Points

- Each dispatcher runs in its **own process** — separate runner per dispatcher.
- Settings are loaded fresh for each process.
- Container initialization happens once per process.
- `start_consuming()` blocks and runs the message consumption loop.
- The function never returns during normal operation.

## Testing Guidance

- Test that runner initializes containers correctly.
- Verify dispatcher is retrieved from container.
- Mock `start_consuming()` in tests to avoid blocking.

---

## Template

```python
def run_{{ dispatcher_name }}_dispatcher() -> None:
    settings = {{ settings_class }}()
    containers: {{ containers_class }} = {{ init_containers_func }}(settings)
    {{ base_init_func }}(containers)

    dispatcher = containers.{{ dispatcher_name }}_dispatcher()
    dispatcher.start_consuming()
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ dispatcher_name }}` | Name identifier for this dispatcher | `document_ops`, `profile_ops` |
| `{{ settings_class }}` | Settings class name | `Settings` |
| `{{ containers_class }}` | Containers class name | `Containers` |
| `{{ init_containers_func }}` | Container initialization function | `init_containers` |
| `{{ base_init_func }}` | Base initialization function | `_base_service_init` |
