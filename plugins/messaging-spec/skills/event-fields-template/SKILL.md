---
name: event-fields-template
description: Reference template for the Event Parameter Mapping table (Table 3) of a messaging consumer input spec. Load when authoring or reviewing per-event mappings between event attributes and `<AggregateRoot>Commands.on_<event>` method parameters — covers per-event sub-block layout, column shape, ordering, completeness, the empty-consumer placeholder, and a worked example.
when_to_use: Authoring or reviewing the per-event parameter mapping of a messaging consumer; binding event attributes to <AggregateRoot>Commands.on_<event> method parameters; Table 3 ordering, empty-state placeholder, or completeness rules.
user-invocable: false
---

# Event Fields Template — Event Parameter Mapping

## Purpose

Defines the canonical shape of **Table 3: Event Parameter Mapping** of a messaging consumer input spec. Table 3 sits directly after Table 2 (see `event-tables-template`) and, for every event the consumer subscribes to, maps each parameter of the bound `<AggregateRoot>Commands.on_<event>` handler method to the event attribute it draws from.

**See also:** `consumer-spec-template` (Table 1: Consumer Basics) and `event-tables-template` (Table 2: Events to Consume) — the two sibling skills that define the rest of the consumer input spec.

Table 3 is what proves the binding declared in Table 2's Command Method column is executable: every parameter the handler passes to the application service is sourced from a named attribute on the event. There is no separate event-fields table — events are documented in their owning service's domain or messaging spec; Table 3 records only the projection from event to handler.

## Placement

- One Table 3 per consumer, immediately after Table 2.
- Heading is always exactly `### Table 3: Event Parameter Mapping`.
- Per-event sub-blocks live inside this single H3 section — never as separate H3 sections per event.

## Table 3 layout

A per-event sub-block, repeated once per row of Table 2, headed by an `**Event:**` line:

```
**Event:** `<EventName>` [(<handler_method>)]

| Command Parameter | Event Field |
| --- | --- |
| `<param>` | `<event_attr>` |
```

The optional `(<handler_method>)` cross-reference matches the Command Method cell of the same row in Table 2 (e.g. `(on_file_uploaded)`); include it when the cross-check between the two tables is non-trivial, omit it for compactness. Either form validates.

## Empty state

When the consumer subscribes to zero events (Table 2 is the `*No events consumed by this consumer.*` placeholder), replace Table 3's body with a single italic line:

```markdown
### Table 3: Event Parameter Mapping

*No event parameter mapping in this consumer — no events consumed.*
```

The italic line is the entire content of the section — never mix it with a real sub-block, never delete the heading. Always keep Table 3 present so every consumer spec has the same shape.

## Per-event sub-block heading

- **Format:** `**Event:** \`<EventName>\`` — label `**Event:**` bolded (colon inside the bold), single space, event name backticked (not bolded). Optional ` (<handler_method>)` may follow the backticked name (no extra bolding).
- **Event Name:** PascalCase, matches the Event Name column of the corresponding Table 2 row verbatim. Backticked here (Table 2 renders Event Name bare) so per-event sub-block headings stand out as code-shaped anchors inside prose.
- **Examples:** `**Event:** \`FileUploaded\``, `**Event:** \`FilePIIReductionStarted\` (on_file_pii_reduction_started)`
- **Counter-examples:** `**Event:** FileUploaded` (missing backticks around event name), `**Event:** \`file_uploaded\`` (must be PascalCase to match Table 2), `**Event: \`FileUploaded\`**` (colon must sit inside the bolded label, not outside), `**Event:** **\`FileUploaded\`**` (event name must not be bolded — bolding is reserved for the `Event:` label), `### Event: FileUploaded` (must be a bolded line, not an H3 heading — H3 is reserved for the Table 3 heading itself)

## Columns

### Command Parameter

- **Format:** `snake_case`, **in backticks**.
- **Cardinality:** Names a single parameter of the bound handler method `<AggregateRoot>Commands.on_<event_name_snake_case>` — the same method enumerated in Table 2's Command Method column for this event.
- **Existence requirement:** The parameter must exist on the handler method's signature. If the handler does not yet declare the parameter, the row is provisional and must be flagged in the surrounding prose.
- **Examples:** `` `id` ``, `` `tenant_id` ``, `` `profile_id` ``, `` `path` ``
- **Counter-examples:** `id` (missing backticks), `` `Id` `` (must be lowercase snake_case), `` `event.id` `` (no qualifier — the column names the parameter, not its source), `` `id, tenant_id` `` (one parameter per row — split into multiple rows), `` `*args` `` / `` `**kwargs` `` (no variadic parameters — every accepted parameter must be named)

### Event Field

- **Format:** `snake_case`, **in backticks**.
- **Cardinality:** Names a single attribute on the source event class. The right column is strictly the bare attribute name — no envelope sources, no constants, no dotted paths, no constructed expressions. If a handler needs anything beyond a direct event attribute (e.g. a value derived from the envelope or composed from multiple attributes), document the deviation in prose around Table 3 and keep the row pointed at the closest single event attribute.
- **Existence requirement:** The attribute must exist on the source event class (the publisher's event class for `external` events, or the local domain event class for `internal` events). If the attribute is missing, the row is provisional.
- **Examples:** `` `id` ``, `` `tenant_id` ``, `` `path` ``, `` `profile_id` ``
- **Counter-examples:** `id` (missing backticks), `` `Id` `` (must be lowercase snake_case), `` `Envelope.id` `` / `` `envelope.tenant_id` `` (envelope sources not allowed in this column), `` `"static-value"` `` / `` `Constant "x"` `` (constants not allowed), `` `event.id` `` (no qualifier — bare attribute name only), `` `id, tenant_id` `` (one attribute per row), `` `Constructed from a, b → T` `` (composite forms not allowed)

## Row ordering

### Sub-block order

Per-event sub-blocks are ordered to match Table 2 row-for-row:

1. All `external` events first, alphabetical by Event Name.
2. All `internal` events next, alphabetical by Event Name.

If one of the two types has zero rows in Table 2, that group is simply absent from Table 3 too. The ordering is deterministic so two authors regenerating Table 3 from the same Table 2 converge on byte-identical output.

### Row order within a sub-block

Rows within a sub-block follow the parameter order of the `<AggregateRoot>Commands.on_<event>` method's Python signature — left to right, ignoring `self`. This makes the table read like the handler's call-site.

## Completeness rules

For each per-event sub-block:

- **Every command-method parameter must appear as a row.** Missing parameters mean the binding is incomplete — review fails until every parameter of the bound handler method has a row.
- **Every event attribute consumed by the handler must appear in the Event Field column of some row.** If the handler reads `event.x`, then `x` must appear on the right side of some row; otherwise the spec under-documents what the binding actually pulls from the event.
- Event attributes the handler does *not* consume need not appear. Table 3 documents the projection from event to handler, not the full event payload.

## Worked example

`profile_reconciliation` consumer in the `clients` service, with two external events:

```markdown
### Table 3: Event Parameter Mapping

**Event:** `FileUploaded` (on_file_uploaded)

| Command Parameter | Event Field |
| --- | --- |
| `id` | `id` |
| `profile_id` | `profile_id` |
| `tenant_id` | `tenant_id` |
| `path` | `path` |

**Event:** `FilePIIReductionStarted` (on_file_pii_reduction_started)

| Command Parameter | Event Field |
| --- | --- |
| `id` | `id` |
| `tenant_id` | `tenant_id` |
```

Both events share `id` and `tenant_id`, but `FilePIIReductionStarted` carries no `profile_id` or `path` — its handler signature is correspondingly narrower, and the Table 3 sub-block reflects that exactly. Because both events are `external`, the sub-blocks are ordered alphabetically by Event Name (`FilePIIReductionStarted` follows `FileUploaded`). Within each sub-block, rows follow the handler method's Python parameter order.

## Validation checklist

### Placement

- [ ] Table 3 sits directly after Table 2 in the consumer spec
- [ ] Heading is exactly `### Table 3: Event Parameter Mapping`
- [ ] Exactly one Table 3 per consumer — no per-source or per-type sub-headings
- [ ] Empty consumers (Table 2 is the `*No events consumed by this consumer.*` placeholder) use `*No event parameter mapping in this consumer — no events consumed.*` as the entire body, never an empty header-only table and never an omitted heading

### Per-event sub-blocks

- [ ] One sub-block per Table 2 row — every event in Table 2 has a corresponding sub-block in Table 3 (provisional sub-blocks must be flagged in surrounding prose)
- [ ] Sub-block heading is `**Event:** \`<EventName>\`` with optional ` (<handler_method>)` cross-reference
- [ ] Event Name in the heading is backticked PascalCase and matches Table 2's Event Name cell verbatim
- [ ] When present, the cross-reference matches Table 2's Command Method cell exactly (`on_` prefix, snake_case, no `_event` suffix)
- [ ] Sub-blocks are ordered: external block (alphabetical by Event Name) then internal block (alphabetical by Event Name); no separator between groups

### Columns

- [ ] Every row has both columns filled — no empty cells, no `N/A`, no em dashes
- [ ] Command Parameter is backticked snake_case; one parameter per row; matches a real parameter on the bound handler method
- [ ] Event Field is backticked snake_case; one attribute per row; matches a real attribute on the source event class
- [ ] Event Field column never contains envelope sources, constants, dotted paths, or constructed expressions

### Completeness

- [ ] Every parameter of `<AggregateRoot>Commands.on_<event>` appears as a row
- [ ] Every event attribute consumed by the handler appears in the Event Field column of some row
- [ ] Row order within a sub-block follows the handler method's Python parameter order (excluding `self`)
