---
name: event-tables-template
description: Reference template for the Events to Consume table (Table 2) of a messaging consumer input spec.
when_to_use: Authoring or reviewing the subscribed events table of a messaging consumer; consumer event inventory; Table 2 ordering or empty-state placeholder; binding events to <AggregateRoot>Commands.on_<event_snake> handlers.
user-invocable: false
---

# Event Tables Template — Events to Consume

## Purpose

Defines the canonical shape of **Table 2: Events to Consume** of a messaging consumer input spec. Table 2 sits directly after Table 1 (see `consumer-spec-template`) and enumerates every event the consumer subscribes to, binding each one to a method on an existing application service in **this** service — either a `<AggregateRoot>Commands` class (method `on_<event>`) or a free-form **ops** orchestration service (any method name). The `Command Class` / `Command Method` column headers are kept literal for both kinds; read them as "Handler Class" / "Handler Method".

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

### Command Class (Handler Class)

- **Format:** PascalCase, **in backticks**. One of two kinds, depending on which application service owns the handler:
    - **Commands handler:** `<AggregateRoot>Commands` — the command application-service class in **this** service. The aggregate referenced is the one in this service whose state changes in response to the event, which need not match the Source Destination.
    - **Ops handler:** a free-form ops orchestration service class (e.g. `SubjectTagging`, `MappingRulesInferencing`) declared in a `<stem>.ops.<op-name>.md` diagram of this aggregate, with **no** `Commands` suffix. The binding is declared in a `%% Messaging - <consumer>` block inside that ops diagram. Both kinds are re-exported from `<pkg>.application` and DI-keyed as `snake_case(<class>)`, so the downstream handler emission is identical.
- **Examples:** `` `ProfileCommands` ``, `` `DocumentCommands` `` (commands); `` `SubjectTagging` ``, `` `MappingRulesInferencing` `` (ops)
- **Counter-examples:** ProfileCommands (missing backticks), `profile_commands` (wrong case — application-service classes are PascalCase), `ProfileCommandHandler` (no `Handler` suffix — the binding is to the application service, not a handler class), `ProfileQueries` (queries cannot consume events — a handler is always a `*Commands` or an ops service, never `*Queries`)

### Command Method (Handler Method)

- **Format:** snake_case, **in backticks**. The method on the Handler Class the event is routed to:
    - **Commands handler:** must be `on_<event_name_snake_case>`. Derivation: lowercase the Event Name and insert `_` at each PascalCase boundary, treating consecutive uppercase letters as a single acronym token (`OCRReportGenerated` → `on_ocr_report_generated`, `ProfileSubmitted` → `on_profile_submitted`).
    - **Ops handler:** any public method name declared on the ops service class — **free name**, no `on_` prefix required (e.g. `tag_subjects`, `infer`). The method's parameters drive Table 3's parameter mapping exactly as for a commands handler.
- **Existence requirement:** The method must already exist on the named Handler Class before the row is considered ready. If the method does not exist yet, the row is provisional.
- **Examples:** `` `on_profile_submitted` ``, `` `on_ocr_report_generated` `` (commands); `` `tag_subjects` ``, `` `infer` `` (ops)
- **Counter-examples (commands only):** `on_ProfileSubmitted` (must be snake_case), `handle_profile_submitted` (a commands prefix must be exactly `on_` — but an **ops** handler may freely use `handle_*`), on_profile_submitted (missing backticks), `_on_profile_submitted` (no leading underscore — handler methods are public)

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

### Mixed consumer (commands + ops handlers)

A single consumer may route some events to a `Commands` handler and others to an ops orchestration service. The `subject-tagging-sync` consumer for the `conversion-reqs` aggregate routes one external event to the ops service `SubjectTagging.tag_subjects` and one internal event to `ConversionReqsCommands.on_mapping_rules_inferred`:

```markdown
### Table 2: Events to Consume

| Event Name | Type | Source Destination | Command Class | Command Method |
| --- | --- | --- | --- | --- |
| RulesPublished | `external` | RuleSet | `SubjectTagging` | `tag_subjects` |
| MappingRulesInferred | `internal` | ConversionReqs | `ConversionReqsCommands` | `on_mapping_rules_inferred` |
```

The `SubjectTagging` row's binding is authored in `conversion-reqs.ops.subject-tagging.md`'s `%% Messaging - subject-tagging-sync` block (free method `tag_subjects`); the `ConversionReqsCommands` row's binding is in `conversion-reqs.commands.md`. `event-tables-writer` globs both diagrams, parses each block under the matching regex, and merges the rows into this one table.

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
- [ ] Command Class is backticked PascalCase — either `<AggregateRoot>Commands` (exact `Commands` suffix) or a free-form ops service class (no suffix); never `<X>Queries`
- [ ] Command Method is backticked snake_case — `on_<event_name_snake_case>` for a commands handler (exact `on_` prefix, no `_event` suffix), or any free method name for an ops handler
- [ ] For a commands handler, Command Method matches the snake_case derivation of Event Name (acronym runs collapse into one token)
- [ ] Command Method exists on the named Handler Class (or the row is flagged as provisional)
- [ ] Rows are ordered: external block (alphabetical by Event Name) then internal block (alphabetical by Event Name); no separator row between groups
