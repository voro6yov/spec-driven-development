---
name: event-tables-template
description: Reference template for the Events to Consume table (Table 2) of a messaging consumer input spec. Load when authoring or reviewing the events inventory of a consumer — covers column shape, per-column casing rules, ordering convention, the empty-consumer placeholder, and a worked example.
when_to_use: Authoring or reviewing the subscribed events table of a messaging consumer; consumer event inventory; Table 2 ordering or empty-state placeholder; binding events to <AggregateRoot>Commands.on_<event_snake> handlers.
user-invocable: false
---

# Event Tables Template — Events to Consume

## Purpose

Defines the canonical shape of **Table 2: Events to Consume** of a messaging consumer input spec. Table 2 sits directly after Table 1 (see `consumer-spec-template`) and enumerates every event the consumer subscribes to, binding each one to a method on an existing application-service command class (`<AggregateRoot>Commands`) in **this** service.

Commands the consumer dispatches or replies it emits are out of scope here — Table 2 covers the event inventory only. A consumer that subscribes to zero events (commands-only consumer) replaces the entire table body with a single placeholder line; see *Empty state* below.

## Placement

- One Table 2 per consumer, immediately after Table 1.
- Heading is always exactly `### Table 2: Events to Consume`.
- No per-source or per-type sub-tables — every event the consumer subscribes to lives in this one table, regardless of source.

## Table 2 layout

| Event Name | Type | Source Destination | Command Class | Command Method |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## Empty state

When the consumer subscribes to zero events (commands-only consumer), replace the table body with the literal placeholder:

```markdown
### Table 2: Events to Consume

*No events consumed by this consumer.*
```

The italic line is the entire content of the section — never mix it with a real table, never delete the heading. Always keep Table 2 present so every consumer spec has the same shape.

## Columns

### Event Name

- **Format:** PascalCase, **no backticks**. Past-tense verb form preferred (the event names a state transition that has already occurred).
- **Traceability:** Recommended (not required) to match the published event class name in the source service so authors can grep for it. When the wire-format name diverges from the source class name, document the deviation in the consumer spec prose around Table 2.
- **Examples:** ProfileSubmitted, FileUploaded, OCRReportGenerated, DocumentSkipped
- **Counter-examples:** `ProfileSubmitted` (wrong delimiter — Event Name is rendered bare; the backticked form here is the *counter-example*, not the correct rendering), profile_submitted (wrong case — snake_case is reserved for Command Method), profile-submitted (kebab-case is reserved for queue names), Profile Submitted Event (free-form label with whitespace and trailing `Event` suffix), Submit (verb, not past-tense), CreateProfile (imperative — that's a command, not an event)

### Type

- **Format:** Backticked literal. Exactly one of `` `external` `` or `` `internal` `` — closed two-value vocabulary.
- **Vocabulary:**
    - `external` — published by another service. The Source Destination is an aggregate type in that other service.
    - `internal` — domain event emitted within this service. The Source Destination is an aggregate type in this service.
- **Examples:** `external`, `internal`
- **Counter-examples:** external (missing backticks), `EXTERNAL` / `External` (must be lowercase), `domain` / `system` / `replay` / `integration` (vocabulary is closed — only `external` and `internal`), `external/internal` (one row carries exactly one Type — split into two rows if a single Event Name is genuinely consumed under both classifications)

### Source Destination

- **Format:** PascalCase, **no backticks**. The aggregate root class name of the publisher — singular or plural matches the actual class name in the source service.
- **For `external` events:** the aggregate type in the other service that emits the event.
- **For `internal` events:** the aggregate type in this service that emits the event.
- **Examples:** Profiles, File, Document, OCRReport
- **Counter-examples:** `Profiles` (wrong delimiter — Source Destination is rendered bare like Event Name; the backticked form here is the *counter-example*, not the correct rendering), profiles (must be PascalCase), profile-service (a service is not an aggregate — name the aggregate, not the service), Profiles/Files (one row carries exactly one source — split into multiple rows if a single Event Name is genuinely emitted by two distinct aggregates)

### Command Class

- **Format:** PascalCase, **in backticks**. Must be `<AggregateRoot>Commands` — the application-service class in **this** service that owns the handler. The aggregate referenced is the one in this service whose state changes in response to the event, which need not match the Source Destination.
- **Examples:** `` `ProfileCommands` ``, `` `FileCommands` ``, `` `DocumentCommands` ``
- **Counter-examples:** ProfileCommands (missing backticks), `profile_commands` (wrong case — application-service classes are PascalCase), `ProfileService` (suffix must be exactly `Commands`), `ProfileCommandHandler` (no `Handler` suffix — the binding is to the application service, not a handler class), `ProfileQueries` (queries cannot consume events — Command Class is always the `*Commands` side)

### Command Method

- **Format:** snake_case, **in backticks**. Must be `on_<event_name_snake_case>` — the handler method on the Command Class.
- **Derivation:** Lowercase the Event Name and insert `_` at each PascalCase boundary. Treat consecutive uppercase letters as a single acronym token: `OCRReportGenerated` → `on_ocr_report_generated`, `ProfileSubmitted` → `on_profile_submitted`.
- **Existence requirement:** The method must already exist on the named `<AggregateRoot>Commands` class before the row is considered ready. If the method does not exist yet, the row is provisional.
- **Examples:** `` `on_profile_submitted` ``, `` `on_file_uploaded` ``, `` `on_ocr_report_generated` ``, `` `on_document_skipped` ``
- **Counter-examples:** `on_ProfileSubmitted` (must be snake_case), `handle_profile_submitted` / `process_profile_submitted` (prefix must be exactly `on_`), `on_profile_submitted_event` (no trailing `_event` — already implied by the binding), on_profile_submitted (missing backticks), `_on_profile_submitted` (no leading underscore — handler methods are public)

## Row ordering

Rows are grouped by Type and alphabetized within each group:

1. All rows with Type `external`, alphabetical by Event Name.
2. All rows with Type `internal`, alphabetical by Event Name.

Both groups live in the same Markdown table — no blank separator row, no inline group header. If one of the two types has zero rows, that group is simply absent. The ordering is deterministic so two authors regenerating Table 2 from the same source converge on byte-identical output.

## Worked example

`profile_reconciliation` consumer in the `clients` service:

```markdown
### Table 2: Events to Consume

| Event Name | Type | Source Destination | Command Class | Command Method |
| --- | --- | --- | --- | --- |
| FileUploaded | `external` | File | `ProfileCommands` | `on_file_uploaded` |
| ProfileSubmitted | `external` | Profiles | `ProfileCommands` | `on_profile_submitted` |
| DocumentSkipped | `internal` | Document | `ProfileCommands` | `on_document_skipped` |
```

The two external rows come first, alphabetized by Event Name (`FileUploaded` before `ProfileSubmitted`); the single internal row follows. Every Command Class in this consumer is `ProfileCommands` because reconciliation mutates the `Profile` aggregate in this service — the Source Destination identifies the publisher, while the Command Class identifies the local aggregate whose state responds.

## Validation checklist

### Placement

- [ ] Table 2 sits directly after Table 1 in the consumer spec
- [ ] Heading is exactly `### Table 2: Events to Consume`
- [ ] Exactly one Table 2 per consumer — no per-source or per-type sub-tables
- [ ] Empty consumers use `*No events consumed by this consumer.*` as the entire body, never an empty header-only table and never an omitted heading

### Table 2 — Events to Consume

- [ ] Every row has all five columns filled — no empty cells, no `N/A`, no em dashes
- [ ] Event Name is PascalCase with no backticks; past-tense verb form; one Event Name per row
- [ ] Type is exactly `` `external` `` or `` `internal` `` — backticked, lowercase, closed vocabulary; one Type per row
- [ ] Source Destination is a PascalCase aggregate root class name with no backticks; one source per row
- [ ] Command Class is `` `<AggregateRoot>Commands` `` — backticked, PascalCase, exact `Commands` suffix
- [ ] Command Method is `` `on_<event_name_snake_case>` `` — backticked, snake_case, exact `on_` prefix, no `_event` suffix
- [ ] Command Method matches the snake_case derivation of Event Name (acronym runs collapse into one token)
- [ ] Command Method exists on the named Command Class (or the row is flagged as provisional)
- [ ] Rows are ordered: external block (alphabetical by Event Name) then internal block (alphabetical by Event Name); no separator row between groups
