---
name: ops
description: Orchestration application-service template that coordinates domain-service (<<Service>>) invocations rather than single-aggregate CRUD. Use when implementing a free-form ops service whose methods fork per-method between transactional (UoW + retry + publish) and pure-coordinator shapes.
user-invocable: false
disable-model-invocation: false
---

# Ops

Purpose: Coordinate domain-service (`<<Service>>`) invocations across one bound aggregate, forking per method between transactional and pure-coordinator shapes

## Purpose

- Orchestrate domain-service (`<<Service>>`) calls, branch on their results, and return a free result type (DTO, value object, or `None`).
- Bind to one aggregate's application package, sitting next to `<Aggregate>Commands` / `<Aggregate>Queries`, but as a free-form, domain-meaningful class with **no** `Ops` / `Service` / `Commands` suffix.
- Relax the aggregate-CRUD invariants: no forced "return the aggregate", repository optional, several services allowed per aggregate (name-discriminated by `<op-name>`).

## Structure

- Class name `{{ service_class }}` is the verbatim diagram class name — free-form, **no suffix**.
- Inject collaborators **in this order**: optional `unit_of_work: AbstractUnitOfWork` (only when any method persists), then optional message publishers, then domain services, then external interfaces.
- Repositories are reached through `self._uow.<plural>` — never injected directly. A pure coordinator declares no repositories and no UoW.
- Use `@retry_on_transaction_error()` only on methods that persist.
- Maintain a logger instance for operation tracking.

**Note on external dependencies**: imports for pubsub infrastructure appear only when a method uses them — `DomainEventPublisher` when a method publishes events, `CommandProducer` when a method dispatches commands; the UoW import (`AbstractUnitOfWork`) appears only when a method persists. Domain services and external interfaces are imported from their declared modules — there is no built-in pubsub/constants block as in `commands`.

## Behavior checklist

- Decide the shape **per method** — the same "mutating?" decision `commands-implementer` makes.
- **Transactional method** (flow persists): emit `@retry_on_transaction_error()`, wrap the body in `with self._uow:`, call `self._uow.commit()` inside the context, then optionally publish, then emit the mandatory `self._logger.info(...)` line, then a free `return`.
- **Pure-coordinator method** (flow does not persist): emit none of the UoW / retry / commit / publish machinery — just the orchestration body (service calls, branching), then a free `return`. No forced logger line.
- Load aggregates from `self._uow.<plural>` and raise `{{ aggregate_not_found }}` when missing; mutate via domain methods; save via `self._uow.<plural>.save(...)`.
- Publish domain events only when the method emits them (optional `self._publish_events(...)`); dispatch commands only when the method emits them (optional `self._send_commands(...)`).
- Emit `return <expr>` **only** when the declared return type is non-None — there is **no** forced "return the aggregate" invariant.

## Testing guidance

- Write integration tests that verify the orchestration flow: domain-service calls, branching outcomes, and (for transactional methods) transaction boundaries and event publishing.
- Use fakes for domain services and external interfaces to isolate the service from external systems and capture calls for assertion.
- Verify the returned result matches the expected outcome; for pure coordinators, assert no persistence side effects occur.

---

## Template

```python
import logging
{% if has_event_publisher %}
from {{ pubsub_module }}.events.publisher import DomainEventPublisher
{% endif %}
{% if has_command_producer %}
from {{ pubsub_module }}.commands.producer import CommandProducer
{% endif %}
from {{ domain_module }} import {{ aggregate_name }}, {{ aggregate_not_found }}
{% if uses_uow %}
from {{ infrastructure_module }}.unit_of_work import AbstractUnitOfWork
from {{ retry_module }} import retry_on_transaction_error
{% endif %}
{% for s in domain_services %}
from {{ s.module }} import {{ s.name }}
{% endfor %}
{% for e in external_interfaces %}
from {{ e.module }} import {{ e.name }}
{% endfor %}

__all__ = ["{{ service_class }}"]

class {{ service_class }}:                       # e.g. MappingRulesInferencing
    def __init__(
        self,
{% if uses_uow %}
        unit_of_work: AbstractUnitOfWork,
{% endif %}
{% for p in publishers %}
        {{ p.attr }}: {{ p.name }},
{% endfor %}
{% for s in domain_services %}
        {{ s.attr }}: {{ s.name }},
{% endfor %}
{% for e in external_interfaces %}
        {{ e.attr }}: {{ e.name }},
{% endfor %}
    ) -> None:
{% if uses_uow %}
        self._uow = unit_of_work
{% endif %}
{% for p in publishers %}
        self._{{ p.attr }} = {{ p.attr }}
{% endfor %}
{% for s in domain_services %}
        self._{{ s.attr }} = {{ s.attr }}
{% endfor %}
{% for e in external_interfaces %}
        self._{{ e.attr }} = {{ e.attr }}
{% endfor %}

        self._logger = logging.getLogger(self.__class__.__name__)

    # --- transactional method (flow persists) ---
    @retry_on_transaction_error()
    def {{ method }}(self, ...) -> {{ free_return_type }}:
        with self._uow:
            # orchestration body: service calls, branching, load/mutate/save
            self._uow.commit()

        # optional self._publish_events(...)
        self._logger.info(...)

        return {{ result }}            # only if return type is non-None

    # --- pure coordinator (flow does not persist) ---
    def {{ method }}(self, ...) -> {{ free_return_type }}:
        # orchestration body: service calls, branching
        return {{ result }}            # only if return type is non-None

    # --- helpers: emitted only when a transactional method publishes / dispatches ---
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
| `{{ service_class }}` | Free-form ops service class name (verbatim diagram class, **no suffix**) | `MappingRulesInferencing`, `SubjectTagging` |
| `{{ domain_module }}` | Module path for domain imports (aggregate + not-found exception) | `conversion_reqs.domain` |
| `{{ aggregate_name }}` | Domain aggregate class name (the bound aggregate) | `ConversionReqs`, `Load` |
| `{{ aggregate_not_found }}` | Domain not-found exception raised when an aggregate is missing | `ConversionReqsNotFound`, `LoadNotFound` |
| `{{ retry_module }}` | Module path for the retry decorator (imported only when `uses_uow`) | `..retry_transaction` |
| `{{ infrastructure_module }}` | Module path for infrastructure (UoW import, only when `uses_uow`) | `conversion_reqs.infrastructure` |
| `{{ pubsub_module }}` | Module path for pubsub (imported only when `any_method_publishes`) | `deps_pubsub` |
| `{{ uses_uow }}` | True when **any** method persists — gates the UoW field, import, and retry import | `true` / `false` |
| `{{ has_event_publisher }}` | True when `DomainEventPublisher` is a dependency — gates its import and the `_publish_events` helper | `true` / `false` |
| `{{ has_command_producer }}` | True when `CommandProducer` is a dependency — gates its import and the `_send_commands` helper | `true` / `false` |
| `{{ publishers }}` | List of message-publisher objects with `attr` and `name` (`DomainEventPublisher` and/or `CommandProducer`) | `[{"attr": "domain_event_publisher", "name": "DomainEventPublisher"}, {"attr": "command_producer", "name": "CommandProducer"}]` |
| `{{ aggregate_var }}` | snake_case variable holding the aggregate instance in helper bodies | `conversion_reqs`, `load` |
| `{{ aggregate_destination }}` | Event destination constant name used by `_publish_events` | `CONVERSION_REQS_DESTINATION` |
| `{{ domain_services }}` | List of domain-service (`<<Service>>`) collaborator objects with `attr`, `name`, `module` | `[{"attr": "rules_inference", "name": "RulesInference", "module": "..rules_inference"}]` |
| `{{ external_interfaces }}` | List of external interface (`I…`) collaborator objects with `attr`, `name`, `module` | `[{"attr": "can_notify_user_by_email", "name": "ICanNotifyUserByEmail", "module": "..i_can_notify_user_by_email"}]` |
| `{{ method }}` | Orchestration method name | `infer`, `preview` |
| `{{ free_return_type }}` | Declared return type, verbatim — DTO, value object, or `None` (no return-aggregate invariant) | `MappingRules`, `InferencePreview`, `None` |
| `{{ result }}` | Expression returned by the flow's final "Return …" step — emitted **only** when `free_return_type` is non-None | `inference.rules`, `preview` |
