# Commands / Queries Detectors — Design

This note documents the design of two new agents that diff the **application-service diagrams** (`<dir>/<stem>.commands.md`, `<dir>/<stem>.queries.md`) against `git HEAD` and emit structured update reports for downstream consumption.

The agents are the application-service-axis analog of `domain-spec:updates-detector`. They fill the gap explicitly flagged in [`update-types.md`](update-types.md) § "The three-diagram trigger surface" and [`spec-updater-approach.md`](spec-updater-approach.md) § "What this updater does NOT cover".

For the catalog of delta types these agents must handle, see the sibling [`commands-queries-update-types.md`](commands-queries-update-types.md).
For the report schema they produce, see the sibling [`commands-queries-updates-report.md`](commands-queries-updates-report.md).
For the domain-side counterpart this design mirrors, see [`plugins/domain-spec/agents/updates-detector.md`](../../domain-spec/agents/updates-detector.md) and [`plugins/domain-spec/skills/updates-report-template/SKILL.md`](../../domain-spec/skills/updates-report-template/SKILL.md).

---

## Goal

Produce, for each application-service diagram, a structured report that:

- Lists every class lifecycle event, member-level change, relationship change, surface-marker change, messaging-marker change (commands only), and prose change in the working tree relative to `git HEAD`.
- Provides a `## Affected Categories` footer using a fixed vocabulary that downstream orchestrators dispatch on — same dispatch shape as the domain detector.
- Is the **single source of truth** for the application-service axis: future `/application-spec:update-specs`, `/rest-api-spec:update-specs`, and `/messaging-spec:update-specs` invocations consume it directly.
- Is **always written**, even when no changes are detected (downstream consumers expect a report to exist when they're chained from a detector run).
- Is **idempotent on stable inputs** — re-running against unchanged working tree + unchanged HEAD produces byte-identical output modulo LLM prose drift (the one prose summarization step per non-trivial section diff).

The agents do **not** mutate any spec sibling. They only emit their own report.

---

## Two agents, one shared template skill

### Why two agents

The commands and queries diagrams share most structural concepts but differ in three load-bearing ways:

| Concept | Commands | Queries |
|---|---|---|
| External `<<Domain Event>>` decls | yes | no |
| `%% Messaging - <consumer>` blocks | yes | no |
| Per-method `## Invariants → ### <method>` prose | typical | typically absent |

A combined detector would carry conditional branches in every parsing and rendering step. Two thin agents (`commands-updates-detector`, `queries-updates-detector`) — each ~120 lines, mostly delegating to the shared template skill — beat one larger agent with branching.

The split mirrors `commands-methods-writer` / `queries-methods-writer`, which the application-spec already establishes as the per-side convention.

### Why one shared template skill

The output schema is mostly identical: same Summary, same Class Lifecycle, same Per-Method Changes block shape, same Dependencies section, same Surface Markers section, same Affected Categories footer. The two queries-only omissions (no External Domain Events section, no Messaging Markers section) are handled by the skill's "omit when empty" rule — the same rule the domain template uses for empty Class Lifecycle sub-sections.

The skill is named **`application-spec:application-service-updates-report-template`**.

| File | Role |
|---|---|
| `plugins/application-spec/skills/application-service-updates-report-template/SKILL.md` | Single source of truth for the output schema, rendering rules, footer specification, stereotype-inference rules, surface-parser rules, messaging-parser rules. Auto-loaded by both detectors and (future) the consumer orchestrators. |
| `plugins/application-spec/agents/commands-updates-detector.md` | Thin agent for the commands side. ~120 lines; defers all rendering to the template skill. |
| `plugins/application-spec/agents/queries-updates-detector.md` | Thin agent for the queries side. ~110 lines; same shape minus External Events and Messaging Markers sections. |

The two notes ([`commands-queries-update-types.md`](commands-queries-update-types.md) for the *what*, this one for the *why* / *how*) and one skill ([`commands-queries-updates-report.md`](commands-queries-updates-report.md) for the schema) follow the existing application-spec convention.

---

## Inputs

| Argument | Required | Used for |
|---|---|---|
| `<application_service_diagram>` | yes (single positional arg) | the diagram file to diff. Used to recover `<dir>` and `<stem>` per `application-spec:naming-conventions`. |

The detectors take no other inputs — same shape as the domain detector.

---

## Output paths

Per [`commands-queries-updates-report.md`](commands-queries-updates-report.md) § "File location and naming":

| Detector | Output |
|---|---|
| `commands-updates-detector` | `<dir>/<stem>.application/commands-updates.md` |
| `queries-updates-detector` | `<dir>/<stem>.application/queries-updates.md` |

The folder `<dir>/<stem>.application/` is already owned by the application-spec generate-specs pipeline; the detectors do not own folder creation (`mkdir -p` is still safe to call defensively). If the folder is missing, this is a first-run-before-generate-specs case; the detector creates it.

---

## Workflow

The workflow mirrors `domain-spec:updates-detector` Step 0–8. Per-step contracts:

### Step 1 — Load both versions

1. **Working tree** — `Read` `<application_service_diagram>`. Missing file → hard-fail with a clear error; write nothing.
2. **HEAD** — recover the repo-root-relative path via `git ls-files --full-name --` then `git show HEAD:<repo_path>`. Empty stdout from `ls-files` → untracked file → first-run (HEAD version is empty). `git show` exit 128 with "does not exist in 'HEAD'" → same first-run path. Any other non-zero exit → hard-fail with a clear error.

Same shape as the domain detector. The detector is git-aware but does not require the working tree to be staged.

### Step 2 — Split each version into Mermaid block + prose

Identical to the domain detector:

- Opening fence regex `^```mermaid\s*$`, closing fence regex `^```\s*$`.
- Exactly one Mermaid block expected in the working tree; zero or many → hard-fail.
- Zero or many at HEAD → degraded baseline (Summary `_warning:_` line, not a hard-fail).
- Prose = concatenation of pre-opening + post-closing line blocks.

### Step 3 — Parse each Mermaid block

Parsing is inline (no shared parser in the codebase; both detectors keep parsing logic in-body, same as the domain detector).

For each version, extract:

1. **Class map** — `class_name → { stereotype, attributes, methods }`:
   - **Stereotype**: the verbatim `<<...>>` token (`<<Application>>`, `<<Interface>>`, `<<Domain Event>>` — commands only). Empty → infer from arrow shape (see *Stereotype inference rules* in the template skill).
   - **Attributes**: list of `(name, type, visibility)` from `-` / `+` sigils. For the application anchor class, these are the dependencies.
   - **Methods**: list of full method signatures.

2. **Relationship list** — list of tuples `(source, kind, target, label)`:
   - `kind ∈ {dependency (-->), realization (--())}` — composition (`*--`) and inheritance (`<|--`) are not used in commands/queries diagrams in practice but are parsed for completeness.
   - Label is the full `: <text>` after the arrow (e.g. `uses`, `manipulates`, `raises`, `takes as argument`, `returns`, `handles (Source, on_method)`).

3. **Surface marker map** — `method_name → surface_name`:
   - Default surface is `v1`. Each line matching `^\s*%%\s+([A-Za-z][A-Za-z0-9_-]*)\s*$` inside the anchor class body opens a new surface scope.
   - Per `rest-api-spec:surface-markers` § "Marker syntax" — the surface-markers skill is the single source of truth for the parsing rules.

4. **Messaging marker blocks** *(commands only)* — `consumer_name → list[(source_class, arrow, event_name, source_dest, on_method)]`:
   - Each line matching `^\s*%%\s+Messaging\s+-\s+(\S+)\s*$` opens a `%% Messaging - <consumer>` block.
   - Subsequent `--() : handles (Source, on_method)` / `--> : handles (Source, on_method)` lines populate the block until the next `%%`-comment or the closing `}` of the class.

5. **Per-method invariants prose** *(commands only, typical)* — keyed by `### <method>` or `### <ClassName>.<method>` headings under the `## Invariants` top-level section in the prose body.

The template skill spells out the parsing regexes verbatim.

### Step 4 — Compute structural diff

Pure set-difference logic (no LLM reasoning). Symmetric difference + per-name member-set diff:

- **Class-level**:
  - `added` / `removed` / `stereotype_changed` — same shape as domain detector.
  - **Renames are not detected** — a renamed class appears as both `removed` (old) and `added` (new).
- **Anchor-class member-level** (the application class only — the diagram invariant says exactly one):
  - `attribute_added` / `attribute_removed` / `attribute_changed` by name; surface type delta and visibility delta separately.
  - `method_added` / `method_removed` / `method_changed` by name; surface full signature delta verbatim.
- **Non-anchor-class member-level** (interfaces and external events):
  - Same member-diff rules. Useful for the consumer-impact analysis even though interface members don't directly appear in the anchor's spec.
- **Relationship-level**:
  - Full-tuple symmetric difference for `added` / `removed`.
  - Tuples sharing `(source, kind, target)` get `label_changed` separately so `: uses → : manipulates` doesn't render as remove + add.
- **Surface-level**:
  - `surface_added` / `surface_removed` from the surface-marker-name set diff.
  - `method_surface_changed` for methods present in both versions whose surface assignment differs.
- **Messaging-marker-level** *(commands only)*:
  - `consumer_added` / `consumer_removed` from the messaging-block-name set diff.
  - Per-consumer: `row_added` / `row_removed` / `row_changed` by full-tuple match.

### Step 5 — Compute prose diff section-by-section

Same shape as the domain detector:

- Split each prose body by ATX headings at levels 1–3. The text before the first heading is a synthetic `Preamble` section.
- For each section name present in either version, compute a unified diff (`diff -u` via Bash). Zero-byte diff → skip.
- For each section with a non-empty diff, generate a **one-paragraph natural-language summary** (the only LLM-driven step in the workflow). The summary describes the semantic change — e.g. "Tightened the precondition on `create` from 'no existing CacheType' to 'no existing CacheType and tenant_id is bound'."

For commands-side prose, a section heading matching `### <method>` or `### <ClassName>.<method>` (where `<ClassName>` is the anchor class) resolves to that anchor method. Resolved prose nests under the matching per-method block in Step 7. Unresolved prose lands in `## Orphan Prose Changes`.

For queries-side prose, the same resolution applies; in practice the queries diagram carries no `## Invariants` section, so every prose change is orphan.

### Step 6 — Compute the affected-categories footer

Apply the footer-computation rules from [`commands-queries-updates-report.md`](commands-queries-updates-report.md) § "Affected Categories computation". Inputs to the procedure:

- Class-level changes from Step 4 (added / removed sets; stereotype-changed is a hard-fail and never reaches here).
- Anchor-class member-level changes (attribute and method deltas).
- Non-anchor-class member-level changes (interface and external-event deltas).
- Relationship-level changes (especially `raises` labels — drive `raised-exceptions`).
- Surface-level changes.
- Messaging-marker-level changes (commands only).
- Non-empty prose section headings (resolved + orphan).

### Step 7 — Render the report

Render per [`commands-queries-updates-report.md`](commands-queries-updates-report.md). The schema is class-grouped for the anchor (per-method blocks) and per-class for non-anchor classes (one block per touched interface / external event).

Before writing, `mkdir -p "<dir>/<stem>.application"` to ensure the folder exists.

### Step 8 — Confirm

Print one sentence: `Updates report written to <dir>/<stem>.application/<side>-updates.md.`

---

## Hard-fail conditions

Owned by the detector. Each prints exactly one `ERROR:` line and writes nothing.

| Gate | Condition | Reason |
|---|---|---|
| 1 | Working tree has 0 or >1 Mermaid blocks | Unparseable. |
| 2 | Anchor class missing from working tree (no class with `<<Application>>` stereotype) | The diagram's anchor is gone; nothing to diff at the spec level. |
| 3 | Anchor class renamed (different name HEAD vs working tree) | Implies an aggregate-root rename — a coordinated multi-file rename the detector cannot describe. Route to `/application-spec:generate-specs`. |
| 4 | Any class's stereotype changed | Cross-category move; downstream orchestrators cannot dispatch by category if the category for a class is ambiguous. |
| 5 | Multiple `<<Application>>` classes in working tree | Diagram invariant violation. |

**Degraded baseline** (HEAD has 0 or >1 Mermaid blocks) is **not** a hard-fail — emitted as a Summary `_warning:_` line. Downstream orchestrators decide whether to abort on the warning. (Domain-side precedent: `/update-specs` 1a aborts; this matches.)

---

## Idempotency

Re-running with unchanged working tree + unchanged HEAD blob produces byte-identical output, modulo prose-summary LLM drift.

The prose-summary step is the only LLM-creative step. Same constraint as the domain detector. Treated as `git diff` noise, not an idempotency failure.

No sentinel comments are written. Every section is a snapshot of the HEAD-vs-working-tree diff; re-running on the same inputs reproduces the same content.

---

## Failure semantics

The detector either writes a complete report or writes nothing — partial writes are not allowed. If a hard-fail fires after Step 1 (e.g. Step 2 detects no Mermaid block, Step 3 detects multiple `<<Application>>` classes), no output file is created or modified.

Exception: when the report is already on disk from a prior run, a Step 1–5 failure leaves the prior report in place (the detector never deletes its output to "clean up" before a hard-fail). The operator is expected to re-run after fixing the trigger.

---

## What the detectors deliberately do NOT do

- **They do not invoke any other agent or skill at runtime.** Same shape as `domain-spec:updates-detector`. The template skill is auto-loaded; nothing else.
- **They do not consume the domain `updates.md`.** Cross-axis reconciliation is the orchestrator's job, not the detector's. The detectors describe one axis each.
- **They do not preserve hand-edits inside any spec.** No spec is touched.
- **They do not rename, move, or delete any file other than their own output report.**
- **They do not enforce semantic consistency with the domain diagram or the persistence spec.** A commands-diagram method whose `<AggregateRoot>` no longer declares the matching method is a downstream consumer's problem (the application-spec methods writer aborts on it). The detector simply reports the structural delta on the commands diagram.
- **They do not detect renames** of methods, attributes, surface markers, consumers, interfaces, or events. A rename surfaces as remove + add. Same convention as the domain detector.
- **They do not consume orchestrator-supplied state.** Stateless, standalone-invocable. The agents are the architectural twins of `domain-spec:updates-detector`.

---

## Chaining contract: where the detectors fit into the wider pipeline

The detectors are *producers*. They have no orchestrator at v1 — they are invoked manually or by a future application-service-axis orchestrator (see "Future work" below). Downstream consumers (`/application-spec:update-specs`, `/rest-api-spec:update-specs`, `/messaging-spec:update-specs`) are extended in later work to consume the reports.

Per the existing chaining contract documented in [`spec-updater-approach.md`](spec-updater-approach.md) § "Chaining contract":

```
existing chain (domain-axis only):
/update-specs <domain_diagram>
  Step 0   domain-spec:updates-detector
  ...
  Step 10  /persistence-spec:update-specs
  Step 11  /application-spec:update-specs    ← consumes <stem>.domain/updates.md only
  Step 12  /rest-api-spec:update-specs       ← consumes <stem>.domain/updates.md only
  Step 13  /messaging-spec:update-specs      ← consumes <stem>.domain/updates.md only
```

The new agents add a *second producer chain* parallel to the domain detector:

```
new chain (application-service-axis):
/application-spec:update-app-service-specs <domain_diagram>   (future orchestrator)
  Step 0a  application-spec:commands-updates-detector   ← if <stem>.commands.md changed
  Step 0b  application-spec:queries-updates-detector    ← if <stem>.queries.md changed
  Step 1   extended /application-spec:update-specs      ← consumes both updates.md and commands-updates.md / queries-updates.md
  Step 2   extended /rest-api-spec:update-specs         ← consumes commands-updates.md / queries-updates.md
  Step 3   extended /messaging-spec:update-specs        ← consumes commands-updates.md
```

The two producer chains are independent. An operator who edits only the domain diagram runs the domain `/update-specs` chain; an operator who edits only the commands diagram runs the application-service chain (or, more likely, runs `@commands-updates-detector` standalone and follows the report's footer). An operator who edits both runs both chains — the orchestrators are idempotent on the producer reports.

---

## Future work (not in this design's scope)

- **Application-service-axis orchestrator** — a new skill `application-spec:update-app-service-specs` that mirrors `/update-specs` (domain): invokes both detectors, then chains the extended downstream updaters.
- **Extended `/application-spec:update-specs`** — currently consumes `<stem>.domain/updates.md` only; needs a second consumption path for `commands-updates.md` and `queries-updates.md` to handle the app-service-axis. Per [`update-types.md`](update-types.md) § "The three-diagram trigger surface", this is *the* central open design decision.
- **Extended `/rest-api-spec:update-specs`** — currently a flat no-op on most domain changes; needs to consume `commands-updates.md` and `queries-updates.md` to refresh Tables 2/3 (endpoint inventory) and Tables 4/5/6 (request/response) when the application-service diagrams change.
- **Extended `/messaging-spec:update-specs`** — currently consumes `<stem>.domain/updates.md` for the internal-event axis; needs to also consume `commands-updates.md` for the messaging-marker axis (consumer add/remove, row changes, external event class changes).
- **Code-axis updaters** (`/application-spec:update-code`, `/rest-api-spec:update-code`, `/messaging-spec:update-code`) — consume the spec-axis reports to perform per-file code edits. Separate concern; not the detector's problem.

---

## Required artifacts

| Artifact | Status |
|---|---|
| `application-spec:application-service-updates-report-template` | **new skill** — single source of truth for the report schema |
| `plugins/application-spec/agents/commands-updates-detector.md` | **new agent** — thin commands-side detector |
| `plugins/application-spec/agents/queries-updates-detector.md` | **new agent** — thin queries-side detector |
| `plugins/application-spec/notes/commands-queries-update-types.md` | **new note** (sibling) — catalog of update types |
| `plugins/application-spec/notes/commands-queries-detectors-approach.md` | **this note** |
| `plugins/application-spec/notes/commands-queries-updates-report.md` | **new note** (sibling) — report schema rationale |
| `plugins/application-spec/.claude-plugin/plugin.json` | bump `version` |

No existing agent or skill is modified. The four writers, the exceptions specifier, the merger, and `services-finder` keep their current input/output behaviour. The current `/application-spec:update-specs` orchestrator is not modified — that extension is future work and gets its own design when it lands.

---

## Alternatives considered

| Approach | Status | Why |
|---|---|---|
| **One combined `application-service-updates-detector` agent that diffs both diagrams** | rejected | Conditional branches in every parsing and rendering step; two output files anyway (one per diagram) means no actual consolidation. |
| **One agent parameterized by `<side>` argument** | rejected | Same code path through both branches; saves one file at the cost of doubled body length. The split mirrors `commands-methods-writer` / `queries-methods-writer`, which the application-spec already accepted as the per-side convention. |
| **Two agents + two separate template skills (no shared template)** | rejected | The schemas are 90% identical; duplicated schema rules drift. One skill with "omit when empty" rules covers both. |
| **Combine detection into the existing `/application-spec:update-specs` orchestrator** | rejected | The orchestrator is currently scoped to the domain axis. Coupling it to a second axis at this layer means a single skill grows two consumption paths; testing and maintenance suffer. Better: keep the detector standalone, extend the orchestrator later. |
| **Two agents, one shared template skill (chosen)** | **accepted** | Mirrors the existing `commands-methods-writer` / `queries-methods-writer` split; the shared template skill encapsulates the common schema with the queries-side omissions handled by "omit when empty" rules; each agent stays thin and side-specific. |
