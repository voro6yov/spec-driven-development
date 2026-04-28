---
name: commands-dependencies-template
description: Commands Dependencies Template for the Dependencies section of a command application service spec. Auto-invoke after the class diagram exists, when authoring the Dependencies section of a `<AggregateRoot>Commands` spec.
user-invocable: false
disable-model-invocation: false
---

# Commands Dependencies Template

A command application service is named `<AggregateRoot>Commands` (see
`commands-specification-template` for the parent spec). It declares its
collaborators in three sections, **rendered in this order**:

1. **Repositories**
2. **Domain Services**
3. **External Interfaces**

Always render all three sections — if a category has no entries, write
`_None_` under the heading.

The three categories differ in how they appear in the class diagram:

| Category | Diagram link from `<AggregateRoot>Commands` |
| --- | --- |
| Repository | `--() Command<AggregateRoot>Repository : uses` (lollipop) |
| Domain Service | `--() <ServiceClass> : uses` (lollipop) |
| External Interface | `--> <IInterfaceClass> : uses` (plain arrow, separate class node) |

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
Use the plain class name.

## External Interfaces

List one bullet per external interface the command service depends on; a
service may declare more than one. External interfaces are declared on the
application service as private attributes
(`-<interface_name>: <IInterfaceClass>`, e.g.
`-can_upload_file: ICanUploadFile`). Unlike domain services, they appear in
the diagram as separate class nodes linked with a plain `-->` arrow. Use
the plain class name as it appears in the diagram.

---

## Skeleton

```markdown
## Repositories

| Repository | UoW attribute |
| --- | --- |
| Command{AggregateRoot}Repository | `uow.{attr}` |

## Domain Services

- {ServiceClass}

## External Interfaces

_None_
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

- OrderPricingService
- InventoryReservationService

## External Interfaces

- IPaymentGateway
- IEmailNotifier
```
