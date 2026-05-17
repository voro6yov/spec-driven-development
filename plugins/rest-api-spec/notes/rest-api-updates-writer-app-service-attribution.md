# `rest-api-updates-writer` — App-Service-Axis Source Attribution (v2)

This note designs the v2 extension of `rest-api-updates-writer` that consumes the two app-service-axis detector reports (`<dir>/<stem>.application/commands-updates.md` and `<dir>/<stem>.application/queries-updates.md`) as additional `Source delta` enrichment sources, so that the per-section `Source delta:` bullets the writer emits become **axis-tagged**.

It is the REST-side counterpart to the application-spec writer's three-axis attribution (see [`plugins/application-spec/agents/application-updates-writer.md`](../../application-spec/agents/application-updates-writer.md) Step 5 and [`plugins/application-spec/skills/updates-report-template/SKILL.md`](../../application-spec/skills/updates-report-template/SKILL.md) § "Source delta format").

For the integration that landed the two new reports as orchestrator inputs (but explicitly punted Source-delta enrichment to a v2 follow-up), see [`commands-queries-integration-approach.md`](commands-queries-integration-approach.md) (Steps 4–5 and Open Questions). For the detector report schemas this design consumes, see [`../../application-spec/notes/commands-queries-updates-report.md`](../../application-spec/notes/commands-queries-updates-report.md).

For the v1 single-axis writer this design extends, see [`plugins/rest-api-spec/agents/rest-api-updates-writer.md`](../agents/rest-api-updates-writer.md) and [`plugins/rest-api-spec/skills/updates-report-template/SKILL.md`](../skills/updates-report-template/SKILL.md).

---

## Decision

Extend `rest-api-updates-writer` to consume three delta reports (instead of one) and emit **axis-tagged** `Source delta` bullets in every section that already carries one, plus new `Source delta` slots in the two sections that today carry none. The probe order and the rendered form mirror the application-spec precedent verbatim — the only REST-specific work is the per-section probe sub-order and the closed app-service-axis category set.

```
Source delta: [domain] <category>: <human_phrase>
Source delta: [commands-diagram] <category>: <human_phrase>
Source delta: [queries-diagram] <category>: <human_phrase>
Source delta: (unknown source)
```

Rejected alternatives:

- **Multi-axis tagging on one bullet** (`Source delta: [commands-diagram + domain] …`). Rejected — the application-spec precedent already settled on "more-specific axis wins, single tag" and changing the rendered form across plugins is out of scope. Multi-source endpoints are surfaced implicitly through the per-delta-bullet evidence already in the body (e.g. "Query parameter added: `mime_type`" + "Nested type added: `TextExtraction`" each individually trace to their own axes; the consumer can read them).
- **Axis-tagging on Affected Artifacts rows.** Rejected — the application-spec footer is axis-agnostic; the consumer walks per-section bodies for axis evidence. Adding a fourth column to the REST footer would diverge for no consumer benefit.
- **Per-delta-bullet `Source delta` instead of per-entry.** Rejected for v2 — a single Modified endpoint can contain several deltas with distinct axis explanations, and rendering one Source delta per bullet would balloon the report and complicate the consumer's parse rule. Deferred to v3 (see Open Questions).

---

## What changes in the schema

The schema in [`plugins/rest-api-spec/skills/updates-report-template/SKILL.md`](../skills/updates-report-template/SKILL.md) changes in three places. The rest of the schema is byte-stable.

### 1. Top-of-file sentinels — extend from one to three

**v1 (today):**

```
<!-- domain-updates-hash:<sha256> -->
```

**v2:**

```
<!-- domain-updates-hash:<sha256> -->
<!-- commands-updates-hash:<sha256> -->
<!-- queries-updates-hash:<sha256> -->
```

Canonical order: domain → commands-diagram → queries-diagram. Three consecutive HTML-comment lines on lines 1–3 (no blanks between them), one blank line, then the `# REST API Updates Report` heading. When an upstream report does not exist on disk, render its hash as `(none)`.

Splitting the sentinel per axis lets a domain-only edit produce a report whose commands/queries sentinels are byte-stable across the run, so the future `/rest-api-spec:update-code` consumer can skip-on-replay along whichever axis didn't move.

Direct copy of the application-spec precedent — same triple in the same order. The hash values themselves come from `shasum -a 256` of each report's working-tree bytes.

### 2. `## Summary` block — extend the upstream-source roster

**v1 (today):**

```
- Spec: <dir>/<stem>.rest-api/spec.md
- Pre-update spec hash: <sha256>
- Post-update spec hash: <sha256>
- Domain updates source: <dir>/<stem>.domain/updates.md (hash: <sha256>) | _none_
- Warnings:
  - <warning text>
```

**v2:**

```
- Spec: <dir>/<stem>.rest-api/spec.md
- Pre-update spec hash: <sha256>
- Post-update spec hash: <sha256>
- Domain updates source: <dir>/<stem>.domain/updates.md (hash: <sha256>) | _none_
- Commands-diagram updates source: <dir>/<stem>.application/commands-updates.md (hash: <sha256>) | _none_
- Queries-diagram updates source: <dir>/<stem>.application/queries-updates.md (hash: <sha256>) | _none_
- Warnings:
  - <warning text>
```

Two new `… updates source` lines, in the canonical order (commands before queries). Each renders `_none_` when its upstream report is absent. The Warnings block gains three new categories (one per missing-axis case, plus an aggregated all-three-missing warning) — see § "Failure modes" below.

### 3. `Source delta` slots — extend coverage and rendered form

**v1 (today):** Source delta slots exist only in Response Fields, Request Fields, and Parameter Mapping Changes (per-endpoint, on Added/Removed/Modified entries). Resource Basics and Endpoint Inventory carry no Source delta — by the v1 design, "they originate in the `<Resource>Commands` / `<Resource>Queries` diagrams, which `<stem>.domain/updates.md` does not capture, so they are not lookup targets."

**v2:** With the commands/queries detectors as input, those two sections gain Source delta slots; the existing three sections' Source delta bullets become axis-tagged.

Per-section slot table:

| Section | Source delta granularity | v1 slot | v2 slot |
|---|---|---|---|
| Resource Basics Changes | per-changed-field (in practice, only the `Surfaces` row can have a non-hard-fail change) | none | **new — one bullet on the `Surfaces:` line** (rendered immediately below the `Surfaces: was X, now Y (surface added: …)` line, indented one level) |
| Endpoint Inventory Changes | per-endpoint (Added / Removed / Modified) | none | **new — one bullet per endpoint entry** |
| Response Fields Changes | per-endpoint | yes (single-axis) | yes (axis-tagged) |
| Request Fields Changes | per-endpoint | yes (single-axis) | yes (axis-tagged) |
| Parameter Mapping Changes | per-endpoint | yes (single-axis) | yes (axis-tagged) |

The two new slots (Resource Basics → Surfaces field, Endpoint Inventory) follow the same `Source delta: [<axis>] <category>: <human_phrase> | (unknown source)` form as the existing three sections.

The five sections' rendered forms become:

```markdown
## Resource Basics Changes

- Resource name: was `<old>`, now `<new>` (_unchanged_)
- Plural: was `<old>`, now `<new>` (_unchanged_)
- Router prefix: was `<old>`, now `<new>` (_unchanged_)
- Surfaces: was `<old>`, now `<new>` (surface added: `<name>` | surface removed: `<name>`)
  - Source delta: [<axis>] <category>: <human_phrase> | (unknown source)
```

```markdown
## Endpoint Inventory Changes

### Surface: <name>

#### Added
- `<HTTP> <PATH>` (<operation>) → `<DomainRef>` — <query | command> endpoint
  - Source delta: [<axis>] <category>: <human_phrase> | (unknown source)
  - Description: <description>

#### Removed
- `<HTTP> <PATH>` (<operation>) — <query | command> endpoint
  - Source delta: [<axis>] <category>: <human_phrase> | (unknown source)

#### Modified
- `<HTTP> <PATH>` (<operation>)
  - Source delta: [<axis>] <category>: <human_phrase> | (unknown source)
  - Operation: was `<old>` → `<new>`
  - Domain Ref: was `<old>` → `<new>`
  - Description: was "<old>" → "<new>"
```

The Source delta bullet sits **first under the entry header**, before the per-cell `was X → Y` bullets — same position as in the existing three sections' Modified entries.

The existing three sections (Response/Request/Parameter Mapping Changes) keep their schemas; only the rendered string changes (`[<axis>] <category>: <human_phrase>` instead of bare `<category>: <human_phrase>`).

---

## What this design does NOT change

- **The seven top-level sections.** The schema's section list (Summary / Resource Basics / Endpoint Inventory / Response Fields / Request Fields / Parameter Mapping / Affected Artifacts) is unchanged. No new H2.
- **Surface-grouping.** The four per-table sections stay grouped by `### Surface: <name>` H3 sub-headings, with the same "omit unchanged surfaces" rule.
- **Within-section ordering.** Sub-bucket order (Added → Removed → Modified), endpoint ordering (by path), Modified-delta bullet order — all unchanged.
- **Affected Artifacts table.** The footer stays axis-agnostic: same columns (Path / Action / Driving section), same dispatch logic, same row-ordering rule. The Driving section column lists section names (e.g. `Response Fields Changes (Surface: v1)`); it never carries `[<axis>]` tags. **Axis information lives in the per-section `Source delta` bullets — the consumer that needs it walks the relevant section's body.**
- **Action vocabulary.** Closed set `add | modify | remove` — unchanged.
- **Determinism contract.** Byte-stable inputs → byte-stable output. The probe added in v2 is itself deterministic (alphabetical canonical tie-break inside each axis), so this contract widens but does not weaken.
- **Domain-axis attribution wording.** The existing domain-axis Source delta phrases (`<category>: <ClassName> <delta_phrase>`, e.g. `data-structures: FileInfo attribute text added`) are preserved verbatim — they just gain a `[domain] ` prefix. No re-wording, no normalization pass.

---

## Per-entry probe order

Probe rules follow the application-spec precedent: **app-service axis first (kind-appropriate side), then domain axis, then `(unknown source)` fallback**. The more-specific axis wins; the app-service axis describes the exact diagram-level edit, the domain axis the upstream cause.

Each REST entry is **either query-kind or command-kind**, determined as follows. The kind drives which app-service axis the writer probes first:

| Entry | Kind determination | Probe order |
|---|---|---|
| Resource Basics — Surfaces field | (no kind — cross-side) | commands first, then queries, then domain |
| Endpoint Inventory entry — Table 2 row | query | queries first, then domain (commands not probed) |
| Endpoint Inventory entry — Table 3 row | command | commands first, then domain (queries not probed) |
| Response Fields entry | query (Table 4 only ever has query endpoints) | queries first, then domain |
| Request Fields entry | command (Table 5 only ever has command endpoints) | commands first, then domain |
| Parameter Mapping entry | by `left_column` header — `Query Parameter` → query; `Command Parameter` → command | matching side first, then domain |

For entries where the app-service axis can't fire by definition (e.g. a Response Fields Modified whose only delta is a domain-driven nested-type field change — the commands diagram never mentions the nested type), the probe falls through to the domain axis. For entries where the domain axis can't fire (e.g. an Endpoint Inventory Added that traces to a new method declaration in the commands diagram and no domain-class lifecycle event), the probe stops at the app-service axis match.

When neither axis matches → `(unknown source)`.

---

## App-service-axis category vocabulary

The detector reports use the closed category set `methods`, `dependencies`, `raised-exceptions`, `external-interfaces`, `external-domain-events`, `surface-markers`, `messaging-markers` (per [`../../application-spec/notes/commands-queries-updates-report.md`](../../application-spec/notes/commands-queries-updates-report.md) § "Affected Categories computation").

Only a subset of these is REST-relevant. The rest are silently ignored by the REST writer's lookup — they never match any REST-side entry by construction:

| Category | REST-relevant? | Reason |
|---|---|---|
| `methods` | **yes** | The dominant axis-source for Endpoint Inventory and (via per-endpoint Tables 4/5/6 regen) for the three I/O sections |
| `surface-markers` | **yes** | Drives Resource Basics → Surfaces row; materializes / drops `## Surface:` sections in `spec.md` |
| `dependencies` | no | App-service constructor attributes don't surface in REST tables |
| `raised-exceptions` | no | Exception classes don't appear in the resource spec |
| `external-interfaces` | no | Application collaborators don't surface in REST |
| `external-domain-events` | no | Inbound events are messaging-axis, not REST |
| `messaging-markers` | no | Owned by `/messaging-spec:update-specs` |

So the REST app-service-axis Source delta vocabulary is, in practice, two categories: `methods` and `surface-markers`.

### Human-phrase shape

The writer constructs `<human_phrase>` mechanically from the matched detector-report entry. Proposed phrasing (matching domain-axis's class-name + lifecycle-keyword tuple shape):

**`methods` category** — from the detector's `## Per-Method Changes → ### <method_name>` block:

| Detector delta | REST Source delta phrase |
|---|---|
| Method added | `method <method_name> added` |
| Method removed | `method <method_name> removed` |
| Signature changed | `method <method_name> signature changed` |
| Surface remapped (`v1 → internal`) | `method <method_name> remapped from <old_surface> to <new_surface>` |
| Prose changed (per-method) | `method <method_name> prose changed` |

Multiple deltas on one method (e.g. signature changed + surface remapped) → emit the first in canonical order: `signature changed` > `remapped` > `prose changed`. (Same single-tag rule as the application-spec writer.)

**`surface-markers` category** — from the detector's `## Surface Markers` block:

| Detector delta | REST Source delta phrase |
|---|---|
| Surface added | `surface <name> added` |
| Surface removed | `surface <name> removed` |
| Method membership change | `method <method_name> moved to surface <name>` |

A `surface-markers` delta that produces both a surface-set change AND method-membership shifts → emit the surface-set change first (it's the upstream cause; method membership is the projection).

### Worked examples (illustrative only — not normative)

**Endpoint added in commands diagram:**

```
- Source delta: [commands-diagram] methods: method redact added
```

**Endpoint moved between surfaces (queries-side):**

```
- Source delta: [queries-diagram] methods: method find_files remapped from v1 to internal
```

**New surface added to the queries diagram:**

```
- Source delta: [queries-diagram] surface-markers: surface internal added
```

**Domain-driven nested-type field change (existing v1 case, now axis-tagged):**

```
- Source delta: [domain] data-structures: FileInfo attribute text added
```

**Endpoint added with both an app-service-axis explanation (method added) and a domain-axis explanation (the matching aggregate-root method also added):**

```
- Source delta: [commands-diagram] methods: method redact added
```

(The app-service axis wins per probe order — it's the more-specific explanation. The domain-axis match is silently dropped.)

---

## Per-section probe sub-rules

The probe for each section reuses the application-spec writer's general shape — read the matched axis report's structured form, look up the entry by its natural key, return the first match in the axis's canonical category order — but with REST-specific key derivation. This section enumerates the key-derivation rule per section.

### Resource Basics — Surfaces field

Key: the surface-set delta (`surface added: <name>` / `surface removed: <name>` parenthetical on the `Surfaces:` line).

Probe order — commands axis → queries axis → domain axis. Probe shape:

1. **Commands axis** (when `commands-updates.md` exists): look up `<name>` under `## Surface Markers → ### Surface Set → Added` / `Removed`. On match, emit `[commands-diagram] surface-markers: surface <name> added/removed`.
2. **Queries axis** (same lookup against `queries-updates.md`). On match, emit `[queries-diagram] surface-markers: surface <name> added/removed`.
3. **Domain axis** — surface markers are not a domain-axis category; this probe always falls through.
4. Fallback `(unknown source)`.

When both commands and queries diagrams gained the same surface (a coordinated multi-axis edit), commands wins by canonical order; the queries-axis match is silently dropped. Worth flagging in the implementation as an Open Question (see below) — a coordinated edit may deserve different attribution, but the application-spec precedent already accepts the loss.

### Endpoint Inventory — Added / Removed / Modified entry

Key: the `(<HTTP>, <PATH>, <operation>)` triple of the endpoint, with `<operation>` as the dominant signal (the operation name on the REST spec is the method name on the application-service diagram).

Probe order — kind-appropriate app-service axis → domain axis. The kind comes from the Table-2-vs-Table-3 row source (query vs command).

For a **query endpoint**:

1. **Queries axis**: look up `<operation>` under `## Per-Method Changes` in `queries-updates.md`. On match, derive the phrase per the `methods`-category table above.
2. **Domain axis**: look up `<operation>` against the aggregate root's `### <AggregateRoot>` block in `domain.per_class_changes` (member-add / member-remove for `<operation>`); if it matches a query-repo finder rename instead, look up under the `### Query<AggregateRoot>Repository` block. On match, emit `[domain] aggregates: <AggregateRoot> method <operation> added/removed` or `[domain] repositories-services: Query<AggregateRoot>Repository finder <operation> added/removed`.
3. Fallback `(unknown source)`.

For a **command endpoint**: symmetric — commands axis first, then domain (aggregate root or `Command<AggregateRoot>Repository`).

For a **Modified** endpoint where only the Description cell changed: there is no upstream-axis match by design (Description is a prose cell, not a structural one). Probe still runs; expected outcome is `(unknown source)`.

### Response Fields — per-endpoint entry

Key: the endpoint's `(<HTTP>, <PATH>, <operation>)` triple plus, when needed, the response DTO type name and per-delta-bullet entity names (a field name, a nested-type name).

Probe order — queries axis → domain axis. Per probe:

1. **Queries axis**: look up the endpoint's operation in `queries-updates.md` `## Per-Method Changes`. A match means the method itself changed (e.g. signature or returns-type updated, which often follows a DTO field change downstream). On match, emit `[queries-diagram] methods: …`. This is the explanation when the endpoint *appeared* (Added entry: a new method, hence a new Table 4 block) or *moved between surfaces* (Modified entry, with the per-method Source delta noting the surface remap).
2. **Domain axis**: this is where field-level deltas come from. The v1 probe rules (look up nested-type / DTO / value-object field changes in the domain detector's `## Per-Class Changes`) apply unchanged. On match, emit `[domain] <category>: <ClassName> attribute <field> added/removed/changed`.
3. Fallback `(unknown source)`.

The v1 multi-delta tie-break ("when a Modified endpoint's deltas trace to several distinct domain changes, attach the Source delta of the first delta bullet") generalizes naturally: the writer evaluates each delta bullet in render order and emits the first one whose probe succeeds. The implementation already iterates the deltas; v2 just adds the app-service axis at the front of the probe sequence and stops at the first match.

### Request Fields — per-endpoint entry

Same shape as Response Fields, with the commands axis substituted for queries. Probe order — commands axis → domain axis. Probe:

1. **Commands axis**: look up the endpoint's operation in `commands-updates.md` `## Per-Method Changes`. On match, emit `[commands-diagram] methods: …`.
2. **Domain axis**: same v1 probe rules.
3. Fallback.

### Parameter Mapping — per-endpoint entry

Same shape, with the kind-dispatch from the `left_column` header (`Command Parameter` → command-kind → commands axis first; `Query Parameter` → query-kind → queries axis first). Probe:

1. **Kind-appropriate app-service axis**: look up the operation in the matching detector report. A pure domain-driven Source-line-change delta (a `Constructed from query params …, → <Type>` whose constituent-field list shifted because the composite type gained/lost a field) **does not match** the app-service axis — the method signature on the diagram is unchanged; only the composite-type's field set changed. This probe falls through.
2. **Domain axis**: the v1 probe rule (look up `<Type>` + `<field>` in `## Per-Class Changes`) applies unchanged.
3. Fallback.

The intent: a parameter-mapping change driven by an app-service-axis method-signature change attributes to the app-service axis; one driven by a composite-type field shift attributes to the domain axis. The two cases are disjoint and the probe order surfaces each correctly.

---

## Failure modes — missing reports

Three optional inputs (any subset may be absent on disk). The writer handles each independently:

| Missing report | Effect on Source delta probes | Warning emitted (Summary → Warnings) |
|---|---|---|
| `<domain_updates_file>` | Domain-axis probe skipped; entries that would have attributed to domain fall through to `(unknown source)` if no app-service match exists | `domain updates source not found; domain-axis source_delta probes skipped.` |
| `<commands_updates_file>` | Commands-axis probe skipped | `commands-diagram updates source not found; commands-axis source_delta probes skipped.` |
| `<queries_updates_file>` | Queries-axis probe skipped | `queries-diagram updates source not found; queries-axis source_delta probes skipped.` |
| All three missing | Every probe is skipped; every Source delta renders `(unknown source)` | All three above, plus `no source attribution available; all source_delta values fell back to '(unknown source)'.` |

Each missing report is **non-fatal** — same contract as v1. The writer continues with whatever subset is on disk. This preserves standalone invocability:

- Operator-driven re-run (`@rest-api-updates-writer <domain_diagram>` invoked directly without an orchestrator wrapper): all three reports may be absent; the writer produces a useful report with `(unknown source)` everywhere.
- Cascade entry via `/rest-api-spec:update-specs`: Step 0 invokes both app-service detectors before the writer fires, so by the time the writer runs all three reports should exist. A missing report at this stage signals a detector bug or a filesystem race — surfaced via the warning, not as an error.

Direct copy of the application-spec writer's missing-report behaviour.

---

## Idempotency

The writer stays byte-stable on stable inputs. The full input set after v2:

1. Working-tree `<spec_file>` bytes.
2. `git show HEAD:<spec_file>` bytes.
3. `<domain_updates_file>` bytes (or absent).
4. `<commands_updates_file>` bytes (or absent).
5. `<queries_updates_file>` bytes (or absent).

Same five inputs → same output. The added probe logic is purely deterministic (canonical category order for tie-breaks within an axis; fixed app-service-first probe order across axes), so re-running on identical bytes produces identical reports.

The three sentinels at top-of-file pin each axis independently — a domain-only edit leaves the commands and queries sentinels byte-stable, and a commands-only edit leaves the domain and queries sentinels byte-stable. This is the consumer's primary skip-on-replay surface (matching the application-spec sentinel triple).

---

## Scope cut — what v2 does NOT do

Explicit out-of-scope list for this design:

- **No rewording of existing domain-axis attribution.** The phrases (`data-structures: FileInfo attribute text added`, etc.) are preserved verbatim; only the leading `[domain] ` prefix is new. A normalization pass over domain-axis phrasing is a separate, future change.
- **No new top-level sections.** The seven H2 sections stay exactly as v1.
- **No new columns in Affected Artifacts.** The footer stays axis-agnostic. A consumer needing per-axis dispatch reads the Source delta bullets in the per-section bodies.
- **No per-delta-bullet `Source delta` rendering.** v2 still emits one Source delta per *entry* (per endpoint, per surfaces-field change, etc.), not one per delta bullet inside the entry. A Modified endpoint with three deltas attributing to two distinct axes still renders one Source delta line — taken from the first delta bullet whose probe succeeds, in the skill's fixed bullet order. (See Open Question 1 below.)
- **No multi-axis tagging.** When two axes both match the same entry (rare, e.g. a coordinated commands + domain edit of one method), the more-specific axis (app-service > domain) wins and the other is silently dropped. The application-spec precedent already accepts this loss.
- **No changes to Affected Artifacts row-ordering rules.** Driving-section order, surface order, endpoint-path order, test-module-last — all unchanged.
- **No changes to the writer's hard-fail set.** Same conditions as v1 (missing spec, malformed Table 1, git-resolution errors). Missing detector reports are warning-not-error, same shape as the missing-domain-report case v1 already handles.
- **No changes to `/rest-api-spec:update-specs`'s orchestration.** The integration ([`commands-queries-integration-approach.md`](commands-queries-integration-approach.md)) already wired the two detector reports onto disk before this writer runs. v2 doesn't touch the orchestrator's Step 0, dispatch tier, or per-writer regen ordering — it only widens the writer's input set.

---

## Implementation plan (subsequent session)

Two artifacts change. Both belong in a single follow-up implementation session.

### 1. `plugins/rest-api-spec/skills/updates-report-template/SKILL.md`

- **Top-of-file sentinel block** — change from one line to three, in canonical order (domain → commands-diagram → queries-diagram), each with the same hash format and `(none)` fallback.
- **`## Summary` schema block** — add two new sources lines (`Commands-diagram updates source:` and `Queries-diagram updates source:`) immediately after the existing `Domain updates source:` line.
- **`## Summary → Warnings`** — extend the warning vocabulary with the four new categories listed in § "Failure modes".
- **`## Source delta format`** — add a new sub-section under "Rendering rules" matching the application-spec template's "Source delta format" block. Document the axis-tagged form, the `(unknown source)` fallback, the category vocabulary per axis (domain vocabulary unchanged; app-service vocabulary scoped to `methods` and `surface-markers`), and the human-phrase shape table.
- **`## Resource Basics Changes`** — add the new Source delta sub-bullet under the `Surfaces:` line in the schema block; document its kind ("Resource-Basics-side, surfaces-scoped") and its probe order in the per-section rules.
- **`## Endpoint Inventory Changes`** — add the new Source delta bullet (first bullet under each entry header) to the schema block in all three sub-buckets; document the probe order in the per-section rules.
- **`## Response/Request/Parameter Mapping Changes`** — replace the existing single-axis `Source delta: <short_phrase>` rendering with the axis-tagged form `Source delta: [<axis>] <category>: <human_phrase> | (unknown source)` in the schema block; reference the new "Source delta format" sub-section.

### 2. `plugins/rest-api-spec/agents/rest-api-updates-writer.md`

- **Frontmatter `description`** — extend to mention three-axis attribution (the application-spec writer's description is the model: "Three-axis `Source delta` attribution probes `<stem>.domain/updates.md`, `commands-updates.md`, and `queries-updates.md` (any may be absent) and tags matches with `[domain]` / `[commands-diagram]` / `[queries-diagram]`").
- **`## Arguments` and `## Path derivation`** — add `<commands_updates_file>` and `<queries_updates_file>` to the path-derivation block; mark both missing-is-non-fatal.
- **Step 1** — extend the missing-input handling: each of the three delta reports is independently optional; record absence per file and emit the matching warning at Step 6.
- **Step 5 (Source-delta enrichment)** — restructure into three sub-steps mirroring the application-spec writer's Step 5:
  - **5.1** Build per-axis lookup tables — one each for domain, commands, queries.
  - **5.2** Per-entry probe order — surface the kind-dispatch rule (Surfaces → cross-side commands-first; Endpoint Inventory → kind-side; Response → queries-side; Request → commands-side; Parameter Mapping → by `left_column`).
  - **5.3** Tie-breaking and idempotency — canonical category order within an axis; app-service axis wins cross-axis; idempotent on stable inputs.
- **Step 6** — extend hash-computation list with `commands_updates_hash` and `queries_updates_hash`. Extend warnings list with the four new categories.
- **Step 7** — render all three sentinels in the canonical order; render the two new Summary lines; substitute the axis-tagged Source delta values everywhere.
- **`## Hard-fail conditions`** — unchanged (no new hard-fails introduced).
- **`## Idempotency contract`** — extend the input set to five items (the two new reports).
- **`## What this agent deliberately does NOT do`** — extend the existing item ("does not re-diff the diagrams") to cover the two new sibling diagrams.

### 3. Plugin version bump

`plugins/rest-api-spec/.claude-plugin/plugin.json` `version` — bump (user-visible report-schema change).

---

## Open questions

1. **Per-delta-bullet `Source delta` rendering.** v2 keeps the single-Source-delta-per-entry rule. A Modified endpoint whose deltas split across two distinct axes (e.g. a query parameter added by the queries diagram + a nested-type field added by the domain) renders only the first match. Surfacing both would require per-delta-bullet Source-delta slots, which inflates report size and complicates the consumer's parse. Defer to v3, after consumer feedback signals the loss is material.

2. **Coordinated multi-axis edits.** When the operator edits the commands diagram, the queries diagram, *and* the domain diagram in one commit such that all three explain the same REST entry, the probe falls back to the first match in axis canonical order (commands > queries > domain). A coordinated edit may warrant `[multi]` tagging or a comment in the body. The application-spec precedent already accepts the lossy single-tag form; matching it is the path of least surprise.

3. **Attribution for the `Description:` cell in Endpoint Inventory Modified.** A Description-only change is a prose-cell hand-edit on the application-service diagram (or, more rarely, an LLM regen drift). Today the queries/commands detectors do emit a per-method prose-changed delta. Should a Description-only REST change attribute to `[commands-diagram] methods: method <operation> prose changed` or stay `(unknown source)`? Tentatively the former (it does describe the underlying edit), but the human phrase may feel weird for a pure REST report. Decide when implementing the probe.

4. **Should app-service-axis Source delta also fire for the surfacing of a new `## Surface:` section in `spec.md`?** A new surface added to the commands diagram materializes a brand-new `## Surface: <name>` block in `spec.md`, populating Tables 2/3 and per-endpoint Tables 4/5/6 within it. Each endpoint inside the new surface attributes individually to `[commands-diagram] methods: method <op> added`. The umbrella attribution (the surface itself) is captured in the Resource Basics → Surfaces row's new Source delta slot. So no extra rendering is needed — but worth confirming during implementation that the probe never emits both an `[commands-diagram] surface-markers: surface <name> added` AND a per-endpoint `[commands-diagram] methods: …` for endpoints inside the new surface; the latter is the right per-endpoint attribution. (The surface-markers attribution is reserved for the Surfaces-row entry.)

5. **Should Affected Artifacts row attribution be re-visited?** The current decision is "no — keep axis-agnostic, axis lives in body bullets." If the future `/rest-api-spec:update-code` skill discovers it wants per-axis dispatch at the row level (e.g. skip rows whose only attribution is queries when the consumer is the commands-side code updater — though no such consumer exists today), a fourth column or a side-channel via the Driving section text would re-open. Not blocking for v2.

---

## Relationship to the application-spec precedent

| Aspect | application-spec writer | rest-api-spec writer (v2) |
|---|---|---|
| Number of axes | three (domain, commands, queries) | three (domain, commands, queries) |
| Number of sentinels at top-of-file | three | three |
| Number of `… updates source` Summary lines | three | three |
| Axis-tag form | `[domain] / [commands-diagram] / [queries-diagram]` | identical |
| Fallback | `(unknown source)` | identical |
| Probe order | app-service axis first, then domain | identical |
| App-service category vocabulary | `methods`, `dependencies`, `raised-exceptions`, `external-interfaces` | `methods`, `surface-markers` (REST-relevant subset) |
| Per-entry Source delta granularity | per Added/Removed/Modified entry | identical |
| Footer axis-tagging | no | identical (no) |
| Missing-report behaviour | non-fatal; per-axis warning | identical |
| Idempotency contract | byte-stable on 5 inputs (3 specs + 3 delta reports = 6 stream pairs, in practice grouped to 5 effective inputs) | byte-stable on 5 inputs (1 spec working tree + 1 spec HEAD + 3 delta reports) |

The shape is intentionally identical wherever it can be. The REST writer differs only where it must — the per-section probe sub-rules are REST-specific because the REST schema is, but every cross-cutting concern (sentinel format, summary block, probe order, fallback, missing-input handling, axis-tag rendering) is a direct port. Future maintainers should treat the two writers as sister agents — a fix to one likely belongs in both.
