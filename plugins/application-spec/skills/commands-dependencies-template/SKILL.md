---
name: commands-dependencies-template
description: Commands Dependencies Template for the Dependencies section of a command application service spec. Auto-invoke after the class diagram exists, when authoring the Dependencies section of a `<AggregateRoot>Commands` spec.
user-invocable: false
disable-model-invocation: false
---

# Commands Dependencies Template

A command application service is named `<AggregateRoot>Commands`. It declares its
collaborators in four sections, **rendered in this order**:

1. **Repositories**
2. **Domain Services**
3. **External Interfaces**
4. **Message Publishers**

Always render all four sections — if a category has no entries, write
`_None_` under the heading.

The four categories differ in how they appear in the class diagram:

| Category | Diagram link from `<AggregateRoot>Commands` |
| --- | --- |
| Repository | `--() Command<AggregateRoot>Repository : uses` (lollipop) |
| Domain Service | `--() <ServiceClass> : uses` (lollipop) |
| External Interface | `--> <IInterfaceClass> : uses` (plain arrow, separate class node) |
| Message Publisher | `--() DomainEventPublisher : uses` or `--() CommandProducer : uses` (lollipop) |

---

## Repositories

List one row per repository the command service depends on; a service may
declare more than one. Repositories are declared on the application service
as private attributes
(`-command_<aggregate_root>_repository: Command<AggregateRoot>Repository`,
where `<aggregate_root>` is the aggregate root name in `snake_case` singular
and `<AggregateRoot>` is the same name in `PascalCase`). Use the class name
as it appears in the diagram (with the `Command` prefix) and the matching
UoW attribute the command body will read it from.

## Domain Services

List one bullet per domain service the command service depends on; a
service may declare more than one. Domain services are declared on the
application service as private attributes
(`-<service_name>: <ServiceClass>`, e.g. `-subject_detection: SubjectDetection`).
The attribute name is **read from the diagram** — the
`<AggregateRoot>Commands` class block must contain a private member
declaration `-<service_name>: <ServiceClass>` whose type matches the
linked target class. Render each entry as `- <service_name>: <ServiceClass>`.

## External Interfaces

List one bullet per external interface the command service depends on; a
service may declare more than one. External interfaces are declared on the
application service as private attributes
(`-<interface_name>: <IInterfaceClass>`, e.g.
`-can_upload_file: ICanUploadFile`). Unlike domain services, they appear in
the diagram as separate class nodes linked with a plain `-->` arrow. The
attribute name is **read from the diagram** — the `<AggregateRoot>Commands`
class block must contain a private member declaration
`-<interface_name>: <IInterfaceClass>` whose type matches the linked target
class. Render each entry as `- <interface_name>: <IInterfaceClass>`.

## Message Publishers

List one bullet per message publisher the command service depends on; a
service may declare more than one. Message publishers are declared on the
application service as private attributes following the same convention as
domain services (`-<publisher_name>: <PublisherClass>`, e.g.
`-domain_event_publisher: DomainEventPublisher` or
`-command_producer: CommandProducer`).

The publisher class name **must be exactly one of**:

- `DomainEventPublisher` — emits domain events to a message bus.
- `CommandProducer` — sends commands to other bounded contexts.

Any other class linked via lollipop is a Domain Service, not a Message
Publisher.

---

## Skeleton

```markdown
## Repositories

| Repository | UoW attribute |
| --- | --- |
| Command{AggregateRoot}Repository | `uow.{attr}` |

## Domain Services

- {service_name}: {ServiceClass}

## External Interfaces

_None_

## Message Publishers

- {DomainEventPublisher | CommandProducer}
```

---

## Filled example

```markdown
## Repositories

| Repository | UoW attribute |
| --- | --- |
| CommandOrderRepository | `uow.orders` |
| CommandCustomerRepository | `uow.customers` |

## Domain Services

- order_pricing: OrderPricingService
- inventory_reservation: InventoryReservationService

## External Interfaces

- payment_gateway: IPaymentGateway
- email_notifier: IEmailNotifier

## Message Publishers

- DomainEventPublisher
- CommandProducer
```
