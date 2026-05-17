# Commands / Queries Updates Reports — Schema Design

This note describes the design of the two new reports emitted by the application-service-axis detectors:

- `<dir>/<stem>.application/commands-updates.md` — produced by `application-spec:commands-updates-detector`
- `<dir>/<stem>.application/queries-updates.md` — produced by `application-spec:queries-updates-detector`

They are the application-service-axis analog of the domain detector's `<stem>.domain/updates.md`. Both reports share one template skill (`application-spec:application-service-updates-report-template`); queries-side reports simply omit the inapplicable top-level sections.

For the catalog of update types these reports describe, see the sibling [`commands-queries-update-types.md`](commands-queries-update-types.md).
For the detector workflow that produces these reports, see the sibling [`commands-queries-detectors-approach.md`](commands-queries-detectors-approach.md).
For the domain-side counterpart this design mirrors, see [`plugins/domain-spec/skills/updates-report-template/SKILL.md`](../../domain-spec/skills/updates-report-template/SKILL.md).

---

## Goal

Capture, in structured form, every change to one application-service diagram (commands or queries) since `git HEAD`, in a shape that lets downstream orchestrators dispatch per-artifact updates without re-diffing the diagram.

The report:

- Is **transient** (never committed; regenerated on every detector run; overwrites the prior report). Same lifecycle as `<stem>.domain/updates.md`.
- Is **class-grouped for the anchor** (per-method blocks) and **per-class for non-anchor classes** (one block per touched interface / external event). Mirrors the domain detector's `## Per-Class Changes` shape, specialized for the diagram's structure.
- Is **stable** between identical inputs (HEAD blob + working tree blob) → byte-identical report, modulo one LLM prose-summary step per non-trivial prose section diff.
- Is **always written**, including the no-change case (downstream orchestrators expect a report to exist).

---

## Lifecycle and ownership

### Producer

Owned entirely by one of the two detectors. The agent runs Step 0–8 of [`commands-queries-detectors-approach.md`](commands-queries-detectors-approach.md) § "Workflow" and writes the report in Step 7. No orchestrator captures or hands off pre-update content.

### Consumer

Currently no automatic consumer. Future:

- `/application-spec:update-specs` (extended) will read both reports to refresh `commands.specs.md` / `queries.specs.md` / `services.md` based on application-service-diagram deltas — currently only the domain axis drives it.
- `/rest-api-spec:update-specs` (extended) will read both reports to refresh REST API Tables 2/3 (endpoint inventory) and Tables 4/5/6 (request/response/parameter mapping).
- `/messaging-spec:update-specs` (extended) will read `commands-updates.md` to refresh consumer Tables 2/3 and external event dataclasses.

The reports' `## Affected Categories` footer is the dispatch input for each of those orchestrators — they walk the footer top-to-bottom, mapping each category to the artifacts they own.

### First-run handling

When the diagram is brand-new (untracked, or absent from HEAD), the detector treats the HEAD version as empty. The resulting report has every class and every method under `## Class Lifecycle → Added` / per-method-block Added, and the footer carries every relevant category. Same shape as the domain detector's first-run.

---

## File location and naming

```
<dir>/<stem>.application/
├── commands.specs.md           (commands-side spec)
├── queries.specs.md            (queries-side spec)
├── services.md                 (services report)
├── updates.md                  (domain-axis-driven application updates — existing)
├── commands-updates.md         (commands-axis-driven update report — NEW)
└── queries-updates.md          (queries-axis-driven update report — NEW)
```

The naming `<side>-updates.md` (hyphenated) was chosen to:

- Sit visually next to `<side>.specs.md` without clashing with that file.
- Avoid the pattern `<side>.updates.md` which could be misread as a member of the `<side>.*` cluster.
- Mirror how the domain detector names its report (`updates.md`, no prefix needed) — when scoped to a side, the side becomes the prefix.

Both new files sit under the existing `<stem>.application/` folder. No new per-plugin folder is introduced.

---

## Top-level schema

```markdown
# Updates Report

_Baseline: git HEAD. Working tree compared against `HEAD:<application_service_diagram>`._

## Summary

## Class Lifecycle           (omit when empty)

## Dependencies              (omit when empty)

## Per-Method Changes        (omit when empty)

## External Interfaces       (omit when empty)

## External Domain Events    (omit on queries side; omit when empty on commands side)

## Surface Markers           (omit when empty)

## Messaging Markers         (omit on queries side; omit when empty on commands side)

## Raised Exceptions         (omit when empty)

## Application Class Relationships   (omit when empty)

## Orphan Prose Changes      (omit when empty)

## Affected Categories       (always emitted; body `_None._` when empty)
```

The "omit when empty" rule matches the domain template's behaviour for `## Class Lifecycle`, `## Per-Class Changes`, `## Orphan Relationship Changes`, `## Orphan Prose Changes`. Empty top-level sections do not render — no heading, no `_None._` placeholder.

`## Summary` and `## Affected Categories` are always emitted, regardless of content. The two queries-only-omitted sections (`## External Domain Events`, `## Messaging Markers`) are simply absent from queries reports — there is no `## Messaging Markers _N/A_` placeholder.

---

## Section-by-section

### Summary

A small bullet list capturing counts, plus an optional `_warning:_` line for degraded baselines.

```markdown
## Summary

- Classes: <N> added, <N> removed
- Anchor methods: <N> added, <N> removed, <N> signature-changed, <N> surface-remapped, <N> prose-changed
- Dependencies: <N> added, <N> removed, <N> type-changed
- External Interfaces: <N> added, <N> removed, <N> members-changed
- External Domain Events: <N> added, <N> removed, <N> attrs-changed         (commands only; row omitted when zero)
- Surface Markers: <N> surfaces added, <N> removed; <N> method remappings
- Messaging Markers: <N> consumers touched, <N> rows changed                 (commands only; row omitted when zero)
- Raised Exceptions: <N> added, <N> removed
- Application Class Relationships: <N> changed
- Description: <N> sections changed
```

If every count is zero, replace the bullet list with the single literal line `No changes detected.`

If HEAD had zero or >1 Mermaid blocks (degraded baseline), append:

```
_warning: HEAD version had <count> Mermaid blocks; structural baseline treated as empty._
```

### Class Lifecycle

```markdown
## Class Lifecycle

### Added
- `ClassName` `<<Stereotype>>`

### Removed
- `ClassName` `<<Stereotype>>`
```

Renders only present sub-sections. `### Stereotype Changed` is intentionally absent — stereotype changes are a detector hard-fail, never reach the report.

The anchor class itself can never appear under Added or Removed (it must exist; otherwise hard-fail). Interfaces and external events do.

### Dependencies

The application anchor class's constructor attributes (private `-name: Type` declarations). These are the application service's dependencies.

```markdown
## Dependencies

- Dependency added: `command_user_repository: CommandUserRepository`
- Dependency removed: `legacy_audit_service: LegacyAuditService`
- Dependency changed: `domain_event_publisher`: type `EventPublisher` → `DomainEventPublisher`
```

Only deltas are rendered. A byte-stable dependency does not appear.

### Per-Method Changes

The core of the report. One `### <method_name>` block per touched method of the anchor class. Renders only sub-sections that have content.

```markdown
## Per-Method Changes

### `create`

**Signature:** `create(code: str, name: str) CacheType` → `create(code: str, name: str, lookups: list[LookupData]) CacheType`

**Surface:** `v1` → `internal`

**Messaging:** Added handler binding `DomainTypeAdded via (ConversionReqs, on_domain_type_added)`         (commands only)

**Prose — `### CacheTypeCommands.create`:**

Summary: Tightened the precondition to require a non-empty `lookups` list and added a step to validate each lookup's `code` uniqueness within the request.

Diff:
```diff
 **Preconditions:**
-- No `CacheType` with the given `name` or `code` may already exist
+- No `CacheType` with the given `name` or `code` may already exist
+- The `lookups` list must be non-empty and contain unique `code` values
 ```
```

Per-method block sub-section order (rendered only when content present):

1. **Signature** — old → new full signature.
2. **Surface** — old → new surface name. Renders when the method moved between surfaces (S3) or shifted into/out of the default-fallback boundary (S4).
3. **Messaging** *(commands only)* — added / removed / changed handler bindings. Renders only on commands diagrams; queries reports never carry this field.
4. **Prose — `<heading>`:** — one sub-section per resolved prose section. The heading is rendered verbatim. Multiple prose sub-sections appear if multiple per-method prose sections were touched (rare).

**Method-rename non-detection** — same convention as the domain detector. A renamed method appears as two blocks: a Removed under Class Lifecycle (no — methods aren't classes; renames surface as `method_added` + `method_removed` reflected in two per-method blocks under Per-Method Changes? No — when a method is *removed*, there's no per-method block for it. The Per-Method Changes section emits blocks only for methods still present in working tree but changed. Removed methods are listed in the Summary count and would have been visible in the prior HEAD state.) — wait, let me clarify: the schema deliberately does not emit a block for fully-removed methods; the count appears in Summary and downstream consumers parse the structural diff itself.

Actually, simplify: a Removed method gets a per-method block with only the `**Signature:** <old>(...) → _removed_` field. An Added method gets a block with only the `**Signature:** _new method_` field + whatever surface/messaging/prose was added with it. A Modified method renders all changed fields. This keeps the schema uniform.

### External Interfaces

Lifecycle-only at the top (Added / Removed); member changes in a flat sub-section. Per the interview decision (member-level granularity is captured as flat bullets keyed by `Interface.member`, not as per-interface blocks).

```markdown
## External Interfaces

### Added
- `IRequirementsGathering`

### Removed
- `LegacyAuditService`

### Members
- `IRequirementsGathering.identify_evo_version`: added — `identify_evo_version() -> str`
- `IRequirementsGathering.gather_domain_type_requirements`: changed — `gather_domain_type_requirements(evo_version: str, domain_type: DomainTypeData) -> ParsingResult` → `gather_domain_type_requirements(evo_version: str, domain_type: DomainTypeData, retries: int) -> ParsingResult`
```

Each `### Added` / `### Removed` / `### Members` sub-section is omitted when empty. The parent `## External Interfaces` is omitted when all three are empty.

### External Domain Events *(commands only)*

Per-event blocks with attribute-level deltas (per the interview decision — full granularity to drive `event-fields-writer` Table 3 regen).

```markdown
## External Domain Events

### `DomainTypeAdded`

**Members:**
- Attribute added: `tenant_id: str`
- Attribute changed: `domain_type`: type `DomainTypeData` → `DomainTypeRef`

### `OrderConfirmed`

(added entirely; lifecycle entry under Class Lifecycle → Added; this per-event block omitted because no members changed yet)
```

When an event is added with no members yet, the lifecycle entry suffices and the per-event block is omitted. When members change, the block is emitted.

Omit entirely from queries-side reports.

### Surface Markers

Three sub-sections capturing the three levels of surface deltas (interview decision: surface-set + per-method-membership + default-fallback).

```markdown
## Surface Markers

### Surface Set
- Added: `internal`
- Removed: `v2`

### Method Membership
- `create`: `v1` → `internal`
- `bulk_reprocess`: default → `internal`
```

`### Method Membership` bullets render only when a method changed surface assignment. A method's membership shift across the default-fallback boundary (S4) is rendered as `default → v1` or `v1 → default` for clarity.

### Messaging Markers *(commands only)*

Per-consumer blocks with row-level deltas (interview decision).

```markdown
## Messaging Markers

### `requirements-gathering`

- Row added: `ConversionReqsCommands --() DomainTypeRemoved : handles (ConversionReqs, on_domain_type_removed)`
- Row removed: `ConversionReqsCommands --() DomainTypeAdded : handles (ConversionReqs, on_domain_type_added)`
- Row changed: `ConversionReqsCommands --() DomainTypeUpdated : handles (Old, on_x)` → `ConversionReqsCommands --() DomainTypeUpdated : handles (ConversionReqs, on_domain_type_updated)`
```

Consumer-lifecycle entries (consumer added or removed entirely) are still rendered as a `### <consumer-name>` block — its body just says "Consumer added" or "Consumer removed":

```markdown
### `inventory-sync` (consumer added)
- Row added: `OrderCommands --() ItemReserved : handles (Inventory, on_item_reserved)`
- Row added: `OrderCommands --() ItemReleased : handles (Inventory, on_item_released)`
```

Omit entirely from queries-side reports.

### Raised Exceptions

Tracks `raises` outgoing-edge changes on the anchor class. Interview decision: dedicated section, separate from generic relationship changes, because it directly drives the Application Exceptions section of `<side>.specs.md`.

```markdown
## Raised Exceptions

- Added: `CacheTypeAlreadyExists`
- Removed: `LegacyValidationError`
```

### Application Class Relationships

All other anchor-class outgoing-relationship deltas (`uses`, `manipulates`, `takes as argument`, `returns`). Catch-all section.

```markdown
## Application Class Relationships

- Added: `CacheTypeCommands --() LookupData : takes as argument`
- Removed: `CacheTypeCommands --() EntryItemData : takes as argument`
- Changed: `CacheTypeCommands --() CacheType`: label `: manipulates` → `: returns`
```

### Orphan Prose Changes

Same shape as the domain detector. Prose sections whose heading does not resolve to a method on the anchor class.

```markdown
## Orphan Prose Changes

### Preamble

**Summary:** Added a paragraph describing the commands service's role in the conversion-reqs workflow.

**Diff:**
```diff
+The ConversionReqsCommands service coordinates the EVO version lifecycle and dispatches
+requirements-gathering events to the requirements-gathering consumer.
```

### `Notes`

**Summary:** Removed an obsolete reference to a deprecated `legacy_audit_service` collaborator.

**Diff:**
```diff
-Note: the legacy_audit_service dependency is retained for backwards compatibility.
```
```

The synthetic `Preamble` section uses bare heading `### Preamble`. Other orphan headings use `### \`<heading>\`` verbatim. Inside an orphan block, the `**Summary:**` and `**Diff:**` labels are bolded (vs. the unbolded inside-per-method form). Same convention as the domain detector's orphan-prose treatment.

### Affected Categories

The dispatch footer. Renders one bullet per non-empty category, in canonical order.

```markdown
## Affected Categories

- methods
- dependencies
- raised-exceptions
- external-interfaces
- external-domain-events       (commands only)
- surface-markers
- messaging-markers            (commands only)
```

Canonical order:

1. `methods`
2. `dependencies`
3. `raised-exceptions`
4. `external-interfaces`
5. `external-domain-events` *(commands only)*
6. `surface-markers`
7. `messaging-markers` *(commands only)*

Body is `_None._` when the set is empty.

---

## Affected Categories computation

The footer is computed mechanically from the structural diff. Inputs:

- Class-level changes (Step 4 of the detector).
- Anchor-class member-level changes.
- Non-anchor-class member-level changes.
- Relationship-level changes.
- Surface-level changes.
- Messaging-marker-level changes (commands only).
- Non-empty prose section headings (Step 5 of the detector).

Rules:

| Trigger | Category |
|---|---|
| Any per-method block has a delta (signature / surface / messaging-binding / prose) | `methods` |
| A method was added / removed | `methods` |
| Any anchor-class dependency added / removed / type-changed | `dependencies` |
| Any anchor-class `--() : raises` edge added / removed | `raised-exceptions` |
| Any `<<Interface>>` class added / removed / member-changed | `external-interfaces` |
| Any `<<Domain Event>>` class added / removed / attribute-changed *(commands only)* | `external-domain-events` |
| Surface set changed OR any per-method surface assignment changed | `surface-markers` |
| Any `%% Messaging - <C>` block added / removed / row-changed *(commands only)* | `messaging-markers` |

Multiple triggers can fire for one bullet (e.g. a per-method block with both a signature change and a surface remap → one `methods` entry; the bullet is not duplicated). Orphan prose changes do **not** contribute to category dispatch — by definition they are not attributable to a method or to a structural element. They are reported only for the audit trail.

The footer is rendered in the canonical order above, regardless of which trigger fired first.

---

## Worked example — commands diagram

Operator edit on `<dir>/cache-type.commands.md`:

1. Adds a new `tenant_id: str` parameter to `create(...)`.
2. Adds an `IExternalAuth` interface decl + a new `external_auth: IExternalAuth` constructor attribute.
3. Tightens the `### CacheTypeCommands.create` Invariants prose.
4. Splits the diagram into two surfaces: `%% v1` (existing methods) and `%% internal` (new `bulk_reprocess` method).
5. Adds a new `%% Messaging - cache-sync` block subscribing to one external `<<Domain Event>>` `CacheTypeChanged` (also added to the diagram).

Detector emits `<dir>/cache-type.application/commands-updates.md`:

```markdown
# Updates Report

_Baseline: git HEAD. Working tree compared against `HEAD:cache-type.commands.md`._

## Summary

- Classes: 2 added, 0 removed
- Anchor methods: 1 added, 0 removed, 1 signature-changed, 0 surface-remapped, 1 prose-changed
- Dependencies: 1 added, 0 removed, 0 type-changed
- External Interfaces: 1 added, 0 removed, 0 members-changed
- External Domain Events: 1 added, 0 removed, 0 attrs-changed
- Surface Markers: 1 surfaces added, 0 removed; 1 method remappings
- Messaging Markers: 1 consumers touched, 1 rows changed
- Raised Exceptions: 0 added, 0 removed
- Application Class Relationships: 1 changed
- Description: 1 section changed

## Class Lifecycle

### Added
- `IExternalAuth` `<<Interface>>`
- `CacheTypeChanged` `<<Domain Event>>`

## Dependencies

- Dependency added: `external_auth: IExternalAuth`

## Per-Method Changes

### `create`

**Signature:** `create(code: str, name: str, lookups: list[LookupData]) CacheType` → `create(code: str, name: str, lookups: list[LookupData], tenant_id: str) CacheType`

**Prose — `### CacheTypeCommands.create`:**

Summary: Added a precondition requiring `tenant_id` to be a non-empty string and a flow step that verifies the caller's tenant binding via `external_auth`.

Diff:
```diff
 **Preconditions:**
 - No `CacheType` with the given `name` or `code` may already exist
+- The provided `tenant_id` must match the caller's tenant binding (verified via `external_auth`)
```

### `bulk_reprocess`

**Signature:** _new method_ — `bulk_reprocess(ids: list[str], tenant_id: str) BulkResult`

**Surface:** _new method on surface `internal`_

## External Interfaces

### Added
- `IExternalAuth`

## External Domain Events

### `CacheTypeChanged`

(class added entirely; no per-event member changes yet — see Class Lifecycle)

## Surface Markers

### Surface Set
- Added: `internal`

### Method Membership
- `bulk_reprocess`: _new method_ → `internal`

## Messaging Markers

### `cache-sync` (consumer added)
- Row added: `CacheTypeCommands --() CacheTypeChanged : handles (External, on_cache_type_changed)`

## Application Class Relationships

- Added: `CacheTypeCommands --() IExternalAuth : uses`

## Affected Categories

- methods
- dependencies
- external-interfaces
- external-domain-events
- surface-markers
- messaging-markers
```

Note:

- The `create` block carries both a signature change and a prose change in one block.
- The `bulk_reprocess` block describes a new method; only the relevant fields are rendered.
- The `CacheTypeChanged` event has no per-event sub-block content yet (no member changes); the lifecycle entry suffices.
- The footer omits `raised-exceptions` because no `raises` edge changed.

---

## Worked example — queries diagram

Operator edit on `<dir>/cache-type.queries.md`:

1. Adds a `find_cache_types_by_tag(tag: str)` query method.
2. Splits the diagram into `%% v1` (existing methods) and `%% internal` (the new method).

Detector emits `<dir>/cache-type.application/queries-updates.md`:

```markdown
# Updates Report

_Baseline: git HEAD. Working tree compared against `HEAD:cache-type.queries.md`._

## Summary

- Classes: 0 added, 0 removed
- Anchor methods: 1 added, 0 removed, 0 signature-changed, 0 surface-remapped, 0 prose-changed
- Dependencies: 0 added, 0 removed, 0 type-changed
- External Interfaces: 0 added, 0 removed, 0 members-changed
- Surface Markers: 1 surfaces added, 0 removed; 1 method remappings
- Raised Exceptions: 0 added, 0 removed
- Application Class Relationships: 0 changed
- Description: 0 sections changed

## Per-Method Changes

### `find_cache_types_by_tag`

**Signature:** _new method_ — `find_cache_types_by_tag(tag: str, pagination: Pagination | None) CacheTypeListResult`

**Surface:** _new method on surface `internal`_

## Surface Markers

### Surface Set
- Added: `internal`

### Method Membership
- `find_cache_types_by_tag`: _new method_ → `internal`

## Affected Categories

- methods
- surface-markers
```

Note:

- The report omits `## External Domain Events` and `## Messaging Markers` entirely — queries-side schema does not include them.
- The Summary row for `External Domain Events: ...` is omitted from the bullet list (queries-side never carries it).
- The Summary row for `Messaging Markers: ...` is omitted from the bullet list (queries-side never carries it).
- The per-method block on the queries side has no `**Messaging:**` field — that field is exclusive to the commands-side schema.

---

## Determinism and idempotency

- **Byte-stable inputs → byte-stable report.** Same HEAD blob + same working-tree blob → byte-identical report, modulo the one LLM prose-summary step per non-trivial prose section diff. Treated as `git diff` noise, not an idempotency failure.
- **Re-running with no diagram changes** produces a report with every section emitting only `_None._` (footer) and `No changes detected.` (Summary), and every other section omitted. Downstream consumers treat this as a no-op.
- **Section ordering is canonical** (Summary → Class Lifecycle → Dependencies → Per-Method Changes → External Interfaces → External Domain Events → Surface Markers → Messaging Markers → Raised Exceptions → Application Class Relationships → Orphan Prose Changes → Affected Categories).
- **Within each section**, items are ordered: Added (alphabetical) → Removed (alphabetical) → Modified / Changed (alphabetical by key). Same convention as the domain detector.
- **Per-method blocks** are ordered alphabetically by method name.
- **No sentinels.** Unlike persistence-spec's append-only `<!-- appended-from updates-hash:<hash> -->`, every section here is a snapshot diff — re-running on identical inputs reproduces the same content. No skip-on-replay logic is needed at the report level.

---

## What the report deliberately does NOT include

- **Source domain class names** beyond what appears verbatim on the application-service diagram. The report describes one axis; cross-axis enrichment (e.g. "this event is also declared on the domain diagram") is the orchestrator's concern.
- **Code-level diffs or generated source text.** The report says what changed in the *diagram*; downstream consumers say what to do in code.
- **Cross-diagram reconciliation hints.** If a commands-diagram method renames its parameter from `id` to `cache_type_id` while the matching aggregate-root method still says `id`, the report describes the commands-diagram change only. The application-spec methods writer (on the next regen) detects the mismatch and aborts; that abort is a downstream concern, not the detector's.
- **Hand-edit reconciliation hints.** Hand-edits in generated specs are not preserved (per the spec contract). The report describes only diagram deltas.
- **`## Dependencies` deltas for non-anchor classes.** Constructor attributes are emitted only for the anchor class. Interface attributes (rare in practice) surface under `## External Interfaces → ### Members`.
- **Renames.** Method, attribute, surface marker, consumer, interface, and event renames all surface as remove + add. Same convention as the domain detector.
- **Reordering.** A method moved within the class body (no signature change, no surface change) produces an empty diff at the structural level. The Mermaid block diff itself may detect line-order changes, but the structural parser is order-agnostic.

---

## Hard-fail conditions

The report is not produced (the detector hard-fails before writing) when:

- The working-tree diagram has 0 or >1 Mermaid blocks (unparseable).
- The anchor class is missing or removed in the working tree.
- The anchor class was renamed (different name in HEAD vs. working tree).
- Any class's stereotype changed.
- Multiple `<<Application>>` classes exist in the working tree.

See [`commands-queries-detectors-approach.md`](commands-queries-detectors-approach.md) § "Hard-fail conditions" for the operator instructions each error message carries.

A **degraded baseline** (HEAD has 0 or >1 Mermaid blocks) is not a hard-fail — it emits a Summary `_warning:_` line and the detector continues with the prose diff (the structural baseline is treated as empty).

---

## Schema-as-skill vs design-as-note

The schema (rendering rules, regex patterns, section ordering, footer-computation rules) lives in `application-spec:application-service-updates-report-template` — a condensed *contract* document auto-loaded by both detectors. The design rationale (why this shape, what trade-offs were considered, future consumers) lives in this note.

Same split as the domain side (`domain-spec:updates-report-template` skill + the absence of a notes equivalent — the domain side is older and pre-dates the notes convention; the application side adopts both).

The two detectors and any future consumer orchestrator should never duplicate schema content from the skill in their own bodies — they reference the skill and apply its rules verbatim. This is the load-bearing reason the schema is in a skill, not just an agent body.

---

## Open questions

1. **First-line-of-diff annotation in Modified per-method blocks.** Current schema lists touched sub-sections (`Signature`, `Surface`, etc.) without a first-line indicator. For very large signature changes this is sufficient — the consumer re-reads the post-update diagram. For tiny tweaks the schema may feel verbose. Trade-off: machine-parseability vs. human readability. Defer until a consumer feedback signal arrives.

2. **Should `_warning:_` lines be promoted to a Summary sub-section?** Currently appended as a single literal line after the Summary bullet list. Multiple warnings would stack. Alternative: a `### Warnings` sub-section under Summary. Defer until we have a second warning type to motivate the structure.

3. **Should orphan prose contribute to category dispatch?** Currently no — orphan prose is informational only. But a far-fetched prose-only edit could indicate the operator changed something significant the structural parser missed. Trade-off: false-positive cascades vs. missed signals. The domain detector takes the same "no" position; mirror it.

4. **Multi-update batching.** If the operator runs the detector N times before the downstream orchestrators catch up, the report overwrites each time. Same behaviour as the domain detector — fine for the spec axis, where re-running is cheap.

5. **Concurrent detector runs.** Two operators on parallel branches editing the same `<stem>.commands.md` produce a normal Git merge conflict on the diagram. The detector runs on whatever the merged working tree contains; not a detector bug.

6. **Surface-marker hard-fail.** Should a malformed `%%` comment (e.g. `%% surface: v1` with the trailing colon, which the surface-markers skill explicitly does not recognize) be flagged as a warning? Currently ignored as a generic comment per the surface-markers skill. The detector defers to the skill; no special-case handling. May warrant a Summary warning if it shows up in practice.

7. **Messaging-marker hard-fail.** Same shape — `%% Messaging - <name>` with an unexpected suffix is treated as a non-marker comment. May warrant a warning.

---

## Relationship to the other update reports

| Aspect | Domain | Persistence | Application (domain-axis) | Application (app-service axis) |
|---|---|---|---|---|
| File path | `<stem>.domain/updates.md` | `<stem>.persistence/updates.md` | `<stem>.application/updates.md` | `<stem>.application/{commands,queries}-updates.md` |
| Sibling of | the diagram | the command-repo-spec | the commands/queries specs + services report | the application diagram |
| Producer | `domain-spec:updates-detector` | `command-repo-spec-updates-writer` | `application-updates-writer` | `commands-updates-detector` / `queries-updates-detector` |
| Producer detection method | git diff of diagram + prose | git diff of working-tree spec vs HEAD | git diff of working-tree specs vs HEAD (3 files) | git diff of working-tree diagram vs HEAD |
| Grouping | per-class | per-artifact | per-artifact | per-method (for anchor) + per-class (non-anchor) |
| Footer | `## Affected Categories` (DDD categories) | `## Affected Artifacts` (file paths + verbs) | `## Affected Artifacts` (file paths + verbs) | `## Affected Categories` (per-axis categories) |
| Consumed by | spec updaters (4 layers) + domain code updater | persistence code updater | application code updater | application / rest-api / messaging spec updaters (future) |
| Lifecycle | transient (regenerated each run) | persistent (committed) | persistent (committed) | transient (regenerated each run) |
| First-run | not produced *(actually it is — empty)* | not produced | not produced | produced (first-run = all Added) |
| Hard-fails preempt emit | yes | yes | yes | yes |

The application-service-axis report lifecycle matches the domain `updates.md` — both are transient producer outputs of detectors, not persistent code-updater inputs. The other two (`<stem>.persistence/updates.md`, `<stem>.application/updates.md`) are persistent because they describe transitions of generated specs and feed code updaters. The new reports are upstream of *both* spec-updater paths, hence transient.

The chain shape after the new agents land (described more fully in [`commands-queries-detectors-approach.md`](commands-queries-detectors-approach.md) § "Chaining contract"):

```
diagram edit (one of three diagrams)
   │
   ▼
domain-spec:updates-detector ───────┐
                                    │
application-spec:commands-updates-detector ──┤
                                             │
application-spec:queries-updates-detector  ──┤
                                             │
                                             ▼
                              <axis>-updates.md reports
                                             │
                                             ▼
                              spec-updater orchestrators
                              (application / rest-api / messaging — all extended later)
                                             │
                                             ▼
                              <layer>/updates.md reports (transitions of generated specs)
                                             │
                                             ▼
                              code-updater orchestrators (later still)
```

Two transient detector layers feed into the spec updaters; the spec updaters emit persistent transition reports that feed the code updaters.
