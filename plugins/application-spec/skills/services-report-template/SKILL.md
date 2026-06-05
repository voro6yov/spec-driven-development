---
name: services-report-template
description: Services Report Template for the `<stem>.application/services.md` sibling file produced by `services-finder`. Auto-invoke when authoring or validating the services report for an application package.
user-invocable: false
disable-model-invocation: false
---

# Services Report Template

The services report enumerates every collaborator that the application
layer must wire up beyond repositories and message publishers. It is the
single source of truth consumed by downstream stub implementers, fake
implementers, DI container wirers, and conftest fixture writers.

Per `application-spec:naming-conventions`, the report is written to
`<stem>.application/services.md` — inside the per-plugin folder next to
the **domain diagram**, not as a flat sibling.

A *service* is a single concrete class that will (eventually) implement
one or more interfaces. Services are grouped **by collaborator attribute
name**: every `- <attr_name>: <InterfaceClass>` bullet that appears
under `### Domain Services` or `### External Interfaces` in any command
or query merged spec, with the same `<attr_name>`, belongs to the same
service.

## Service identifier

The service identifier is the `<attr_name>` converted to `PascalCase`
(e.g., `payment_gateway` → `PaymentGateway`,
`can_upload_file` → `CanUploadFile`). This identifier is what stub
implementers, fake implementers, and DI wirers will use as the class
name and binding key.

## Classification

Each service is classified as **domain** or **external**:

- `domain` — every interface contributed by this attr name appears
  under `### Domain Services` in the source specs.
- `external` — every interface contributed by this attr name appears
  under `### External Interfaces` in the source specs.

If the same attr name contributes interfaces from both subsections
across specs, treat it as a spec error and fail.

## Required structure

Each service section contains a metadata bullet list. Render one
`## <ServiceIdentifier>` section per service, sorted alphabetically by
identifier:

```markdown
# Services

## <ServiceIdentifier>

- **Attr name:** `<attr_name>`
- **Classification:** <domain | external>
- **Interfaces:**
  - <InterfaceClassA>
  - <InterfaceClassB>
- **Consumers:**
  - <AggregateRoot>Commands
  - <AggregateRoot>Queries
```

Within a service:

- `Interfaces` lists every interface class contributed by this attr name
  across all specs, deduped, sorted alphabetically.
- `Consumers` lists every application service class that injects
  this attr name, deduped, sorted alphabetically. A consumer is any
  application-service class — `<AggregateRoot>Commands`,
  `<AggregateRoot>Queries`, or a free-form ops orchestration class
  (e.g. `MappingRulesInferencing`).

If no services are found, write only:

```markdown
# Services

_None_
```

## Filled example

```markdown
# Services

## CanUploadFile

- **Attr name:** `can_upload_file`
- **Classification:** external
- **Interfaces:**
  - ICanUploadFile
- **Consumers:**
  - PhotoCommands

## SubjectDetection

- **Attr name:** `subject_detection`
- **Classification:** domain
- **Interfaces:**
  - SubjectDetection
- **Consumers:**
  - PhotoCommands
  - PhotoQueries
```
