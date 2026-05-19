---
name: application-updates-report-template
description: Reference template for the application-service-axis updates reports emitted by commands-updates-detector and queries-updates-detector. Use when generating, parsing, or reviewing these reports.
user-invocable: false
---

# Application-Service Updates Report Template

> **Scope of this skill:** output format only. The detector workflow (loading both versions of the diagram, splitting the Mermaid block, structural diffing, surface-marker and messaging-marker parsing, prose-section diffing, summary writing voice) lives in the producer agent bodies.

This template is shared by both commands-side and queries-side detectors. A single schema describes both reports; sub-sections marked *(commands only)* are emitted only on commands-side reports and are absent (no `_N/A_` placeholder) from queries-side reports.

---

## File location

Each report is written next to the application-service diagram it describes, inside the existing per-plugin folder:

```
<dir>/<stem>.application/
├── commands-updates.md         (produced by commands-updates-detector)
└── queries-updates.md          (produced by queries-updates-detector)
```

The `<stem>` matches the originating diagram's stem (e.g. `cache-type.commands.md` → `cache-type.application/commands-updates.md`).

---

## Anchor class concept

Each application-service diagram has exactly one `<<Application>>` class (the **anchor**) plus zero or more `<<Interface>>` and `<<Domain Event>>` classes (the **non-anchors**).

The schema partitions sections accordingly:

- **Anchor-keyed sections** describe deltas attributable to the anchor class: `## Dependencies`, `## Per-Method Changes`, `## Surface Markers`, `## Messaging Markers` *(commands only)*, `## Raised Exceptions`, `## Application Class Relationships`.
- **Non-anchor-keyed sections** describe deltas attributable to non-anchor classes: `## Class Lifecycle`, `## External Interfaces`, `## External Domain Events` *(commands only)*.
- **Cross-cutting sections** describe deltas not bound to a specific class: `## Summary`, `## Orphan Prose Changes`, `## Affected Categories`.

The anchor class never appears under `## Class Lifecycle → Added/Removed`. Interfaces and external events do.

---

## Schema

Substitute every `<placeholder>` with the actual value when rendering.

````markdown
# Updates Report

_Baseline: git HEAD. Working tree compared against `HEAD:<application_service_diagram>`._

## Summary

- Classes: <N> added, <N> removed
- Anchor methods: <N> added, <N> removed, <N> signature-changed, <N> surface-remapped, <N> prose-changed
- Dependencies: <N> added, <N> removed, <N> type-changed
- External Interfaces: <N> added, <N> removed, <N> members-changed
- External Domain Events: <N> added, <N> removed, <N> attrs-changed
- Surface Markers: <N> surfaces added, <N> removed; <N> method remappings
- Messaging Markers: <N> consumers touched, <N> rows changed
- Raised Exceptions: <N> added, <N> removed
- Application Class Relationships: <N> changed
- Description: <N> sections changed

## Class Lifecycle

### Added
- `ClassName` `<<Stereotype>>`

### Removed
- `ClassName` `<<Stereotype>>`

## Dependencies

- Dependency added: `<name>: <Type>`
- Dependency removed: `<name>: <Type>`
- Dependency changed: `<name>`: type `<OldType>` → `<NewType>`

## Per-Method Changes

### `<method_name>`

**Signature:** `<old signature>` → `<new signature>`

**Surface:** `<old surface>` → `<new surface>`

**Messaging:** Added handler binding `<Event> via (<SourceDest>, <on_method>)`

**Prose — `<section heading>`:**

Summary: One-paragraph natural-language description of what changed in this prose section.

Diff:
```diff
- old line
+ new line
```

## External Interfaces

### Added
- `InterfaceName`

### Removed
- `InterfaceName`

### Members
- `InterfaceName.member`: added — `<signature>`
- `InterfaceName.member`: removed — `<signature>`
- `InterfaceName.member`: changed — `<old signature>` → `<new signature>`

## External Domain Events

### `EventName`

**Members:**
- Attribute added: `<name>: <Type>`
- Attribute removed: `<name>: <Type>`
- Attribute changed: `<name>`: type `<OldType>` → `<NewType>`

## Surface Markers

### Surface Set
- Added: `<surface>`
- Removed: `<surface>`

### Method Membership
- `<method_name>`: `<old surface>` → `<new surface>`

## Messaging Markers

### `<consumer-name>`

- Row added: `<CommandsClass> --() <Event> : handles (<SourceDest>, <on_method>)`
- Row removed: `<CommandsClass> --() <Event> : handles (<SourceDest>, <on_method>)`
- Row changed: `<old row>` → `<new row>`

## Raised Exceptions

- Added: `ExceptionName`
- Removed: `ExceptionName`

## Application Class Relationships

- Added: `AnchorClass --() Target : <label>`
- Removed: `AnchorClass --() Target : <label>`
- Changed: `AnchorClass --() Target`: label `: <old label>` → `: <new label>`

## Orphan Prose Changes

### Preamble

**Summary:** One-paragraph natural-language description.

**Diff:**
```diff
- old line
+ new line
```

### `<section heading>`

**Summary:** One-paragraph natural-language description.

**Diff:**
```diff
- old line
+ new line
```

## Affected Categories

- <category>
````

---

## Rendering rules

### Top-level sections

- `## Summary` and `## Affected Categories` are **always emitted**, regardless of content.
- All other top-level sections are **omitted entirely when empty** — do not emit the heading, do not emit a `_None._` placeholder.
- `## External Domain Events` and `## Messaging Markers` are **commands-only**. On queries-side reports they are absent entirely — no heading, no placeholder. The Summary rows for these sections are also omitted from the queries-side Summary bullet list (not rendered as zero counts).

### Canonical section order

When non-empty, sections render in this fixed order:

1. `## Summary`
2. `## Class Lifecycle`
3. `## Dependencies`
4. `## Per-Method Changes`
5. `## External Interfaces`
6. `## External Domain Events` *(commands only)*
7. `## Surface Markers`
8. `## Messaging Markers` *(commands only)*
9. `## Raised Exceptions`
10. `## Application Class Relationships`
11. `## Orphan Prose Changes`
12. `## Affected Categories`

### Within-section ordering

Inside every section, items are ordered: **Added** (alphabetical) → **Removed** (alphabetical) → **Changed / Modified** (alphabetical by key). Per-method blocks under `## Per-Method Changes` are ordered alphabetically by method name. Per-event blocks under `## External Domain Events` are ordered alphabetically by event name. Per-consumer blocks under `## Messaging Markers` are ordered alphabetically by consumer name.

### `## Summary`

- If every count in the bullet list is zero, replace the bullet list with the single literal line `No changes detected.`
- If HEAD had zero or >1 Mermaid blocks (degraded baseline), append the literal line `_warning: HEAD version had <count> Mermaid blocks; structural baseline treated as empty._` immediately after the Summary bullet list (or after the `No changes detected.` line).
- Commands-only rows (`External Domain Events: ...`, `Messaging Markers: ...`) are omitted entirely from queries-side Summary bullet lists.

### `## Class Lifecycle`

- Sub-sections (`### Added`, `### Removed`) are individually **omitted when empty** — do not emit the heading, do not emit a `_None._` placeholder.
- `### Stereotype Changed` is intentionally absent — stereotype changes are a detector hard-fail and never reach the report.
- If both sub-sections are empty, omit the parent `## Class Lifecycle` section entirely.
- The anchor class never appears under `### Added` or `### Removed` (it must exist; otherwise the detector hard-fails).

### `## Dependencies`

- Tracks deltas on the anchor class's constructor attributes (private `-name: Type` declarations). Only deltas render — byte-stable dependencies do not appear.
- Constructor attributes of non-anchor classes are **not** rendered here. Rare interface attribute changes surface under `## External Interfaces → ### Members`.

### `## Per-Method Changes`

Emit one `### \`<method_name>\`` block per touched method of the anchor class. A method is **touched** if it was added, removed, or modified in any of: signature, surface assignment, messaging binding, or attached prose section.

Block shape is uniform across lifecycle states; emit only the sub-section fields that have content:

- **Added method:** `**Signature:**` renders as `_new method_ — <new signature>`. `**Surface:**` (when on a non-default surface) renders as `_new method on surface \`<surface>\`_`. `**Messaging:**` and `**Prose —`** render only when the added method shipped with those.
- **Removed method:** `**Signature:**` renders as `<old signature> → _removed_`. Other sub-section fields render only when the removal entailed dropping a messaging binding or a prose section keyed to this method.
- **Modified method:** every changed sub-section field renders with its `<old> → <new>` form.

Sub-section order within a per-method block is fixed: **Signature**, then **Surface**, then **Messaging** *(commands only)*, then one **Prose — `<heading>`** sub-section per resolved prose section. Sub-section labels (`**Signature:**`, `**Surface:**`, `**Messaging:**`, `**Prose — \`<heading>\`:**`) are rendered in **bold**.

Inside a **Prose** sub-section, the `Summary:` and `Diff:` labels are rendered as plain (not bolded) lines, mirroring the in-class prose convention of the domain template. The diff fenced block uses ```` ```diff ````.

A method's surface shift across the default-fallback boundary is rendered as `default → <surface>` or `<surface> → default` for clarity.

### `## External Interfaces`

- Lifecycle-only at the top (`### Added` / `### Removed`); member-level granularity in a flat `### Members` sub-section keyed by `InterfaceName.member`.
- Each `### Added` / `### Removed` / `### Members` sub-section is **omitted when empty**. The parent `## External Interfaces` is omitted when all three are empty.

### `## External Domain Events` *(commands only)*

- Emit one `### \`EventName\`` block per event whose member set changed.
- When an event is **added** with no members yet, the lifecycle entry under `## Class Lifecycle → Added` suffices and the per-event block is omitted.
- When an event is **removed** entirely, the lifecycle entry under `## Class Lifecycle → Removed` suffices and the per-event block is omitted.
- When an event's members change (with the event itself present in both versions, or present in working tree with new members), emit the block with the `**Members:**` sub-section.
- Omitted entirely from queries-side reports.

### `## Surface Markers`

Three sub-sections capture the three levels of surface delta:

- `### Surface Set` — surfaces added to or removed from the diagram's overall surface set. Omit when no surfaces were added or removed.
- `### Method Membership` — per-method surface-assignment changes. Bullets render only for methods that changed surface assignment (including shifts across the default-fallback boundary). Omit when no methods were remapped.

Each sub-section is **omitted when empty**. The parent `## Surface Markers` is omitted when both are empty.

### `## Messaging Markers` *(commands only)*

- Emit one `### \`<consumer-name>\`` block per consumer that had a row added, removed, or changed.
- Consumer-lifecycle entries (consumer added or removed entirely) are still rendered as a `### \`<consumer-name>\`` block — the heading carries the lifecycle annotation `(consumer added)` or `(consumer removed)` after the consumer name, e.g. `### \`inventory-sync\` (consumer added)`. The block body enumerates the rows.
- Rows render verbatim from the diagram's `<CommandsClass> --() <Event> : handles (<SourceDest>, <on_method>)` form.
- Omitted entirely from queries-side reports.

### `## Raised Exceptions`

- Tracks `: raises` outgoing-edge changes on the anchor class. Dedicated section (separate from `## Application Class Relationships`) because it directly drives the Application Exceptions section of `<side>.specs.md`.
- Two bullet kinds: `Added: \`ExceptionName\`` and `Removed: \`ExceptionName\``. The exception class name is the tail of the `--() : raises` edge.

### `## Application Class Relationships`

- Catch-all for anchor-class outgoing-relationship deltas **other than** `: raises` (which belongs in `## Raised Exceptions`). Covers `: uses`, `: manipulates`, `: takes as argument`, `: returns`, etc.
- Three bullet kinds: `Added: ...`, `Removed: ...`, `Changed: ...` with the same `<source> --() <target> : <label>` rendering form used by the diagram.

### `## Orphan Prose Changes`

- Houses prose section changes whose heading does not resolve to a method on the anchor class (or to the anchor class itself).
- The synthetic preamble section is rendered as `### Preamble` (no backticks). Other orphan headings are rendered as `### \`<heading>\`` verbatim.
- Inside an orphan prose block, use the bolded `**Summary:**` / `**Diff:**` labels (top-level form) since these blocks are not nested inside a method block.

---

## `## Affected Categories` computation

The footer lists every category that has at least one structural change. It is the orchestrator's primary dispatch input — consumers should be able to skip parsing the rest of the report and still pick the right downstream artifacts to refresh.

### Trigger → category mapping

| Trigger | Category |
|---|---|
| Any per-method block has a delta (signature / surface / messaging-binding / prose) | `methods` |
| A method was added or removed | `methods` |
| Any anchor-class dependency added / removed / type-changed | `dependencies` |
| Any anchor-class `: raises` outgoing edge added or removed | `raised-exceptions` |
| Any `<<Interface>>` class added / removed / member-changed | `external-interfaces` |
| Any `<<Domain Event>>` class added / removed / attribute-changed *(commands only)* | `external-domain-events` |
| Surface set changed OR any per-method surface assignment changed | `surface-markers` |
| Any `%% Messaging - <C>` block added / removed / row-changed *(commands only)* | `messaging-markers` |

Multiple triggers for one category coalesce to a single bullet — the footer is a set, not a multiset.

**Orphan prose does not contribute to category dispatch.** Orphan-prose changes (including the synthetic `Preamble` section) appear under `## Orphan Prose Changes` for the audit trail only. The detector deliberately does not promote them to category triggers because, by construction, they are not attributable to a method or to a structural element.

### Canonical category order

When listing categories in the footer, use this sequence (omit categories whose triggers did not fire):

1. `methods`
2. `dependencies`
3. `raised-exceptions`
4. `external-interfaces`
5. `external-domain-events` *(commands only — never appears on queries-side reports)*
6. `surface-markers`
7. `messaging-markers` *(commands only — never appears on queries-side reports)*

If the set is empty, render the single line `_None._` as the section body.

---

## Not in scope

The report deliberately excludes the following — these are downstream-consumer concerns, not detector concerns:

- **Renames.** Method, attribute, surface marker, consumer, interface, and event renames all surface as `remove` + `add`. The detector does not attempt rename detection. Downstream consumers that need rename semantics must re-derive them from the structural diff.
- **Source domain class names** beyond what appears verbatim on the application-service diagram. The report describes one axis only; cross-axis enrichment (e.g. "this event is also declared on the domain diagram") is the orchestrator's concern.
- **Code-level diffs or generated source text.** The report describes diagram deltas, not code deltas.
- **Cross-diagram reconciliation hints.** Mismatches between the application-service diagram and its companion domain diagram (e.g. a parameter renamed on one side but not the other) are not flagged here. Downstream specifiers detect and abort on such mismatches; the detector reports diagram deltas only.
- **Hand-edit reconciliation hints.** Hand-edits to generated specs are not preserved by the spec contract; the report describes only diagram deltas.
- **`## Dependencies` deltas for non-anchor classes.** Constructor attributes are emitted only for the anchor class. Interface attribute changes (rare in practice) surface under `## External Interfaces → ### Members`.
- **Reordering.** A method moved within the class body with no signature, surface, messaging, or prose change produces no structural delta — the structural parser is order-agnostic.
