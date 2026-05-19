---
name: container-initialization
description: Container Initialization pattern for messaging applications. Use when initializing DI containers with configuration, resources, and dependency injection wiring.
user-invocable: false
disable-model-invocation: false
---

# Container Initialization

Category: Structural Guide

# Container Initialization

## Purpose

- Initialize the DI container with application settings.
- Load configuration from Pydantic settings.
- Initialize resources (database connections, message broker clients).
- Wire packages for dependency injection.

## Structure

- Function named `init_containers(settings)` returning configured container.
- Creates container instance with driver-specific settings.
- Loads configuration from Pydantic settings object.
- Initializes resources (triggers `Resource` providers).
- Wires packages that use `@inject` decorators.
- Sets any required context on broker client.

## Example

```python
# entrypoint.py
import logging

from my_project import api, messaging
from my_project.containers import Containers
from my_project.infrastructure.access_management import user
from my_project.settings import Settings

logger = logging.getLogger(__name__)

def init_containers(settings: Settings) -> Containers:
    # Create container with messaging driver settings
    containers = Containers(messaging_driver_settings=settings.messaging_driver_settings)
    
    # Load configuration from Pydantic settings
    containers.config.from_pydantic(settings)
    
    # Initialize resources (broker connections, etc.)
    containers.init_resources()
    
    # Wire packages that use @inject decorator
    containers.wire(
        packages=[api, messaging],
    )

    # Set user context for multi-tenant message handling
    containers.message_brokers.broker_client().user_context = user

    # Wire specific modules for sub-containers
    containers.core.wire(
        modules=[api.endpoints.service_info],
    )
    containers.datasources.wire(
        modules=[api.endpoints.healthcheck],
    )

    return containers
```

## Initialization Steps

### 1. Create Container

```python
containers = Containers(messaging_driver_settings=settings.messaging_driver_settings)
```

Pass any runtime dependencies that can't be configured via `config`.

### 2. Load Configuration

```python
containers.config.from_pydantic(settings)
```

Maps Pydantic settings to container configuration providers.

### 3. Initialize Resources

```python
containers.init_resources()
```

Triggers initialization of `Resource` providers (broker clients, connections).

### 4. Wire Packages

```python
containers.wire(packages=[api, messaging])
```

Enables `@inject` decorator in specified packages. Wire:

- `messaging` — for handler DI
- `api` — for endpoint DI

### 5. Set Context

```python
containers.message_brokers.broker_client().user_context = user
```

Set any runtime context needed by broker client (e.g., user context for multi-tenancy).

## Key Points

- **Order matters** — `init_resources()` before `wire()`, config before resources.
- **Wire packages, not modules** — wiring packages covers all submodules.
- **Resources are lazy** — only initialized when `init_resources()` is called.
- **Container is reusable** — same pattern for API server and dispatchers.

## Base Service Initialization

After container init, call `_base_service_init()` for common setup:

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

This handles:

- Observability instrumentation setup
- Messaging producer/consumer instrumentation

## Testing Guidance

- Test that container initializes without errors.
- Verify resources are properly initialized.
- Test wiring by checking `@inject` works in handlers.
- Mock external dependencies (broker, database) in tests.
