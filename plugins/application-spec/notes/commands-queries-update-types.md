# Commands / Queries Diagram Update Types

Analysis of how every kind of **application-service diagram** delta — captured by two new detector agents (`application-spec:commands-updates-detector`, `application-spec:queries-updates-detector`) into `<dir>/<stem>.application/commands-updates.md` and `queries-updates.md` — ripples into the application, REST API, and messaging specs.

This document covers the **app-diagram axis** explicitly flagged as out-of-scope in [`update-types.md`](update-types.md) § "The three-diagram trigger surface" and [`spec-updater-approach.md`](spec-updater-approach.md) § "What this updater does NOT cover". Read those first — they catalog the domain-driven axis. The two axes are complementary: every change to the application layer reaches it through *one* of them, never both.

For the schema of the detector output, see the sibling [`commands-queries-updates-report.md`](commands-queries-updates-report.md).
For the detector workflow, see the sibling [`commands-queries-detectors-approach.md`](commands-queries-detectors-approach.md).

---

## Scope

The two application-service diagrams are hand-authored Mermaid sources:

| Diagram | Path | Anchor class stereotype | Distinguishing constructs |
|---|---|---|---|
| Commands | `<dir>/<stem>.commands.md` | `<<Application>>` on `<Resource>Commands` | `<<Interface>>` collaborators; external `<<Domain Event>>` decls; `%% Messaging - <consumer>` blocks; surface markers `%% <name>`; per-method `## Invariants → ### <method>` prose with Preconditions/Flow/Postconditions |
| Queries | `<dir>/<stem>.queries.md` | `<<Application>>` on `<Resource>Queries` | `<<Interface>>` collaborators; surface markers `%% <name>`; no external events, no messaging markers, no per-method Invariants prose (typically) |

The two diagrams share most structural concepts: one application anchor class with constructor-attribute dependencies and public methods, plus external `<<Interface>>` collaborators bound by `--()` and `-->` relationships. Queries omits the messaging and external-events concepts.

The detectors run **independently per diagram**. Each emits its own report. Downstream updaters consume one or both reports as needed.

---

## The four trigger axes (post-split)

| Diagram | Axis | Detected by | Driven into |
|---|---|---|---|
| Domain | structural + prose | `domain-spec:updates-detector` → `<stem>.domain/updates.md` | persistence-spec, application-spec (Method Flow / postcondition prose only), messaging-spec (internal events), rest-api-spec (Tables 4/5/6 type tokens) |
| Commands | structural + prose | `application-spec:commands-updates-detector` → `<stem>.application/commands-updates.md` | application-spec (Dependencies + Method Specifications + Application Exceptions, commands side), rest-api-spec (Tables 2/3 + 4/5/6 for commands endpoints), messaging-spec (consumer Tables 2/3 + external `events.py` dataclasses) |
| Queries | structural + prose | `application-spec:queries-updates-detector` → `<stem>.application/queries-updates.md` | application-spec (Dependencies + Method Specifications + Application Exceptions, queries side), rest-api-spec (Tables 2/3 + 4/5/6 for queries endpoints) |
| *(unwritten)* Per-service code-side diff | n/a | future `/application-spec:update-code`, `/messaging-spec:update-code`, `/rest-api-spec:update-code` | code |

The four axes are *orthogonal*. A single operator edit touches one diagram (or one set of test edits) and rides through exactly one detector. No detector reads any other axis's report; the orchestrators (`/application-spec:update-specs`, `/messaging-spec:update-specs`, `/rest-api-spec:update-specs`) compose multiple reports when both an upstream and a same-layer report exist.

---

## Snapshot only — no append-only log

Like the domain-driven axis, every section of the new detectors' output is a pure snapshot of the diff between `git HEAD` and the working tree. No row-immutability contract, no migration-log analog. Re-running with byte-identical inputs (HEAD blob + working-tree blob) produces a byte-identical report. The detector itself is structurally simpler than `command-repo-spec-updates-writer` (no `§2.Migrations`-style append).

---

## Per-section sensitivity matrix

### `commands.specs.md`

| Application-service spec section | Commands-diagram-sensitive to | Queries-diagram-sensitive to |
|---|---|---|
| `## Dependencies` | constructor-attribute changes on `<Resource>Commands`; `<<Interface>>` class lifecycle and member changes; any `--() : uses` / `--() : raises` / `--() : manipulates` etc. relationship change with the anchor as source | — |
| `## Method Specifications` | public method add/remove/signature change; surface-marker assignment change (drives surface annotation on each Method block); `%% Messaging - <C>` row add/remove (drives the `Handles event` Method-block annotation); per-method Invariants prose (Preconditions / Flow / Postconditions sub-sections) | — |
| `## Application Exceptions` | `--() : raises` edges on the anchor class; constructor-arg shape of raising methods (which determines the exception ctor's params) | — |

### `queries.specs.md`

| Application-service spec section | Queries-diagram-sensitive to | Commands-diagram-sensitive to |
|---|---|---|
| `## Dependencies` | constructor-attribute changes on `<Resource>Queries`; `<<Interface>>` class lifecycle and member changes; any `--() : uses` / `--() : raises` etc. relationship change with the anchor as source | — |
| `## Method Specifications` | public method add/remove/signature change; surface-marker assignment change | — |
| `## Application Exceptions` | `--() : raises` edges on the anchor class | — |

### `services.md`

| Section | Commands-diagram-sensitive to | Queries-diagram-sensitive to |
|---|---|---|
| Service inventory | `<<Interface>>` add/remove (a service the commands diagram declares is no longer a `Domain Service` candidate if the domain diagram does not stereotype it `<<Service>>`); `<<Interface>>` referenced by a `--() : uses` edge | same shape |

### REST API `<stem>.rest-api/spec.md`

| Section | Commands-diagram-sensitive to | Queries-diagram-sensitive to |
|---|---|---|
| Table 1 (Resource Basics — `Surfaces` row) | `%% surface` marker set | `%% surface` marker set |
| Table 2 (Query endpoints, per surface) | — | public methods of `<Resource>Queries` + surface assignment |
| Table 3 (Command endpoints, per surface) | public methods of `<Resource>Commands` + surface assignment | — |
| Table 4 (Response fields, per endpoint) | command return shape (`<AggregateRoot>` reflected through the response serializer) | query return-type DTO (TypedDict shape from the queries diagram) |
| Table 5 (Request fields, per endpoint) | command parameter list | query parameter list |
| Table 6 (Parameter mapping, per endpoint) | command parameter list mapped to source vocabulary (Path / Query / Body / …) | query parameter list mapped to source vocabulary |

### Messaging `<stem>.messaging/<consumer>.md`

| Section | Commands-diagram-sensitive to |
|---|---|
| Table 1 (Consumer Basics) | none directly — derived from the `%% Messaging - <C>` group name + project package |
| Table 2 (Events to Consume) | rows of the `%% Messaging - <C>` block (each `<X>Commands <arrow> <Event> : handles (<Source>, <on_method>)` line is one row) |
| Table 3 (Event Parameter Mapping) | the `<AggregateRoot>Commands.on_<event>` handler's parameter list (a public method on the commands anchor) **and** the external `<<Domain Event>>` class's attribute list (when the row is `external`) |
| External event classes (`events.py`) | `<<Domain Event>>` classes declared directly on the commands diagram (each becomes one `@dataclass(DomainEvent)` in the consumer's `events.py`) |

---

## Update types (commands diagram)

Mirroring the L / M / R / P / C structure of the domain-axis catalog. The application-service version has two extra concept layers (S for surface-markers, X for messaging-markers) that the domain side lacks.

### L. Lifecycle updates (whole-class)

- **L1. Class added** — dispatch by stereotype:
  - **`<<Application>>`** → multiple-application hard-fail (the diagram invariant says exactly one).
  - **`<<Interface>>`** → new collaborator. → application Dependencies regen; new infrastructure stub + DI provider + autouse fake fixture in tests (handled by `/application-spec:update-code`).
  - **`<<Domain Event>>`** → external event class declared on this diagram. → messaging `events.py` regen (a new `@dataclass(DomainEvent)`); only matters once a `%% Messaging` row references it.
  - Any other stereotype → diagram-malformed (the commands diagram has no other class types).
- **L2. Class removed** — symmetric:
  - **`<<Application>>`** → diagram-anchor-missing hard-fail.
  - **`<<Interface>>`** → former collaborator gone. → application Dependencies regen; existing infrastructure stub / DI provider / autouse fake fixture targeted for removal by `/application-spec:update-code`.
  - **`<<Domain Event>>`** → external event class gone. → messaging `events.py` regen; if a `%% Messaging` row still references it → **ABORT** (consumer's Table 2 references a class that no longer exists).
- **L3. Stereotype changed** — **hard-fail** (route to `/application-spec:generate-specs`), mirroring all other detectors. A `<<Interface>>` ⇄ `<<Domain Event>>` flip changes the kind of artifact downstream consumers emit.

### M. Member updates (in-class)

- **M1. Anchor-class constructor attribute added / removed / type-changed** — these are the application service's *dependencies*. → application Dependencies regen; new / removed provider in `containers.py`; new / removed conftest fixture; new / removed infrastructure stub (the existing service-implementer dispatch decides whether the dep maps to a domain service ABC or an external-interface implementation, see `application-spec:services-finder`).
- **M2. Anchor-class public method added** — new application method. → application Method Specifications regen (new `### Method:` block); new REST API endpoint row in the appropriate surface's Tables 2/3 + new request/response serializer pair + new Table 4/5/6 entries; if the method is named `on_<event>` and a `%% Messaging` row binds to it → new messaging Table 2 row + new Table 3 sub-block + new handler stub in the consumer's `handlers.py`.
- **M3. Anchor-class public method removed** — application Method Specifications regen (block dropped); REST API endpoint dropped from the surface's Tables 2/3 (+ Table 4/5/6 entries pruned); if it was bound by a `%% Messaging` row → row + Table 3 sub-block + handler are dropped (or the `%% Messaging` row was already removed in the same edit; see X3).
- **M4. Anchor-class method signature changed** — parameter add/remove/rename/type-change, return-type change. → application Method Specifications regen (`### Method:` block's `Method Flow` section); REST API Tables 5 (Request Fields) + 6 (Parameter Mapping) regen for the affected endpoint; if the method is bound by a `%% Messaging` row → consumer's Table 3 (Event Parameter Mapping) regen.
- **M5. `<<Interface>>` attribute add/remove/type-change** — informational. → application Dependencies optionally re-renders the type token if it's surfaced in prose; no direct application-spec body change for unchanged method sets.
- **M6. `<<Interface>>` method add/remove/signature-change** — new collaboration surface. → application-spec Method Specifications may regen (a flow step may invoke the new method); infrastructure stub for the interface is regenerated (new method body to fill in).
- **M7. `<<Domain Event>>` attribute add/remove/type-change** — external event wire shape changed. → messaging `events.py` dataclass regen (the `@dataclass(DomainEvent)` field list); consumer Table 3 regen for every consumer that subscribes to the event as `external`.

### R. Relationship updates (cross-class topology)

The commands diagram uses `-->` for directed-dependency (typically external events) and `--()` for realization-with-label (the dominant arrow — `uses`, `manipulates`, `takes as argument`, `returns`, `raises`, `handles`).

- **R1. `-->` added/removed** (anchor → external `<<Domain Event>>`) — an external event was declared but its label-less relationship to the anchor was the wire. Treat as informational; the event class lifecycle (L1/L2) is the primary signal.
- **R2. `--() : uses` added/removed** (anchor → `<<Interface>>` or `<<Service>>` or `<<Repository>>` from domain) — a dependency was added/dropped. → application Dependencies regen; downstream code wires (containers/conftest/infrastructure).
- **R3. `--() : raises` added/removed** (anchor → exception class) — an exception was added/removed to the raised set. → application Application Exceptions regen (the exception class spec is appended/removed). The exception's constructor and message are derived from the raising method's args + the preceding repo-call's args (the pair-derived rule lives in `application-spec:application-exceptions-specifier`).
- **R4. `--() : manipulates` added/removed** (anchor → `<<Aggregate Root>>`) — informational; the anchor manipulates the aggregate it commands by construction. Not separately tracked.
- **R5. `--() : takes as argument` added/removed** (anchor → `<<Value Object>>` / `<<TypedDict>>` / `<<Query DTO>>`) — informational; the parameter list of the methods is the source of truth, this label is documentation.
- **R6. `--() : returns` added/removed** (anchor → return type) — informational; the method signature carries the return type.
- **R7. `--() : handles` added/removed** (anchor → `<<Domain Event>>`, inside `%% Messaging - <C>` block) — this is the X-axis signal (see below), not a generic R signal.
- **R8. Label changed** (`: uses` → `: manipulates`) — usually a no-op for downstream; informational.
- **R9. Inheritance / composition between non-anchor classes** — `<<Interface>>` and `<<Domain Event>>` are leaves in practice; ignore unless the diagram grows polymorphic.

### P. Prose updates (semantic, not structural)

The commands diagram carries a `## Invariants` section with one `### <ClassName>.<method>` (or `### <method>`) heading per public method, each containing Preconditions / Flow / Postconditions / *(optional)* Invariants-or-Constraints bullets. The queries diagram typically carries no per-method prose.

- **P1. Per-method invariants prose change** — `### <ClassName>.<method>` heading body diffed. → application Method Specifications regen (the methods writer reads this prose as advisory description). The writer may keep its output byte-stable if the prose change touched no signal channel (Purpose / Preconditions / Flow / Postconditions); the detector reports the prose delta regardless.
- **P2. Orphan prose change** — `### Preamble`, `### Notes`, `### Glossary`, or any heading that doesn't parse to a method. Advisory only; rendered under `## Orphan Prose Changes`. Downstream re-runs may be byte-stable.

### S. Surface marker updates

Surface markers are Mermaid line comments inside the anchor class body. The parsing rules live in `rest-api-spec:surface-markers`. The default surface is `v1` when no marker is present.

- **S1. Surface added** (new `%% <name>` block appears) — REST API `## Surface: <name>` section emerges in `<stem>.rest-api/spec.md`; the per-surface package layout (`api/endpoints/<surface>/`, `api/serializers/<surface>/`) needs scaffolding; Table 1's `Surfaces` row updates.
- **S2. Surface removed** (last method under a `%% <name>` marker drops, or the marker itself is dropped) — REST API `## Surface: <name>` section is dropped; per-surface package targeted for cleanup; Table 1 updates.
- **S3. Method moved between surfaces** — a method that was under `%% v1` is now under `%% internal` (or vice versa). The application spec doesn't care (method is the same); REST API needs to move the endpoint row from one Tables-2/3 to another and move the serializer module file.
- **S4. Default-fallback boundary shift** — methods exist before the first marker (implicitly `v1`) and a `%% v1` marker is added explicitly before them, or vice versa. Byte-neutral semantically (still `v1`) but the detector reports it for completeness.

### X. Messaging marker updates (commands only)

`%% Messaging - <consumer-name>` blocks group `--() : handles` lines that bind external or internal events to the anchor's `on_<event>` handlers. The block's name is the consumer name. Parsing rules live in `messaging-spec:event-tables-template`.

- **X1. Consumer added** (new `%% Messaging - <C>` block appears) — a new consumer subscribes; the messaging consumer spec (`<stem>.messaging/<C>.md`) needs initialization (`consumer-spec-initializer`); the consumer subpackage (`<pkg>/messaging/<C>/`) needs scaffolding (`consumer-scaffolder`).
- **X2. Consumer removed** (entire `%% Messaging - <C>` block dropped) — the consumer spec + subpackage are targeted for cleanup.
- **X3. Row added/removed within a consumer** — `<X>Commands --() <Event> : handles (<Source>, <on_method>)` line added or removed inside an existing block. → consumer Table 2 regen; consumer Table 3 regen for the new row; handler stub added/removed in `handlers.py`; if `external` event class new → `events.py` regen.
- **X4. Row signature changed** — same `<X>Commands --() <Event> : ...` but different `(<Source>, <on_method>)` triple. → Table 2 row updated; Table 3 regen (the handler binding shifted); handler function name may change (see `consumer-scaffolder` collision rule).
- **X5. Arrow flipped between `-->` (external) and `--()` (internal)** — same event name, different type classification. Table 2's `Type` column flips between `external` and `internal`; Table 3 regen (external rows resolve fields from external event class, internal rows from domain diagram's `<<Domain Event>>`); `events.py` may need to add/remove the external dataclass.

### C. Composite / derived signals

- **C1. Pure prose change, zero structural** — re-run the methods writer; output usually byte-stable. Same semantics as the domain axis.
- **C2. Pure structural, zero prose** — standard regen path; the methods writers don't consume prose for the structural bits.
- **C3. `Affected Categories` empty (no structural deltas, no class lifecycle, no anchor-method or anchor-dependency change, no surface/messaging marker change)** — no-op for every consumer. Orphan prose is the only possible content.
- **C4. `Affected Categories` spans multiple** — fan out to all matching consumers; each consumer's update-specs orchestrator decides what to regenerate from its own footer parse.
- **C5. First-run / degraded baseline** — `_warning: HEAD ..._` line in the report's Summary. Downstream consumers hard-fail (route to `/application-spec:generate-specs`).

---

## Update types (queries diagram)

The queries detector handles a strict subset of the commands detector's categories:

| Category | Applicable to queries diagram? |
|---|---|
| L1–L3 (class lifecycle) | Yes — `<<Application>>` and `<<Interface>>` only (no `<<Domain Event>>`) |
| M1 (anchor constructor attrs) | Yes |
| M2–M4 (anchor public methods) | Yes |
| M5–M6 (interface members) | Yes |
| M7 (event attrs) | N/A (no events on queries diagram) |
| R1, R7 (relationships involving events / messaging) | N/A |
| R2–R6, R8–R9 (other relationships) | Yes |
| P1–P2 (prose) | Rare in practice (queries diagrams typically carry no Invariants section), but supported by the same prose-diff machinery |
| S1–S4 (surface markers) | Yes |
| X1–X5 (messaging markers) | **N/A — queries diagrams have no `%% Messaging` blocks** |

The same report schema applies; queries reports simply omit the inapplicable top-level sections (`## External Domain Events`, `## Messaging Markers`) and the `Messaging:` field within per-method blocks.

---

## Mapping `## Affected Categories` → consumer impact

The footer vocabulary is fixed (see [`commands-queries-updates-report.md`](commands-queries-updates-report.md) § "Affected Categories"). This table maps each category to the consumer artifacts it drives.

| Category | Drives in `application-spec:update-specs` | Drives in `rest-api-spec:update-specs` | Drives in `messaging-spec:update-specs` |
|---|---|---|---|
| `methods` | `## Method Specifications` regen for the dirty side | Tables 2/3 regen (endpoint inventory) + Tables 4/5/6 regen for the affected endpoint | (commands only) Tables 2 + 3 regen if the method is an `on_<event>` handler bound by a `%% Messaging` row |
| `dependencies` | `## Dependencies` regen for the dirty side | — | — |
| `raised-exceptions` | `## Application Exceptions` regen for the dirty side; exception class definitions in `domain/<aggregate>/exceptions.py` (driven by `/application-spec:update-code` later) | error-handler mapping in `<api_pkg>/error_handlers.py` (driven by `/rest-api-spec:update-code` later) | — |
| `external-interfaces` | `## Dependencies` regen for the dirty side; downstream infrastructure stubs + DI providers + fakes (driven by code-updater later) | — | — |
| `external-domain-events` *(commands only)* | — | — | external event dataclasses in consumer `events.py`; Table 3 regen for `external` rows referencing the event |
| `surface-markers` | — | Table 1 `Surfaces` row; per-surface section set; per-surface package layout regen (only if surfaces added/removed); per-method endpoint relocation (only if methods moved between surfaces) | — |
| `messaging-markers` *(commands only)* | — | — | per-consumer spec lifecycle (init/teardown); Table 2 + Table 3 regen for affected consumers; consumer subpackage scaffold/teardown |

A multi-category report (e.g. `methods + raised-exceptions + surface-markers`) fans out to all three consumers; each consumer's orchestrator parses the footer for the categories it owns and ignores the rest.

---

## Hard-fail conditions

Hard-fails are owned by the detector (block production of the report) — downstream consumers report the failure verbatim via the report's `_warning:_` channel or refuse to process the report. The decisions from the design interview:

1. **Working-tree diagram has 0 or >1 Mermaid blocks** — unparseable. Detector aborts, writes nothing.
2. **Anchor class missing or removed in working tree** — the diagram's anchor is gone. Detector aborts; route to `/application-spec:generate-specs`.
3. **Anchor class renamed** (different name in HEAD vs. working tree) — this implies an aggregate-root rename (multi-file rename territory). Detector aborts; route to `/application-spec:generate-specs`.
4. **Any class's stereotype changed** — cross-category move; same gate as `domain-spec:updates-detector` 1b.
5. **Multiple `<<Application>>` classes in working tree** — diagram invariant violation.

Degraded baseline (HEAD has 0 or >1 Mermaid blocks) is **not** a hard-fail — emitted as a Summary `_warning:_` line mirroring the domain detector. Downstream consumers (orchestrators) decide whether to abort on the warning.

---

## Out-of-scope but worth flagging

- **Code regen** — detection stops at the report. The eventual `<aggregate>_commands.py` / `<aggregate>_queries.py` body changes, REST API endpoint module body changes, messaging `events.py` / `handlers.py` body changes, etc., are owned by the per-layer code updaters (`/application-spec:update-code`, `/rest-api-spec:update-code`, `/messaging-spec:update-code`) that will consume the reports.
- **Cross-detector reconciliation** — if a commands-diagram method add and a domain `<<Domain Event>>` rename happen in the same operator edit, both detectors run, both reports are emitted, both consumers see their respective signals. The detectors do not coordinate. The orchestrators do: `/messaging-spec:update-specs` already consumes both `<stem>.domain/updates.md` and per-consumer specs; once the commands report is wired, it joins the same union.
- **Hand-edits inside the application specs** — the detectors do not preserve them. The detector is a pre-existing condition — it merely says what changed in the diagrams. Hand-edits inside generated specs are the orchestrator's concern (currently dropped) and the code-updater's concern (probably will surface as warnings).
- **Concurrent detector runs** — two operators on parallel branches editing the same `<stem>.commands.md` produce a normal Git merge conflict on the diagram, resolved by standard merge tooling. The detectors run on whatever the merged working tree contains; not a detector bug.
- **Diagram-axis updates outside the supported set** — anything not categorized above (e.g. Mermaid `note for` directives, embedded `direction LR/TB` config, link styles) is ignored. The detector parses the structural surface, not the cosmetic surface.

---

## Relationship to the domain-axis catalog

The two axes never overlap structurally. A single edit touches one diagram; the matching detector emits the matching report; downstream orchestrators consume one or both. The categories the detectors emit are *non-overlapping vocabularies* — `methods` on a commands-updates report means an application-service method changed, while `aggregates` on a domain `updates.md` means a domain aggregate class changed. Downstream orchestrators dispatch per category without ambiguity.

When an operator edit is *semantically* coordinated across diagrams (e.g. renaming a domain aggregate root *and* its commands/queries diagrams in one commit), the detectors run independently and the per-layer orchestrators surface the corresponding hard-fails in each report. The operator follows each route to recovery; there is no master-orchestrator reconciliation. This mirrors the domain ↔ persistence ↔ application chain that exists today.
