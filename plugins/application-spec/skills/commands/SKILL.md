---
name: commands
description: Commands pattern for application services. Use when implementing write operations (create, update, delete) for domain aggregates with transaction management, domain event publishing, and command dispatching.
user-invocable: false
disable-model-invocation: false
---

# Commands

Purpose: Handle write operations (create, update, delete) for domain aggregates with transaction management and event publishing

## Purpose

- Handle write operations (create, update, delete) for domain aggregates.
- Coordinate transactions, domain event publishing, and command dispatching.
- Encapsulate business workflows that span multiple aggregates or external systems.

## Structure

- Accept `AbstractUnitOfWork`, `DomainEventPublisher`, `CommandProducer` as core dependencies.
- Accept Protocol-based interfaces (e.g., `ICanUpdateLineItems`) for external system interactions.
- Use `@retry_on_transaction_error()` decorator on all methods that modify state.
- Maintain a logger instance for operation tracking.

**Note on External Dependencies**: The template includes imports for pubsub infrastructure (CommandProducer, DomainEventPublisher). You can customize the module path via the `pubsub_module` template variable, or it defaults to `deps_pubsub`. If your project uses different event/command infrastructure, provide the appropriate module path.

## Behavior checklist

- Wrap aggregate operations in `with self._uow:` context manager.
- Load aggregates from repository or create new instances using domain factories.
- Invoke domain methods on aggregates to perform state changes.
- Save aggregates via `self._uow.{aggregate_plural}.save(aggregate)`.
- Commit transaction with `self._uow.commit()`.
- Publish domain events via `_publish_events()` helper after commit.
- Send commands via `_send_commands()` helper if aggregate emits commands.
- Log successful operations with appropriate detail level.
- Raise domain exceptions (e.g., `AggregateNotFound`) when aggregates are missing.

## Testing guidance

- Write integration tests that verify transaction boundaries, event publishing, and command dispatching.
- Use fakes for Protocol interfaces to isolate external system interactions.
- Verify aggregate state changes and emitted events match expected outcomes.

---

## Template

```python
import logging

{% if pubsub_module %}
from {{ pubsub_module }}.commands.producer import CommandProducer
from {{ pubsub_module }}.events.publisher import DomainEventPublisher
{% else %}
from deps_pubsub.commands.producer import CommandProducer
from deps_pubsub.events.publisher import DomainEventPublisher
{% endif %}

{% if constants_module %}
from {{ constants_module }} import {{ aggregate_destination }}{% if default_tenant_id %}, {{ default_tenant_id }}{% endif %}
{% else %}
{{ aggregate_destination }} = "{{ aggregate_destination_value }}"
{% if default_tenant_id %}
{{ default_tenant_id }} = "{{ default_tenant_id_value }}"
{% endif %}
{% endif %}
from {{ domain_module }} import {{ aggregate_name }}, {{ aggregate_not_found }}
from {{ infrastructure_module }}.unit_of_work import AbstractUnitOfWork

from {{ retry_module }} import retry_on_transaction_error
{% for interface in interfaces %}
{% if interface.module %}
from {{ interface.module }} import {{ interface.name }}
{% endif %}
{% endfor %}

__all__ = ["{{ commands_class_name }}"]

class {{ commands_class_name }}:
    def __init__(
        self,
        unit_of_work: AbstractUnitOfWork,
        domain_event_publisher: DomainEventPublisher,
        command_producer: CommandProducer,
{% for interface in interfaces %}
        {{ interface.param_name }}: {{ interface.name }},
{% endfor %}
    ) -> None:
        self._uow = unit_of_work

        self._domain_event_publisher = domain_event_publisher
        self._command_producer = command_producer

{% for interface in interfaces %}
        self._{{ interface.param_name }} = {{ interface.param_name }}
{% endfor %}

        self._logger = logging.getLogger(self.__class__.__name__)

    @retry_on_transaction_error()
    def {{ method_name }}(
        self,
        {{ aggregate_id_param }}: str,
{% if tenant_param %}
        {{ tenant_param }}: str{% if default_tenant_id %} = {{ default_tenant_id }}{% endif %},
{% endif %}
    ) -> {{ aggregate_name }}:
        with self._uow:
            {{ aggregate_var }} = self._find_{{ aggregate_var }}({{ aggregate_id_param }}{% if tenant_param %}, {{ tenant_param }}{% endif %})

            {{ aggregate_var }}.{{ domain_method }}()

            self._uow.{{ aggregate_plural }}.save({{ aggregate_var }})
            self._uow.commit()

            self._publish_events({{ aggregate_var }})
            self._send_commands({{ aggregate_var }})

        self._logger.info("{{ aggregate_name }} with id %s is {{ action_description }}.", {{ aggregate_var }}.id)

        return {{ aggregate_var }}

    def _find_{{ aggregate_var }}(self, {{ aggregate_id_param }}: str{% if tenant_param %}, {{ tenant_param }}: str{% endif %}) -> {{ aggregate_name }}:
        if ({{ aggregate_var }} := self._uow.{{ aggregate_plural }}.{{ find_method }}({{ aggregate_id_param }}{% if tenant_param %}, {{ tenant_param }}{% endif %})) is None:
            raise {{ aggregate_not_found }}({{ aggregate_id_param }}{% if tenant_param %}, {{ tenant_param }}{% endif %})

        return {{ aggregate_var }}

    def _publish_events(self, {{ aggregate_var }}: {{ aggregate_name }}) -> None:
        self._domain_event_publisher.publish(
            aggregate_type={{ aggregate_destination }},
            aggregate_id={{ aggregate_var }}.id,
            domain_events={{ aggregate_var }}.events,
        )

    def _send_commands(self, {{ aggregate_var }}: {{ aggregate_name }}) -> None:
        for command in {{ aggregate_var }}.commands:
            self._command_producer.send(
                command.COMMAND_CHANNEL,
                command,
                command.REPLY_CHANNEL,
            )
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ commands_class_name }}` | Name of the commands class | `LoadCommands`, `ProfileCommands` |
| `{{ aggregate_name }}` | Domain aggregate class name | `Load`, `Profile` |
| `{{ aggregate_var }}` | Variable name for aggregate instance | `load`, `profile` |
| `{{ aggregate_plural }}` | Plural form for repository access | `loads`, `profiles` |
| `{{ aggregate_not_found }}` | Domain exception class | `LoadNotFound`, `ProfileNotFound` |
| `{{ aggregate_destination }}` | Event destination constant name | `LOAD_DESTINATION` |
| `{{ aggregate_destination_value }}` | Event destination value (if not using constants module) | `"loads"` |
| `{{ aggregate_id_param }}` | Parameter name for aggregate ID | `load_id`, `profile_id` |
| `{{ method_name }}` | Command method name | `start_receiving`, `update_status` |
| `{{ domain_method }}` | Domain method to call | `start_receiving()`, `update_status()` |
| `{{ action_description }}` | Log message description | `started receiving`, `updated` |
| `{{ find_method }}` | Repository find method | `load_of_id`, `profile_of_id` |
| `{{ domain_module }}` | Module path for domain imports | `tss_load_processing.domain` |
| `{{ infrastructure_module }}` | Module path for infrastructure | `tss_load_processing.infrastructure` |
| `{{ retry_module }}` | Module path for retry decorator | `..retry_transaction` |
| `{{ pubsub_module }}` | Optional module path for pubsub (defaults to `deps_pubsub`) | `deps_pubsub` |
| `{{ constants_module }}` | Optional module path for constants | `tss_load_processing.constants` |
| `{{ tenant_param }}` | Optional tenant/warehouse parameter name | `warehouse_id` |
| `{{ default_tenant_id }}` | Optional default tenant constant name | `DEFAULT_WAREHOUSE_ID` |
| `{{ default_tenant_id_value }}` | Optional default tenant value (if not using constants module) | `"default_warehouse"` |
| `{{ interfaces }}` | Optional list of interface objects with `name`, `param_name`, and optional `module` | `[{"name": "ICanStopConveyor", "param_name": "conveyor_client", "module": "..i_can_stop_conveyor"}]` |
