# Messaging Updates Report — Design

This note describes the design of `<dir>/<stem>.messaging/updates.md`, the **messaging-side analog of the domain, persistence, and application updates reports**.

It is the input contract a future `/messaging-spec:update-code` skill will consume to surgically update generated messaging artifacts (the per-consumer `messaging/<consumer>/handlers.py` bodies and the handler integration tests) without re-running `/messaging-spec:generate-code` from scratch — analogous to how `domain-spec:update-code` consumes the domain `updates.md`, the future `/persistence-spec:update-code` consumes the persistence `updates.md`, and the future `/application-spec:update-code` consumes the application `updates.md`.

For the catalog of *upstream* domain deltas that drive the messaging spec updater, see [`update-types.md`](update-types.md).
For the spec updater design that produces the artifacts this report captures, see [`spec-updater-approach.md`](spec-updater-approach.md).
For the counterparts this design is modelled on, see [`plugins/persistence-spec/notes/updates-report.md`](../../persistence-spec/notes/updates-report.md) and [`plugins/application-spec/notes/updates-report.md`](../../application-spec/notes/updates-report.md).

**The dominant structural difference vs the persistence/application reports:** there is no single spec file. `<dir>/<stem>.messaging/` holds *N* consumer specs (`<consumer_name>.md`), and a domain change touches a *subset* of them — exactly those whose Table 2 has an `internal` row naming a changed domain event. So this report is **consumer-keyed**, and the per-consumer change body is tiny: the only domain-sensitive table is Table 3's `Event Field` column for `internal`-event sub-blocks (see `update-types.md` § *The trigger surface*).

---

## Goal

Capture, in structured form, every change `/messaging-spec:update-specs` made to the consumer specs under `<stem>.messaging/` — and every consumer it *couldn't* update without an operator reconciling the commands diagram — in a shape that lets a downstream code updater dispatch per-consumer artifact updates without re-diffing the specs.

The report:

- Is **persistent** (committed alongside the consumer specs) so it survives between `update-specs` and `update-code`.
- Is **consumer-keyed and per-artifact**: it lists *which consumers changed* (and which generated files of theirs the code updater must touch), not which domain classes changed. The domain `updates.md` already covers per-class deltas; this report projects them onto consumer specs and their generated submodules.
- Is **stable** between identical inputs — same domain `updates.md` hash + same pre-update consumer specs → byte-identical report.
- Is **self-contained** for the code updater: combined with the updated consumer specs, it has everything needed to compute the on-disk edits.

---

## Lifecycle and ownership

### Producer

`<stem>.messaging/updates.md` is produced by `/messaging-spec:update-specs` as its **terminal step** (see [`spec-updater-approach.md`](spec-updater-approach.md) § Step 5 — the producer-step number; the operator one-liner that currently is "Step 5" becomes the renumbered last step). Emitted in the same run that regenerates the affected consumers' Table 3s and records the aborted-and-reconcile consumers.

The architecture mirrors the persistence/application asymmetry vs the domain side: the domain `updates.md` is produced by a standalone detector (`domain-spec:updates-detector`) because the Mermaid diagram is human-edited and must be diffed to recover operator intent. The consumer specs are *generated* — the writer detects changes by diffing each consumer spec's working tree against `git HEAD`, requiring no separately-maintained pre-update snapshot, and also records the per-consumer "aborted" outcomes the orchestrator computed in its Step 2 gate.

| Aspect | Domain | Persistence | Application | Messaging |
|---|---|---|---|---|
| Source of truth | Mermaid diagram (human-edited) | command-repo-spec (generated) | three generated specs | *N* consumer specs (generated) |
| Detection | git diff of diagram + prose | git diff of working-tree spec vs HEAD | git diff of working-tree specs vs HEAD | git diff of each working-tree consumer spec vs HEAD |
| Re-diffing | unavoidable | tractable; producer already has deltas | tractable | tractable |

#### Alternative considered: standalone `messaging-spec:updates-detector` (commands-diagram axis)

A standalone detector for `<stem>.commands.md` (its `%% Messaging` blocks, external `<<Domain Event>>` nodes, and `on_<event>` signatures) is a *separate* concern — it would be the producer of a *different* report contract (a commands-diagram delta report), not a replacement for this one. It is deliberately out of scope (see `spec-updater-approach.md` § *Out of scope*). When/if it lands, `/messaging-spec:update-specs` consumes both `<stem>.domain/updates.md` and that report in one pass and this `updates.md` schema naturally absorbs the additional deltas (a consumer whose markers changed surfaces with a different `Source delta` and possibly a Table 2 regen note — see *Open questions*).

### Consumer

`<stem>.messaging/updates.md` is consumed by the future `/messaging-spec:update-code` skill — an analog of `domain-spec:update-code` and the future `/persistence-spec:update-code` / `/application-spec:update-code`. The code updater walks the report's `## Affected Artifacts` footer to dispatch per-file updates, reading the `## Consumer Changes` bodies for the structured delta details.

It is **not** chained automatically into `/update-specs` (domain). Code regeneration is a separate operator-driven step: spec updates on every diagram edit; code updates on demand.

### First-run pipeline

`/messaging-spec:generate-code` does **not** produce this report. The report describes deltas, not absolute state. On first run, `/messaging-spec:generate-code` runs against the consumer spec directly with no report to consult.

---

## Producer architecture

The producer is split into two artifacts that mirror the persistence-side `updates-report-template` skill + `command-repo-spec-updates-writer` agent pair (and the application-side `updates-report-template` + `application-updates-writer` pair):

### Reference skill: `messaging-spec:updates-report-template`

A condensed *contract* document — schema + rendering rules, not design rationale — auto-loaded by:

- The producer agent (when rendering the report).
- The future `/messaging-spec:update-code` consumer (when parsing the report).

Covers:

- Top-of-file sentinel (`<!-- domain-updates-hash:<hash> -->`) and the `sha256` hash format.
- Top-level section order (`## Summary` → `## Consumer Changes` → `## Affected Artifacts`).
- The per-consumer block convention: status keyword (`updated` | `aborted` | `unaffected`), pre/post hash pair, the list of regenerated Table 3 sub-blocks (for `updated`), the dangling-event + reconcile instructions (for `aborted`), the `_no changes_` placeholder (for `unaffected`).
- Closed status vocabulary (`updated | aborted | unaffected`) and closed action-verb vocabulary (`add | modify | remove`) for the footer.
- Within-section ordering rules: consumers alphabetical by name; within a consumer's `updated` block, sub-blocks ordered like Table 3 (external block alphabetical, then internal block alphabetical — though only `internal` sub-blocks ever appear here, since the domain axis never touches `external` rows).
- `## Affected Artifacts` table shape (path + action + driving-consumer columns).

The split between schema-as-skill and design-as-notes is the same one the domain, persistence, and application sides draw — the *why* lives here in the notes; the *how to render and parse* lives in the skill.

### Agent: `messaging-updates-writer`

A small, deterministic agent invoked at the tail of `/messaging-spec:update-specs` — also standalone-invocable. Composes `<stem>.messaging/updates.md` by diffing each consumer spec's working tree against `git HEAD`; reads the sibling domain `updates.md` only as an enrichment source for `Source delta` lookups; receives the orchestrator's per-consumer abort list (or recomputes it from the domain `updates.md` + each consumer's Table 2 `internal` rows). Does not otherwise consult orchestrator-supplied runtime state.

The workflow shape mirrors `command-repo-spec-updates-writer` and `application-updates-writer`: takes a single positional arg, recovers each consumer's pre-update baseline via `git show HEAD:<file>`, writes a sibling report. The messaging side is structurally the simplest of the three — one kind of change body (Table 3 sub-block regen), no migrations-log row diffing, no destructive-change flagging, no LLM-creative prose summarization.

**Arguments:**

- `<domain_diagram>` — first and only positional arg. Used solely to recover `<dir>` and `<stem>` (and the derived `<commands_diagram>`) per `messaging-spec:naming-conventions`. The diagram itself is not parsed.

**Reads (filesystem):**

1. **Working-tree consumer specs** — every `<dir>/<stem>.messaging/*.md` except `updates.md` itself (must contain at least one; otherwise the report is a degenerate "no consumers" no-op — see *Determinism*).
2. **HEAD consumer specs** — recovered via `git ls-files --full-name` + `git show HEAD:<repo_path>` per file. First-run-of-a-consumer handling: missing-at-HEAD → empty baseline; the whole consumer spec is "newly tracked", but on the domain axis this is informational only (a brand-new consumer's Table 3 was just generated, not "updated by this run").
3. **Domain updates report** — `<dir>/<stem>.domain/updates.md` (sibling). Missing is non-fatal; `Source delta` falls back to `(unknown source)` and the Summary's domain-source line renders `_none_`. Used to compute the changed-domain-event set and to enrich each `updated` block's `Source delta`.
4. **Commands diagram** — `<dir>/<stem>.commands.md` (read-only), to read each consumer's `%% Messaging - <consumer>` block and recover its `internal` Table 2 rows (authoritative; the consumer spec's Table 2 mirrors it).

**Reads (auto-loaded skills):** `messaging-spec:naming-conventions`, `messaging-spec:updates-report-template`.

**Output:** `<dir>/<stem>.messaging/updates.md`, written from scratch (replaces any prior file).

**Determinism:** structured-input-driven, not LLM-creative. Re-running with byte-identical inputs (working-tree consumer specs + HEAD blobs + domain `updates.md` + commands diagram) produces a byte-identical report. The `## Affected Artifacts` table is mechanically derived: each `updated` consumer `C` (with snake-case dir name `<C_snake>`) emits `messaging/<C_snake>/handlers.py | modify` and `tests/integration/messaging/<C_snake>/test_<C_snake>_handlers.py | modify`; nothing else is touched on the domain axis (`events.py` is external-only; `dispatcher.py` is routing-structural; `constants.py` and the `containers.py` / `entrypoint.py` / `__main__.py` wiring are untouched by an internal-event attribute change).

**Standalone invocability:** supported. The writer reads everything from disk (working tree + git HEAD + sibling files + commands diagram), so it does not require an orchestrator wrapper. Useful for testing, operator-driven recovery (e.g. when a prior `update-specs` run hard-failed mid-Step-4), and CI verification. The orchestrator (`/messaging-spec:update-specs`) is one of several callers.

### Workflow integration

Slots into `/messaging-spec:update-specs` as its terminal producer step (see [`spec-updater-approach.md`](spec-updater-approach.md) for the full pipeline):

```
Step 0  Preflight + consumer discovery
Step 1  Hard-fail gate
Step 2  Abort-and-reconcile gate           (per-consumer aborts recorded)
Step 3  Compute affected consumers
Step 4  Regenerate Table 3 per affected consumer  (event-tables-writer? + event-fields-writer, parallel)
Step 5  Emit updates.md                    (messaging-updates-writer)        ← this artifact
Step 6  Report (operator one-liner)
```

The orchestrator does not need to capture pre-update consumer-spec content — the writer recovers it via `git show HEAD:<file>` per consumer. It *does* hand the writer (or the writer recomputes) the per-consumer abort list from Step 2. This keeps the orchestrator near-stateless and lets the writer also run standalone.

The writer runs on every successful spec-update run, including no-op early-exit cases (Step 0 "no consumers", Tier-3 "nothing affected") — those produce a report whose `## Consumer Changes` lists every consumer as `unaffected` and whose `## Affected Artifacts` table is empty. This keeps the consumer's contract simple: `updates.md` always exists after a successful run. The writer does **not** run when the workflow hard-fails at Step 1 (aggregate-root lifecycle / stereotype change / degraded baseline) — there is no transition to describe; the operator gets only the `ERROR:` line.

A subtle case: a run that aborts *some* consumers at Step 2 but updates *others* at Step 4 is **not** a hard-fail — the writer runs, the report lists the aborted consumers with `aborted` status (and the reconcile instructions) and the updated ones with `updated` status. The terminal operator one-liner (Step 6) summarizes counts.

---

## File location and naming

```
<dir>/<stem>.messaging/
├── <consumer-1>.md            (consumer-1 input spec)
├── <consumer-2>.md            (consumer-2 input spec)
├── …
└── updates.md                 (this report — one per aggregate, covering all consumers)
```

Mirrors the domain, persistence, and application conventions: a single `updates.md` sits in the plugin's sibling folder. Per `messaging-spec:naming-conventions`, this file is added to the `<stem>.messaging/` folder catalog as a new durable artifact alongside the per-consumer `<consumer-name>.md` specs. (The naming-conventions skill currently lists only `<consumer-name>.md` for that folder — add `updates.md` there first.)

One report per aggregate, not per consumer — even though the specs are per-consumer. The consumer-keyed `## Consumer Changes` section carries the per-consumer breakdown.

---

## Report schema

Top-level structure (canonical section order):

```markdown
<!-- domain-updates-hash:<sha256> -->

# Messaging Updates Report

## Summary
## Consumer Changes
## Affected Artifacts
```

Each section's body follows fixed conventions; `## Consumer Changes` always lists every discovered consumer (no consumer disappears — an unaffected one renders with `unaffected` status and a `_no changes_` body), and `## Affected Artifacts` is empty (just the header row) when no consumer was `updated`.

The `<!-- domain-updates-hash:<sha256> -->` sentinel at the top records the content hash of `<stem>.domain/updates.md` at production time. The future code updater uses it for skip-on-replay detection: re-applying an already-applied report is a no-op (informational, not enforced — the code updater also has its own per-artifact idempotency).

### Section: Summary

```markdown
## Summary

- Messaging folder: `<dir>/<stem>.messaging/`
- Commands diagram: `<dir>/<stem>.commands.md`
- Domain updates source: `<dir>/<stem>.domain/updates.md` (hash: <sha256>)
- Generated at: 2026-05-11T10:14:33Z
- Consumers discovered: 3
- Consumers updated: 1
- Consumers aborted (reconcile commands diagram): 1
- Consumers unaffected: 1
- Warnings:
  - `shipping_events` subscribes to internal event `OrderShipped`, which is no longer emitted by `Order` (dead subscription — byte-stable spec)
```

The four count lines (`discovered`, `updated`, `aborted`, `unaffected`) always sum: `updated + aborted + unaffected = discovered`. (A consumer is never both updated and aborted: if any of its `internal` subscriptions is dangling, the whole consumer is aborted-and-skipped for this run; its other subscriptions wait for the next run after the operator reconciles the commands diagram.)

### Section: Consumer Changes

One H3 block per discovered consumer, alphabetical by consumer name, headed by the consumer name + a status keyword.

```markdown
## Consumer Changes

### `profile_reconciliation` — updated

- Spec: `dir/order.messaging/profile_reconciliation.md`
- Pre-update hash: a1b2c3…
- Post-update hash: d4e5f6…
- Table 3 sub-blocks regenerated:
  - `**Event:** ProfileSubmitted` (internal · source `Profiles`)
    - Source delta: `domain-events: ProfileSubmitted attribute middle_name added`
    - Event Field mappings changed: row `middle_name` ↦ `middle_name` added (handler `on_profile_submitted` consumes it)
    - Low-confidence flags: _none_
  - `**Event:** ProfileArchived` (internal · source `Profiles`)
    - Source delta: `domain-events: ProfileArchived attribute archived_by removed`
    - Event Field mappings changed: row `archived_by` ↦ `archived_by` removed
    - Low-confidence flags: `**Event:** ProfileArchived` flagged — handler param `archived_by` no longer resolves to an event attribute; best-guess emitted in italic prose

### `shipping_events` — aborted (reconcile commands diagram)

- Spec: `dir/order.messaging/shipping_events.md` (unchanged this run)
- Dangling internal event(s): `OrderShipped` (removed or renamed in `dir/order.domain/updates.md`)
- Required reconcile:
  - Edit the `%% Messaging - shipping_events` block in `dir/order.commands.md`: drop or rename the `OrderCommands --() OrderShipped : handles (Order, on_order_shipped)` line, and the `on_order_shipped` handler on `OrderCommands`.
  - Then re-run `event-tables-writer dir/order.commands.md shipping_events` and `event-fields-writer dir/order.commands.md shipping_events` (or `/messaging-spec:generate-code dir/order.md shipping_events`).

### `audit_log` — unaffected

_No internal subscription intersects the changed-domain-event set._
```

Conventions:

The status vocabulary grew from the original three-status set `{updated, aborted, unaffected}` to a **five-status set** `{updated, aborted, unaffected, needs-init, orphaned}` once the commands-diagram axis (`<stem>.application/commands-updates.md`) joined the writer's inputs — see [`messaging-updates-writer-commands-axis.md`](messaging-updates-writer-commands-axis.md) for the design of the two new advisory statuses. The precedence ladder is `orphaned → aborted → needs-init → updated → unaffected` (first match wins). `needs-init` and `orphaned` are advisory — they describe a *state mismatch* between the commands diagram and the on-disk spec set, not a transition of a single file, and contribute zero rows to `## Affected Artifacts` (they surface in a new `## Operator Actions` H2 between `## Consumer Changes` and `## Affected Artifacts`).

- **`updated`** — Table 3 was regenerated. `Pre-update hash` ≠ `Post-update hash`. Lists each regenerated sub-block (most often an `internal` event — the domain axis never touches `external` rows; under the commands-diagram axis an `external` row's source event attributes may also drive an `external` sub-block regen), each with: the axis-tagged delta phrase (`Source delta: [<axis>] <category>: <human_phrase>` — `[domain]` for domain `<stem>.domain/updates.md` matches, `[commands-diagram]` for `<stem>.application/commands-updates.md` matches), the row-level mapping changes in Table 3's `Event Field` column (added/removed/relocated rows), and any low-confidence flag `event-fields-writer` (re-)emitted in italic prose around that sub-block. Mixed-axis attribution within one consumer is expected (sub-blocks may carry different `[<axis>]` tags). If Step 4 also refreshed Table 2 (the optional `event-tables-writer` re-run), add a line `- Table 2 refreshed: <reason>` — on a pure domain-axis change Table 2 is byte-stable and the bullet is absent; on a commands-axis edit the bullet carries the row delta (`added: <rows>; removed: <rows>; changed: <rows>`).
- **`aborted`** — the consumer subscribes (as `internal`) to a domain event that was removed or renamed; the consumer spec is **unchanged this run** (`Pre-update hash` == `Post-update hash`, omitted for brevity). Lists the dangling event(s) and the exact reconcile instructions (matching `spec-updater-approach.md` § Step 2). The code updater treats `aborted` consumers as no-ops — there is nothing to regenerate until the operator reconciles and re-runs. When the commands diagram already reconciled the dangling row (the `%% Messaging - <C>` block dropped the row in the same operator edit), the consumer drops out of `aborted` and may surface as `orphaned` or `updated` instead.
- **`unaffected`** — no `internal` Table 2 row names a changed domain event. Body is the single italic line `_No internal subscription intersects the changed-domain-event set._` (or the precise form naming the byte-stable-affected event(s) when applicable).
- **`needs-init`** *(advisory)* — the commands diagram declares a `%% Messaging - <C>` block (X1) but no consumer spec exists on disk. The body lists `Spec: _not yet created_`, the commands diagram declaration, the subscriptions declared in the commands-updates report's `Row added` lines for the consumer, and a single `Operator action:` directing the operator to `/messaging-spec:generate-code <domain_diagram> <C>`.
- **`orphaned`** *(advisory)* — a consumer spec exists on disk but the commands diagram no longer declares its `%% Messaging - <C>` block (X2). The body lists the spec path (with the `(unchanged this run)` suffix), an italic line stating the commands diagram no longer declares it, the stale subscriptions read from the on-disk Table 2, and a two-sub-bullet `Operator action:` directing the operator to decide preserve-vs-delete and then run `/messaging-spec:generate-code <domain_diagram>` (without a consumer arg) to reconcile the code side.

### Section: Affected Artifacts

A flat dispatch table. The code updater walks this footer top-to-bottom. Only `updated` consumers contribute rows.

```markdown
## Affected Artifacts

| Path | Action | Driving consumer |
|---|---|---|
| `messaging/profile_reconciliation/handlers.py` | modify | `profile_reconciliation` |
| `tests/integration/messaging/profile_reconciliation/test_profile_reconciliation_handlers.py` | modify | `profile_reconciliation` |
```

Action vocabulary is closed: `add`, `modify`, `remove`. On the domain axis only `modify` ever appears (an internal-event attribute change re-renders an existing handler's call kwargs and that handler's test; it never adds or removes a handler — handler add/remove is a Table 2 / commands-diagram concern). When no consumer is `updated`, the table is the header row only.

This footer is the messaging analog of the persistence/application `## Affected Artifacts` footers and the domain `## Affected Categories` footer: a flat, machine-parseable dispatch list.

---

## Per-consumer-change → code-action mapping

Quick-reference matrix the future code updater dispatches against:

| Report content | Drives | Action verbs |
|---|---|---|
| `updated` consumer `C`, a regenerated internal-event sub-block (rows added/removed/relocated) | Re-render the `on_<event>` call kwargs in `messaging/<C_snake>/handlers.py` for that event's handler; re-render the event-body kwargs in `tests/integration/messaging/<C_snake>/test_<C_snake>_handlers.py` for that handler's test | modify |
| `updated` consumer `C`, a sub-block flagged low-confidence | Same as above, **plus** surface the italic flag to the operator (the best-guess kwargs may be wrong until the commands diagram's `on_<event>` signature is reconciled) | modify + warning |
| `aborted` consumer `C` | _no action_ — wait for the operator to reconcile `<stem>.commands.md` and re-run | — |
| `unaffected` consumer `C` | _no action_ | — |

The code updater dispatches on `(consumer, status)`; for `updated` it walks the regenerated sub-blocks and edits exactly the named handler + its test. It does **not** regenerate the whole submodule — `dispatcher.py`, `events.py`, the constants, and the wiring are byte-stable on the domain axis.

---

## Worked example

Domain change: add `middle_name: str` to the `ProfileSubmitted` domain event and remove `archived_by: str` from the `ProfileArchived` domain event. Both events are subscribed by the `profile_reconciliation` consumer as `internal`; the `shipping_events` consumer subscribes to `OrderShipped` (unchanged) and `audit_log` subscribes to no internal events.

Domain `updates.md` Affected Categories: `[domain-events]`.

Messaging updater: Step 1 clean; Step 2 finds no dangling events (nothing removed/renamed); Step 3 finds `profile_reconciliation` affected (`ProfileSubmitted`, `ProfileArchived` both in its `internal` set); Step 4 re-runs `event-fields-writer dir/order.commands.md profile_reconciliation`, regenerating its Table 3; Step 5 invokes `messaging-updates-writer`, which produces:

```markdown
<!-- domain-updates-hash: 7890ab… -->

# Messaging Updates Report

## Summary

- Messaging folder: `dir/order.messaging/`
- Commands diagram: `dir/order.commands.md`
- Domain updates source: `dir/order.domain/updates.md` (hash: 7890ab…)
- Generated at: 2026-05-11T10:14:33Z
- Consumers discovered: 3
- Consumers updated: 1
- Consumers aborted (reconcile commands diagram): 0
- Consumers unaffected: 2
- Warnings: _none_

## Consumer Changes

### `audit_log` — unaffected

_No internal subscription intersects the changed-domain-event set._

### `profile_reconciliation` — updated

- Spec: `dir/order.messaging/profile_reconciliation.md`
- Pre-update hash: a1b2c3…
- Post-update hash: d4e5f6…
- Table 3 sub-blocks regenerated:
  - `**Event:** ProfileArchived` (internal · source `Profiles`)
    - Source delta: `domain-events: ProfileArchived attribute archived_by removed`
    - Event Field mappings changed: row `archived_by` ↦ `archived_by` removed
    - Low-confidence flags: `**Event:** ProfileArchived` flagged — handler param `archived_by` no longer resolves to an event attribute (best-guess emitted in italic prose; reconcile the `on_profile_archived` signature on `ProfileCommands` if the parameter is gone)
  - `**Event:** ProfileSubmitted` (internal · source `Profiles`)
    - Source delta: `domain-events: ProfileSubmitted attribute middle_name added`
    - Event Field mappings changed: row `middle_name` ↦ `middle_name` added (handler `on_profile_submitted` consumes it)
    - Low-confidence flags: _none_

### `shipping_events` — unaffected

_No internal subscription intersects the changed-domain-event set._

## Affected Artifacts

| Path | Action | Driving consumer |
|---|---|---|
| `messaging/profile_reconciliation/handlers.py` | modify | `profile_reconciliation` |
| `tests/integration/messaging/profile_reconciliation/test_profile_reconciliation_handlers.py` | modify | `profile_reconciliation` |
```

Notice:

- `shipping_events` and `audit_log` render as `unaffected` — the writer detected their consumer-spec hashes are byte-stable and they have no `internal` subscription in the changed-domain-event set.
- The `ProfileArchived` sub-block is flagged low-confidence because the removed `archived_by` attribute was the source of an `on_profile_archived` parameter; `event-fields-writer` emits its best guess and flags it — the report surfaces that flag and the reconcile hint, but the run is *not* an abort (the event class still exists; only an attribute went away).
- A future `/messaging-spec:update-code` walks the footer: re-render the `on_profile_submitted` / `on_profile_archived` handler bodies in `handlers.py` and their tests; touch nothing else in the submodule.

---

## Determinism and idempotency

- **Byte-stable inputs → byte-stable report.** Same domain `updates.md` content + same pre-update consumer specs + same post-update consumer specs + same commands diagram → byte-identical report.
- **Re-running `/messaging-spec:update-specs` with no new domain changes** produces a report whose every consumer is `unaffected` and whose `## Affected Artifacts` table is the header row only. The code updater treats it as a no-op.
- **No consumers under `<stem>.messaging/`** → the writer (if invoked) emits a degenerate report: `Consumers discovered: 0`, an empty `## Consumer Changes` section (`_no consumers_`), an empty footer. In practice the orchestrator short-circuits at Step 0 and may skip the writer entirely; if it doesn't, this is the output.
- **Section ordering is canonical** (`## Summary` → `## Consumer Changes` → `## Affected Artifacts`).
- **Consumer ordering** inside `## Consumer Changes` is alphabetical by consumer name, regardless of status — `aborted`, `updated`, and `unaffected` blocks interleave by name (no status grouping).
- **Sub-block ordering** inside an `updated` block follows Table 3's order (external block alphabetical, then internal block alphabetical) — only `internal` sub-blocks ever appear, so in practice it is alphabetical by Event Name.

---

## Cross-aggregate edits

**None.** Unlike persistence (per-context `unit_of_work/` and `query_context/` shared across aggregates) and application (`containers.py` / `tests/conftest.py` / `domain/<aggregate>/exceptions.py` shared), every artifact this report touches is **per-consumer** and lives under that consumer's own `messaging/<consumer>/` submodule (plus its own test module). There is no shared file the domain axis edits — `messaging/__init__.py` (the root aggregator), `constants.py`, `containers.py`, `entrypoint.py`, and `__main__.py` are all byte-stable on an internal-event attribute change (they're touched only by consumer add/remove or dispatcher wiring, which are commands-diagram / `generate-code` concerns). So the code updater needs no idempotent-patcher contract for shared files on this axis.

---

## What the report deliberately does NOT include

- **`external`-event deltas.** External event classes live on `<stem>.commands.md`; no domain change touches them. They are a commands-diagram-axis concern, not in this report.
- **Table 1 / Table 2 deltas.** Table 1 is hand/prefix-derived; Table 2 is a pure function of the commands diagram's `%% Messaging` markers. A domain change never *regenerates* either (it can only leave Table 2 *stale* — which is the `aborted` case, recorded as such, not as a Table 2 delta). If the commands-diagram axis is added later, a Table 2 regen note can be folded into the `updated` block (see *Open questions*).
- **Command-handler-side deltas.** The consumer spec doesn't model the command side beyond Table 1's queue name; domain `<<Command>>` changes ripple into *generated* `command-handlers` / `command-replies` code only, reconciled by `/messaging-spec:generate-code`, not by this updater or report.
- **Code-level diffs or generated source text.** The report says **what** to change (which handler, which event); the code updater owns **how** (re-rendering the call kwargs from Table 3, the test reverse-mapping).
- **Dispatcher / events / constants / wiring artifacts.** Byte-stable on the domain axis — not listed.
- **Hand-edit reconciliation hints.** Hand-edits in generated handler bodies are not preserved (per the spec/code updater contract). The code updater can flag divergence (especially since `event-handlers-implementer` preserves user-implemented handlers byte-identical, so a domain-driven re-render *will* overwrite a hand-edited handler) but the report doesn't pre-classify it — though the low-confidence flags it carries are the closest thing to a reconciliation prompt.
- **Stable-throughput artifacts** in other layers (domain/application/persistence/rest-api) — not messaging concerns.

---

## Hard-fail conditions

The report is not produced (the run hard-fails before reaching the emit step) when:

- The spec updater itself hard-fails at Step 1 (aggregate-root removal / stereotype-demotion / rename, any stereotype change) or at Step 0 (degraded baseline, or missing `<stem>.domain/updates.md`). See [`spec-updater-approach.md`](spec-updater-approach.md) § "Hard-fail conditions". The operator gets only the `ERROR:` line.
- A pre-update consumer spec is unparseable when invoked standalone.
- A post-update consumer-spec hash cannot be computed (filesystem error).

A per-consumer Step-2 abort is **not** a hard-fail — the report is emitted, with the aborted consumer(s) marked `aborted`. In all non-hard-fail cases the report is emitted, even if every consumer is `unaffected`.

---

## Open questions

1. **Per-consumer hash placement.** Current design puts the pre/post hashes inside each consumer's `updated` block (and omits them for `aborted` / `unaffected`). An alternative is a hash table in `## Summary` covering every consumer. The per-block placement keeps the Summary terse and co-locates the hash with the change it pins; the table form is easier to scan when there are many consumers. Lean: per-block, switch to a Summary table only if real specs routinely carry >5 consumers.

2. **Folding a Table 2 regen note when the commands-diagram axis lands.** *(Partially answered.)* Once `/messaging-spec:update-specs` also consumes a commands-diagram delta report, a consumer whose `%% Messaging` markers changed will have its Table 2 regenerated (`event-tables-writer`) *and* possibly its Table 3 (`event-fields-writer`). The `updated` block grew a `- Table 2 refreshed: <added: …; removed: …; changed: …>` line above the `Table 3 sub-blocks regenerated:` list, emitted when the consumer spec's Table 2 differs between HEAD and the working tree. The detection is trivial — diff the Table 2 markdown table between HEAD and working tree — and is implemented by `messaging-updates-writer`. The broader `## Consumer Changes` schema extension that surfaces X1/X2 advisory statuses (`needs-init` / `orphaned`) and the axis-tagged `Source delta` grammar is designed in [`messaging-updates-writer-commands-axis.md`](messaging-updates-writer-commands-axis.md) — that note is the v2 follow-up to the integration-level integration in [`commands-queries-integration-approach.md`](commands-queries-integration-approach.md). What remains open is **structural extension to capture commands-diagram-only changes** beyond Table 2 row deltas — e.g. a `%% v1`/`%% internal` surface marker change that touches *no* `%% Messaging` block; this is currently silent on the messaging axis (correct: messaging consumes only `%% Messaging` markers).

3. **Multi-update batching.** If the operator runs `/messaging-spec:update-specs` N times before catching up with `/messaging-spec:update-code`, do we stack N reports or merge them? Recommended (mirrors persistence/application): each `update-specs` run writes a fresh `updates.md` *replacing* the prior one; if the prior report's `domain-updates-hash` is still present (the code updater hasn't acknowledged it), fold its `## Affected Artifacts` rows into the new report so nothing is dropped. Open: producer's contract vs consumer's.

4. **Concurrent updaters.** Two operators running `/messaging-spec:update-specs` in parallel against the same `<stem>.messaging/` both write `updates.md` — a Git merge conflict on a generated file, same shape as the spec-side concurrent-updater problem. Document as expected; no code support needed.

5. **Dead-subscription warnings vs the abort gate.** A subscribed internal event whose `: emits` edge is removed but whose class survives produces a `Warnings:` line (dead subscription) but does *not* abort the consumer (the class still exists, so `event-fields-writer` can still resolve it). Open whether to escalate this to an `aborted`-like status when the dead subscription is the consumer's *only* internal subscription — arguably the consumer is now pointless. Lean: keep it a warning; the consumer spec is still valid, and the operator may be mid-refactor.

6. **Standalone-recompute of the abort list.** When invoked standalone (not via the orchestrator), the writer recomputes the per-consumer abort list itself from the domain `updates.md` (`removed_or_renamed_events`) ∩ each consumer's Table 2 `internal` rows. This must match what the orchestrator's Step 2 gate computed. Worth a contract note in the agent body that the two derivations are byte-identical (same inputs, same rule).

---

## Relationship to the domain, persistence, and application updates reports

| Aspect | Domain | Persistence | Application | Messaging |
|---|---|---|---|---|
| File path | `<dir>/<stem>.domain/updates.md` | `<dir>/<stem>.persistence/updates.md` | `<dir>/<stem>.application/updates.md` | `<dir>/<stem>.messaging/updates.md` |
| Sibling of | the diagram | the command-repo-spec | the commands/queries specs + services report | the per-consumer input specs |
| Producer | `domain-spec:updates-detector` (standalone agent) | `command-repo-spec-updates-writer` (tail of `/persistence-spec:update-specs`) | `application-updates-writer` (tail of `/application-spec:update-specs`) | `messaging-updates-writer` (tail of `/messaging-spec:update-specs`) |
| Producer detection method | git diff of diagram + prose | git diff of working-tree spec vs HEAD | git diff of three working-tree specs vs HEAD | git diff of each working-tree consumer spec vs HEAD + the orchestrator's abort list |
| Grouping | per-class | per-artifact (tables / mappers / migrations / repository / context-integration) | per-artifact (commands methods / queries methods / exceptions / services) | **per-consumer** (status + regenerated Table 3 sub-blocks) |
| Footer | `## Affected Categories` (DDD categories) | `## Affected Artifacts` (file paths + action verbs) | `## Affected Artifacts` (file paths + action verbs) | `## Affected Artifacts` (file paths + action verbs + driving consumer) |
| Consumed by | spec updaters (domain, persistence, application, messaging) **and** domain code updater | persistence code updater (only) | application code updater (only) | messaging code updater (only) |
| Lifecycle | persistent (committed) | persistent (committed) | persistent (committed) | persistent (committed) |
| First-run | not produced | not produced | not produced | not produced |
| Append-only sub-section | — | `§2.Migrations` row IDs | _none_ | _none_ |
| "Couldn't apply" outcome | n/a | n/a (writer always succeeds post-spec-update) | n/a | **`aborted` consumer status** — domain event removed/renamed leaves the commands-diagram marker dangling; recorded, not silently swallowed |
| Hard-fails preempt emit | yes | yes | yes | yes |

The four reports are **chained**: domain `updates.md` drives the persistence, application, and messaging spec updaters, each of which produces its own layer-specific `updates.md`, which drives that layer's code updater:

```
diagram edit
   │
   ▼
domain-spec:updates-detector
   │
   ▼
<stem>.domain/updates.md ────┬──► /update-specs (domain) ─────────► spec siblings
                             │
                             ├──► /persistence-spec:update-specs ──► command-repo-spec.md  +  <stem>.persistence/updates.md ──► /persistence-spec:update-code ──► tables/, mappers/, migrations/, repos/
                             │
                             ├──► /application-spec:update-specs ──► {commands,queries}.specs.md + services.md  +  <stem>.application/updates.md ──► /application-spec:update-code ──► application/, infrastructure/, exceptions, containers, conftest, tests/
                             │
                             └──► /messaging-spec:update-specs ────► <stem>.messaging/<consumer>.md (Table 3)  +  <stem>.messaging/updates.md ──► /messaging-spec:update-code ──► messaging/<consumer>/handlers.py, handler tests
```

Each layer's report is **independent** of the others — readers needing cross-layer context follow the chain back to the domain `updates.md`. The messaging report is the narrowest: one change body (Table 3 sub-block regen), per-consumer-scoped, no shared-file edits, and an explicit `aborted` outcome for the cases where a domain change orphans a commands-diagram marker the updater can't fix on its own.
